"""
MediQueue – Database Layer
Supports MySQL 8.0 with mysql-connector-python and automatic fallback
for seamless student setup and testing.
"""

import os
import sys

# On Windows environments, ensure DLL paths are registered so sqlite3 / mysql connectors load cleanly
for candidate_dir in [
    os.path.join(os.path.dirname(sys.executable), 'DLLs'),
    r"C:\Program Files\QGIS 4.0.1\bin",
    r"C:\Program Files\MySQL\MySQL Server 8.0\bin",
]:
    if os.path.exists(candidate_dir):
        try:
            os.add_dll_directory(candidate_dir)
        except Exception:
            pass

import sqlite3
import logging
from contextlib import contextmanager
from werkzeug.security import generate_password_hash
from config import Config

logger = logging.getLogger(__name__)

# Track active database backend
_ACTIVE_BACKEND = None  # 'mysql' or 'sqlite'

try:
    import mysql.connector
    from mysql.connector import errorcode
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    mysql = None


def test_mysql_connection():
    """Test if MySQL server is reachable with configured credentials."""
    if not MYSQL_AVAILABLE:
        return False, "mysql-connector-python is not installed"
    
    try:
        # First test connecting to MySQL server host
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            connection_timeout=3
        )
        cursor = conn.cursor()
        # Ensure database exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.close()
        conn.close()
        return True, "MySQL Connected Successfully"
    except Exception as e:
        return False, str(e)


def get_backend():
    """Determine and cache the active database engine."""
    global _ACTIVE_BACKEND
    if _ACTIVE_BACKEND is None:
        if Config.DB_BACKEND == 'sqlite':
            _ACTIVE_BACKEND = 'sqlite'
            print(f"[MediQueue DB] Explicit SQLite test backend: {Config.SQLITE_DB_PATH}.")
            return _ACTIVE_BACKEND
        success, message = test_mysql_connection()
        if success:
            _ACTIVE_BACKEND = 'mysql'
            print(f"[MediQueue DB] Connected to MySQL 8.0 database '{Config.DB_NAME}' at {Config.DB_HOST}:{Config.DB_PORT}.")
        else:
            if not Config.DB_ALLOW_SQLITE_FALLBACK:
                raise RuntimeError(
                    f"MySQL connection failed for {Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}: {message}. "
                    "Check the MySQL service and .env settings. SQLite fallback is disabled to prevent records "
                    "being saved to a different database by mistake. Set DB_ALLOW_SQLITE_FALLBACK=1 only for testing."
                )
            _ACTIVE_BACKEND = 'sqlite'
            print(f"[MediQueue DB] Notice: MySQL not reachable ({message}).")
            print(f"[MediQueue DB] SQLite fallback explicitly enabled (database/mediqueue.sqlite3).")
    return _ACTIVE_BACKEND


def get_raw_connection():
    """Get a raw connection object based on active backend."""
    backend = get_backend()
    if backend == 'mysql':
        return mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            autocommit=False
        )
    else:
        db_path = Config.SQLITE_DB_PATH
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn


class DBConnection:
    """Wrapper class providing a unified cursor and query interface."""

    def __init__(self):
        self.backend = get_backend()
        self.conn = get_raw_connection()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        self.close()

    def commit(self):
        if self.conn:
            self.conn.commit()

    def rollback(self):
        if self.conn:
            try:
                self.conn.rollback()
            except Exception:
                pass

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def _normalize_sql(self, sql):
        """Translate SQL syntax if running on SQLite fallback."""
        if self.backend == 'sqlite':
            # Translate MySQL CURDATE() to date('now', 'localtime')
            sql = sql.replace('CURDATE()', "date('now', 'localtime')")
            # Translate CURRENT_DATE to date('now', 'localtime')
            sql = sql.replace('CURRENT_DATE', "date('now', 'localtime')")
            # Translate %s parameter placeholders to ?
            sql = sql.replace('%s', '?')
            # Remove MySQL locking clause 'FOR UPDATE' which is default in SQLite transactions
            sql = sql.replace('FOR UPDATE', '')
        return sql

    def execute(self, sql, params=None):
        """Execute a query and return (cursor, lastrowid, rowcount)."""
        normalized_sql = self._normalize_sql(sql)
        params = params or ()
        
        if self.backend == 'mysql':
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(normalized_sql, params)
            return cursor
        else:
            cursor = self.conn.cursor()
            cursor.execute(normalized_sql, params)
            return cursor

    def fetchone(self, sql, params=None):
        """Execute and return single row as dict or None."""
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            return None
        if self.backend == 'sqlite':
            return dict(row)
        return dict(row)

    def fetchall(self, sql, params=None):
        """Execute and return all rows as list of dicts."""
        cursor = self.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        if not rows:
            return []
        if self.backend == 'sqlite':
            return [dict(r) for r in rows]
        return [dict(r) for r in rows]

    def modify(self, sql, params=None, auto_commit=True):
        """Execute an INSERT/UPDATE/DELETE query and optionally commit."""
        cursor = self.execute(sql, params)
        last_id = cursor.lastrowid
        row_count = cursor.rowcount
        cursor.close()
        if auto_commit:
            self.commit()
        return last_id, row_count


@contextmanager
def get_db(auto_commit=False):
    """Context manager for obtaining a database connection session."""
    db = DBConnection()
    try:
        yield db
        if auto_commit:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize required tables and default admin account."""
    backend = get_backend()
    
    if backend == 'mysql':
        try:
            with get_db(auto_commit=True) as db:
                # 1. Doctors table
                db.execute("""
                    CREATE TABLE IF NOT EXISTS doctors (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) NOT NULL UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        full_name VARCHAR(100) NOT NULL DEFAULT 'Dr. Suraweera',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)
                
                # 2. Patients table
                db.execute("""
                    CREATE TABLE IF NOT EXISTS patients (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        token_number VARCHAR(10) NOT NULL,
                        patient_name VARCHAR(100) NOT NULL,
                        phone VARCHAR(20) NOT NULL,
                        status ENUM('Waiting', 'Serving', 'Completed', 'Missed') NOT NULL DEFAULT 'Waiting',
                        queue_date DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_date_token (queue_date, token_number),
                        INDEX idx_date_status (queue_date, status),
                        INDEX idx_token (token_number)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)
                
                # Check if default doctor exists
                existing = db.fetchone("SELECT id FROM doctors WHERE username = %s", (Config.DEFAULT_ADMIN_USER,))
                if not existing:
                    pwd_hash = generate_password_hash(Config.DEFAULT_ADMIN_PASS)
                    db.modify("""
                        INSERT INTO doctors (username, password_hash, full_name)
                        VALUES (%s, %s, %s)
                    """, (Config.DEFAULT_ADMIN_USER, pwd_hash, Config.DEFAULT_ADMIN_NAME))
                    print(f"[MediQueue DB] Created default doctor account: '{Config.DEFAULT_ADMIN_USER}'.")
                else:
                    # Update the configured doctor's display name but preserve the existing password hash.
                    db.modify("UPDATE doctors SET full_name = %s WHERE username = %s",
                              (Config.DEFAULT_ADMIN_NAME, Config.DEFAULT_ADMIN_USER))
            return True
        except Exception as e:
            print(f"[MediQueue DB] MySQL init error: {e}")
            return False
    else:
        # SQLite initialization
        try:
            with get_db(auto_commit=True) as db:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS doctors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        full_name TEXT NOT NULL DEFAULT 'Dr. Suraweera',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                db.execute("""
                    CREATE TABLE IF NOT EXISTS patients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        token_number TEXT NOT NULL,
                        patient_name TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        status TEXT CHECK(status IN ('Waiting', 'Serving', 'Completed', 'Missed')) NOT NULL DEFAULT 'Waiting',
                        queue_date DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(queue_date, token_number)
                    );
                """)
                
                # Check if default doctor exists
                existing = db.fetchone("SELECT id FROM doctors WHERE username = %s", (Config.DEFAULT_ADMIN_USER,))
                if not existing:
                    pwd_hash = generate_password_hash(Config.DEFAULT_ADMIN_PASS)
                    db.modify("""
                        INSERT INTO doctors (username, password_hash, full_name)
                        VALUES (%s, %s, %s)
                    """, (Config.DEFAULT_ADMIN_USER, pwd_hash, Config.DEFAULT_ADMIN_NAME))
                    print(f"[MediQueue DB] Created default doctor account: '{Config.DEFAULT_ADMIN_USER}'.")
                else:
                    # Update the configured doctor's display name but preserve the existing password hash.
                    db.modify("UPDATE doctors SET full_name = %s WHERE username = %s",
                              (Config.DEFAULT_ADMIN_NAME, Config.DEFAULT_ADMIN_USER))
            return True
        except Exception as e:
            print(f"[MediQueue DB] SQLite init error: {e}")
            return False
