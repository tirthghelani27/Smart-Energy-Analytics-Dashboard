# ============================================================
# Admin Panel Tests
# ============================================================
import pytest
from app import db
from src.models.user import User
from src.models.alert import Alert
from src.models.electricity_usage import ElectricityUsage
from datetime import date, timedelta


def _make_admin(app):
    admin = User(
        username="sysadmin",
        email="admin@test.com",
        first_name="System",
        last_name="Admin",
        role="admin",
        is_active=True,
    )
    admin.set_password("AdminPass123")
    db.session.add(admin)
    db.session.commit()
    return admin


def _login(client, email, password):
    client.post("/auth/login", data={
        "identifier": email,
        "password": password,
    }, follow_redirects=True)


def _seed_usage(user_id, days=5):
    for i in range(days):
        rec = ElectricityUsage(
            user_id=user_id,
            date=date.today() - timedelta(days=days - i),
            units_consumed=8.0,
            source="manual",
        )
        db.session.add(rec)
    db.session.commit()


# ── Access control ───────────────────────────────────────────
def test_admin_dashboard_requires_login(client):
    resp = client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 302


def test_admin_dashboard_forbidden_for_normal_user(logged_in_client):
    resp = logged_in_client.get("/admin/")
    assert resp.status_code == 403


def test_admin_dashboard_accessible_to_admin(client, app):
    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")
    resp = client.get("/admin/")
    assert resp.status_code == 200
    assert b"Admin Dashboard" in resp.data


# ── KPI cards ────────────────────────────────────────────────
def test_admin_shows_user_count(client, app, new_user):
    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")
    resp = client.get("/admin/")
    assert resp.status_code == 200
    assert b"Total Users" in resp.data


def test_admin_shows_energy_tracked(client, app, new_user):
    admin = _make_admin(app)
    _seed_usage(new_user.id, days=5)
    _login(client, "admin@test.com", "AdminPass123")
    resp = client.get("/admin/")
    assert resp.status_code == 200
    assert b"Total Energy Tracked" in resp.data


# ── User management ──────────────────────────────────────────
def test_admin_users_page(client, app):
    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")
    resp = client.get("/admin/users")
    assert resp.status_code == 200
    assert b"User Management" in resp.data


def test_admin_toggle_user_active(client, app, new_user):
    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")

    original_status = new_user.is_active
    resp = client.get(
        f"/admin/users/{new_user.id}/toggle-active", follow_redirects=True
    )
    assert resp.status_code == 200

    db.session.refresh(new_user)
    assert new_user.is_active != original_status


def test_admin_cannot_deactivate_self(client, app):
    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")

    resp = client.get(
        f"/admin/users/{admin.id}/toggle-active", follow_redirects=True
    )
    assert resp.status_code == 200
    # Flash message should warn
    assert b"cannot deactivate your own account" in resp.data.lower() or b"cannot" in resp.data


def test_admin_toggle_user_role(client, app, new_user):
    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")

    original_role = new_user.role
    client.get(f"/admin/users/{new_user.id}/toggle-role", follow_redirects=True)

    db.session.refresh(new_user)
    assert new_user.role != original_role


def test_admin_delete_user(client, app):
    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")

    victim = User(username="victim", email="victim@test.com", role="user", is_active=True)
    victim.set_password("Victim123")
    db.session.add(victim)
    db.session.commit()
    victim_id = victim.id

    resp = client.get(f"/admin/users/{victim_id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(User, victim_id) is None


# ── Alert management ─────────────────────────────────────────
def test_admin_alerts_page(client, app, new_user):
    alert = Alert(
        user_id=new_user.id,
        alert_type="spike",
        severity="high",
        message="Big spike detected",
    )
    db.session.add(alert)
    db.session.commit()

    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")
    resp = client.get("/admin/alerts")
    assert resp.status_code == 200
    assert b"Big spike detected" in resp.data


def test_admin_mark_alert_read(client, app, new_user):
    alert = Alert(
        user_id=new_user.id,
        alert_type="cost",
        severity="low",
        message="Cost alert",
        is_read=False,
    )
    db.session.add(alert)
    db.session.commit()

    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        f"/admin/alerts/{alert.id}/mark-read", follow_redirects=True
    )
    assert resp.status_code == 200
    db.session.refresh(alert)
    assert alert.is_read is True


def test_admin_delete_alert(client, app, new_user):
    alert = Alert(
        user_id=new_user.id,
        alert_type="anomaly",
        severity="medium",
        message="Anomaly detected",
    )
    db.session.add(alert)
    db.session.commit()
    alert_id = alert.id

    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        f"/admin/alerts/{alert_id}/delete", follow_redirects=True
    )
    assert resp.status_code == 200
    assert db.session.get(Alert, alert_id) is None


# ── Dataset management ────────────────────────────────────────
def test_admin_datasets_page(client, app, new_user):
    _seed_usage(new_user.id, days=3)
    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")
    resp = client.get("/admin/datasets")
    assert resp.status_code == 200
    assert b"Dataset Management" in resp.data


def test_admin_delete_usage_record(client, app, new_user):
    _seed_usage(new_user.id, days=1)
    record = ElectricityUsage.query.filter_by(user_id=new_user.id).first()
    record_id = record.id

    admin = _make_admin(app)
    _login(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        f"/admin/datasets/{record_id}/delete", follow_redirects=True
    )
    assert resp.status_code == 200
    assert db.session.get(ElectricityUsage, record_id) is None
