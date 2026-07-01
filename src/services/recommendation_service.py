# ============================================================
# Recommendation Service
# Generates energy-saving, appliance, peak-hour, and cost
# reduction recommendations — used by
# src/routes/recommendations.py
# ============================================================
from datetime import date, timedelta

from sqlalchemy import func
from src.extensions import db
from src.models.electricity_usage import ElectricityUsage
from src.models.appliance import Appliance
from src.models.recommendation import Recommendation

# Efficient household baseline (kWh/day) — same benchmark used by carbon_service
EFFICIENT_BASELINE_KWH_PER_DAY = 3.0

# High power appliances above this rating (W) are flagged for optimization
HIGH_POWER_THRESHOLD_W = 1000

# Appliances running more than this many hours/day are flagged
EXCESSIVE_USAGE_HOURS = 8


def _recent_avg_daily_kwh(user_id: int, days: int = 30) -> float:
    cutoff = date.today() - timedelta(days=days)
    total = db.session.query(
        func.coalesce(func.sum(ElectricityUsage.units_consumed), 0)
    ).filter(
        ElectricityUsage.user_id == user_id,
        ElectricityUsage.date >= cutoff,
    ).scalar()

    count = db.session.query(
        func.count(func.distinct(ElectricityUsage.date))
    ).filter(
        ElectricityUsage.user_id == user_id,
        ElectricityUsage.date >= cutoff,
    ).scalar() or 0

    if count == 0:
        return 0.0
    return float(total) / count


def _generate_candidates(user_id: int, tariff: float) -> list[dict]:
    """
    Build a fresh list of recommendation candidates based on the user's
    current usage and appliance data. Each candidate is a dict matching
    the Recommendation model's columns.
    """
    candidates: list[dict] = []
    avg_daily = _recent_avg_daily_kwh(user_id, days=30)

    # ── 1. Energy Saving Recommendations (overall usage) ────
    if avg_daily > EFFICIENT_BASELINE_KWH_PER_DAY:
        excess_daily = avg_daily - EFFICIENT_BASELINE_KWH_PER_DAY
        monthly_kwh_saving = round(excess_daily * 30 * 0.5, 2)  # target 50% of excess
        candidates.append({
            "category": "behaviour",
            "title": "Reduce overall daily consumption",
            "description": (
                f"Your average usage is {avg_daily:.2f} kWh/day, which is "
                f"{excess_daily:.2f} kWh above the efficient household "
                f"benchmark of {EFFICIENT_BASELINE_KWH_PER_DAY} kWh/day. "
                f"Switching off idle devices, using natural light, and "
                f"shifting non-essential loads to off-peak hours could "
                f"cut this gap roughly in half."
            ),
            "potential_saving_kwh": monthly_kwh_saving,
            "potential_saving_cost": round(monthly_kwh_saving * tariff, 2),
            "priority": "high" if excess_daily > 3 else "medium",
        })
    else:
        candidates.append({
            "category": "behaviour",
            "title": "Great job — you're below the efficient usage benchmark!",
            "description": (
                f"Your average usage is {avg_daily:.2f} kWh/day, at or "
                f"below the {EFFICIENT_BASELINE_KWH_PER_DAY} kWh/day "
                f"efficient benchmark. Keep up routines like switching "
                f"off standby devices and using energy-efficient lighting."
            ),
            "potential_saving_kwh": 0.0,
            "potential_saving_cost": 0.0,
            "priority": "low",
        })

    # ── 2. Appliance Optimization Suggestions ────────────────
    appliances = Appliance.query.filter_by(user_id=user_id, is_active=True).all()

    for appl in appliances:
        flags = []
        if appl.power_rating_w >= HIGH_POWER_THRESHOLD_W:
            flags.append("high power rating")
        if appl.daily_usage_hrs >= EXCESSIVE_USAGE_HOURS:
            flags.append(f"runs {appl.daily_usage_hrs:.0f}+ hrs/day")

        if flags:
            # Suggest reducing usage by 1 hour/day
            reduced_hours = max(appl.daily_usage_hrs - 1, 0)
            current_kwh = (appl.power_rating_w / 1000) * appl.daily_usage_hrs * 30
            reduced_kwh = (appl.power_rating_w / 1000) * reduced_hours * 30
            saving_kwh = round(current_kwh - reduced_kwh, 2)

            candidates.append({
                "category": "appliance",
                "title": f"Optimize usage: {appl.name}",
                "description": (
                    f"{appl.name} ({appl.power_rating_w:.0f}W) is flagged for "
                    f"{', '.join(flags)}. Reducing its daily runtime by just "
                    f"1 hour could save approximately {saving_kwh:.2f} kWh per month. "
                    f"Consider using a timer, eco-mode, or scheduling it during "
                    f"off-peak hours."
                ),
                "potential_saving_kwh": saving_kwh,
                "potential_saving_cost": round(saving_kwh * tariff, 2),
                "priority": "high" if appl.power_rating_w >= 1500 else "medium",
            })

    if not appliances:
        candidates.append({
            "category": "appliance",
            "title": "Add your appliances for personalized tips",
            "description": (
                "You haven't added any appliances yet. Add your major "
                "appliances (AC, refrigerator, washing machine, etc.) with "
                "their power rating and daily usage hours to get tailored "
                "optimization suggestions."
            ),
            "potential_saving_kwh": 0.0,
            "potential_saving_cost": 0.0,
            "priority": "low",
        })

    # ── 3. Peak Hour Optimization ─────────────────────────────
    # Identify the weekday with the highest average consumption
    rows = (db.session.query(
                func.extract("dow", ElectricityUsage.date).label("dow")
                if db.engine.dialect.name != "mysql"
                else func.dayofweek(ElectricityUsage.date).label("dow"),
                func.avg(ElectricityUsage.units_consumed).label("avg_kwh"),
            )
            .filter(ElectricityUsage.user_id == user_id)
            .group_by("dow")
            .order_by(func.avg(ElectricityUsage.units_consumed).desc())
            .first())

    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                      "Friday", "Saturday", "Sunday"]

    if rows is not None and rows.avg_kwh:
        # SQLite dow: 0=Sunday..6=Saturday ; MySQL dayofweek: 1=Sunday..7=Saturday
        dow_raw = int(rows.dow)
        if db.engine.dialect.name == "mysql":
            weekday_idx = (dow_raw - 1) % 7  # convert 1-7(Sun-Sat) -> 0-6(Sun-Sat)
            weekday_name = ["Sunday","Monday","Tuesday","Wednesday",
                            "Thursday","Friday","Saturday"][weekday_idx]
        else:
            weekday_idx = dow_raw % 7
            weekday_name = ["Sunday","Monday","Tuesday","Wednesday",
                            "Thursday","Friday","Saturday"][weekday_idx]

        peak_avg = float(rows.avg_kwh)
        shift_saving_kwh = round(peak_avg * 0.15 * 4, 2)  # 15% shift, 4x/month

        candidates.append({
            "category": "peak",
            "title": f"Shift load away from {weekday_name}s",
            "description": (
                f"{weekday_name} shows your highest average consumption "
                f"({peak_avg:.2f} kWh). Shifting heavy tasks like laundry, "
                f"dishwashing, or EV charging to lower-usage days or "
                f"off-peak hours (typically late night/early morning) can "
                f"reduce demand charges and overall cost."
            ),
            "potential_saving_kwh": shift_saving_kwh,
            "potential_saving_cost": round(shift_saving_kwh * tariff, 2),
            "priority": "medium",
        })

    # ── 4. Cost Reduction Suggestions (tariff-based) ──────────
    monthly_kwh = db.session.query(
        func.coalesce(func.sum(ElectricityUsage.units_consumed), 0)
    ).filter(
        ElectricityUsage.user_id == user_id,
        func.extract("month", ElectricityUsage.date) == date.today().month,
        func.extract("year",  ElectricityUsage.date) == date.today().year,
    ).scalar()
    monthly_kwh = float(monthly_kwh)
    monthly_cost = monthly_kwh * tariff

    if monthly_cost > 0:
        # Standby/vampire power: typically 5-10% of a bill
        standby_saving_cost = round(monthly_cost * 0.07, 2)
        standby_saving_kwh = round(standby_saving_cost / tariff, 2) if tariff else 0.0

        candidates.append({
            "category": "billing",
            "title": "Eliminate standby ('vampire') power drain",
            "description": (
                f"Devices left plugged in on standby (TVs, chargers, "
                f"set-top boxes, routers) typically account for 5-10% of "
                f"a household bill. At your current usage, unplugging idle "
                f"devices or using smart power strips could save around "
                f"₹{standby_saving_cost:.2f} per month."
            ),
            "potential_saving_kwh": standby_saving_kwh,
            "potential_saving_cost": standby_saving_cost,
            "priority": "medium",
        })

    return candidates


def get_recommendations(user_id: int, tariff: float, regenerate: bool = False) -> dict:
    """
    Return recommendations for a user. If none exist (or `regenerate` is
    True), generate fresh ones based on current usage/appliance data and
    persist them.
    """
    existing = (Recommendation.query
                .filter_by(user_id=user_id)
                .order_by(Recommendation.created_at.desc())
                .all())

    if regenerate or not existing:
        # Clear old, un-applied recommendations to avoid duplicates piling up
        Recommendation.query.filter_by(user_id=user_id, is_applied=False).delete()
        db.session.commit()

        candidates = _generate_candidates(user_id, tariff)
        for c in candidates:
            db.session.add(Recommendation(user_id=user_id, **c))
        db.session.commit()

        existing = (Recommendation.query
                    .filter_by(user_id=user_id)
                    .order_by(Recommendation.created_at.desc())
                    .all())

    # ── Aggregate savings ────────────────────────────────────
    active_recs = [r for r in existing if not r.is_applied]

    total_monthly_kwh_saving  = sum(r.potential_saving_kwh or 0 for r in active_recs)
    total_monthly_cost_saving = sum(r.potential_saving_cost or 0 for r in active_recs)
    total_annual_cost_saving  = round(total_monthly_cost_saving * 12, 2)
    total_annual_kwh_saving   = round(total_monthly_kwh_saving * 12, 2)

    # ── Efficiency improvement % ──────────────────────────────
    avg_daily = _recent_avg_daily_kwh(user_id, days=30)
    current_monthly_kwh = avg_daily * 30
    if current_monthly_kwh > 0:
        efficiency_improvement_pct = round(
            (total_monthly_kwh_saving / current_monthly_kwh) * 100, 1
        )
    else:
        efficiency_improvement_pct = 0.0

    # ── Group by category for display ────────────────────────
    by_category: dict[str, list] = {"behaviour": [], "appliance": [], "peak": [], "billing": []}
    for r in existing:
        by_category.setdefault(r.category, []).append(r)

    return {
        "recommendations": existing,
        "by_category": by_category,
        "total_monthly_kwh_saving":  round(total_monthly_kwh_saving, 2),
        "total_monthly_cost_saving": round(total_monthly_cost_saving, 2),
        "total_annual_kwh_saving":   total_annual_kwh_saving,
        "total_annual_cost_saving":  total_annual_cost_saving,
        "efficiency_improvement_pct": efficiency_improvement_pct,
        "tariff": tariff,
    }


def mark_applied(user_id: int, recommendation_id: int) -> bool:
    """Mark a recommendation as applied. Returns True on success."""
    rec = Recommendation.query.filter_by(id=recommendation_id, user_id=user_id).first()
    if not rec:
        return False
    rec.is_applied = True
    db.session.commit()
    return True
