# ============================================================
# Prediction Model
# ============================================================
from datetime import datetime, timezone
from src.extensions import db


class Prediction(db.Model):
    __tablename__ = "predictions"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                                nullable=False, index=True)
    prediction_date = db.Column(db.Date,       nullable=False)
    period          = db.Column(db.String(20),  nullable=False)   # day / week / month
    predicted_units = db.Column(db.Float,       nullable=False)
    predicted_cost  = db.Column(db.Float,       nullable=True)
    model_used      = db.Column(db.String(50),  nullable=True)    # linear_regression / random_forest
    mae             = db.Column(db.Float,       nullable=True)
    rmse            = db.Column(db.Float,       nullable=True)
    r2_score        = db.Column(db.Float,       nullable=True)
    created_at      = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Prediction {self.period} {self.predicted_units} kWh>"
