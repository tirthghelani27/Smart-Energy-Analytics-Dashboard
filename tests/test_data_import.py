# ============================================================
# Data Import & CSV Processing Tests
# ============================================================
import io
import os
import csv
import tempfile
from datetime import date, timedelta
import pytest
from app import db
from src.models.electricity_usage import ElectricityUsage
from src.services import data_import_service


TARIFF = 6.5


def _make_csv(rows, headers=None):
    """Write rows to a temp CSV file and return its path."""
    if headers is None:
        headers = ["date", "units_consumed", "cost", "notes"]
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline=""
    )
    writer = csv.writer(tmp)
    writer.writerow(headers)
    writer.writerows(rows)
    tmp.close()
    return tmp.name


# ── Data import service unit tests ───────────────────────────
def test_process_csv_inserts_valid_rows(app, new_user):
    today = date.today()
    rows = [
        [(today - timedelta(days=i)).isoformat(), 7.0 + i * 0.1, "", ""]
        for i in range(5)
    ]
    path = _make_csv(rows)
    try:
        report = data_import_service.process_csv(path, new_user.id, TARIFF)
        assert report["inserted_rows"] == 5
        assert report["valid_rows"] == 5
        assert report["missing_values"] == 0
        assert not report["errors"]
    finally:
        os.unlink(path)


def test_process_csv_skips_missing_values(app, new_user):
    today = date.today()
    rows = [
        [today.isoformat(), "", "", "missing units"],
        [(today - timedelta(days=1)).isoformat(), 5.0, "", "ok"],
    ]
    path = _make_csv(rows)
    try:
        report = data_import_service.process_csv(path, new_user.id, TARIFF)
        assert report["missing_values"] == 1
        assert report["inserted_rows"] == 1
    finally:
        os.unlink(path)


def test_process_csv_skips_invalid_numbers(app, new_user):
    today = date.today()
    rows = [
        [today.isoformat(), "not_a_number", "", ""],
        [(today - timedelta(days=1)).isoformat(), 6.0, "", ""],
    ]
    path = _make_csv(rows)
    try:
        report = data_import_service.process_csv(path, new_user.id, TARIFF)
        assert report["invalid_records"] >= 1
        assert report["inserted_rows"] == 1
    finally:
        os.unlink(path)


def test_process_csv_skips_negative_values(app, new_user):
    today = date.today()
    rows = [
        [today.isoformat(), -5.0, "", ""],
        [(today - timedelta(days=1)).isoformat(), 6.0, "", ""],
    ]
    path = _make_csv(rows)
    try:
        report = data_import_service.process_csv(path, new_user.id, TARIFF)
        assert report["invalid_records"] >= 1
        assert report["inserted_rows"] == 1
    finally:
        os.unlink(path)


def test_process_csv_handles_duplicate_dates_in_file(app, new_user):
    today = date.today()
    rows = [
        [today.isoformat(), 5.0, "", "first"],
        [today.isoformat(), 7.0, "", "duplicate"],  # same date
    ]
    path = _make_csv(rows)
    try:
        report = data_import_service.process_csv(path, new_user.id, TARIFF)
        assert report["duplicate_records"] == 1
        assert report["inserted_rows"] == 1
    finally:
        os.unlink(path)


def test_process_csv_updates_existing_record(app, new_user):
    today = date.today()
    # Insert first
    rec = ElectricityUsage(
        user_id=new_user.id, date=today, units_consumed=5.0, source="manual"
    )
    db.session.add(rec)
    db.session.commit()

    rows = [[today.isoformat(), 9.0, "", "updated"]]
    path = _make_csv(rows)
    try:
        report = data_import_service.process_csv(path, new_user.id, TARIFF)
        assert report["updated_rows"] == 1
        assert report["inserted_rows"] == 0
        db.session.refresh(rec)
        assert rec.units_consumed == 9.0
    finally:
        os.unlink(path)


def test_process_csv_bad_date_format_skipped(app, new_user):
    rows = [
        ["not-a-date", 5.0, "", ""],
        [date.today().isoformat(), 6.0, "", ""],
    ]
    path = _make_csv(rows)
    try:
        report = data_import_service.process_csv(path, new_user.id, TARIFF)
        assert report["date_format_errors"] >= 1
        assert report["inserted_rows"] == 1
    finally:
        os.unlink(path)


def test_process_csv_missing_required_column(app, new_user):
    path = _make_csv([["2026-01-01", "5.0"]], headers=["date", "wrong_column"])
    try:
        report = data_import_service.process_csv(path, new_user.id, TARIFF)
        assert report["errors"]  # Should have an error message
        assert "units_consumed" in report["errors"][0].lower() or "missing" in report["errors"][0].lower()
    finally:
        os.unlink(path)


def test_process_csv_computes_cost_from_tariff(app, new_user):
    today = date.today()
    rows = [[today.isoformat(), 10.0, "", ""]]  # no cost provided
    path = _make_csv(rows)
    try:
        data_import_service.process_csv(path, new_user.id, TARIFF)
        rec = ElectricityUsage.query.filter_by(
            user_id=new_user.id, date=today
        ).first()
        assert rec is not None
        assert abs(rec.cost - 10.0 * TARIFF) < 0.01
    finally:
        os.unlink(path)


# ── Manual entry tests ────────────────────────────────────────
def test_manual_entry_adds_record(app, new_user):
    entry_date = date.today() - timedelta(days=1)
    success, _ = data_import_service.add_manual_entry(
        new_user.id, entry_date, 7.5, TARIFF, "test note"
    )
    assert success is True
    rec = ElectricityUsage.query.filter_by(
        user_id=new_user.id, date=entry_date
    ).first()
    assert rec is not None
    assert rec.units_consumed == 7.5
    assert rec.notes == "test note"


def test_manual_entry_updates_existing_record(app, new_user):
    entry_date = date.today() - timedelta(days=2)
    rec = ElectricityUsage(
        user_id=new_user.id, date=entry_date, units_consumed=5.0, source="manual"
    )
    db.session.add(rec)
    db.session.commit()

    success, msg = data_import_service.add_manual_entry(
        new_user.id, entry_date, 9.0, TARIFF
    )
    assert success is True
    db.session.refresh(rec)
    assert rec.units_consumed == 9.0


def test_manual_entry_rejects_negative_units(app, new_user):
    success, msg = data_import_service.add_manual_entry(
        new_user.id, date.today(), -1.0, TARIFF
    )
    assert success is False


def test_manual_entry_rejects_excessive_units(app, new_user):
    success, msg = data_import_service.add_manual_entry(
        new_user.id, date.today(), 9999.0, TARIFF
    )
    assert success is False


# ── Route tests ───────────────────────────────────────────────
def test_data_import_page_requires_login(client):
    resp = client.get("/data/import", follow_redirects=False)
    assert resp.status_code == 302


def test_data_import_page_loads(logged_in_client):
    resp = logged_in_client.get("/data/import")
    assert resp.status_code == 200
    assert b"Import" in resp.data


def test_manual_entry_via_route(logged_in_client, new_user):
    entry_date = (date.today() - timedelta(days=3)).isoformat()
    resp = logged_in_client.post(
        "/data/import/manual",
        data={"date": entry_date, "units_consumed": "8.5", "notes": "test"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    rec = ElectricityUsage.query.filter_by(user_id=new_user.id).first()
    assert rec is not None


def test_csv_upload_via_route(logged_in_client, new_user, app):
    today = date.today()
    csv_content = f"date,units_consumed,cost,notes\n{today.isoformat()},8.0,,test\n"
    data = {
        "file": (io.BytesIO(csv_content.encode()), "test.csv"),
    }
    resp = logged_in_client.post(
        "/data/import/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_invalid_file_type_rejected(logged_in_client):
    data = {
        "file": (io.BytesIO(b"hello world"), "test.txt"),
    }
    resp = logged_in_client.post(
        "/data/import/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Invalid file type" in resp.data
