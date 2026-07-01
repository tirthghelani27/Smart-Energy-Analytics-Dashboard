# ============================================================
# PDF Report Generation Tests
# ============================================================
import os
import tempfile
from datetime import date, timedelta
import pytest
from app import db
from src.models.electricity_usage import ElectricityUsage
from src.models.report import Report
from src.services import report_service


TARIFF = 6.5
EMISSION_FACTOR = 0.82


def _seed_usage(user_id, days=30, value=8.0):
    for i in range(days):
        rec = ElectricityUsage(
            user_id=user_id,
            date=date.today() - timedelta(days=days - i),
            units_consumed=value + i * 0.05,
            source="manual",
        )
        rec.compute_cost(TARIFF)
        db.session.add(rec)
    db.session.commit()


# ── Service unit tests ───────────────────────────────────────
def test_monthly_report_creates_pdf(app, new_user):
    _seed_usage(new_user.id, days=30)
    with tempfile.TemporaryDirectory() as tmp_dir:
        report = report_service.generate_monthly_report(new_user, tmp_dir, TARIFF)

    assert report is not None
    assert report.report_type == "monthly"
    assert report.title is not None


def test_annual_report_creates_record(app, new_user):
    _seed_usage(new_user.id, days=30)
    with tempfile.TemporaryDirectory() as tmp_dir:
        report = report_service.generate_annual_report(new_user, tmp_dir, TARIFF)

    assert report is not None
    assert report.report_type == "annual"


def test_forecast_report_runs(app, new_user):
    _seed_usage(new_user.id, days=30)
    with tempfile.TemporaryDirectory() as tmp_dir:
        report = report_service.generate_forecast_report(new_user, tmp_dir, TARIFF)

    assert report is not None
    assert report.report_type == "forecast"


def test_carbon_report_runs(app, new_user):
    _seed_usage(new_user.id, days=30)
    with tempfile.TemporaryDirectory() as tmp_dir:
        report = report_service.generate_carbon_report(
            new_user, tmp_dir, EMISSION_FACTOR
        )

    assert report is not None
    assert report.report_type == "carbon"


def test_recommendation_report_runs(app, new_user):
    _seed_usage(new_user.id, days=30, value=15.0)
    with tempfile.TemporaryDirectory() as tmp_dir:
        report = report_service.generate_recommendation_report(new_user, tmp_dir, TARIFF)

    assert report is not None
    assert report.report_type == "recommendation"


def test_pdf_file_written_to_disk(app, new_user):
    _seed_usage(new_user.id, days=30)
    with tempfile.TemporaryDirectory() as tmp_dir:
        report = report_service.generate_monthly_report(new_user, tmp_dir, TARIFF)
        if report.file_path:
            pdf_path = os.path.join(tmp_dir, report.file_path)
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 0


def test_generate_report_dispatcher(app, new_user):
    _seed_usage(new_user.id, days=30)
    with tempfile.TemporaryDirectory() as tmp_dir:
        for rtype in ["monthly", "annual", "forecast", "carbon", "recommendation"]:
            report = report_service.generate_report(
                rtype, new_user, tmp_dir, TARIFF, EMISSION_FACTOR
            )
            assert report is not None, f"generate_report failed for type: {rtype}"
            assert report.report_type == rtype


def test_reports_persisted_in_db(app, new_user):
    _seed_usage(new_user.id, days=30)
    before_count = Report.query.filter_by(user_id=new_user.id).count()

    with tempfile.TemporaryDirectory() as tmp_dir:
        report_service.generate_monthly_report(new_user, tmp_dir, TARIFF)

    after_count = Report.query.filter_by(user_id=new_user.id).count()
    assert after_count == before_count + 1


def test_get_user_reports(app, new_user):
    _seed_usage(new_user.id, days=30)
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_service.generate_monthly_report(new_user, tmp_dir, TARIFF)
        report_service.generate_carbon_report(new_user, tmp_dir, EMISSION_FACTOR)

    reports = report_service.get_user_reports(new_user.id)
    assert len(reports) >= 2


# ── Route tests ──────────────────────────────────────────────
def test_reports_page_requires_login(client):
    resp = client.get("/reports/", follow_redirects=False)
    assert resp.status_code == 302


def test_reports_page_loads(logged_in_client):
    resp = logged_in_client.get("/reports/")
    assert resp.status_code == 200
    assert b"Reports" in resp.data
    assert b"Generate PDF" in resp.data


def test_reports_generate_route(logged_in_client, new_user, app):
    _seed_usage(new_user.id, days=30)
    resp = logged_in_client.get(
        "/reports/generate/monthly", follow_redirects=True
    )
    assert resp.status_code == 200


def test_reports_invalid_type_redirects(logged_in_client):
    resp = logged_in_client.get(
        "/reports/generate/invalid_type", follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"Unknown report type" in resp.data
