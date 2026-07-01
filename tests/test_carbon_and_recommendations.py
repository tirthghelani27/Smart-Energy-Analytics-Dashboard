# ============================================================
# Carbon & Recommendation Service Tests
# ============================================================
from datetime import date, timedelta
from app import db
from src.models.electricity_usage import ElectricityUsage
from src.models.appliance import Appliance
from src.services import carbon_service, recommendation_service


def _seed_usage(user_id, days=10, value=5.0):
    for i in range(days):
        rec = ElectricityUsage(
            user_id=user_id,
            date=date.today() - timedelta(days=days - 1 - i),
            units_consumed=value,
        )
        db.session.add(rec)
    db.session.commit()


def test_carbon_dashboard_basic(new_user):
    _seed_usage(new_user.id, days=5, value=10.0)
    result = carbon_service.get_carbon_dashboard(new_user.id, emission_factor=0.82)

    assert result["co2_generated"] >= 0
    assert "rating" in result
    assert result["rating"]["label"] in ("Bronze", "Silver", "Gold", "Platinum")
    assert 0 <= result["sustainability_score"] <= 100


def test_recommendations_generated_for_high_usage(new_user):
    _seed_usage(new_user.id, days=30, value=15.0)  # well above 3 kWh/day baseline

    data = recommendation_service.get_recommendations(new_user.id, tariff=6.5)

    assert len(data["recommendations"]) > 0
    assert data["total_monthly_kwh_saving"] >= 0
    assert data["total_annual_cost_saving"] == round(data["total_monthly_cost_saving"] * 12, 2)


def test_recommendations_appliance_flagging(new_user):
    appl = Appliance(user_id=new_user.id, name="Heater", power_rating_w=2000,
                       daily_usage_hrs=10, is_active=True)
    db.session.add(appl)
    db.session.commit()

    _seed_usage(new_user.id, days=10, value=5.0)
    data = recommendation_service.get_recommendations(new_user.id, tariff=6.5, regenerate=True)

    titles = [r.title for r in data["recommendations"]]
    assert any("Heater" in t for t in titles)


def test_mark_applied(new_user):
    _seed_usage(new_user.id, days=10, value=10.0)
    data = recommendation_service.get_recommendations(new_user.id, tariff=6.5)
    rec = data["recommendations"][0]

    success = recommendation_service.mark_applied(new_user.id, rec.id)
    assert success is True
    assert rec.is_applied is True

    assert recommendation_service.mark_applied(new_user.id, 999999) is False
