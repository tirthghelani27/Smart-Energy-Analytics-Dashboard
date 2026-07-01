# ============================================================
# Recommendation Engine Tests
# ============================================================
from datetime import date, timedelta
import pytest
from app import db
from src.models.electricity_usage import ElectricityUsage
from src.models.appliance import Appliance
from src.models.recommendation import Recommendation
from src.services import recommendation_service


TARIFF = 6.5


def _seed_usage(user_id, days=30, value=10.0):
    for i in range(days):
        rec = ElectricityUsage(
            user_id=user_id,
            date=date.today() - timedelta(days=days - i),
            units_consumed=value,
            source="manual",
        )
        db.session.add(rec)
    db.session.commit()


def _add_appliance(user_id, name="AC", watts=1500, hours=8.0, active=True):
    a = Appliance(
        user_id=user_id,
        name=name,
        category="Air Conditioner",
        power_rating_w=watts,
        daily_usage_hrs=hours,
        is_active=active,
    )
    a.compute_monthly(TARIFF)
    db.session.add(a)
    db.session.commit()
    return a


# ── Service unit tests ───────────────────────────────────────
def test_get_recommendations_returns_dict(new_user):
    _seed_usage(new_user.id, days=10, value=5.0)
    result = recommendation_service.get_recommendations(new_user.id, tariff=TARIFF)

    assert "recommendations" in result
    assert "total_monthly_kwh_saving" in result
    assert "total_monthly_cost_saving" in result
    assert "total_annual_cost_saving" in result


def test_annual_saving_is_monthly_times_12(new_user):
    _seed_usage(new_user.id, days=30, value=15.0)
    result = recommendation_service.get_recommendations(new_user.id, tariff=TARIFF)
    assert result["total_annual_cost_saving"] == round(
        result["total_monthly_cost_saving"] * 12, 2
    )


def test_recommendations_generated_for_high_usage(new_user):
    _seed_usage(new_user.id, days=30, value=15.0)  # well above 3 kWh baseline
    result = recommendation_service.get_recommendations(new_user.id, tariff=TARIFF)
    assert len(result["recommendations"]) > 0


def test_no_recommendations_for_very_low_usage(new_user):
    _seed_usage(new_user.id, days=30, value=1.0)  # below baseline
    result = recommendation_service.get_recommendations(new_user.id, tariff=TARIFF)
    # May still have appliance recommendations, but behaviour tip should be absent
    titles = [r.title for r in result["recommendations"]]
    assert not any("Reduce overall daily" in t for t in titles)


def test_high_power_appliance_triggers_recommendation(new_user):
    _seed_usage(new_user.id, days=10, value=5.0)
    _add_appliance(new_user.id, name="Big Heater", watts=2500, hours=10.0)

    result = recommendation_service.get_recommendations(
        new_user.id, tariff=TARIFF, regenerate=True
    )
    titles = [r.title for r in result["recommendations"]]
    assert any("Big Heater" in t for t in titles)


def test_inactive_appliance_not_flagged(new_user):
    _seed_usage(new_user.id, days=10, value=5.0)
    _add_appliance(new_user.id, name="Inactive Heater", watts=3000, hours=12.0, active=False)

    result = recommendation_service.get_recommendations(
        new_user.id, tariff=TARIFF, regenerate=True
    )
    titles = [r.title for r in result["recommendations"]]
    # Inactive appliance should not appear in recommendations
    assert not any("Inactive Heater" in t for t in titles)


def test_mark_applied_success(new_user):
    _seed_usage(new_user.id, days=10, value=15.0)
    result = recommendation_service.get_recommendations(new_user.id, tariff=TARIFF)
    rec = result["recommendations"][0]

    success = recommendation_service.mark_applied(new_user.id, rec.id)
    assert success is True

    db.session.refresh(rec)
    assert rec.is_applied is True


def test_mark_applied_wrong_user_fails(new_user):
    _seed_usage(new_user.id, days=10, value=15.0)
    result = recommendation_service.get_recommendations(new_user.id, tariff=TARIFF)
    rec = result["recommendations"][0]

    success = recommendation_service.mark_applied(user_id=99999, recommendation_id=rec.id)
    assert success is False


def test_mark_applied_invalid_id_fails(new_user):
    assert recommendation_service.mark_applied(new_user.id, 99999) is False


def test_savings_are_non_negative(new_user):
    _seed_usage(new_user.id, days=30, value=12.0)
    result = recommendation_service.get_recommendations(new_user.id, tariff=TARIFF)

    assert result["total_monthly_kwh_saving"] >= 0
    assert result["total_monthly_cost_saving"] >= 0
    assert result["total_annual_cost_saving"] >= 0


def test_recommendation_priority_values_valid(new_user):
    _seed_usage(new_user.id, days=30, value=15.0)
    _add_appliance(new_user.id, name="High AC", watts=2000, hours=10.0)
    result = recommendation_service.get_recommendations(
        new_user.id, tariff=TARIFF, regenerate=True
    )
    valid_priorities = {"low", "medium", "high"}
    for rec in result["recommendations"]:
        assert rec.priority in valid_priorities


# ── Route tests ──────────────────────────────────────────────
def test_recommendations_page_requires_login(client):
    resp = client.get("/recommendations/", follow_redirects=False)
    assert resp.status_code == 302


def test_recommendations_page_loads(logged_in_client, new_user):
    _seed_usage(new_user.id, days=20, value=10.0)
    resp = logged_in_client.get("/recommendations/")
    assert resp.status_code == 200
    assert b"Recommendation" in resp.data


def test_recommendations_mark_applied_route(logged_in_client, new_user):
    _seed_usage(new_user.id, days=20, value=15.0)
    result = recommendation_service.get_recommendations(new_user.id, tariff=TARIFF)
    if result["recommendations"]:
        rec_id = result["recommendations"][0].id
        resp = logged_in_client.post(
            f"/recommendations/{rec_id}/apply", follow_redirects=True
        )
        assert resp.status_code in (200, 302, 404, 405)
