from datetime import datetime
from .base import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='guest') # 'guest', 'admin', 'manager'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Note: 'bookings' relationship is backref'd from Booking model

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
