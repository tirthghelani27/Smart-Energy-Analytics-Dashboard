# ============================================================
# Route Smoke Tests — every page should at least render 200
# ============================================================
from datetime import date, timedelta
from app import db
from src.models.electricity_usage import ElectricityUsage


def _seed_usage(user_id, days=10, value=5.0):
    for i in range(days):
        rec = ElectricityUsage(
            user_id=user_id,
            date=date.today() - timedelta(days=days - 1 - i),
            units_consumed=value + i * 0.3,
        )
        rec.compute_cost(6.5)
        db.session.add(rec)
    db.session.commit()


def test_home_page(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_login_page(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200


def test_register_page(client):
    resp = client.get("/auth/register")
    assert resp.status_code == 200


def test_dashboard_authenticated(logged_in_client, new_user):
    _seed_usage(new_user.id, days=5)
    resp = logged_in_client.get("/dashboard/")
    assert resp.status_code == 200


def test_analytics_all_periods(logged_in_client, new_user):
    _seed_usage(new_user.id, days=10)
    for period in ["daily", "weekly", "monthly", "yearly"]:
        resp = logged_in_client.get(f"/analytics/?period={period}")
        assert resp.status_code == 200, f"{period} failed"


def test_forecasting_insufficient_data(logged_in_client, new_user):
    _seed_usage(new_user.id, days=2)  # below MIN_RECORDS_REQUIRED
    resp = logged_in_client.get("/forecasting/")
    assert resp.status_code == 200
    assert b"Not enough data" in resp.data


def test_carbon_page(logged_in_client, new_user):
    _seed_usage(new_user.id, days=5)
    resp = logged_in_client.get("/carbon/")
    assert resp.status_code == 200


def test_recommendations_page(logged_in_client, new_user):
    _seed_usage(new_user.id, days=10)
    resp = logged_in_client.get("/recommendations/")
    assert resp.status_code == 200


def test_appliances_page(logged_in_client):
    resp = logged_in_client.get("/appliances/")
    assert resp.status_code == 200


def test_appliances_add(logged_in_client, new_user):
    resp = logged_in_client.post("/appliances/add", data={
        "name": "Fridge",
        "category": "Refrigerator",
        "power_rating_w": "150",
        "daily_usage_hrs": "24",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Fridge" in resp.data


def test_data_import_page(logged_in_client):
    resp = logged_in_client.get("/data/import")
    assert resp.status_code == 200


def test_reports_page(logged_in_client):
    resp = logged_in_client.get("/reports/")
    assert resp.status_code == 200


def test_admin_page_forbidden_for_non_admin(logged_in_client):
    resp = logged_in_client.get("/admin/")
    assert resp.status_code == 403


def test_admin_page_allowed_for_admin(client, app):
    from src.models.user import User
    admin = User(username="adminuser", email="admin@example.com",
                   first_name="Admin", last_name="User", role="admin")
    admin.set_password("AdminPass123")
    db.session.add(admin)
    db.session.commit()

    client.post("/auth/login", data={
        "identifier": "admin@example.com",
        "password": "AdminPass123",
    }, follow_redirects=True)

    resp = client.get("/admin/")
    assert resp.status_code == 200


def test_forgot_password_page(client):
    resp = client.get("/auth/forgot-password")
    assert resp.status_code == 200
