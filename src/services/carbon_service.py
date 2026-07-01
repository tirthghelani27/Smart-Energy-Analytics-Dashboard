# ============================================================
# Carbon Footprint Service
# Business logic for carbon emissions / savings — used by
# src/routes/carbon.py
# ============================================================
from datetime import date
from calendar import month_name

from sqlalchemy import func
from src.extensions import db
from src.models.electricity_usage import ElectricityUsage
from src.models.carbon_footprint import CarbonFootprint, KG_CO2_PER_TREE_MONTH

# A reasonably efficient household uses ~3 kWh/day as a "good" benchmark.
# Anything consumed below this baseline counts as "CO2 saved".
EFFICIENT_BASELINE_KWH_PER_DAY = 3.0


def _sustainability_rating(score: float) -> dict:
    """Map a 0-100 score to a rating tier with display info."""
    if score >= 85:
        return {"label": "Platinum", "color": "info",     "icon": "fa-gem"}
    if score >= 70:
        return {"label": "Gold",     "color": "warning",  "icon": "fa-trophy"}
    if score >= 50:
        return {"label": "Silver",   "color": "secondary","icon": "fa-medal"}
    return {"label": "Bronze",       "color": "danger",    "icon": "fa-award"}


def get_carbon_dashboard(user_id: int, emission_factor: float) -> dict:
    """
    Compute everything the carbon dashboard needs:
      - current month CO2 generated / saved / trees / score
      - annual (year-to-date) CO2 generated
      - monthly trend chart data (CO2 generated per month)
      - sustainability rating tier
    """
    today = date.today()
    cur_month, cur_year = today.month, today.year

    # ── Current month consumption ───────────────────────────
    month_kwh = db.session.query(
        func.coalesce(func.sum(ElectricityUsage.units_consumed), 0)
    ).filter(
        ElectricityUsage.user_id == user_id,
        func.extract("month", ElectricityUsage.date) == cur_month,
        func.extract("year",  ElectricityUsage.date) == cur_year,
    ).scalar()
    month_kwh = float(month_kwh)

    # Days with data this month (for baseline comparison)
    days_with_data = db.session.query(
        func.count(func.distinct(ElectricityUsage.date))
    ).filter(
        ElectricityUsage.user_id == user_id,
        func.extract("month", ElectricityUsage.date) == cur_month,
        func.extract("year",  ElectricityUsage.date) == cur_year,
    ).scalar() or 0

    co2_generated = round(month_kwh * emission_factor, 2)

    # ── CO2 saved vs. an "efficient" baseline ───────────────
    baseline_kwh = EFFICIENT_BASELINE_KWH_PER_DAY * days_with_data
    saved_kwh = max(baseline_kwh - month_kwh, 0)
    co2_saved = round(saved_kwh * emission_factor, 2)

    trees_equivalent = round(co2_generated / KG_CO2_PER_TREE_MONTH, 1)

    # Sustainability score — lower CO2 relative to baseline = higher score
    if baseline_kwh > 0:
        ratio = month_kwh / baseline_kwh
        score = max(0.0, min(100.0, round(100 - (ratio - 1) * 100, 1)))
    else:
        score = 0.0

    rating = _sustainability_rating(score)

    # ── Annual (year-to-date) emissions ─────────────────────
    annual_kwh = db.session.query(
        func.coalesce(func.sum(ElectricityUsage.units_consumed), 0)
    ).filter(
        ElectricityUsage.user_id == user_id,
        func.extract("year", ElectricityUsage.date) == cur_year,
    ).scalar()
    annual_co2 = round(float(annual_kwh) * emission_factor, 2)

    # ── Monthly CO2 trend (last 12 months) ──────────────────
    rows = (db.session.query(
                func.extract("year",  ElectricityUsage.date).label("yr"),
                func.extract("month", ElectricityUsage.date).label("mo"),
                func.sum(ElectricityUsage.units_consumed).label("kwh"),
            )
            .filter(ElectricityUsage.user_id == user_id)
            .group_by("yr", "mo")
            .order_by("yr", "mo")
            .limit(12)
            .all())

    chart_labels = [f"{month_name[int(r.mo)][:3]} {int(r.yr)}" for r in rows]
    chart_co2    = [round(float(r.kwh) * emission_factor, 2) for r in rows]

    # ── Persist / update this month's record ────────────────
    record = CarbonFootprint.query.filter_by(
        user_id=user_id, month=cur_month, year=cur_year
    ).first()

    if record:
        record.co2_generated = co2_generated
        record.co2_saved = co2_saved
        record.trees_equivalent = trees_equivalent
        record.sustainability_score = score
    else:
        record = CarbonFootprint.from_kwh(
            user_id=user_id, month=cur_month, year=cur_year,
            kwh=month_kwh, emission_factor=emission_factor
        )
        record.co2_saved = co2_saved
        db.session.add(record)

    db.session.commit()

    return {
        "month_kwh":        round(month_kwh, 2),
        "co2_generated":    co2_generated,
        "co2_saved":        co2_saved,
        "trees_equivalent": trees_equivalent,
        "sustainability_score": score,
        "rating":           rating,
        "annual_co2":       annual_co2,
        "chart_labels":     chart_labels,
        "chart_co2":        chart_co2,
        "cur_month_name":   month_name[cur_month],
        "cur_year":         cur_year,
        "emission_factor":  emission_factor,
    }
