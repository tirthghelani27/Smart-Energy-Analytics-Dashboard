# ============================================================
# Admin Service
# Aggregated platform-wide stats and management helpers — used
# by src/routes/admin.py
# ============================================================
from calendar import month_name

from sqlalchemy import func
from src.extensions import db
from src.models.user import User
from src.models.electricity_usage import ElectricityUsage
from src.models.carbon_footprint import CarbonFootprint
from src.models.report import Report
from src.models.alert import Alert
from src.models.prediction import Prediction


def get_admin_dashboard() -> dict:
    """Aggregate platform-wide KPIs and chart data for the admin dashboard."""

    total_users  = db.session.query(func.count(User.id)).scalar() or 0
    active_users = db.session.query(func.count(User.id)).filter_by(is_active=True).scalar() or 0
    admin_users  = db.session.query(func.count(User.id)).filter_by(role="admin").scalar() or 0

    total_energy_kwh = db.session.query(
        func.coalesce(func.sum(ElectricityUsage.units_consumed), 0)
    ).scalar()
    total_energy_kwh = round(float(total_energy_kwh), 2)

    total_carbon_saved = db.session.query(
        func.coalesce(func.sum(CarbonFootprint.co2_saved), 0)
    ).scalar()
    total_carbon_saved = round(float(total_carbon_saved), 2)

    total_carbon_generated = db.session.query(
        func.coalesce(func.sum(CarbonFootprint.co2_generated), 0)
    ).scalar()
    total_carbon_generated = round(float(total_carbon_generated), 2)

    total_reports = db.session.query(func.count(Report.id)).scalar() or 0
    total_predictions = db.session.query(func.count(Prediction.id)).scalar() or 0

    unread_alerts = db.session.query(func.count(Alert.id)).filter_by(is_read=False).scalar() or 0
    total_alerts  = db.session.query(func.count(Alert.id)).scalar() or 0

    total_records = db.session.query(func.count(ElectricityUsage.id)).scalar() or 0

    # ── New users per month (last 12 months) ────────────────
    user_rows = (db.session.query(
                    func.extract("year",  User.created_at).label("yr"),
                    func.extract("month", User.created_at).label("mo"),
                    func.count(User.id).label("cnt"),
                )
                .group_by("yr", "mo")
                .order_by("yr", "mo")
                .limit(12)
                .all())
    user_chart_labels = [f"{month_name[int(r.mo)][:3]} {int(r.yr)}" for r in user_rows]
    user_chart_values = [int(r.cnt) for r in user_rows]

    # ── Platform-wide energy usage per month (last 12 months) ─
    energy_rows = (db.session.query(
                    func.extract("year",  ElectricityUsage.date).label("yr"),
                    func.extract("month", ElectricityUsage.date).label("mo"),
                    func.sum(ElectricityUsage.units_consumed).label("kwh"),
                )
                .group_by("yr", "mo")
                .order_by("yr", "mo")
                .limit(12)
                .all())
    energy_chart_labels = [f"{month_name[int(r.mo)][:3]} {int(r.yr)}" for r in energy_rows]
    energy_chart_values = [round(float(r.kwh), 2) for r in energy_rows]

    return {
        "total_users": total_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "total_energy_kwh": total_energy_kwh,
        "total_carbon_saved": total_carbon_saved,
        "total_carbon_generated": total_carbon_generated,
        "total_reports": total_reports,
        "total_predictions": total_predictions,
        "total_alerts": total_alerts,
        "unread_alerts": unread_alerts,
        "total_records": total_records,
        "user_chart_labels": user_chart_labels,
        "user_chart_values": user_chart_values,
        "energy_chart_labels": energy_chart_labels,
        "energy_chart_values": energy_chart_values,
    }


# ── User Management ──────────────────────────────────────────
def get_all_users(page: int = 1, per_page: int = 10):
    return (User.query
            .order_by(User.created_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False))


def toggle_user_active(user_id: int) -> User | None:
    user = db.session.get(User, user_id)
    if not user:
        return None
    user.is_active = not user.is_active
    db.session.commit()
    return user


def toggle_user_role(user_id: int) -> User | None:
    user = db.session.get(User, user_id)
    if not user:
        return None
    user.role = "user" if user.role == "admin" else "admin"
    db.session.commit()
    return user


def delete_user(user_id: int) -> bool:
    user = db.session.get(User, user_id)
    if not user:
        return False
    db.session.delete(user)
    db.session.commit()
    return True


# ── Dataset (usage record) Management ────────────────────────
def get_recent_usage_records(limit: int = 50):
    return (db.session.query(ElectricityUsage, User)
            .join(User, ElectricityUsage.user_id == User.id)
            .order_by(ElectricityUsage.created_at.desc())
            .limit(limit)
            .all())


def delete_usage_record(record_id: int) -> bool:
    record = db.session.get(ElectricityUsage, record_id)
    if not record:
        return False
    db.session.delete(record)
    db.session.commit()
    return True


# ── Alert Management ──────────────────────────────────────────
def get_recent_alerts(limit: int = 50):
    return (db.session.query(Alert, User)
            .join(User, Alert.user_id == User.id)
            .order_by(Alert.triggered_at.desc())
            .limit(limit)
            .all())


def mark_alert_read(alert_id: int) -> bool:
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return False
    alert.is_read = True
    db.session.commit()
    return True


def delete_alert(alert_id: int) -> bool:
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return False
    db.session.delete(alert)
    db.session.commit()
    return True
