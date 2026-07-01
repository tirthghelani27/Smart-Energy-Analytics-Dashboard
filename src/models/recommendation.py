# ============================================================
# Recommendation Model
# ============================================================
from datetime import datetime, timezone
from src.extensions import db


class Recommendation(db.Model):
    __tablename__ = "recommendations"

    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                                     nullable=False, index=True)
    category             = db.Column(db.String(50),  nullable=False)   # appliance/behaviour/peak/billing
    title                = db.Column(db.String(200), nullable=False)
    description          = db.Column(db.Text,        nullable=False)
    potential_saving_kwh = db.Column(db.Float,  nullable=True)
    potential_saving_cost= db.Column(db.Float,  nullable=True)
    priority             = db.Column(db.String(20),  default="medium")  # low/medium/high
    is_applied           = db.Column(db.Boolean,     default=False)
    created_at           = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Recommendation {self.title}>"
