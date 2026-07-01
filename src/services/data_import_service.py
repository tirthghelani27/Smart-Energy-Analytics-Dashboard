# ============================================================
# Data Import Service
# CSV upload, validation, cleaning, and ingestion — used by
# src/routes/data_import.py
# ============================================================
from datetime import datetime

import pandas as pd
from src.extensions import db
from src.models.electricity_usage import ElectricityUsage

REQUIRED_COLUMNS = {"date", "units_consumed"}
DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]


def _parse_date(value):
    """Try multiple common date formats; return a date object or None."""
    if pd.isna(value):
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date()
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Last resort: let pandas try
    try:
        return pd.to_datetime(text).date()
    except (ValueError, TypeError):
        return None


def process_csv(file_path: str, user_id: int, tariff: float) -> dict:
    """
    Read a CSV/Excel file, validate it, clean it, and insert valid rows
    into ElectricityUsage. Returns a data-quality report dict.
    """
    report = {
        "total_rows": 0,
        "valid_rows": 0,
        "inserted_rows": 0,
        "updated_rows": 0,
        "missing_values": 0,
        "invalid_records": 0,
        "duplicate_records": 0,
        "date_format_errors": 0,
        "errors": [],
    }

    # ── Read file ────────────────────────────────────────────
    try:
        if file_path.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(f"Could not read file: {exc}")
        return report

    # ── Normalize column names ───────────────────────────────
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Common aliases
    aliases = {
        "units": "units_consumed", "kwh": "units_consumed", "consumption": "units_consumed",
        "usage": "units_consumed", "energy": "units_consumed",
        "day": "date", "reading_date": "date",
    }
    df.rename(columns={k: v for k, v in aliases.items() if k in df.columns}, inplace=True)

    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        report["errors"].append(
            f"Missing required column(s): {', '.join(sorted(missing_cols))}. "
            f"Required: date, units_consumed (optional: cost, notes)."
        )
        return report

    report["total_rows"] = len(df)

    seen_dates = set()
    # Pre-fetch existing dates for this user to detect DB duplicates
    existing_dates = {
        r.date for r in ElectricityUsage.query.filter_by(user_id=user_id).all()
    }

    for _, row in df.iterrows():
        # ── Missing values ───────────────────────────────────
        units_raw = row.get("units_consumed")
        date_raw = row.get("date")

        if pd.isna(units_raw) or pd.isna(date_raw) or str(date_raw).strip() == "":
            report["missing_values"] += 1
            continue

        # ── Date format ───────────────────────────────────────
        parsed_date = _parse_date(date_raw)
        if parsed_date is None:
            report["date_format_errors"] += 1
            continue

        # ── Numeric validity ─────────────────────────────────
        try:
            units = float(units_raw)
        except (ValueError, TypeError):
            report["invalid_records"] += 1
            continue

        if units < 0 or units > 1000:  # sanity bound for a single day's kWh
            report["invalid_records"] += 1
            continue

        # ── Duplicate detection (within file) ────────────────
        if parsed_date in seen_dates:
            report["duplicate_records"] += 1
            continue
        seen_dates.add(parsed_date)

        report["valid_rows"] += 1

        cost_raw = row.get("cost")
        notes_raw = row.get("notes")
        cost = float(cost_raw) if pd.notna(cost_raw) else None
        notes = str(notes_raw) if pd.notna(notes_raw) else None

        # ── Upsert into DB ────────────────────────────────────
        if parsed_date in existing_dates:
            existing = ElectricityUsage.query.filter_by(
                user_id=user_id, date=parsed_date
            ).first()
            existing.units_consumed = units
            existing.notes = notes or existing.notes
            existing.source = "csv"
            if cost is not None:
                existing.cost = cost
                existing.tariff_rate = round(cost / units, 4) if units else None
            else:
                existing.compute_cost(tariff)
            report["updated_rows"] += 1
        else:
            record = ElectricityUsage(
                user_id=user_id,
                date=parsed_date,
                units_consumed=units,
                source="csv",
                notes=notes,
            )
            if cost is not None:
                record.cost = cost
                record.tariff_rate = round(cost / units, 4) if units else None
            else:
                record.compute_cost(tariff)
            db.session.add(record)
            existing_dates.add(parsed_date)
            report["inserted_rows"] += 1

    db.session.commit()
    return report


def add_manual_entry(user_id: int, entry_date, units: float, tariff: float, notes: str = None) -> tuple[bool, str]:
    """Add or update a single manual usage entry. Returns (success, message)."""
    if units < 0 or units > 1000:
        return False, "Units consumed must be between 0 and 1000 kWh."

    existing = ElectricityUsage.query.filter_by(user_id=user_id, date=entry_date).first()
    if existing:
        existing.units_consumed = units
        existing.notes = notes
        existing.source = "manual"
        existing.compute_cost(tariff)
        db.session.commit()
        return True, "Updated existing record for this date."

    record = ElectricityUsage(
        user_id=user_id, date=entry_date, units_consumed=units,
        source="manual", notes=notes,
    )
    record.compute_cost(tariff)
    db.session.add(record)
    db.session.commit()
    return True, "Entry added successfully."


def get_recent_imports(user_id: int, limit: int = 20):
    return (ElectricityUsage.query
            .filter_by(user_id=user_id)
            .order_by(ElectricityUsage.created_at.desc())
            .limit(limit)
            .all())
