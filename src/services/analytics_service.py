# ============================================================
# Analytics Service
# Business logic for consumption analytics (daily/weekly/
# monthly/yearly) — used by src/routes/analytics.py
# ============================================================
from datetime import date, timedelta
from calendar import month_name

from sqlalchemy import func
from src.extensions import db
from src.models.electricity_usage import ElectricityUsage


def _empty_stats() -> dict:
    """Return zeroed-out stats so templates never crash on no data."""
    return {
        "total": 0.0,
        "average": 0.0,
        "highest": 0.0,
        "lowest": 0.0,
        "growth_rate": 0.0,
        "count": 0,
    }


def _growth_rate(values: list[float]) -> float:
    """% change between the first half and second half of the series."""
    if len(values) < 2:
        return 0.0
    mid = len(values) // 2
    first_half  = values[:mid] or values[:1]
    second_half = values[mid:] or values[-1:]
    avg_first  = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    if avg_first == 0:
        return 0.0 if avg_second == 0 else 100.0
    return round(((avg_second - avg_first) / avg_first) * 100, 2)


def _build_stats(values: list[float]) -> dict:
    if not values:
        return _empty_stats()
    return {
        "total":       round(sum(values), 2),
        "average":     round(sum(values) / len(values), 2),
        "highest":     round(max(values), 2),
        "lowest":      round(min(values), 2),
        "growth_rate": _growth_rate(values),
        "count":       len(values),
    }


# ── Daily Analytics (last N days) ────────────────────────────
def get_daily_analytics(user_id: int, days: int = 30) -> dict:
    cutoff = date.today() - timedelta(days=days)

    rows = (db.session.query(
                ElectricityUsage.date,
                func.sum(ElectricityUsage.units_consumed).label("kwh"),
            )
            .filter(ElectricityUsage.user_id == user_id,
                    ElectricityUsage.date >= cutoff)
            .group_by(ElectricityUsage.date)
            .order_by(ElectricityUsage.date)
            .all())

    labels = [r.date.strftime("%d %b") for r in rows]
    values = [round(float(r.kwh), 2) for r in rows]

    stats = _build_stats(values)
    return {"labels": labels, "values": values, "stats": stats}


# ── Weekly Analytics (last N weeks) ──────────────────────────
def get_weekly_analytics(user_id: int, weeks: int = 12) -> dict:
    cutoff = date.today() - timedelta(weeks=weeks)

    if db.engine.dialect.name == "sqlite":
        week_expr = func.strftime("%Y-W%W", ElectricityUsage.date)
    else:
        week_expr = func.concat(
            func.year(ElectricityUsage.date), "-W",
            func.lpad(func.week(ElectricityUsage.date), 2, "0")
        )

    rows = (db.session.query(
                week_expr.label("wk"),
                func.min(ElectricityUsage.date).label("wk_start"),
                func.sum(ElectricityUsage.units_consumed).label("kwh"),
            )
            .filter(ElectricityUsage.user_id == user_id,
                    ElectricityUsage.date >= cutoff)
            .group_by("wk")
            .order_by("wk_start")
            .all())

    labels = [f"Week of {r.wk_start.strftime('%d %b')}" for r in rows]
    values = [round(float(r.kwh), 2) for r in rows]

    stats = _build_stats(values)
    return {"labels": labels, "values": values, "stats": stats}


# ── Monthly Analytics (last N months) ────────────────────────
def get_monthly_analytics(user_id: int, months: int = 12) -> dict:
    rows = (db.session.query(
                func.extract("year",  ElectricityUsage.date).label("yr"),
                func.extract("month", ElectricityUsage.date).label("mo"),
                func.sum(ElectricityUsage.units_consumed).label("kwh"),
            )
            .filter(ElectricityUsage.user_id == user_id)
            .group_by("yr", "mo")
            .order_by("yr", "mo")
            .limit(months)
            .all())

    labels = [f"{month_name[int(r.mo)][:3]} {int(r.yr)}" for r in rows]
    values = [round(float(r.kwh), 2) for r in rows]

    stats = _build_stats(values)
    return {"labels": labels, "values": values, "stats": stats}


# ── Yearly Analytics (all years) ─────────────────────────────
def get_yearly_analytics(user_id: int) -> dict:
    rows = (db.session.query(
                func.extract("year", ElectricityUsage.date).label("yr"),
                func.sum(ElectricityUsage.units_consumed).label("kwh"),
            )
            .filter(ElectricityUsage.user_id == user_id)
            .group_by("yr")
            .order_by("yr")
            .all())

    labels = [str(int(r.yr)) for r in rows]
    values = [round(float(r.kwh), 2) for r in rows]

    stats = _build_stats(values)
    return {"labels": labels, "values": values, "stats": stats}


# ── Peak usage helpers ────────────────────────────────────────
def get_peak_day(user_id: int):
    """Return the ElectricityUsage row with the highest consumption."""
    return (ElectricityUsage.query
            .filter_by(user_id=user_id)
            .order_by(ElectricityUsage.units_consumed.desc())
            .first())


def get_lowest_day(user_id: int):
    """Return the ElectricityUsage row with the lowest consumption."""
    return (ElectricityUsage.query
            .filter_by(user_id=user_id)
            .order_by(ElectricityUsage.units_consumed.asc())
            .first())
