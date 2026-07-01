# ============================================================
# Recommendations Routes
# ============================================================
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from src.services import recommendation_service

recommendations_bp = Blueprint("recommendations", __name__)


@recommendations_bp.route("/")
@login_required
def index():
    tariff = current_app.config["DEFAULT_TARIFF_RATE"]
    data = recommendation_service.get_recommendations(current_user.id, tariff)
    return render_template("recommendations/index.html", **data)


@recommendations_bp.route("/refresh")
@login_required
def refresh():
    tariff = current_app.config["DEFAULT_TARIFF_RATE"]
    recommendation_service.get_recommendations(current_user.id, tariff, regenerate=True)
    flash("Recommendations refreshed based on your latest usage data.", "success")
    return redirect(url_for("recommendations.index"))


@recommendations_bp.route("/apply/<int:rec_id>")
@login_required
def apply(rec_id):
    if recommendation_service.mark_applied(current_user.id, rec_id):
        flash("Marked as applied. Nice work on improving your efficiency!", "success")
    else:
        flash("Recommendation not found.", "danger")
    return redirect(url_for("recommendations.index"))
