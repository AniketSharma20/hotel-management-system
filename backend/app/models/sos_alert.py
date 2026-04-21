"""
SOS Alert Model
Persists every emergency event triggered by a guest client.
"""
from datetime import datetime
from .base import db


class SosAlert(db.Model):
    """
    Represents a single SOS / emergency event raised by a guest.

    Columns
    -------
    id           : auto-increment primary key
    room_number  : the room that raised the alert
    guest_name   : optional name provided by guest app
    timestamp    : ISO-8601 string sent by the mobile client
    received_at  : server-side UTC timestamp (auto-filled)
    status       : 'active' | 'acknowledged' | 'resolved'
    notes        : free-text field for staff notes
    """

    __tablename__ = 'sos_alerts'

    id          = db.Column(db.Integer,  primary_key=True)
    room_number = db.Column(db.String(10), nullable=False)
    guest_name  = db.Column(db.String(100), nullable=True)
    timestamp   = db.Column(db.String(50),  nullable=False)   # from client
    received_at = db.Column(db.DateTime,    default=datetime.utcnow)
    status      = db.Column(db.String(20),  default='active')
    notes       = db.Column(db.Text,        nullable=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'room_number': self.room_number,
            'guest_name':  self.guest_name or 'Unknown Guest',
            'timestamp':   self.timestamp,
            'received_at': self.received_at.isoformat() + 'Z',
            'status':      self.status,
            'notes':       self.notes or '',
        }

    def __repr__(self):
        return f'<SosAlert room={self.room_number} status={self.status}>'
