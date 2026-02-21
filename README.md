# 🚛 FleetFlow — Fleet & Logistics Management System

A modular, role-based fleet management system built with **Django 5.2** and **PostgreSQL**. Designed to replace manual logbooks with a clean web interface for managing vehicles, drivers, trips, maintenance, and financials.

---

## ✨ Features

| Module | Capabilities |
|---|---|
| 🔐 **Auth** | Register, Login, Forgot Password (OTP via email), Change Password |
| 🚗 **Fleet** | Vehicle CRUD, status tracking, document uploads, fuel logging |
| 🗺️ **Dispatch** | Driver management, trip lifecycle (Planned → Dispatched → In Transit → Completed) |
| 🔧 **Maintenance** | Maintenance log open/close (atomic), scheduling |
| 💰 **Finance** | Expense recording, invoice management, revenue vs cost reporting |
| 📊 **Analytics** | Live KPI dashboard with 5 Chart.js charts |
| 👥 **Users** | Role-based access control (RBAC), user create/edit/delete |

---

## 🏗️ Tech Stack

- **Backend:** Django 5.2.11, Python 3.11
- **Database:** PostgreSQL (SQLite for local dev)
- **Auth:** Custom `CustomUser` model with email login
- **Email:** SMTP (Gmail) for OTP password reset
- **Charts:** Chart.js 4 (CDN, no npm required)
- **Config:** `python-decouple` for `.env` file management

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd odoo-fleetflow
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example and fill in your values:
```bash
copy .env.example .env    # Windows
cp .env.example .env      # macOS/Linux
```

Edit `.env`:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_NAME=fleetflow_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Email (OTP password reset)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=FleetFlow <your-email@gmail.com>
```

> **Gmail tip:** Use an [App Password](https://myaccount.google.com/apppasswords) if 2-Step Verification is enabled.  
> **Dev tip:** Set `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` to print OTPs to the terminal instead of sending real emails.

### 5. Run migrations and seed demo data
```bash
python manage.py migrate
python manage.py seed_demo   # optional demo data
```

### 6. Start the development server
```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000/**

---

## 👤 Default Roles & Permissions

| Role | Vehicles | Drivers | Trips | Maintenance | Finance | Users |
|---|---|---|---|---|---|---|
| **Manager** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Dispatcher** | 👁️ View | 👁️ View | ✅ Create/Manage | 👁️ View | 👁️ View | ❌ |
| **Safety Officer** | 👁️ View | 👁️ View | 👁️ View | ✅ Open/Close | 👁️ View | ❌ |
| **Financial Analyst** | 👁️ View | 👁️ View | 👁️ View | 👁️ View | ✅ Create/Manage | ❌ |
| **No Role** | 👁️ View | 👁️ View | 👁️ View | 👁️ View | 👁️ View | ❌ |

New self-registered users start without a role. A Manager assigns roles via **Admin → Users**.

---

## 📁 Project Structure

```
odoo-fleetflow/
├── apps/
│   ├── users/          # Auth, RBAC, user management
│   ├── fleet/          # Vehicles, fuel logs, documents
│   ├── dispatch/       # Drivers, trips, assignments
│   ├── maintenance/    # Maintenance logs & scheduling
│   ├── finance/        # Expenses, invoices
│   └── analytics/      # Dashboard, KPIs, charts
├── fleetflow/
│   ├── settings/
│   │   ├── base.py     # Shared settings
│   │   └── dev.py      # Development overrides
│   └── urls.py
├── templates/          # All HTML templates
├── static/             # CSS, JS, images
├── .env                # Environment variables (not committed)
├── requirements.txt
└── manage.py
```

---

## 🔐 OTP Password Reset Flow

1. Go to `/users/forgot-password/` → enter email
2. Receive a **6-digit OTP** (valid for 10 minutes) in your inbox
3. Go to `/users/verify-otp/` → enter the code
4. Go to `/users/set-new-password/` → set a new password
5. Redirected to login ✅

---

## 📊 Analytics Dashboard Charts

| Chart | Type | Data |
|---|---|---|
| Fleet Status Breakdown | Doughnut | Available / On Trip / Maintenance |
| Trip Status Breakdown | Doughnut | Planned / Active / Completed / Cancelled |
| Monthly Trips | Bar | Last 6 months |
| Expense by Category | Horizontal Bar | Fuel / Labour / Insurance / etc. |
| Revenue vs Expenses | Line | Last 6 months (Managers only) |

---

## ⚙️ Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | Django secret key |
| `DEBUG` | `False` | Enable debug mode |
| `DB_NAME` | `fleetflow_db` | PostgreSQL database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres` | Database password |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |
| `EMAIL_BACKEND` | console | Email backend class |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP server |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_USE_TLS` | `True` | Use TLS |
| `EMAIL_HOST_USER` | — | Sender email address |
| `EMAIL_HOST_PASSWORD` | — | SMTP password / App password |
| `DEFAULT_FROM_EMAIL` | — | Display name + address |

---

## 🗄️ Django Admin

Access the admin panel at `/admin/` (superuser only).

Features:
- Create / edit / delete users with role assignment
- Inline activation toggle (`is_active`) on the user list
- View and manage all models across all apps
- Monitor password reset OTPs

Create a superuser:
```bash
python manage.py createsuperuser
```

---

## 📦 Requirements

```
Django==5.2.11
psycopg2-binary==2.9.11
python-decouple==3.8
Pillow==12.1.0
python-dateutil==2.9.0.post0
```

---

## 📝 License

This project is for internal/educational use. Replace with your preferred license.
