# ============================================================
# Reports Routes
# ============================================================
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    current_app, send_from_directory, abort
)
from flask_login import login_required, current_user

from src.services import report_service
from src.models.report import Report

reports_bp = Blueprint("reports", __name__)

REPORT_TYPES = {
    "monthly":        ("Monthly Consumption Report", "fa-calendar-alt", "text-info"),
    "annual":         ("Annual Consumption Report",  "fa-calendar",     "text-success"),
    "forecast":       ("Forecast Report",            "fa-brain",        "text-warning"),
    "carbon":         ("Carbon Footprint Report",     "fa-leaf",         "text-danger"),
    "recommendation": ("Recommendation Report",       "fa-lightbulb",    "text-primary"),
}


@reports_bp.route("/")
@login_required
def index():
    history = report_service.get_user_reports(current_user.id)
    return render_template(
        "reports/index.html",
        report_types=REPORT_TYPES,
        history=history,
    )


@reports_bp.route("/generate/<report_type>")
@login_required
def generate(report_type):
    if report_type not in REPORT_TYPES:
        flash("Unknown report type.", "danger")
        return redirect(url_for("reports.index"))

    tariff = current_app.config["DEFAULT_TARIFF_RATE"]
    emission_factor = current_app.config["CO2_EMISSION_FACTOR"]
    reports_folder = current_app.config["REPORTS_FOLDER"]

    try:
        report = report_service.generate_report(
            report_type, current_user, reports_folder, tariff, emission_factor
        )
        flash(f"{report.title} generated successfully!", "success")
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Report generation failed")
        flash(f"Could not generate report: {exc}", "danger")

    return redirect(url_for("reports.index"))


@reports_bp.route("/download/<int:report_id>")
@login_required
def download(report_id):
    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()
    if not report or not report.file_path:
        abort(404)

    reports_folder = current_app.config["REPORTS_FOLDER"]
    return send_from_directory(
        reports_folder, report.file_path,
        as_attachment=True,
        download_name=f"{report.report_type}_report.pdf",
    )
