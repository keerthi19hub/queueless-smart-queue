import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "queueless-secure-dev-key-2026-college-demo")
    
    # Database config: default to persistent SQLite file in project dir or custom path
    # If DATABASE_URL is set (e.g., PostgreSQL on Render/Heroku/Railway/Supabase), use it
    db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'queueless.db'}")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    # Application Defaults
    DEFAULT_APPROACHING_THRESHOLD = 2  # When people ahead <= 2, turn is approaching
    DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "QueueLessAdmin2026!")
    DEFAULT_ADMIN_NAME = "System Administrator"
    
    # Polling intervals (in seconds for client hints)
    POLL_INTERVAL_VISITOR = 3
    POLL_INTERVAL_DISPLAY = 4
    POLL_INTERVAL_ADMIN = 5
