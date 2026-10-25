import os
import uuid
from datetime import datetime, timezone
from flask import (
    Flask, render_template, request, redirect, url_for,
    jsonify, session, flash, abort
)

from config import Config
from db import init_db, Session
from models import Service, Token, AdminUser, SystemSetting, utcnow
from services.queue_service import QueueService
from auth import login_required, AuthService

app = Flask(__name__)
app.config.from_object(Config)

# Ensure database tables exist and are seeded
with app.app_context():
    init_db()

@app.teardown_appcontext
def shutdown_session(exception=None):
    Session.remove()

# Context processor for templates
@app.context_processor
def inject_global_data():
    return {
        "current_year": datetime.now().year,
        "org_name": "QueueLess Campus Portal",
        "is_admin": session.get("admin_logged_in", False),
        "admin_user": session.get("admin_username", "")
    }

# -------------------------------------------------------------
# Visitor Routes (Pages)
# -------------------------------------------------------------

@app.route("/")
def index():
    """Home page: Overview, How It Works, Quick Queue Joining & Tracking"""
    services = QueueService.get_services(active_only=True)
    return render_template("index.html", services=services)

@app.route("/services")
def services_page():
    """Services listing and status"""
    services = QueueService.get_services(active_only=True)
    return render_template("services.html", services=services)

@app.route("/token/new")
@app.route("/token/new/<service_code>")
def get_token_page(service_code=None):
    """Token generation form"""
    services = QueueService.get_services(active_only=True)
    selected_service = None
    if service_code:
        for s in services:
            if s["code"] == service_code:
                selected_service = s
                break
    
    # Generate a unique idempotency key for this form load to prevent double submissions
    form_idempotency_key = str(uuid.uuid4())
    return render_template(
        "get_token.html",
        services=services,
        selected_service=selected_service,
        idempotency_key=form_idempotency_key
    )

@app.route("/token/view/<reference_code>")
def token_view_page(reference_code):
    """Digital token ticket view after generation"""
    status_data = QueueService.get_token_status(reference_code)
    if not status_data:
        flash("Invalid or expired token reference code.", "error")
        return redirect(url_for("index"))
    return render_template("token_view.html", token=status_data)

@app.route("/status")
@app.route("/status/<reference_code>")
def status_page(reference_code=None):
    """Live queue status tracking page"""
    initial_status = None
    if reference_code:
        initial_status = QueueService.get_token_status(reference_code)
    return render_template("status.html", reference_code=reference_code, initial_status=initial_status)

@app.route("/display")
def display_page():
    """Public TV / Kiosk Display screen for waiting rooms"""
    return render_template("display.html")

# -------------------------------------------------------------
# Visitor APIs
# -------------------------------------------------------------

@app.route("/api/services", methods=["GET"])
def api_get_services():
    """Return all active services and their live queue metrics"""
    services = QueueService.get_services(active_only=True)
    return jsonify({"success": True, "services": services})

@app.route("/api/token/generate", methods=["POST"])
def api_generate_token():
    """Generate a digital token with concurrency and duplicate prevention"""
    data = request.get_json() or request.form
    
    service_id = data.get("service_id")
    visitor_name = data.get("visitor_name", "").strip() or "Visitor"
    student_id = data.get("student_id", "").strip() or None
    phone_or_email = data.get("phone_or_email", "").strip() or None
    notes = data.get("notes", "").strip() or None
    idempotency_key = data.get("idempotency_key")
    
    if not service_id:
        return jsonify({"success": False, "error": "Please select a service."}), 400

    try:
        service_id = int(service_id)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid service ID."}), 400

    result = QueueService.create_token(
        service_id=service_id,
        visitor_name=visitor_name,
        student_id=student_id,
        phone_or_email=phone_or_email,
        notes=notes,
        idempotency_key=idempotency_key
    )
    
    if not result.get("success"):
        return jsonify(result), 400
        
    return jsonify(result), 201

@app.route("/api/token/status/<ref_or_number>", methods=["GET"])
def api_get_token_status(ref_or_number):
    """Fetch live status of a token by reference code or token number"""
    status = QueueService.get_token_status(ref_or_number)
    if not status:
        return jsonify({"success": False, "error": "Token not found."}), 404
    return jsonify({"success": True, "data": status})

@app.route("/api/token/cancel", methods=["POST"])
def api_cancel_token():
    """Visitor voluntarily cancels their token"""
    data = request.get_json() or {}
    ref_code = data.get("reference_code")
    if not ref_code:
        return jsonify({"success": False, "error": "Reference code is required."}), 400
    
    result = QueueService.cancel_token_by_visitor(ref_code)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

@app.route("/api/display", methods=["GET"])
def api_display_data():
    """Live public display board data"""
    data = QueueService.get_public_display_data()
    return jsonify({"success": True, "data": data})

# -------------------------------------------------------------
# Administrator Routes & APIs
# -------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login page and authentication"""
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        user, err_msg = AuthService.authenticate(username, password)
        if user:
            session["admin_logged_in"] = True
            session["admin_id"] = user["id"]
            session["admin_username"] = user["username"]
            session["admin_name"] = user["full_name"]
            flash(f"Welcome back, {user['full_name']}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("admin_dashboard"))
        else:
            error = err_msg

    return render_template(
        "admin_login.html",
        error=error,
        default_username=Config.DEFAULT_ADMIN_USERNAME,
        default_password=Config.DEFAULT_ADMIN_PASSWORD
    )

@app.route("/admin/logout")
def admin_logout():
    """Admin logout"""
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("admin_login"))

@app.route("/admin")
@login_required
def admin_dashboard():
    """Main Administrator Dashboard"""
    dashboard_data = QueueService.get_admin_dashboard_data()
    return render_template("admin_dashboard.html", data=dashboard_data)

@app.route("/admin/settings")
@login_required
def admin_settings():
    """Admin settings page"""
    services = QueueService.get_services(active_only=False)
    return render_template("admin_settings.html", services=services)

@app.route("/api/admin/dashboard-data", methods=["GET"])
@login_required
def api_admin_dashboard_data():
    """Live polling endpoint for admin dashboard"""
    data = QueueService.get_admin_dashboard_data()
    return jsonify({"success": True, "data": data})

@app.route("/api/admin/call-next", methods=["POST"])
@login_required
def api_admin_call_next():
    """Call next waiting visitor for a service counter"""
    data = request.get_json() or {}
    service_id = data.get("service_id")
    if not service_id:
        return jsonify({"success": False, "error": "Service ID is required."}), 400

    result = QueueService.call_next_token(int(service_id))
    status_code = 200 if result.get("success") or result.get("queue_empty") else 400
    return jsonify(result), status_code

@app.route("/api/admin/complete", methods=["POST"])
@login_required
def api_admin_complete():
    """Mark a serving token as completed"""
    data = request.get_json() or {}
    token_id = data.get("token_id")
    if not token_id:
        return jsonify({"success": False, "error": "Token ID is required."}), 400

    result = QueueService.complete_token(int(token_id))
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

@app.route("/api/admin/skip", methods=["POST"])
@login_required
def api_admin_skip():
    """Mark a token as skipped"""
    data = request.get_json() or {}
    token_id = data.get("token_id")
    reason = data.get("reason", "Visitor absent when called")
    if not token_id:
        return jsonify({"success": False, "error": "Token ID is required."}), 400

    result = QueueService.skip_token(int(token_id), reason=reason)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

@app.route("/api/admin/recall", methods=["POST"])
@login_required
def api_admin_recall():
    """Re-announce a token currently being served"""
    data = request.get_json() or {}
    token_id = data.get("token_id")
    if not token_id:
        return jsonify({"success": False, "error": "Token ID is required."}), 400

    result = QueueService.recall_token(int(token_id))
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

@app.route("/api/admin/reset", methods=["POST"])
@login_required
def api_admin_reset():
    """Safely clear/archive remaining active tokens"""
    data = request.get_json() or {}
    service_id = data.get("service_id")
    sid = int(service_id) if service_id else None
    result = QueueService.reset_queue(service_id=sid)
    return jsonify(result)

@app.route("/api/admin/change-password", methods=["POST"])
@login_required
def api_admin_change_password():
    """Allow administrator to change password securely"""
    data = request.get_json() or {}
    current_pwd = data.get("current_password", "")
    new_pwd = data.get("new_password", "")
    confirm_pwd = data.get("confirm_password", "")

    if not current_pwd or not new_pwd:
        return jsonify({"success": False, "error": "All fields are required."}), 400

    if new_pwd != confirm_pwd:
        return jsonify({"success": False, "error": "New passwords do not match."}), 400

    success, msg = AuthService.change_password(session["admin_id"], current_pwd, new_pwd)
    status_code = 200 if success else 400
    return jsonify({"success": success, "message" if success else "error": msg}), status_code

@app.route("/api/admin/service/update", methods=["POST"])
@login_required
def api_admin_update_service():
    """Update service counter information or active status"""
    data = request.get_json() or {}
    service_id = data.get("service_id")
    if not service_id:
        return jsonify({"success": False, "error": "Service ID is required."}), 400

    db_session = Session()
    try:
        service = db_session.query(Service).filter_by(id=int(service_id)).first()
        if not service:
            return jsonify({"success": False, "error": "Service not found."}), 404

        if "counter_number" in data:
            service.counter_number = data["counter_number"].strip()
        if "avg_service_time_mins" in data:
            service.avg_service_time_mins = max(1, int(data["avg_service_time_mins"]))
        if "is_active" in data:
            service.is_active = bool(data["is_active"])

        db_session.commit()
        return jsonify({"success": True, "message": "Service configuration updated."})
    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        db_session.close()

# -------------------------------------------------------------
# System & Health Routes
# -------------------------------------------------------------

@app.route("/health")
def health_check():
    """Public healthcheck for hosting platforms"""
    db_status = "connected"
    try:
        db_session = Session()
        db_session.query(SystemSetting).first()
        db_session.close()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "app": "QueueLess: Smart Queue Management System",
        "timestamp": utcnow().isoformat()
    })

@app.route("/api/docs")
def api_docs():
    """Simple API catalog for reference and college viva"""
    return jsonify({
        "project": "QueueLess — Smart Queue Management System",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/services": "List all active services and queue metrics",
            "POST /api/token/generate": "Generate digital token (service_id, visitor_name, student_id, idempotency_key)",
            "GET /api/token/status/<ref_or_number>": "Get live position, waiting time, and events for a token",
            "POST /api/token/cancel": "Visitor self-service cancellation",
            "GET /api/display": "Public TV/kiosk display status for all counters",
            "POST /api/admin/call-next": "[Admin] Advance queue and call next token",
            "POST /api/admin/complete": "[Admin] Mark token as completed",
            "POST /api/admin/skip": "[Admin] Mark token as skipped / absent",
            "POST /api/admin/recall": "[Admin] Re-announce current token",
            "POST /api/admin/reset": "[Admin] Reset queue safely",
            "GET /api/admin/dashboard-data": "[Admin] Live overview metrics and token table",
            "POST /api/admin/change-password": "[Admin] Change admin password"
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
