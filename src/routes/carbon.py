# ============================================================
# Carbon Footprint Routes
# ============================================================
from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user

from src.services import carbon_service

carbon_bp = Blueprint("carbon", __name__)


@carbon_bp.route("/")
@login_required
def index():
    emission_factor = current_app.config["CO2_EMISSION_FACTOR"]
    data = carbon_service.get_carbon_dashboard(current_user.id, emission_factor)

    return render_template("carbon/index.html", **data)
