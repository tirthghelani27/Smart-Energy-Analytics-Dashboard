# ============================================================
# Forecasting Routes
# ============================================================
from flask import Blueprint, render_template, current_app, flash
from flask_login import login_required, current_user

from src.extensions import db
from src.services import forecasting_service
from src.models.prediction import Prediction

forecasting_bp = Blueprint("forecasting", __name__)


@forecasting_bp.route("/")
@login_required
def index():
    tariff = current_app.config["DEFAULT_TARIFF_RATE"]

    forecast = forecasting_service.generate_forecast(current_user.id, tariff)

    # ── Persist predictions so they appear in history / reports ──
    if forecast["has_data"]:
        from datetime import date, timedelta
        today = date.today()

        for model_key, m in forecast["models"].items():
            for period, days_ahead, units_key, cost_key in [
                ("day",   1,  "next_day_kwh",   "next_day_cost"),
                ("week",  7,  "next_week_kwh",  "next_week_cost"),
                ("month", 30, "next_month_kwh", "next_month_cost"),
            ]:
                existing = Prediction.query.filter_by(
                    user_id=current_user.id,
                    period=period,
                    model_used=model_key,
                ).order_by(Prediction.created_at.desc()).first()

                # Only insert a fresh row if none exists yet for today
                if not existing or existing.prediction_date != today:
                    pred = Prediction(
                        user_id=current_user.id,
                        prediction_date=today + timedelta(days=days_ahead),
                        period=period,
                        predicted_units=m[units_key],
                        predicted_cost=m[cost_key],
                        model_used=model_key,
                        mae=m["mae"],
                        rmse=m["rmse"],
                        r2_score=m["accuracy_pct"] / 100,
                    )
                    db.session.add(pred)
        db.session.commit()
    else:
        flash(
            f"Add at least {forecast['min_required']} days of usage data to "
            f"enable forecasting (you have {forecast['record_count']}).",
            "info"
        )

    return render_template(
        "forecasting/index.html",
        forecast = forecast,
        tariff   = tariff,
    )
