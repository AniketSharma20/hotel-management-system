"""
Application entry-point.
Run with:  python run.py
The server now uses eventlet + Flask-SocketIO for real-time WebSocket support.
"""
from app import create_app, socketio
from app.models.base import db
from app.models.room import Room
from app.models.user import User
from app.models.sos_alert import SosAlert    # ensure table is created

app = create_app()


def init_db():
    with app.app_context():
        # Create all tables (including sos_alerts)
        db.create_all()

        # Seed dummy data if empty
        if not User.query.first():
            dummy_user = User(
                first_name="Test",
                last_name="User",
                email="test@user.com",
                password_hash="mockhash",
                role="guest"
            )
            db.session.add(dummy_user)

        if not Room.query.first():
            dummy_room = Room(
                room_number="101",
                room_type="Suite",
                capacity=2,
                base_price=200.00,
                status="available"
            )
            db.session.add(dummy_room)

        db.session.commit()
        print("[DB] Tables initialised successfully.")


if __name__ == '__main__':
    init_db()
    print("[SERVER] Starting Flask-SocketIO server on http://127.0.0.1:5000")
    print("[SERVER] Real-time SOS WebSocket endpoint is active.")
    # socketio.run() replaces app.run() for WebSocket support
    socketio.run(app, debug=True, host='127.0.0.1', port=5000)
