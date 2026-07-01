# ============================================================
# Appliance Service
# CRUD + monthly cost computation — used by
# src/routes/appliances.py
# ============================================================
from src.extensions import db
from src.models.appliance import Appliance

APPLIANCE_CATEGORIES = [
    "Air Conditioner", "Refrigerator", "Washing Machine", "Television",
    "Lights", "Fans", "Water Heater", "Computer", "Other",
]


def get_user_appliances(user_id: int, tariff: float) -> dict:
    appliances = (Appliance.query
                  .filter_by(user_id=user_id)
                  .order_by(Appliance.monthly_kwh.desc())
                  .all())

    # Ensure computed fields are fresh
    changed = False
    for a in appliances:
        old_kwh, old_cost = a.monthly_kwh, a.monthly_cost
        a.compute_monthly(tariff)
        if a.monthly_kwh != old_kwh or a.monthly_cost != old_cost:
            changed = True
    if changed:
        db.session.commit()

    total_kwh  = round(sum(a.monthly_kwh or 0 for a in appliances if a.is_active), 2)
    total_cost = round(sum(a.monthly_cost or 0 for a in appliances if a.is_active), 2)

    # ── Ranking & consumption share ──────────────────────────
    ranked = []
    for a in appliances:
        share = round((a.monthly_kwh / total_kwh) * 100, 1) if total_kwh > 0 and a.is_active else 0.0
        ranked.append({"appliance": a, "share": share})

    chart_labels = [a.name for a in appliances if a.is_active]
    chart_values = [round(a.monthly_kwh or 0, 2) for a in appliances if a.is_active]

    return {
        "appliances": appliances,
        "ranked": ranked,
        "total_kwh": total_kwh,
        "total_cost": total_cost,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "categories": APPLIANCE_CATEGORIES,
        "tariff": tariff,
    }


def add_appliance(user_id: int, name: str, category: str,
                   power_rating_w: float, daily_usage_hrs: float, tariff: float) -> Appliance:
    appliance = Appliance(
        user_id=user_id,
        name=name,
        category=category,
        power_rating_w=power_rating_w,
        daily_usage_hrs=daily_usage_hrs,
        is_active=True,
    )
    appliance.compute_monthly(tariff)
    db.session.add(appliance)
    db.session.commit()
    return appliance


def update_appliance(user_id: int, appliance_id: int, **fields) -> Appliance | None:
    appliance = Appliance.query.filter_by(id=appliance_id, user_id=user_id).first()
    if not appliance:
        return None
    for key, value in fields.items():
        if hasattr(appliance, key) and value is not None:
            setattr(appliance, key, value)
    db.session.commit()
    return appliance


def toggle_appliance_active(user_id: int, appliance_id: int) -> Appliance | None:
    appliance = Appliance.query.filter_by(id=appliance_id, user_id=user_id).first()
    if not appliance:
        return None
    appliance.is_active = not appliance.is_active
    db.session.commit()
    return appliance


def delete_appliance(user_id: int, appliance_id: int) -> bool:
    appliance = Appliance.query.filter_by(id=appliance_id, user_id=user_id).first()
    if not appliance:
        return False
    db.session.delete(appliance)
    db.session.commit()
    return True
