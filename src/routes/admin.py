# ============================================================
# Admin Routes
# ============================================================
from functools import wraps

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, abort
)
from flask_login import login_required, current_user

from src.services import admin_service

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """Decorator that enforces the admin role.

    Must be applied AFTER @login_required so current_user is always
    authenticated when this runs.  Returns 403 for authenticated
    non-admins and relies on @login_required to redirect anonymous users.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/")
@login_required
@admin_required
def index():
    data = admin_service.get_admin_dashboard()
    return render_template("admin/index.html", **data)


# ── User Management ──────────────────────────────────────────
@admin_bp.route("/users")
@login_required
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    pagination = admin_service.get_all_users(page=page, per_page=10)
    return render_template("admin/users.html", pagination=pagination)


@admin_bp.route("/users/<int:user_id>/toggle-active")
@login_required
@admin_required
def toggle_user_active(user_id):
    if user_id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin.users"))

    user = admin_service.toggle_user_active(user_id)
    if user:
        status = "activated" if user.is_active else "deactivated"
        flash(f"User '{user.username}' {status}.", "success")
    else:
        flash("User not found.", "danger")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-role")
@login_required
@admin_required
def toggle_user_role(user_id):
    if user_id == current_user.id:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for("admin.users"))

    user = admin_service.toggle_user_role(user_id)
    if user:
        flash(f"User '{user.username}' role changed to {user.role}.", "success")
    else:
        flash("User not found.", "danger")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete")
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin.users"))

    if admin_service.delete_user(user_id):
        flash("User deleted successfully.", "success")
    else:
        flash("User not found.", "danger")
    return redirect(url_for("admin.users"))


# ── Dataset Management ─────────────────────────────────────────
@admin_bp.route("/datasets")
@login_required
@admin_required
def datasets():
    records = admin_service.get_recent_usage_records(limit=50)
    return render_template("admin/datasets.html", records=records)


@admin_bp.route("/datasets/<int:record_id>/delete")
@login_required
@admin_required
def delete_dataset_record(record_id):
    if admin_service.delete_usage_record(record_id):
        flash("Usage record deleted.", "success")
    else:
        flash("Record not found.", "danger")
    return redirect(url_for("admin.datasets"))


# ── Alert Management ─────────────────────────────────────────
@admin_bp.route("/alerts")
@login_required
@admin_required
def alerts():
    alert_rows = admin_service.get_recent_alerts(limit=50)
    return render_template("admin/alerts.html", alert_rows=alert_rows)


@admin_bp.route("/alerts/<int:alert_id>/mark-read")
@login_required
@admin_required
def mark_alert_read(alert_id):
    if admin_service.mark_alert_read(alert_id):
        flash("Alert marked as read.", "success")
    else:
        flash("Alert not found.", "danger")
    return redirect(url_for("admin.alerts"))


@admin_bp.route("/alerts/<int:alert_id>/delete")
@login_required
@admin_required
def delete_alert(alert_id):
    if admin_service.delete_alert(alert_id):
        flash("Alert deleted.", "success")
    else:
        flash("Alert not found.", "danger")
    return redirect(url_for("admin.alerts"))
