# ============================================================
# Model Tests — relationships, FKs, computed fields
# ============================================================
from datetime import date
from app import db
from src.models.user import User
from src.models.electricity_usage import ElectricityUsage
from src.models.appliance import Appliance
from src.models.carbon_footprint import CarbonFootprint, KG_CO2_PER_TREE_MONTH


def test_electricity_usage_compute_cost(new_user):
    rec = ElectricityUsage(user_id=new_user.id, date=date.today(), units_consumed=10)
    rec.compute_cost(6.5)
    assert rec.cost == 65.0
    assert rec.tariff_rate == 6.5


def test_appliance_compute_monthly(new_user):
    appl = Appliance(user_id=new_user.id, name="AC", power_rating_w=1500, daily_usage_hrs=4)
    appl.compute_monthly(6.5, days=30)
    expected_kwh = (1500 / 1000) * 4 * 30
    assert appl.monthly_kwh == round(expected_kwh, 2)
    assert appl.monthly_cost == round(expected_kwh * 6.5, 2)


def test_carbon_footprint_from_kwh():
    cf = CarbonFootprint.from_kwh(user_id=1, month=6, year=2026, kwh=100, emission_factor=0.82)
    assert cf.co2_generated == 82.0
    assert cf.trees_equivalent == round(82.0 / KG_CO2_PER_TREE_MONTH, 1)
    assert 0 <= cf.sustainability_score <= 100


def test_user_relationships_cascade_delete(app, new_user):
    rec = ElectricityUsage(user_id=new_user.id, date=date.today(), units_consumed=5)
    db.session.add(rec)
    db.session.commit()

    assert ElectricityUsage.query.filter_by(user_id=new_user.id).count() == 1

    db.session.delete(new_user)
    db.session.commit()

    assert ElectricityUsage.query.filter_by(user_id=new_user.id).count() == 0


def test_unique_constraint_on_usage_date(new_user):
    rec1 = ElectricityUsage(user_id=new_user.id, date=date.today(), units_consumed=5)
    db.session.add(rec1)
    db.session.commit()

    rec2 = ElectricityUsage(user_id=new_user.id, date=date.today(), units_consumed=8)
    db.session.add(rec2)

    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_is_admin_property():
    admin = User(username="admin1", email="admin1@example.com", role="admin")
    user = User(username="user1", email="user1@example.com", role="user")
    assert admin.is_admin is True
    assert user.is_admin is False


def test_full_name_fallback():
    u = User(username="noname", email="noname@example.com")
    assert u.full_name == "noname"

    u2 = User(username="hasname", email="hasname@example.com", first_name="A", last_name="B")
    assert u2.full_name == "A B"
