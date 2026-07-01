# ============================================================
# Report Generation Service
# Generates downloadable PDF reports using ReportLab —
# used by src/routes/reports.py
# ============================================================
import os
from datetime import date, datetime, timezone
from calendar import month_name

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)

from src.extensions import db
from src.models.electricity_usage import ElectricityUsage
from src.models.report import Report
from src.models.user import User
from src.services import analytics_service, forecasting_service, carbon_service, recommendation_service

# ── Brand colors ─────────────────────────────────────────────
PRIMARY_COLOR = colors.HexColor("#f59e0b")
DARK_COLOR    = colors.HexColor("#111827")
MUTED_COLOR   = colors.HexColor("#6b7280")

_styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle(
    "ReportTitle", parent=_styles["Title"], textColor=DARK_COLOR, fontSize=20, spaceAfter=4,
)
SUBTITLE_STYLE = ParagraphStyle(
    "ReportSubtitle", parent=_styles["Normal"], textColor=MUTED_COLOR, fontSize=10, spaceAfter=18,
)
SECTION_STYLE = ParagraphStyle(
    "SectionHeading", parent=_styles["Heading2"], textColor=PRIMARY_COLOR, fontSize=14,
    spaceBefore=14, spaceAfter=8,
)
BODY_STYLE = _styles["Normal"]


# ── Helpers ───────────────────────────────────────────────────
def _filename(user_id: int, report_type: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"user{user_id}_{report_type}_{ts}.pdf"


def _header_table(title: str, user: User, subtitle: str) -> list:
    elements = [
        Paragraph(title, TITLE_STYLE),
        Paragraph(subtitle, SUBTITLE_STYLE),
        Paragraph(
            f"<b>Account:</b> {user.full_name} ({user.email})<br/>"
            f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')}",
            BODY_STYLE,
        ),
        Spacer(1, 0.5 * cm),
    ]
    return elements


def _kpi_table(rows: list) -> Table:
    data = [["Metric", "Value"]] + rows
    table = Table(data, colWidths=[8 * cm, 8 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _series_table(headers: list, rows: list) -> Table:
    data = [headers] + rows
    col_widths = [8 * cm, 8 * cm] if len(headers) == 2 else None
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _persist_report(user_id: int, title: str, report_type: str, file_path: str) -> Report:
    rec = Report(user_id=user_id, title=title, report_type=report_type, file_path=file_path)
    db.session.add(rec)
    db.session.commit()
    return rec


# ── 1. Monthly Consumption Report ────────────────────────────
def generate_monthly_report(user: User, reports_folder: str, tariff: float) -> Report:
    today = date.today()

    rows = (ElectricityUsage.query
            .filter(ElectricityUsage.user_id == user.id,
                    db.extract("month", ElectricityUsage.date) == today.month,
                    db.extract("year", ElectricityUsage.date) == today.year)
            .order_by(ElectricityUsage.date)
            .all())

    total_kwh = sum(r.units_consumed for r in rows)
    total_cost = sum((r.cost or r.units_consumed * tariff) for r in rows)

    filename = _filename(user.id, "monthly")
    output_path = os.path.join(reports_folder, filename)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    elements = _header_table(
        "Monthly Consumption Report",
        user,
        f"{month_name[today.month]} {today.year}",
    )

    elements.append(_kpi_table([
        ["Total Consumption", f"{total_kwh:,.2f} kWh"],
        ["Total Estimated Cost", f"\u20b9{total_cost:,.2f}"],
        ["Days Recorded", str(len(rows))],
        ["Average Daily Usage", f"{(total_kwh / len(rows)) if rows else 0:,.2f} kWh"],
        ["Tariff Rate", f"\u20b9{tariff:.2f} / kWh"],
    ]))

    elements.append(Paragraph("Daily Breakdown", SECTION_STYLE))
    if rows:
        table_rows = [[r.date.strftime("%d %b %Y"), f"{r.units_consumed:.2f} kWh",
                        f"\u20b9{(r.cost or r.units_consumed * tariff):.2f}"] for r in rows]
        elements.append(_series_table(["Date", "Units", "Cost"], table_rows))
    else:
        elements.append(Paragraph("No usage records found for this month.", BODY_STYLE))

    doc.build(elements)

    return _persist_report(
        user.id, f"Monthly Report \u2014 {month_name[today.month]} {today.year}",
        "monthly", filename
    )


# ── 2. Annual Consumption Report ─────────────────────────────
def generate_annual_report(user: User, reports_folder: str, tariff: float) -> Report:
    today = date.today()
    yearly = analytics_service.get_monthly_analytics(user.id, months=12)

    total_kwh = sum(yearly["values"])
    total_cost = total_kwh * tariff

    filename = _filename(user.id, "annual")
    output_path = os.path.join(reports_folder, filename)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    elements = _header_table(
        "Annual Consumption Report",
        user,
        f"Last 12 months (as of {today.strftime('%d %b %Y')})",
    )

    elements.append(_kpi_table([
        ["Total Consumption", f"{total_kwh:,.2f} kWh"],
        ["Total Estimated Cost", f"\u20b9{total_cost:,.2f}"],
        ["Average Monthly Usage", f"{yearly['stats']['average']:,.2f} kWh"],
        ["Highest Month", f"{yearly['stats']['highest']:,.2f} kWh"],
        ["Lowest Month", f"{yearly['stats']['lowest']:,.2f} kWh"],
        ["Growth Rate", f"{yearly['stats']['growth_rate']:+.2f}%"],
    ]))

    elements.append(Paragraph("Monthly Breakdown", SECTION_STYLE))
    if yearly["labels"]:
        table_rows = [[label, f"{val:.2f} kWh", f"\u20b9{val * tariff:.2f}"]
                       for label, val in zip(yearly["labels"], yearly["values"])]
        elements.append(_series_table(["Month", "Units", "Estimated Cost"], table_rows))
    else:
        elements.append(Paragraph("No usage records found.", BODY_STYLE))

    doc.build(elements)

    return _persist_report(
        user.id, f"Annual Report \u2014 {today.year}", "annual", filename
    )


# ── 3. Forecast Report ───────────────────────────────────────
def generate_forecast_report(user: User, reports_folder: str, tariff: float) -> Report:
    forecast = forecasting_service.generate_forecast(user.id, tariff)

    filename = _filename(user.id, "forecast")
    output_path = os.path.join(reports_folder, filename)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    elements = _header_table(
        "Forecast Report",
        user,
        "Predicted electricity usage and bill (Linear Regression & Random Forest)",
    )

    if not forecast["has_data"]:
        elements.append(Paragraph(
            f"Not enough historical data to forecast. "
            f"You have {forecast['record_count']} record(s); "
            f"at least {forecast['min_required']} are required.",
            BODY_STYLE,
        ))
    else:
        for model_key, m in forecast["models"].items():
            elements.append(Paragraph(m["name"], SECTION_STYLE))
            elements.append(_kpi_table([
                ["Next Day Usage", f"{m['next_day_kwh']:.2f} kWh (\u20b9{m['next_day_cost']:.2f})"],
                ["Next Week Usage", f"{m['next_week_kwh']:.2f} kWh (\u20b9{m['next_week_cost']:.2f})"],
                ["Next Month Usage", f"{m['next_month_kwh']:.2f} kWh (\u20b9{m['next_month_cost']:.2f})"],
                ["Predicted Monthly Bill", f"\u20b9{m['next_month_cost']:.2f}"],
                ["MAE", f"{m['mae']:.3f}"],
                ["RMSE", f"{m['rmse']:.3f}"],
                ["Model Accuracy (R\u00b2)", f"{m['accuracy_pct']:.1f}%"],
            ]))
            elements.append(Spacer(1, 0.4 * cm))

    doc.build(elements)

    return _persist_report(
        user.id, f"Forecast Report \u2014 {date.today().strftime('%d %b %Y')}",
        "forecast", filename
    )


# ── 4. Carbon Footprint Report ───────────────────────────────
def generate_carbon_report(user: User, reports_folder: str, emission_factor: float) -> Report:
    carbon = carbon_service.get_carbon_dashboard(user.id, emission_factor)

    filename = _filename(user.id, "carbon")
    output_path = os.path.join(reports_folder, filename)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    elements = _header_table(
        "Carbon Footprint Report",
        user,
        f"{carbon['cur_month_name']} {carbon['cur_year']}",
    )

    elements.append(_kpi_table([
        ["CO2 Generated (this month)", f"{carbon['co2_generated']:.2f} kg"],
        ["CO2 Saved (this month)", f"{carbon['co2_saved']:.2f} kg"],
        ["Trees Equivalent", f"{carbon['trees_equivalent']:.1f} trees"],
        ["Sustainability Score", f"{carbon['sustainability_score']:.1f} / 100 ({carbon['rating']['label']})"],
        ["Annual CO2 (Year-to-Date)", f"{carbon['annual_co2']:.2f} kg"],
        ["Emission Factor", f"{emission_factor} kg CO2/kWh"],
    ]))

    elements.append(Paragraph("Monthly CO2 Emissions Trend", SECTION_STYLE))
    if carbon["chart_labels"]:
        table_rows = [[label, f"{val:.2f} kg"]
                       for label, val in zip(carbon["chart_labels"], carbon["chart_co2"])]
        elements.append(_series_table(["Month", "CO2 Emitted"], table_rows))
    else:
        elements.append(Paragraph("No usage records found.", BODY_STYLE))

    doc.build(elements)

    return _persist_report(
        user.id, f"Carbon Report \u2014 {carbon['cur_month_name']} {carbon['cur_year']}",
        "carbon", filename
    )


# ── 5. Recommendation Report ─────────────────────────────────
def generate_recommendation_report(user: User, reports_folder: str, tariff: float) -> Report:
    data = recommendation_service.get_recommendations(user.id, tariff)

    filename = _filename(user.id, "recommendation")
    output_path = os.path.join(reports_folder, filename)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    elements = _header_table(
        "Energy Recommendation Report",
        user,
        "Personalized suggestions to reduce consumption and cost",
    )

    elements.append(_kpi_table([
        ["Potential Monthly Savings", f"\u20b9{data['total_monthly_cost_saving']:.2f} "
                                       f"({data['total_monthly_kwh_saving']:.2f} kWh)"],
        ["Potential Annual Savings", f"\u20b9{data['total_annual_cost_saving']:.2f} "
                                      f"({data['total_annual_kwh_saving']:.2f} kWh)"],
        ["Efficiency Improvement", f"{data['efficiency_improvement_pct']:.1f}%"],
        ["Total Recommendations", str(len(data["recommendations"]))],
    ]))

    elements.append(Paragraph("Recommendations", SECTION_STYLE))
    if data["recommendations"]:
        table_rows = [
            [r.title, r.category.capitalize(), r.priority.capitalize(),
             f"\u20b9{(r.potential_saving_cost or 0):.2f}",
             "Yes" if r.is_applied else "No"]
            for r in data["recommendations"]
        ]
        elements.append(_series_table(
            ["Recommendation", "Category", "Priority", "Monthly Saving", "Applied"],
            table_rows
        ))
    else:
        elements.append(Paragraph("No recommendations generated yet.", BODY_STYLE))

    doc.build(elements)

    return _persist_report(
        user.id, f"Recommendation Report \u2014 {date.today().strftime('%d %b %Y')}",
        "recommendation", filename
    )


# ── Dispatch ───────────────────────────────────────────────────
def generate_report(report_type: str, user: User, reports_folder: str,
                     tariff: float, emission_factor: float) -> Report:
    """Dispatch to the correct generator based on report_type."""
    if report_type == "monthly":
        return generate_monthly_report(user, reports_folder, tariff)
    if report_type == "annual":
        return generate_annual_report(user, reports_folder, tariff)
    if report_type == "forecast":
        return generate_forecast_report(user, reports_folder, tariff)
    if report_type == "carbon":
        return generate_carbon_report(user, reports_folder, emission_factor)
    if report_type == "recommendation":
        return generate_recommendation_report(user, reports_folder, tariff)
    raise ValueError(f"Unknown report type: {report_type}")


def get_user_reports(user_id: int) -> list:
    return (Report.query
            .filter_by(user_id=user_id)
            .order_by(Report.generated_at.desc())
            .all())
