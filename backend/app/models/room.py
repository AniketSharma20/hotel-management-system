from .base import db

class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), unique=True, nullable=False, index=True)
    room_type = db.Column(db.String(50), nullable=False) # e.g., 'Suite', 'Deluxe', 'Standard'
    capacity = db.Column(db.Integer, nullable=False, default=2)
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='available') # 'available', 'maintenance', 'cleaning'

    def __repr__(self):
        return f"<Room {self.room_number} - {self.room_type}>"
