# ============================================================
# Analytics Routes
# ============================================================
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from src.services import analytics_service

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/")
@login_required
def index():
    period = request.args.get("period", "monthly")  # daily / weekly / monthly / yearly

    if period == "daily":
        data = analytics_service.get_daily_analytics(current_user.id, days=30)
    elif period == "weekly":
        data = analytics_service.get_weekly_analytics(current_user.id, weeks=12)
    elif period == "yearly":
        data = analytics_service.get_yearly_analytics(current_user.id)
    else:
        period = "monthly"
        data = analytics_service.get_monthly_analytics(current_user.id, months=12)

    peak_day   = analytics_service.get_peak_day(current_user.id)
    lowest_day = analytics_service.get_lowest_day(current_user.id)

    return render_template(
        "analytics/index.html",
        period       = period,
        chart_labels = data["labels"],
        chart_values = data["values"],
        stats        = data["stats"],
        peak_day     = peak_day,
        lowest_day   = lowest_day,
    )
