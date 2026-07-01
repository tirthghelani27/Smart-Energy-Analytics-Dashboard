# ============================================================
# Email Service
# Sends transactional emails (password reset, etc.) via
# Flask-Mail — used by src/routes/auth.py
# ============================================================
from flask import current_app, render_template, url_for
from flask_mail import Message

from src.extensions import mail


def send_password_reset_email(user) -> bool:
    """
    Send a password-reset email containing a signed, time-limited link.
    Returns True if the email was sent (or in dev mode if no mail
    credentials are configured, logs the link instead), False on
    hard failure.
    """
    token = user.get_reset_token()
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    expiry_minutes = current_app.config["PASSWORD_RESET_EXPIRY"] // 60

    # ── Dev fallback: if mail isn't configured, log the link ────
    if not current_app.config.get("MAIL_USERNAME"):
        current_app.logger.info(
            "MAIL_USERNAME not configured — password reset link for "
            "%s: %s (valid %d minutes)", user.email, reset_url, expiry_minutes
        )
        return True

    try:
        msg = Message(
            subject="Reset Your Smart Energy Analytics Password",
            recipients=[user.email],
            html=render_template(
                "emails/reset_password.html",
                user=user,
                reset_url=reset_url,
                expiry_minutes=expiry_minutes,
            ),
            body=(
                f"Hi {user.first_name or user.username},\n\n"
                f"We received a request to reset your password. Click the "
                f"link below to choose a new password. This link expires "
                f"in {expiry_minutes} minutes.\n\n"
                f"{reset_url}\n\n"
                f"If you didn't request this, you can safely ignore this email.\n\n"
                f"— Smart Energy Analytics"
            ),
        )
        mail.send(msg)
        return True
    except Exception:  # noqa: BLE001
        current_app.logger.exception("Failed to send password reset email to %s", user.email)
        return False
