# ============================================================
# Data Import Routes
# ============================================================
import os
from datetime import datetime, timezone, date as date_type

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from src.services import data_import_service

data_import_bp = Blueprint("data_import", __name__)

# Absolute max file size enforced in the route itself (belt-and-suspenders
# alongside Flask's MAX_CONTENT_LENGTH which triggers a 413 before this).
_MAX_BYTES = 16 * 1024 * 1024  # 16 MB


def _allowed_file(filename: str) -> bool:
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


@data_import_bp.route("/import")
@login_required
def index():
    recent = data_import_service.get_recent_imports(current_user.id, limit=20)
    return render_template("data_import/index.html", recent=recent, report=None)


@data_import_bp.route("/import/upload", methods=["POST"])
@login_required
def upload():
    tariff = current_app.config["DEFAULT_TARIFF_RATE"]

    if "file" not in request.files or not request.files["file"].filename:
        flash("Please select a CSV or Excel file to upload.", "danger")
        return redirect(url_for("data_import.index"))

    file = request.files["file"]

    # Security: validate file extension before touching content
    if not _allowed_file(file.filename):
        flash("Invalid file type. Allowed: CSV, XLSX, XLS.", "danger")
        return redirect(url_for("data_import.index"))

    # Security: secure_filename strips path separators and dangerous chars
    filename = secure_filename(file.filename)
    if not filename:
        flash("Invalid filename.", "danger")
        return redirect(url_for("data_import.index"))

    # Namespace saved file by user id + timestamp to prevent collisions
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    saved_name = f"u{current_user.id}_{ts}_{filename}"
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], saved_name)

    # Security: ensure resolved path stays inside UPLOAD_FOLDER
    upload_folder = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
    real_path = os.path.realpath(save_path)
    if not real_path.startswith(upload_folder + os.sep):
        flash("Invalid file path.", "danger")
        return redirect(url_for("data_import.index"))

    file.save(save_path)

    # Verify saved file isn't oversized (defence-in-depth)
    if os.path.getsize(save_path) > _MAX_BYTES:
        os.remove(save_path)
        flash("File is too large. Maximum size is 16 MB.", "danger")
        return redirect(url_for("data_import.index"))

    report = data_import_service.process_csv(save_path, current_user.id, tariff)

    if report["errors"]:
        for err in report["errors"]:
            flash(err, "danger")
    else:
        skipped = (
            report["missing_values"]
            + report["invalid_records"]
            + report["date_format_errors"]
            + report["duplicate_records"]
        )
        flash(
            f"Import complete: {report['inserted_rows']} added, "
            f"{report['updated_rows']} updated, {skipped} row(s) skipped.",
            "success" if (report["inserted_rows"] or report["updated_rows"]) else "warning",
        )

    recent = data_import_service.get_recent_imports(current_user.id, limit=20)
    return render_template("data_import/index.html", recent=recent, report=report)


@data_import_bp.route("/import/manual", methods=["POST"])
@login_required
def manual_entry():
    tariff = current_app.config["DEFAULT_TARIFF_RATE"]

    date_str = request.form.get("date", "").strip()
    units_str = request.form.get("units_consumed", "").strip()
    notes = request.form.get("notes", "").strip() or None

    if not date_str:
        flash("Date is required.", "danger")
        return redirect(url_for("data_import.index"))

    if not units_str:
        flash("Units consumed is required.", "danger")
        return redirect(url_for("data_import.index"))

    try:
        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Please provide a valid date in YYYY-MM-DD format.", "danger")
        return redirect(url_for("data_import.index"))

    # Prevent future-dated entries
    if entry_date > date_type.today():
        flash("Cannot add usage data for a future date.", "danger")
        return redirect(url_for("data_import.index"))

    try:
        units = float(units_str)
    except ValueError:
        flash("Units consumed must be a number.", "danger")
        return redirect(url_for("data_import.index"))

    # Truncate notes to DB column limit
    if notes and len(notes) > 500:
        notes = notes[:500]

    success, message = data_import_service.add_manual_entry(
        current_user.id, entry_date, units, tariff, notes
    )
    flash(message, "success" if success else "danger")
    return redirect(url_for("data_import.index"))
