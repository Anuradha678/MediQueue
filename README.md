# MediQueue – Digital Patient Queue Management System

A modern, full-stack, responsive web application for managing patient queues in a single-doctor medical clinic. Built with Python, Flask, MySQL 8.0, HTML5, CSS3, and Vanilla JavaScript.

---

## 🏥 About the System

MediQueue is specifically tailored for an individual doctor's medical practice (**Dr. Suraweera**). Unlike complex hospital enterprise systems, MediQueue provides a lean, transparent, and dignified queuing experience:

1. **Patients** register digitally in seconds, receive an instant sequential daily token (e.g. `MQ-001`, `MQ-002`), and track their queue position live from their smartphones.
2. **The Doctor** manages consultations via an authenticated single-doctor dashboard with real-time statistics, one-click patient calling, consultation completion, and missed patient handling.

---

## 🚀 Technology Stack

- **Backend**: Python 3.12+, Flask 3.0+
- **Database**: MySQL 8.0 (with `mysql-connector-python` and transaction safety)
- **Frontend**: Semantic HTML5, Modern CSS3 (Variables, Flexbox/Grid, Glassmorphism), Vanilla JavaScript (Fetch API, DOM manipulation)
- **Security**: Werkzeug password hashing (scrypt/pbkdf2), Flask secure HTTP-only sessions, prepared SQL statements
- **Configuration**: `python-dotenv` environment variables

---

## 📁 Project Structure

```text
MediQueue/
│
├── app.py                      # Main Flask application entry point
├── config.py                   # Centralized configuration & clinic settings
├── database.py                 # Resilient database connection layer (MySQL 8.0)
├── requirements.txt            # Python package dependencies
├── .env.example                # Example environment variable template
├── .env                        # Active environment configuration
├── .gitignore                  # Git ignore rules
├── README.md                   # Complete documentation & guide
├── python.bat                  # Convenient Windows wrapper for venv execution
├── test_app.py                 # Automated unit and integration test suite
│
├── frontend/
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── index.html          # Public landing & hero page
│   │   ├── patient.html        # Patient registration form & token confirmation slip
│   │   ├── login.html          # Doctor authentication portal
│   │   ├── staff.html          # Doctor queue dashboard (protected)
│   │   ├── track_queue.html    # Patient real-time queue tracker (auto-refresh)
│   │   ├── about.html          # About Dr. Suraweera & clinic philosophy
│   │   ├── contact.html        # Clinic contact info, emergency guide & inquiries
│   │   └── 404.html            # Custom styled 404 error page
│   │
│   └── static/
│       ├── css/
│       │   └── style.css       # Unified medical theme stylesheet (#16A085 & #16324F)
│       │
│       ├── js/
│       │   ├── main.js         # Mobile navbar, global toasts, home queue snapshot
│       │   ├── patient.js      # Patient input validation & token generation
│       │   ├── login.js        # Doctor authentication & password visibility toggle
│       │   ├── dashboard.js    # Live dashboard data, Next/Complete/Missed actions
│       │   └── queue.js        # 3-second live queue polling & turn notifications
│       │
│       └── images/
│           ├── logo.svg        # Medical brand logo vector
│           └── clinic-badge.svg
│
├── backend/
│   ├── __init__.py             # Backend package initialization
│   ├── auth.py                 # Doctor authentication, login/logout, session decorator
│   ├── patients.py             # Patient registration & transactional token issuing
│   ├── queue.py                # Public queue status & privacy-safe token lookup
│   └── dashboard.py            # Real-time dashboard stats & queue state transitions
│
└── database/
    ├── mediqueue.sql           # Complete MySQL 8.0 schema & seed data
    └── create_admin.py         # Script to provision or update doctor credentials
```

---

## ⚙️ Installation & Setup Guide

### 1. Prerequisites
- **Python 3.10+** (Python 3.12 recommended)
- **MySQL 8.0 Server** (MySQL Community Server or MySQL Workbench)
- **Git** (optional)

### 2. Create Virtual Environment & Install Dependencies
Open your terminal inside the `MediQueue` project folder:

```bash
# 1. Create a Python virtual environment
python -m venv .venv

# 2. Activate the virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.\.venv\Scripts\activate.bat
# On macOS / Linux:
source .venv/bin/activate

# 3. Install required Python packages
pip install -r requirements.txt
```

### 3. Database Configuration (MySQL 8.0)

1. Open your MySQL client (Command Line, MySQL Workbench, or MySQL Shell) and execute the schema:
   ```bash
   mysql -u root -p < database/mediqueue.sql
   ```
   Or run the queries inside `database/mediqueue.sql` directly inside MySQL Workbench.

2. Verify or update your database credentials in `.env`:
   ```env
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_mysql_password_here
   DB_NAME=mediqueue_db
   ```

3. Initialize the Doctor Account:
   Run the provisioning script to set up Dr. Suraweera's login:
   ```bash
   python database/create_admin.py
   ```

> **Important database safety**: MySQL is the default and only database backend. SQLite fallback is disabled by default so registrations cannot silently go into a different database. Only enable `DB_ALLOW_SQLITE_FALLBACK=1` in `.env` for isolated testing; do not use it for normal clinic operation.

---

## 🏃 Running the Application

Launch the Flask development server:

```bash
python app.py
```

The application will start on:
👉 **http://127.0.0.1:5000**

---

## 🔑 Default Doctor Credentials

- **Doctor Portal URL**: `http://127.0.0.1:5000/login`
- **Username**: `doctor`
- **Password**: `Doctor@123`
- **Physician**: `Dr. Suraweera`

*(You can customize or change these credentials anytime by running `python database/create_admin.py --username admin --password MyCustomPassword`)*

---

## 🧪 Running Automated Tests

Run the automated test suite. It creates a separate temporary SQLite database and does not delete or modify your real MySQL patient records:

```bash
python test_app.py
```

---

## 📋 Queue Management Business Rules

1. **Daily Reset & Numbering**: Tokens start fresh from `MQ-001` each day (`queue_date = CURDATE()`).
2. **Single Serving Constraint**: Exactly **one** patient can hold `Serving` status at any given time.
3. **Next Patient Transition**:
   - The currently `Serving` patient is marked `Completed`.
   - The earliest patient in `Waiting` status for today is retrieved and marked `Serving`.
   - If no waiting patients remain, the dashboard notifies the doctor with `"No Waiting Patients"`.
4. **Mark as Missed**:
   - If a patient is absent when called, the doctor can mark them as `Missed`.
   - Missed patients are excluded from automatic `Next Patient` selection.
   - The doctor can choose to `Re-queue` them if they arrive late.
5. **Patient Privacy**:
   - The public queue tracker at `/track-queue` requires a valid token number.
   - It only exposes the patient's own token, queue position, patients ahead, and current serving token.
   - Phone numbers and other personal information of other patients are **never** exposed.

---

## 🎨 Creative UI/UX Theme

- **Medical Green (`#16A085`)**: Primary action buttons, active badges, progress indicators.
- **Dark Navy (`#16324F`)**: Headers, brand logo, strong typography, deep contrast.
- **Light Grey (`#F5F8FA`)**: Clean, clinical, modern background that is easy on the eyes.
- **Card-based layout**: Subtle elevations (`0 4px 14px rgba(22, 50, 79, 0.07)`), smooth hover animations, and responsive mobile drawers.
