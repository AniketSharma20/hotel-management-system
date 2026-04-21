from .base import db

class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # e.g., 'Laundry', 'Room Service - Burger'
    category = db.Column(db.String(50), nullable=False) # 'Food', 'Spa', 'Laundry'
    price = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Service {self.name} - ${self.price}>"
