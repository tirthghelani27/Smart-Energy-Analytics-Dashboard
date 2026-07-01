# ============================================================
# Dashboard Route — real data from DB
# ============================================================
from datetime import date
from calendar import month_name
from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from src.extensions import db
from src.models.electricity_usage import ElectricityUsage
from src.models.alert import Alert

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    today      = date.today()
    cur_month  = today.month
    cur_year   = today.year
    tariff     = current_app.config["DEFAULT_TARIFF_RATE"]
    co2_factor = current_app.config["CO2_EMISSION_FACTOR"]

    # ── Total all-time consumption ──────────────────────────
    total_kwh = db.session.query(
        func.coalesce(func.sum(ElectricityUsage.units_consumed), 0)
    ).filter_by(user_id=current_user.id).scalar()

    # ── Current month consumption ───────────────────────────
    month_kwh = db.session.query(
        func.coalesce(func.sum(ElectricityUsage.units_consumed), 0)
    ).filter(
        ElectricityUsage.user_id == current_user.id,
        func.extract("month", ElectricityUsage.date) == cur_month,
        func.extract("year",  ElectricityUsage.date) == cur_year,
    ).scalar()

    estimated_bill = round(float(month_kwh) * tariff, 2)
    carbon_month   = round(float(month_kwh) * co2_factor, 2)

    # ── Unread alerts ───────────────────────────────────────
    unread_alerts = Alert.query.filter_by(
        user_id=current_user.id, is_read=False
    ).order_by(Alert.triggered_at.desc()).limit(5).all()

    # ── Last 12 months chart data ───────────────────────────
    rows = db.session.query(
        func.extract("year",  ElectricityUsage.date).label("yr"),
        func.extract("month", ElectricityUsage.date).label("mo"),
        func.sum(ElectricityUsage.units_consumed).label("kwh"),
    ).filter_by(user_id=current_user.id).group_by("yr", "mo").order_by("yr", "mo").limit(12).all()

    chart_labels = [f"{month_name[int(r.mo)][:3]} {int(r.yr)}" for r in rows]
    chart_values = [round(float(r.kwh), 2) for r in rows]

    # ── Recent records (last 7 days) ────────────────────────
    recent = (ElectricityUsage.query
              .filter_by(user_id=current_user.id)
              .order_by(ElectricityUsage.date.desc())
              .limit(7).all())

    return render_template("dashboard/index.html",
        total_kwh      = round(float(total_kwh), 2),
        month_kwh      = round(float(month_kwh), 2),
        estimated_bill = estimated_bill,
        carbon_month   = carbon_month,
        unread_alerts  = unread_alerts,
        alert_count    = len(unread_alerts),
        chart_labels   = chart_labels,
        chart_values   = chart_values,
        recent_records = recent,
        cur_month_name = month_name[cur_month],
        cur_year       = cur_year,
        tariff         = tariff,
    )
