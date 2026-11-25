-- =======================================================
-- MediQueue – Digital Patient Queue Management System
-- Database Schema for MySQL 8.0
-- =======================================================

-- Create Database if not exists
CREATE DATABASE IF NOT EXISTS mediqueue_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE mediqueue_db;

-- -------------------------------------------------------
-- 1. Doctors Table
-- Holds doctor login credentials and profile information
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL DEFAULT 'Dr. Suraweera',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------
-- 2. Patients Table
-- Holds daily queue entries, tokens, and patient details
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token_number VARCHAR(10) NOT NULL,
    patient_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    status ENUM('Waiting', 'Serving', 'Completed', 'Missed') NOT NULL DEFAULT 'Waiting',
    queue_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints & Indexes
    -- Enforce unique token per date (e.g. MQ-001 is unique for 2026-11-12)
    UNIQUE KEY uq_date_token (queue_date, token_number),
    
    -- Index for rapid queue retrieval by date and status
    INDEX idx_date_status (queue_date, status),
    
    -- Index for rapid lookup by token number
    INDEX idx_token (token_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------
-- Default Admin Account (Optional SQL seed)
-- Username: doctor
-- Password: Doctor@123 (hashed using Werkzeug scrypt/pbkdf2)
-- Note: create_admin.py dynamically creates/updates this with your custom secret
-- -------------------------------------------------------
INSERT INTO doctors (username, password_hash, full_name)
VALUES (
    'doctor',
    'scrypt:32768:8:1$5qZ0lG8kS1Z8$8131d9b3fe1c5e63be78d4617415494d45c110996bcff2473489feeafe48a0429a3962d2906b3a0a38b29ffbe7a13df1d2f707fca6a18aa3aa2785d1e4c3c2f0',
    'Dr. Suraweera'
)
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name);
