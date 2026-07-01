# ============================================================
# Forecasting Service
# Linear Regression & Random Forest forecasting — used by
# src/routes/forecasting.py
# ============================================================
from datetime import date, timedelta

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.models.electricity_usage import ElectricityUsage

MIN_RECORDS_REQUIRED = 7  # need at least a week of data to train


def _load_series(user_id: int):
    """Return ordered (dates, kwh values) for a user."""
    rows = (ElectricityUsage.query
            .filter_by(user_id=user_id)
            .order_by(ElectricityUsage.date.asc())
            .all())
    dates  = [r.date for r in rows]
    values = [r.units_consumed for r in rows]
    return dates, values


def _build_features(dates: list, values: list):
    """
    Build a simple feature matrix:
      X = [day_index, day_of_week, month]
      y = units_consumed
    day_index = number of days since the first record (captures trend).
    """
    if not dates:
        return None, None
    start = dates[0]
    X = np.array([
        [(d - start).days, d.weekday(), d.month]
        for d in dates
    ], dtype=float)
    y = np.array(values, dtype=float)
    return X, y


def _evaluate(model, X, y) -> dict:
    """Train/test split evaluation -> MAE, RMSE, R2."""
    if len(X) < 4:
        # Too little data for a meaningful split — fit on everything,
        # evaluate on the same data (still gives a sense of fit).
        model.fit(X, y)
        preds = model.predict(X)
        y_eval = y
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        y_eval = y_test

    mae  = float(mean_absolute_error(y_eval, preds))
    rmse = float(np.sqrt(mean_squared_error(y_eval, preds)))
    try:
        r2 = float(r2_score(y_eval, preds)) if len(y_eval) > 1 else 0.0
    except ValueError:
        r2 = 0.0

    return {"mae": round(mae, 3), "rmse": round(rmse, 3), "r2": round(max(r2, 0.0), 3)}


def _predict_future(model, last_date: date, start_offset_days: int, horizon_days: int,
                     base_index: int) -> float:
    """
    Predict the total kWh for `horizon_days` starting `start_offset_days`
    after `last_date`, by summing per-day predictions.
    """
    total = 0.0
    for i in range(horizon_days):
        target_date = last_date + timedelta(days=start_offset_days + i)
        day_index = base_index + start_offset_days + i
        features = np.array([[day_index, target_date.weekday(), target_date.month]], dtype=float)
        pred = model.predict(features)[0]
        total += max(pred, 0.0)  # consumption can't be negative
    return round(total, 2)


def generate_forecast(user_id: int, tariff: float) -> dict:
    """
    Train Linear Regression and Random Forest models on the user's
    historical electricity usage, and return predictions for the
    next day, next week, and next month, plus model accuracy metrics.
    """
    dates, values = _load_series(user_id)

    result = {
        "has_data": len(dates) >= MIN_RECORDS_REQUIRED,
        "record_count": len(dates),
        "min_required": MIN_RECORDS_REQUIRED,
        "models": {},
        "chart": {"labels": [], "actual": [], "linear_fit": [], "random_fit": []},
    }

    if not result["has_data"]:
        return result

    X, y = _build_features(dates, values)
    last_date = dates[-1]
    base_index = (last_date - dates[0]).days

    for model_key, model_name, estimator, fit_key in [
        ("linear_regression", "Linear Regression", LinearRegression(), "linear_fit"),
        ("random_forest",     "Random Forest",     RandomForestRegressor(
            n_estimators=100, random_state=42, max_depth=6
        ), "random_fit"),
    ]:
        metrics = _evaluate(estimator, X, y)

        # Re-fit on full data for the actual forecast (after evaluation)
        estimator.fit(X, y)

        next_day   = _predict_future(estimator, last_date, 1, 1,  base_index)
        next_week  = _predict_future(estimator, last_date, 1, 7,  base_index)
        next_month = _predict_future(estimator, last_date, 1, 30, base_index)

        result["models"][model_key] = {
            "name": model_name,
            "next_day_kwh":    next_day,
            "next_week_kwh":   next_week,
            "next_month_kwh":  next_month,
            "next_day_cost":   round(next_day   * tariff, 2),
            "next_week_cost":  round(next_week  * tariff, 2),
            "next_month_cost": round(next_month * tariff, 2),
            "mae":  metrics["mae"],
            "rmse": metrics["rmse"],
            "accuracy_pct": round(metrics["r2"] * 100, 1),
        }

        # Fitted line over historical data (for chart comparison)
        result["chart"][fit_key] = [round(float(v), 2) for v in estimator.predict(X)]

    result["chart"]["labels"] = [d.strftime("%d %b") for d in dates]
    result["chart"]["actual"] = [round(float(v), 2) for v in values]

    return result
