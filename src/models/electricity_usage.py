# ============================================================
# ElectricityUsage Model
# ============================================================
from datetime import datetime, timezone
from src.extensions import db


class ElectricityUsage(db.Model):
    __tablename__ = "electricity_usage"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                               nullable=False, index=True)
    date           = db.Column(db.Date,    nullable=False, index=True)
    units_consumed = db.Column(db.Float,   nullable=False)          # kWh
    cost           = db.Column(db.Float,   nullable=True)           # ₹  (computed)
    tariff_rate    = db.Column(db.Float,   nullable=True)           # ₹ per kWh
    source         = db.Column(db.String(50),  default="manual")    # manual / csv / smart_meter
    notes          = db.Column(db.Text,    nullable=True)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_user_date"),
    )

    # ── Helpers ──────────────────────────────────────────────
    def compute_cost(self, tariff: float) -> float:
        self.tariff_rate = tariff
        self.cost = round(self.units_consumed * tariff, 2)
        return self.cost

    @property
    def month(self) -> int:
        return self.date.month

    @property
    def year(self) -> int:
        return self.date.year

    def __repr__(self) -> str:
        return f"<Usage {self.date} {self.units_consumed} kWh>"
