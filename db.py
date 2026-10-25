from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from werkzeug.security import generate_password_hash

from config import Config
from models import Base, Service, AdminUser, SystemSetting

# Setup engine with optimal connection arguments
engine_kwargs = {"echo": False}
if Config.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 15}

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, **engine_kwargs)

# Enable SQLite foreign keys and WAL mode for reliable concurrency and persistence
if Config.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=10000")
        finally:
            cursor.close()

session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Session = scoped_session(session_factory)

def get_db():
    """Context manager or session getter for requests"""
    return Session()

def init_db():
    """Create tables and seed initial services, settings, and admin user"""
    Base.metadata.create_all(bind=engine)
    session = Session()
    try:
        # Seed default college services if table is empty
        if session.query(Service).count() == 0:
            default_services = [
                Service(
                    name="College Administration Office",
                    code="admin-office",
                    prefix="ADM",
                    counter_number="Counter 1",
                    description="Admissions, bonafide certificates, transfer certificates, transcript requests & ID verification.",
                    icon="building",
                    avg_service_time_mins=8,
                    is_active=True,
                ),
                Service(
                    name="Fee Payment & Accounts",
                    code="fee-payment",
                    prefix="FEE",
                    counter_number="Counter 2",
                    description="Semester tuition fees, examination challans, receipt validation & scholarship clearance.",
                    icon="credit-card",
                    avg_service_time_mins=5,
                    is_active=True,
                ),
                Service(
                    name="Student Support & Counselling",
                    code="student-support",
                    prefix="SUP",
                    counter_number="Counter 3",
                    description="Course registration, timetable conflicts, student welfare, hostel desk & exam queries.",
                    icon="users",
                    avg_service_time_mins=7,
                    is_active=True,
                ),
                Service(
                    name="General Service & Inquiries",
                    code="general-service",
                    prefix="GEN",
                    counter_number="Counter 4",
                    description="Campus navigation, lost and found, general visitor queries & library pass services.",
                    icon="info-circle",
                    avg_service_time_mins=4,
                    is_active=True,
                ),
            ]
            session.add_all(default_services)
            session.commit()
            print("[DB] Initialized default college services.")

        # Seed default admin user if not exists
        admin = session.query(AdminUser).filter_by(username=Config.DEFAULT_ADMIN_USERNAME).first()
        if not admin:
            hashed = generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD, method="scrypt")
            admin = AdminUser(
                username=Config.DEFAULT_ADMIN_USERNAME,
                password_hash=hashed,
                full_name=Config.DEFAULT_ADMIN_NAME,
                role="admin",
            )
            session.add(admin)
            session.commit()
            print(f"[DB] Initialized default admin account: {Config.DEFAULT_ADMIN_USERNAME}")

        # Seed system settings
        default_settings = [
            ("approaching_threshold", str(Config.DEFAULT_APPROACHING_THRESHOLD), "Number of waiting positions before turn is approaching"),
            ("org_name", "National Institute of Science & Technology", "Institution or organization name"),
            ("sound_alert", "true", "Enable audio chime alerts for called visitors"),
            ("allow_browser_notifications", "true", "Allow web push / desktop notifications"),
        ]
        for key, val, desc in default_settings:
            existing = session.query(SystemSetting).filter_by(key=key).first()
            if not existing:
                session.add(SystemSetting(key=key, value=val, description=desc))
        session.commit()

    except Exception as e:
        session.rollback()
        print(f"[DB] Error initializing database: {e}")
        raise e
    finally:
        session.close()
