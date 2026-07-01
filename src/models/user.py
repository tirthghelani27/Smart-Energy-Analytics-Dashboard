# ============================================================
# User Model — authentication, roles, relationships
# ============================================================
from datetime import datetime, timezone
from src.extensions import db, bcrypt
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer,     primary_key=True)
    username   = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    email      = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password   = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50),  nullable=True)
    last_name  = db.Column(db.String(50),  nullable=True)
    role       = db.Column(db.String(20),  nullable=False, default="user")   # user / admin
    is_active  = db.Column(db.Boolean,     default=True,   nullable=False)
    last_login = db.Column(db.DateTime,    nullable=True)
    created_at = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # ── Relationships ────────────────────────────────────────
    usage_records   = db.relationship("ElectricityUsage", backref="user", lazy="dynamic",
                                      cascade="all, delete-orphan")
    appliances      = db.relationship("Appliance",        backref="user", lazy="dynamic",
                                      cascade="all, delete-orphan")
    predictions     = db.relationship("Prediction",       backref="user", lazy="dynamic",
                                      cascade="all, delete-orphan")
    alerts          = db.relationship("Alert",            backref="user", lazy="dynamic",
                                      cascade="all, delete-orphan")
    recommendations = db.relationship("Recommendation",   backref="user", lazy="dynamic",
                                      cascade="all, delete-orphan")
    carbon_records  = db.relationship("CarbonFootprint",  backref="user", lazy="dynamic",
                                      cascade="all, delete-orphan")
    reports         = db.relationship("Report",           backref="user", lazy="dynamic",
                                      cascade="all, delete-orphan")

    # ── Password helpers ─────────────────────────────────────
    def set_password(self, plain_text: str) -> None:
        """Hash and store a password."""
        self.password = bcrypt.generate_password_hash(plain_text).decode("utf-8")

    def check_password(self, plain_text: str) -> bool:
        """Return True if plain_text matches the stored hash."""
        return bcrypt.check_password_hash(self.password, plain_text)

    # ── Role helpers ─────────────────────────────────────────
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    # ── Password reset tokens ─────────────────────────────────
    def get_reset_token(self) -> str:
        """Generate a signed, time-limited token for password resets."""
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app

        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps(self.email, salt="password-reset-salt")

    @staticmethod
    def verify_reset_token(token: str, max_age: int = 3600) -> "User | None":
        """
        Verify a password-reset token and return the matching User,
        or None if the token is invalid or expired.

        Args:
            token:   The signed token string produced by get_reset_token().
            max_age: Maximum age in seconds.  0 or negative means the token
                     is considered immediately expired and None is returned.
        """
        from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
        from flask import current_app

        # itsdangerous uses `age > max_age`, so max_age=0 lets a
        # brand-new token (age=0) through.  Treat 0 / negative as
        # "always expired" before even hitting the serializer.
        if max_age is not None and max_age <= 0:
            return None

        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            email = serializer.loads(token, salt="password-reset-salt", max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None
        return User.query.filter_by(email=email).first()

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
