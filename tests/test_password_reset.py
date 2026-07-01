# ============================================================
# Password Reset Tests (token generation, verification, flow)
# ============================================================
import pytest
from app import db
from src.models.user import User


# ── Token generation ──────────────────────────────────────────
def test_get_reset_token_returns_string(app, new_user):
    with app.app_context():
        token = new_user.get_reset_token()
        assert isinstance(token, str)
        assert len(token) > 20


def test_verify_reset_token_returns_user(app, new_user):
    with app.app_context():
        token = new_user.get_reset_token()
        resolved = User.verify_reset_token(token)
        assert resolved is not None
        assert resolved.id == new_user.id


def test_verify_reset_token_bad_token_returns_none(app):
    with app.app_context():
        result = User.verify_reset_token("this-is-not-a-valid-token")
        assert result is None


def test_verify_reset_token_tampered_returns_none(app, new_user):
    with app.app_context():
        token = new_user.get_reset_token()
        bad_token = token[:-4] + "XXXX"
        result = User.verify_reset_token(bad_token)
        assert result is None


def test_verify_reset_token_expired_returns_none(app, new_user):
    with app.app_context():
        token = new_user.get_reset_token()
        # Pass max_age=0 to force expiry
        result = User.verify_reset_token(token, max_age=0)
        assert result is None


# ── Forgot password route ─────────────────────────────────────
def test_forgot_password_page_loads(client):
    resp = client.get("/auth/forgot-password")
    assert resp.status_code == 200
    assert b"Reset" in resp.data or b"reset" in resp.data


def test_forgot_password_post_with_valid_email(client, new_user, app):
    # Must not crash and must show the safe "if registered" message
    resp = client.post("/auth/forgot-password",
                       data={"email": "test@example.com"},
                       follow_redirects=True)
    assert resp.status_code == 200
    # Should redirect to login with info flash
    assert b"reset link" in resp.data or b"registered" in resp.data


def test_forgot_password_post_with_unknown_email(client, new_user):
    # Should respond the same as a valid email (no info leak)
    resp = client.post("/auth/forgot-password",
                       data={"email": "nobody@nowhere.com"},
                       follow_redirects=True)
    assert resp.status_code == 200


def test_forgot_password_post_with_invalid_email(client):
    resp = client.post("/auth/forgot-password",
                       data={"email": "not-an-email"},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert b"valid email" in resp.data


# ── Reset password route ─────────────────────────────────────
def test_reset_password_page_valid_token(client, app, new_user):
    with app.app_context():
        token = new_user.get_reset_token()
    resp = client.get(f"/auth/reset-password/{token}")
    assert resp.status_code == 200
    assert b"New Password" in resp.data


def test_reset_password_page_invalid_token(client):
    resp = client.get("/auth/reset-password/invalid-token",
                      follow_redirects=True)
    assert resp.status_code == 200
    # Should redirect to forgot-password with an error flash
    assert b"invalid" in resp.data or b"expired" in resp.data


def test_reset_password_updates_password(client, app, new_user):
    with app.app_context():
        token = new_user.get_reset_token()

    resp = client.post(f"/auth/reset-password/{token}", data={
        "password": "NewSecure99",
        "confirm_password": "NewSecure99",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"updated" in resp.data or b"log in" in resp.data.lower()

    # Verify the new password actually works
    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        assert user.check_password("NewSecure99")
        assert not user.check_password("Password123")


def test_reset_password_rejects_weak_password(client, app, new_user):
    with app.app_context():
        token = new_user.get_reset_token()

    resp = client.post(f"/auth/reset-password/{token}", data={
        "password": "short",
        "confirm_password": "short",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"8 characters" in resp.data


def test_reset_password_rejects_mismatched_passwords(client, app, new_user):
    with app.app_context():
        token = new_user.get_reset_token()

    resp = client.post(f"/auth/reset-password/{token}", data={
        "password": "ValidPass1",
        "confirm_password": "DifferentPass1",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"match" in resp.data
