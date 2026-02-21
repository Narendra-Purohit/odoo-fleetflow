"""FleetFlow – Development settings."""
from pathlib import Path
from decouple import config
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# ── Use SQLite locally so no PostgreSQL install is needed ──────────────────────
# To switch back to PostgreSQL, comment out this block and ensure PostgreSQL
# is running with the credentials in your .env file.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ── Email Configuration ────────────────────────────────────────────────────────
# In development: emails print to the console (no SMTP needed).
# In production: set EMAIL_BACKEND to smtp and fill in SMTP_* values in .env
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="FleetFlow <noreply@fleetflow.com>")
