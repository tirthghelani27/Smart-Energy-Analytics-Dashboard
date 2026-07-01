# ============================================================
# Authentication Tests
# ============================================================
from app import db
from src.models.user import User


def test_register_creates_user(client):
    resp = client.post("/auth/register", data={
        "first_name": "Jane",
        "last_name": "Doe",
        "username": "janedoe",
        "email": "jane@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    }, follow_redirects=True)

    assert resp.status_code == 200
    user = User.query.filter_by(email="jane@example.com").first()
    assert user is not None
    assert user.username == "janedoe"
    assert user.check_password("Password123")


def test_register_rejects_mismatched_passwords(client):
    resp = client.post("/auth/register", data={
        "first_name": "Jane",
        "last_name": "Doe",
        "username": "janedoe2",
        "email": "jane2@example.com",
        "password": "Password123",
        "confirm_password": "Different123",
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert User.query.filter_by(email="jane2@example.com").first() is None


def test_login_success(client, new_user):
    resp = client.post("/auth/login", data={
        "identifier": "test@example.com",
        "password": "Password123",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data or b"dashboard" in resp.data


def test_login_wrong_password(client, new_user):
    resp = client.post("/auth/login", data={
        "identifier": "test@example.com",
        "password": "WrongPassword",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Invalid credentials" in resp.data


def test_logout(logged_in_client):
    resp = logged_in_client.get("/auth/logout", follow_redirects=True)
    assert resp.status_code == 200


def test_password_hashing_not_plaintext(new_user):
    assert new_user.password != "Password123"
    assert new_user.check_password("Password123") is True
    assert new_user.check_password("wrong") is False


def test_dashboard_requires_login(client):
    resp = client.get("/dashboard/", follow_redirects=False)
    assert resp.status_code in (302, 401)


# ── Password Reset Token Tests ───────────────────────────────
def test_get_reset_token_returns_string(app, new_user):
    token = new_user.get_reset_token()
    assert isinstance(token, str)
    assert len(token) > 20


def test_verify_reset_token_returns_user(app, new_user):
    token = new_user.get_reset_token()
    user = new_user.verify_reset_token(token, max_age=3600)
    assert user is not None
    assert user.id == new_user.id


def test_verify_invalid_token_returns_none(app, new_user):
    user = new_user.verify_reset_token("invalid-token", max_age=3600)
    assert user is None


def test_verify_tampered_token_returns_none(app, new_user):
    token = new_user.get_reset_token()
    tampered = token[:-5] + "XXXXX"
    user = new_user.verify_reset_token(tampered, max_age=3600)
    assert user is None


def test_forgot_password_page_loads(client):
    resp = client.get("/auth/forgot-password")
    assert resp.status_code == 200
    assert b"Reset Password" in resp.data or b"Forgot" in resp.data


def test_forgot_password_always_shows_info_message(client):
    resp = client.post(
        "/auth/forgot-password",
        data={"email": "nonexistent@example.com"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"reset link" in resp.data.lower() or b"registered" in resp.data.lower()


def test_reset_password_invalid_token_redirects(client):
    resp = client.get(
        "/auth/reset-password/bad-token-abc",
        follow_redirects=True
    )
    assert resp.status_code == 200
    # Should be redirected to forgot-password with an error message
    assert b"invalid" in resp.data.lower() or b"expired" in resp.data.lower()


def test_reset_password_valid_token_shows_form(app, new_user):
    token = new_user.get_reset_token()
    from app import create_app
    with app.test_client() as c:
        resp = c.get(f"/auth/reset-password/{token}")
        assert resp.status_code == 200
        assert b"Set New Password" in resp.data or b"New Password" in resp.data


def test_reset_password_updates_password(app, new_user):
    token = new_user.get_reset_token()
    from app import create_app, db
    with app.test_client() as c:
        resp = c.post(
            f"/auth/reset-password/{token}",
            data={"password": "NewPassword456", "confirm_password": "NewPassword456"},
            follow_redirects=True,
        )
    assert resp.status_code == 200
    db.session.refresh(new_user)
    assert new_user.check_password("NewPassword456")


def test_reset_password_mismatched_passwords_fails(app, new_user):
    token = new_user.get_reset_token()
    with app.test_client() as c:
        resp = c.post(
            f"/auth/reset-password/{token}",
            data={"password": "NewPass456", "confirm_password": "Different456"},
            follow_redirects=True,
        )
    assert resp.status_code == 200
    assert b"do not match" in resp.data.lower() or b"mismatch" in resp.data.lower()
