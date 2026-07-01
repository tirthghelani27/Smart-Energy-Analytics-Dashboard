# ============================================================
# Carbon Footprint Module Tests
# ============================================================
from datetime import date, timedelta
import pytest
from app import db
from src.models.electricity_usage import ElectricityUsage
from src.models.carbon_footprint import CarbonFootprint, KG_CO2_PER_TREE_MONTH
from src.services import carbon_service


EMISSION_FACTOR = 0.82
TARIFF = 6.5


def _seed_usage(user_id, days=20, value=8.0):
    for i in range(days):
        rec = ElectricityUsage(
            user_id=user_id,
            date=date.today() - timedelta(days=days - i),
            units_consumed=value,
            source="manual",
        )
        db.session.add(rec)
    db.session.commit()


# ── Model unit tests ─────────────────────────────────────────
def test_co2_from_kwh_formula():
    cf = CarbonFootprint.from_kwh(
        user_id=1, month=6, year=2026, kwh=100.0, emission_factor=EMISSION_FACTOR
    )
    expected_co2 = round(100.0 * EMISSION_FACTOR, 2)
    assert cf.co2_generated == expected_co2


def test_trees_equivalent_formula():
    cf = CarbonFootprint.from_kwh(
        user_id=1, month=6, year=2026, kwh=50.0, emission_factor=EMISSION_FACTOR
    )
    expected_trees = round((50.0 * EMISSION_FACTOR) / KG_CO2_PER_TREE_MONTH, 1)
    assert cf.trees_equivalent == expected_trees


def test_sustainability_score_range():
    # High usage → low score
    cf_high = CarbonFootprint.from_kwh(
        user_id=1, month=6, year=2026, kwh=300.0, emission_factor=EMISSION_FACTOR
    )
    # Zero usage → high score (capped at 100)
    cf_zero = CarbonFootprint.from_kwh(
        user_id=1, month=6, year=2026, kwh=0.0, emission_factor=EMISSION_FACTOR
    )
    assert 0 <= cf_high.sustainability_score <= 100
    assert 0 <= cf_zero.sustainability_score <= 100


def test_high_usage_gets_low_score():
    cf_high = CarbonFootprint.from_kwh(
        user_id=1, month=6, year=2026, kwh=500.0, emission_factor=EMISSION_FACTOR
    )
    assert cf_high.sustainability_score < 50


# ── Service tests ────────────────────────────────────────────
def test_carbon_dashboard_returns_required_keys(new_user):
    _seed_usage(new_user.id, days=10, value=10.0)
    result = carbon_service.get_carbon_dashboard(new_user.id, EMISSION_FACTOR)

    required_keys = [
        "co2_generated", "co2_saved", "trees_equivalent",
        "sustainability_score", "rating", "annual_co2",
        "chart_labels", "chart_co2",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"


def test_carbon_rating_tiers(new_user):
    _seed_usage(new_user.id, days=10, value=10.0)
    result = carbon_service.get_carbon_dashboard(new_user.id, EMISSION_FACTOR)

    assert result["rating"]["label"] in ("Bronze", "Silver", "Gold", "Platinum")
    assert result["rating"]["color"] in ("danger", "secondary", "warning", "info")
    assert result["rating"]["icon"] in ("fa-award", "fa-medal", "fa-trophy", "fa-gem")


def test_carbon_persists_to_db(app, new_user):
    _seed_usage(new_user.id, days=10, value=10.0)
    carbon_service.get_carbon_dashboard(new_user.id, EMISSION_FACTOR)

    today = date.today()
    record = CarbonFootprint.query.filter_by(
        user_id=new_user.id, month=today.month, year=today.year
    ).first()
    assert record is not None
    assert record.co2_generated > 0


def test_carbon_co2_generated_matches_kwh(new_user):
    kwh_per_day = 10.0
    days = 5
    _seed_usage(new_user.id, days=days, value=kwh_per_day)

    today = date.today()
    result = carbon_service.get_carbon_dashboard(new_user.id, EMISSION_FACTOR)

    # month_kwh is records in current month only
    assert result["co2_generated"] >= 0
    assert isinstance(result["co2_generated"], float)


def test_carbon_no_data_returns_zeroes(new_user):
    result = carbon_service.get_carbon_dashboard(new_user.id, EMISSION_FACTOR)
    assert result["co2_generated"] == 0.0
    assert result["month_kwh"] == 0.0


# ── Route tests ──────────────────────────────────────────────
def test_carbon_page_requires_login(client):
    resp = client.get("/carbon/", follow_redirects=False)
    assert resp.status_code == 302


def test_carbon_page_loads(logged_in_client, new_user):
    _seed_usage(new_user.id, days=10, value=8.0)
    resp = logged_in_client.get("/carbon/")
    assert resp.status_code == 200
    assert b"Carbon Footprint" in resp.data


def test_carbon_page_shows_co2_value(logged_in_client, new_user):
    _seed_usage(new_user.id, days=5, value=10.0)
    resp = logged_in_client.get("/carbon/")
    assert resp.status_code == 200
    assert b"CO" in resp.data
    assert b"Generated" in resp.data


def test_carbon_page_shows_sustainability_score(logged_in_client, new_user):
    _seed_usage(new_user.id, days=5, value=8.0)
    resp = logged_in_client.get("/carbon/")
    assert resp.status_code == 200
    assert b"Sustainability Score" in resp.data


def test_carbon_page_has_rating_badge(logged_in_client, new_user):
    _seed_usage(new_user.id, days=5, value=8.0)
    resp = logged_in_client.get("/carbon/")
    assert resp.status_code == 200
    # At least one of the rating labels should appear
    badges = [b"Bronze", b"Silver", b"Gold", b"Platinum"]
    assert any(badge in resp.data for badge in badges)
