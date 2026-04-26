"""Modelo SQLAlchemy para la tabla blacklists."""
from datetime import datetime

from src.main import db


class Blacklist(db.Model):
    """Entrada de un email en la lista negra global."""

    __tablename__ = "blacklists"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    app_uuid = db.Column(db.String(36), nullable=False)
    blocked_reason = db.Column(db.String(255), nullable=True)
    request_ip = db.Column(db.String(45), nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "app_uuid": self.app_uuid,
            "blocked_reason": self.blocked_reason,
            "request_ip": self.request_ip,
            "created_at": self.created_at.isoformat() + "Z",
        }
