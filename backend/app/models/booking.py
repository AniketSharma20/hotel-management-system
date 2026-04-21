from datetime import datetime
from .base import db

# Association table for tracking which services were ordered during a booking
booking_services = db.Table('booking_services',
    db.Column('booking_id', db.Integer, db.ForeignKey('bookings.id'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('services.id'), primary_key=True),
    db.Column('quantity', db.Integer, default=1),
    db.Column('requested_at', db.DateTime, default=datetime.utcnow)
)

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    
    status = db.Column(db.String(20), default='pending') # 'pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled'
    total_cost = db.Column(db.Numeric(10, 2), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    guest = db.relationship('User', backref=db.backref('bookings', lazy='dynamic', cascade="all, delete-orphan"))
    room = db.relationship('Room', backref=db.backref('bookings', lazy='dynamic'))
    services_ordered = db.relationship('Service', secondary=booking_services, lazy='subquery',
        backref=db.backref('bookings', lazy=True))

    def __repr__(self):
        return f"<Booking {self.id} | Room {self.room_id} | Guest {self.user_id}>"
