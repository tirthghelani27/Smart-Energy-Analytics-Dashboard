# ============================================================
# Appliance Routes
# ============================================================
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from src.extensions import db
from src.services import appliance_service

appliances_bp = Blueprint("appliances", __name__)


@appliances_bp.route("/")
@login_required
def index():
    tariff = current_app.config["DEFAULT_TARIFF_RATE"]
    data = appliance_service.get_user_appliances(current_user.id, tariff)
    return render_template("appliances/index.html", **data)


@appliances_bp.route("/add", methods=["POST"])
@login_required
def add():
    tariff = current_app.config["DEFAULT_TARIFF_RATE"]

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Other").strip()

    try:
        power = float(request.form.get("power_rating_w", 0))
        hours = float(request.form.get("daily_usage_hrs", 0))
    except ValueError:
        flash("Power rating and daily usage hours must be numbers.", "danger")
        return redirect(url_for("appliances.index"))

    if not name:
        flash("Appliance name is required.", "danger")
        return redirect(url_for("appliances.index"))
    if power <= 0:
        flash("Power rating must be greater than 0.", "danger")
        return redirect(url_for("appliances.index"))
    if not (0 <= hours <= 24):
        flash("Daily usage hours must be between 0 and 24.", "danger")
        return redirect(url_for("appliances.index"))

    appliance_service.add_appliance(current_user.id, name, category, power, hours, tariff)
    flash(f"'{name}' added successfully.", "success")
    return redirect(url_for("appliances.index"))


@appliances_bp.route("/<int:appliance_id>/edit", methods=["POST"])
@login_required
def edit(appliance_id):
    tariff = current_app.config["DEFAULT_TARIFF_RATE"]

    fields = {}
    name = request.form.get("name", "").strip()
    if name:
        fields["name"] = name

    category = request.form.get("category", "").strip()
    if category:
        fields["category"] = category

    try:
        if request.form.get("power_rating_w"):
            fields["power_rating_w"] = float(request.form["power_rating_w"])
        if request.form.get("daily_usage_hrs"):
            fields["daily_usage_hrs"] = float(request.form["daily_usage_hrs"])
    except ValueError:
        flash("Power rating and daily usage hours must be numbers.", "danger")
        return redirect(url_for("appliances.index"))

    appliance = appliance_service.update_appliance(current_user.id, appliance_id, **fields)
    if appliance:
        appliance.compute_monthly(tariff)
        db.session.commit()
        flash(f"'{appliance.name}' updated.", "success")
    else:
        flash("Appliance not found.", "danger")

    return redirect(url_for("appliances.index"))


@appliances_bp.route("/<int:appliance_id>/toggle")
@login_required
def toggle(appliance_id):
    appliance = appliance_service.toggle_appliance_active(current_user.id, appliance_id)
    if appliance:
        status = "activated" if appliance.is_active else "deactivated"
        flash(f"'{appliance.name}' {status}.", "success")
    else:
        flash("Appliance not found.", "danger")
    return redirect(url_for("appliances.index"))


@appliances_bp.route("/<int:appliance_id>/delete")
@login_required
def delete(appliance_id):
    if appliance_service.delete_appliance(current_user.id, appliance_id):
        flash("Appliance removed.", "success")
    else:
        flash("Appliance not found.", "danger")
    return redirect(url_for("appliances.index"))
