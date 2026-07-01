# ============================================================
# Dashboard Tests
# ============================================================
from datetime import date, timedelta
from app import db
from src.models.electricity_usage import ElectricityUsage
from src.models.alert import Alert


def _seed_usage(user_id, days=30, value=8.0):
    for i in range(days):
        rec = ElectricityUsage(
            user_id=user_id,
            date=date.today() - timedelta(days=days - i),
            units_consumed=value + i * 0.1,
            source="manual",
        )
        rec.compute_cost(6.5)
        db.session.add(rec)
    db.session.commit()


def test_dashboard_requires_login(client):
    resp = client.get("/dashboard/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_dashboard_loads_with_no_data(logged_in_client):
    resp = logged_in_client.get("/dashboard/")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


def test_dashboard_shows_kwh_totals(logged_in_client, new_user):
    _seed_usage(new_user.id, days=10, value=5.0)
    resp = logged_in_client.get("/dashboard/")
    assert resp.status_code == 200
    # total is 10 records * ~5 kWh each
    assert b"kWh" in resp.data


def test_dashboard_shows_alert_count(logged_in_client, new_user):
    alert = Alert(
        user_id=new_user.id,
        alert_type="spike",
        severity="medium",
        message="Test spike alert",
        is_read=False,
    )
    db.session.add(alert)
    db.session.commit()

    resp = logged_in_client.get("/dashboard/")
    assert resp.status_code == 200
    assert b"Test spike alert" in resp.data


def test_dashboard_chart_data_in_response(logged_in_client, new_user):
    _seed_usage(new_user.id, days=15, value=7.0)
    resp = logged_in_client.get("/dashboard/")
    assert resp.status_code == 200
    # Chart.js canvas should be rendered when there's data
    assert b"consumptionChart" in resp.data


def test_dashboard_recent_records_table(logged_in_client, new_user):
    _seed_usage(new_user.id, days=5, value=6.0)
    resp = logged_in_client.get("/dashboard/")
    assert resp.status_code == 200
    assert b"Recent Usage Records" in resp.data


def test_dashboard_bill_calculation(logged_in_client, new_user):
    """Estimated bill = month_kwh * tariff (₹6.50)"""
    today = date.today()
    rec = ElectricityUsage(
        user_id=new_user.id,
        date=today - timedelta(days=1),
        units_consumed=10.0,
        source="manual",
    )
    rec.compute_cost(6.5)
    db.session.add(rec)
    db.session.commit()

    resp = logged_in_client.get("/dashboard/")
    assert resp.status_code == 200
    # ₹65.00 bill for 10 kWh
    assert b"65" in resp.data
