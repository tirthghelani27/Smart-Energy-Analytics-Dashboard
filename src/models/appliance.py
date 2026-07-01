# ============================================================
# Appliance Model
# ============================================================
from datetime import datetime, timezone
from src.extensions import db


class Appliance(db.Model):
    __tablename__ = "appliances"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                                nullable=False, index=True)
    name            = db.Column(db.String(100), nullable=False)
    category        = db.Column(db.String(50),  nullable=True)   # cooling/heating/kitchen/etc.
    power_rating_w  = db.Column(db.Float,  nullable=False)       # Watts
    daily_usage_hrs = db.Column(db.Float,  nullable=False)       # Hours/day
    monthly_kwh     = db.Column(db.Float,  nullable=True)        # Computed
    monthly_cost    = db.Column(db.Float,  nullable=True)        # Computed ₹
    is_active       = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def compute_monthly(self, tariff: float, days: int = 30) -> None:
        """Compute and store monthly kWh and cost."""
        self.monthly_kwh  = round((self.power_rating_w / 1000) * self.daily_usage_hrs * days, 2)
        self.monthly_cost = round(self.monthly_kwh * tariff, 2)

    def __repr__(self) -> str:
        return f"<Appliance {self.name} {self.power_rating_w}W>"
