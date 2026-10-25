from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timezone

from models import AdminUser, utcnow

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            # Check if request is an AJAX/API call
            if request.is_json or request.path.startswith("/api/admin"):
                return jsonify({"success": False, "error": "Unauthorized. Please log in as administrator."}), 401
            flash("Please log in to access the administrator panel.", "warning")
            return redirect(url_for("admin_login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

class AuthService:
    @staticmethod
    def authenticate(username: str, password: str):
        from db import Session
        db_session = Session()
        try:
            user = db_session.query(AdminUser).filter_by(username=username.strip()).first()
            if not user:
                return None, "Invalid username or password."
            
            if not check_password_hash(user.password_hash, password):
                return None, "Invalid username or password."
            
            # Record last login
            user.last_login = utcnow()
            db_session.commit()
            return user.to_dict(), None
        finally:
            db_session.close()

    @staticmethod
    def change_password(user_id: int, current_pwd: str, new_pwd: str):
        from db import Session
        db_session = Session()
        try:
            user = db_session.query(AdminUser).filter_by(id=user_id).first()
            if not user:
                return False, "User not found."
            
            if not check_password_hash(user.password_hash, current_pwd):
                return False, "Current password is incorrect."
            
            if len(new_pwd) < 6:
                return False, "New password must be at least 6 characters long."
            
            user.password_hash = generate_password_hash(new_pwd, method="scrypt")
            db_session.commit()
            return True, "Password updated successfully."
        finally:
            db_session.close()
