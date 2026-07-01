# ============================================================
# Authentication Routes
# ============================================================
import re
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from src.extensions import db
from src.models.user import User

auth_bp = Blueprint("auth", __name__)

# ── Helpers ──────────────────────────────────────────────────
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _validate_registration(form) -> list[str]:
    errors = []
    username  = form.get("username", "").strip()
    email     = form.get("email", "").strip()
    password  = form.get("password", "")
    confirm   = form.get("confirm_password", "")
    first     = form.get("first_name", "").strip()
    last      = form.get("last_name", "").strip()

    if not username or len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    elif len(username) > 80:
        errors.append("Username must be under 80 characters.")
    elif not re.match(r"^[A-Za-z0-9_]+$", username):
        errors.append("Username may only contain letters, numbers, and underscores.")

    if not email or not EMAIL_RE.match(email):
        errors.append("Please enter a valid email address.")

    if not first:
        errors.append("First name is required.")
    if not last:
        errors.append("Last name is required.")

    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    elif not re.search(r"[0-9]", password):
        errors.append("Password must contain at least one number.")

    if password != confirm:
        errors.append("Passwords do not match.")

    return errors


# ── Register ─────────────────────────────────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        form = request.form
        errors = _validate_registration(form)

        username = form.get("username", "").strip()
        email    = form.get("email", "").strip().lower()

        if not errors:
            if User.query.filter_by(username=username).first():
                errors.append("That username is already taken.")
            if User.query.filter_by(email=email).first():
                errors.append("An account with that email already exists.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html", form=form)

        user = User(
            username   = username,
            email      = email,
            first_name = form.get("first_name", "").strip(),
            last_name  = form.get("last_name", "").strip(),
            role       = "user",
        )
        user.set_password(form.get("password"))
        db.session.add(user)
        db.session.commit()

        flash(f"Account created! Welcome, {user.first_name}. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form={})


# ── Login ────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()   # email or username
        password   = request.form.get("password", "")
        remember   = bool(request.form.get("remember"))

        if not identifier or not password:
            flash("Please enter your email/username and password.", "danger")
            return render_template("auth/login.html")

        # Look up by email first, then username
        user = (User.query.filter_by(email=identifier.lower()).first()
                or User.query.filter_by(username=identifier).first())

        if not user or not user.check_password(password):
            flash("Invalid credentials. Please try again.", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("Your account has been deactivated. Contact support.", "warning")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        flash(f"Welcome back, {user.first_name or user.username}!", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard.index"))

    return render_template("auth/login.html")


# ── Logout ───────────────────────────────────────────────────
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("main.index"))


# ── Forgot Password ──────────────────────────────────────────
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email or not EMAIL_RE.match(email):
            flash("Please enter a valid email address.", "danger")
            return render_template("auth/forgot_password.html")

        user = User.query.filter_by(email=email).first()

        # Always show the same message so we don't reveal if an email exists
        if user:
            from src.services.email_service import send_password_reset_email
            send_password_reset_email(user)

        flash(
            "If that email is registered, a password reset link has been "
            "sent. Please check your inbox (and spam folder).",
            "info"
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


# ── Reset Password ───────────────────────────────────────────
@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    expiry = current_app.config["PASSWORD_RESET_EXPIRY"]
    user = User.verify_reset_token(token, max_age=expiry)

    if user is None:
        flash(
            "That password reset link is invalid or has expired. "
            "Please request a new one.",
            "danger"
        )
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        errors = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        elif not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter.")
        elif not re.search(r"[0-9]", password):
            errors.append("Password must contain at least one number.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/reset_password.html", token=token)

        user.set_password(password)
        db.session.commit()

        flash("Your password has been updated. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)
