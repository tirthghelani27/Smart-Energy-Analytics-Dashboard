# ============================================================
# Report Model
# ============================================================
from datetime import datetime, timezone
from src.extensions import db


class Report(db.Model):
    __tablename__ = "reports"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    title        = db.Column(db.String(200), nullable=False)
    report_type  = db.Column(db.String(50),  nullable=False)  # monthly/annual/carbon/forecast
    file_path    = db.Column(db.String(500), nullable=True)
    generated_at = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Report {self.title}>"
