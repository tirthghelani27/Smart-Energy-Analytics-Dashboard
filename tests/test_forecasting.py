# ============================================================
# Forecasting Module Tests
# ============================================================
from datetime import date, timedelta
import pytest
from app import db
from src.models.electricity_usage import ElectricityUsage
from src.models.prediction import Prediction
from src.services import forecasting_service


def _seed_usage(user_id, days=30, base=8.0, step=0.1):
    for i in range(days):
        rec = ElectricityUsage(
            user_id=user_id,
            date=date.today() - timedelta(days=days - i),
            units_consumed=max(1.0, round(base + i * step, 2)),
            source="manual",
        )
        db.session.add(rec)
    db.session.commit()


# ── Service unit tests ───────────────────────────────────────
def test_forecast_returns_no_data_flag_for_insufficient_records(new_user):
    # 3 records — below MIN_RECORDS_REQUIRED (7)
    _seed_usage(new_user.id, days=3)
    result = forecasting_service.generate_forecast(new_user.id, tariff=6.5)
    assert result["has_data"] is False
    assert result["record_count"] == 3


def test_forecast_runs_with_sufficient_data(new_user):
    _seed_usage(new_user.id, days=20)
    result = forecasting_service.generate_forecast(new_user.id, tariff=6.5)
    assert result["has_data"] is True
    assert "linear_regression" in result["models"]
    assert "random_forest" in result["models"]


def test_forecast_predictions_are_positive(new_user):
    _seed_usage(new_user.id, days=20)
    result = forecasting_service.generate_forecast(new_user.id, tariff=6.5)

    for model_key, m in result["models"].items():
        assert m["next_day_kwh"] >= 0, f"{model_key} next_day_kwh negative"
        assert m["next_week_kwh"] >= 0, f"{model_key} next_week_kwh negative"
        assert m["next_month_kwh"] >= 0, f"{model_key} next_month_kwh negative"


def test_forecast_cost_equals_kwh_times_tariff(new_user):
    tariff = 6.5
    _seed_usage(new_user.id, days=20)
    result = forecasting_service.generate_forecast(new_user.id, tariff=tariff)

    for _, m in result["models"].items():
        assert abs(m["next_day_cost"] - m["next_day_kwh"] * tariff) < 0.01
        assert abs(m["next_week_cost"] - m["next_week_kwh"] * tariff) < 0.01
        assert abs(m["next_month_cost"] - m["next_month_kwh"] * tariff) < 0.01


def test_forecast_chart_data_matches_input_length(new_user):
    n = 15
    _seed_usage(new_user.id, days=n)
    result = forecasting_service.generate_forecast(new_user.id, tariff=6.5)
    assert len(result["chart"]["labels"]) == n
    assert len(result["chart"]["actual"]) == n
    assert len(result["chart"]["linear_fit"]) == n
    assert len(result["chart"]["random_fit"]) == n


def test_forecast_mae_rmse_non_negative(new_user):
    _seed_usage(new_user.id, days=20)
    result = forecasting_service.generate_forecast(new_user.id, tariff=6.5)
    for _, m in result["models"].items():
        assert m["mae"] >= 0
        assert m["rmse"] >= 0
        assert 0 <= m["accuracy_pct"] <= 100


def test_forecast_accuracy_pct_bounded(new_user):
    _seed_usage(new_user.id, days=25)
    result = forecasting_service.generate_forecast(new_user.id, tariff=6.5)
    for _, m in result["models"].items():
        assert 0 <= m["accuracy_pct"] <= 100


# ── Route tests ──────────────────────────────────────────────
def test_forecasting_page_requires_login(client):
    resp = client.get("/forecasting/", follow_redirects=False)
    assert resp.status_code == 302


def test_forecasting_page_shows_not_enough_data(logged_in_client, new_user):
    _seed_usage(new_user.id, days=2)
    resp = logged_in_client.get("/forecasting/")
    assert resp.status_code == 200
    assert b"Not enough data" in resp.data or b"not enough" in resp.data.lower()


def test_forecasting_page_shows_predictions(logged_in_client, new_user):
    _seed_usage(new_user.id, days=20)
    resp = logged_in_client.get("/forecasting/")
    assert resp.status_code == 200
    assert b"Linear Regression" in resp.data
    assert b"Random Forest" in resp.data


def test_forecasting_persists_predictions(logged_in_client, new_user):
    _seed_usage(new_user.id, days=20)
    logged_in_client.get("/forecasting/")

    predictions = Prediction.query.filter_by(user_id=new_user.id).all()
    assert len(predictions) > 0


def test_forecasting_page_has_chart(logged_in_client, new_user):
    _seed_usage(new_user.id, days=20)
    resp = logged_in_client.get("/forecasting/")
    assert resp.status_code == 200
    assert b"forecastChart" in resp.data
