# ============================================================
# CarbonFootprint Model
# ============================================================
from datetime import datetime, timezone
from src.extensions import db

# One tree absorbs ~21 kg CO₂ per year → 1.75 kg/month
KG_CO2_PER_TREE_MONTH = 1.75


class CarbonFootprint(db.Model):
    __tablename__ = "carbon_footprint"

    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                                     nullable=False, index=True)
    month                = db.Column(db.Integer, nullable=False)
    year                 = db.Column(db.Integer, nullable=False)
    co2_generated        = db.Column(db.Float,   nullable=False)   # kg CO₂
    co2_saved            = db.Column(db.Float,   nullable=True,  default=0.0)
    trees_equivalent     = db.Column(db.Float,   nullable=True)
    sustainability_score = db.Column(db.Float,   nullable=True)    # 0–100
    created_at           = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "month", "year", name="uq_user_month_year"),
    )

    @classmethod
    def from_kwh(cls, user_id: int, month: int, year: int,
                 kwh: float, emission_factor: float) -> "CarbonFootprint":
        co2 = round(kwh * emission_factor, 2)
        trees = round(co2 / KG_CO2_PER_TREE_MONTH, 1)
        # Score: 100 is best (low CO2). Simple inverse scale capped at 200 kg/month.
        score = max(0, round(100 - (co2 / 200) * 100, 1))
        return cls(user_id=user_id, month=month, year=year,
                   co2_generated=co2, trees_equivalent=trees, sustainability_score=score)

    def __repr__(self) -> str:
        return f"<CO₂ {self.month}/{self.year} {self.co2_generated} kg>"
