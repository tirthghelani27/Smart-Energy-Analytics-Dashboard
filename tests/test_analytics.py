# ============================================================
# Analytics Service & Route Tests
# ============================================================
from datetime import date, timedelta
from app import db
from src.models.electricity_usage import ElectricityUsage
from src.services import analytics_service


# ── Shared helper ─────────────────────────────────────────────
def _seed_usage(user_id, days=10, start_value=5.0, step=0.5):
    for i in range(days):
        rec = ElectricityUsage(
            user_id=user_id,
            date=date.today() - timedelta(days=days - 1 - i),
            units_consumed=max(1.0, round(start_value + i * step, 2)),
        )
        db.session.add(rec)
    db.session.commit()


# ── Service: daily analytics ──────────────────────────────────
def test_daily_analytics_stats(new_user):
    _seed_usage(new_user.id, days=10)
    result = analytics_service.get_daily_analytics(new_user.id, days=30)
    assert result["stats"]["count"] == 10
    assert result["stats"]["total"] > 0
    assert result["stats"]["highest"] >= result["stats"]["average"] >= result["stats"]["lowest"]
    assert len(result["labels"]) == 10
    assert len(result["values"]) == 10


def test_daily_analytics_no_data(new_user):
    result = analytics_service.get_daily_analytics(new_user.id, days=30)
    assert result["stats"]["count"] == 0
    assert result["labels"] == []
    assert result["values"] == []


# ── Service: weekly analytics ─────────────────────────────────
def test_weekly_analytics_returns_data(new_user):
    _seed_usage(new_user.id, days=14, start_value=6.0, step=0.2)
    result = analytics_service.get_weekly_analytics(new_user.id, weeks=4)
    assert result["stats"]["total"] > 0
    assert len(result["labels"]) > 0


# ── Service: monthly analytics ────────────────────────────────
def test_monthly_analytics_no_data(new_user):
    result = analytics_service.get_monthly_analytics(new_user.id)
    assert result["stats"]["count"] == 0
    assert result["stats"]["total"] == 0.0
    assert result["labels"] == []


def test_monthly_analytics_with_data(new_user):
    _seed_usage(new_user.id, days=10)
    result = analytics_service.get_monthly_analytics(new_user.id)
    assert result["stats"]["total"] > 0
    assert len(result["labels"]) >= 1


# ── Service: yearly analytics ──────────────────────────────────
def test_yearly_analytics(new_user):
    _seed_usage(new_user.id, days=10)
    result = analytics_service.get_yearly_analytics(new_user.id)
    assert result["stats"]["total"] > 0
    assert len(result["labels"]) == 1


# ── Service: growth rate ──────────────────────────────────────
def test_growth_rate_empty_series():
    assert analytics_service._growth_rate([]) == 0.0


def test_growth_rate_single_element():
    assert analytics_service._growth_rate([5]) == 0.0


def test_growth_rate_increasing():
    rate = analytics_service._growth_rate([1, 1, 1, 5, 5, 5])
    assert rate > 0


def test_growth_rate_decreasing():
    rate = analytics_service._growth_rate([10, 10, 10, 2, 2, 2])
    assert rate < 0


def test_growth_rate_flat():
    rate = analytics_service._growth_rate([5, 5, 5, 5, 5, 5])
    assert rate == 0.0


# ── Service: peak / lowest day ───────────────────────────────
def test_peak_day(new_user):
    _seed_usage(new_user.id, days=5, start_value=1.0, step=2.0)
    peak = analytics_service.get_peak_day(new_user.id)
    assert peak is not None
    assert peak.units_consumed >= analytics_service.get_lowest_day(new_user.id).units_consumed


def test_peak_day_no_data(new_user):
    assert analytics_service.get_peak_day(new_user.id) is None
    assert analytics_service.get_lowest_day(new_user.id) is None


# ── Stats helper ──────────────────────────────────────────────
def test_build_stats_accuracy():
    stats = analytics_service._build_stats([4.0, 6.0, 8.0])
    assert stats["total"] == 18.0
    assert stats["average"] == 6.0
    assert stats["highest"] == 8.0
    assert stats["lowest"] == 4.0
    assert stats["count"] == 3


# ── Route: analytics page (all periods) ──────────────────────
def test_analytics_page_requires_login(client):
    resp = client.get("/analytics/", follow_redirects=False)
    assert resp.status_code == 302


def test_analytics_daily_period(logged_in_client, new_user):
    _seed_usage(new_user.id, days=5)
    resp = logged_in_client.get("/analytics/?period=daily")
    assert resp.status_code == 200


def test_analytics_weekly_period(logged_in_client, new_user):
    _seed_usage(new_user.id, days=14)
    resp = logged_in_client.get("/analytics/?period=weekly")
    assert resp.status_code == 200


def test_analytics_monthly_period(logged_in_client, new_user):
    _seed_usage(new_user.id, days=10)
    resp = logged_in_client.get("/analytics/?period=monthly")
    assert resp.status_code == 200


def test_analytics_yearly_period(logged_in_client, new_user):
    _seed_usage(new_user.id, days=10)
    resp = logged_in_client.get("/analytics/?period=yearly")
    assert resp.status_code == 200


def test_analytics_unknown_period_defaults_to_monthly(logged_in_client, new_user):
    resp = logged_in_client.get("/analytics/?period=unknown")
    assert resp.status_code == 200


def test_analytics_page_shows_kpi_cards(logged_in_client, new_user):
    _seed_usage(new_user.id, days=5)
    resp = logged_in_client.get("/analytics/")
    assert b"Total Consumption" in resp.data or b"kWh" in resp.data
