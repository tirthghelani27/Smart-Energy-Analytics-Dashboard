# ============================================================
# Alert Model
# ============================================================
from datetime import datetime, timezone
from src.extensions import db

SEVERITY_COLORS = {"low": "info", "medium": "warning", "high": "danger"}


class Alert(db.Model):
    __tablename__ = "alerts"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    alert_type   = db.Column(db.String(50), nullable=False)    # spike / leakage / anomaly / cost
    severity     = db.Column(db.String(20), nullable=False)    # low / medium / high
    message      = db.Column(db.Text,       nullable=False)
    is_read      = db.Column(db.Boolean,    default=False)
    triggered_at = db.Column(db.DateTime,   default=lambda: datetime.now(timezone.utc))

    @property
    def badge_color(self) -> str:
        return SEVERITY_COLORS.get(self.severity, "secondary")

    def __repr__(self) -> str:
        return f"<Alert {self.severity} {self.alert_type}>"
