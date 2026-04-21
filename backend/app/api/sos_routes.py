"""
SOS / Emergency Real-Time Module
=================================
This module wires together two mechanisms:

  1. Flask-SocketIO event handler  –  listens for 'sos_trigger' from any
     connected client (Flutter mobile app, web demo, etc.) and immediately
     broadcasts an 'emergency_alert' to the 'admin_room' channel so every
     open Admin Dashboard receives the alert in real time.

  2. REST Blueprint  –  exposes HTTP endpoints so the Admin panel can also
     fetch / acknowledge / resolve historical alerts stored in the DB.

Architecture
------------
  Flutter / Mobile              Flask-SocketIO Server         Admin Dashboard
       │                               │                            │
       │──── emit('sos_trigger') ─────►│                            │
       │      { room, timestamp,       │── persist to DB ──────────►│
       │        guest_name? }          │── emit('emergency_alert') ►│
       │                               │    to 'admin_room'         │
       │◄── emit('sos_acknowledged') ──│                            │
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_socketio import emit, join_room, leave_room
from ..models.base import db
from ..models.sos_alert import SosAlert

sos_bp = Blueprint('sos_bp', __name__)


# ─────────────────────────────────────────────────────────────────────────────
#  SocketIO event handlers
#  (These functions are registered in create_app() via socketio.on() wrappers)
# ─────────────────────────────────────────────────────────────────────────────

def register_sos_socket_events(socketio):
    """
    Called ONCE from create_app() with the shared SocketIO instance.
    Registers all real-time SOS event listeners.
    """

    # ── Admin clients join a dedicated room on connection ────────────────────
    @socketio.on('join_admin')
    def handle_join_admin(data):
        """
        Admin Dashboard emits this after connecting so it receives
        emergency_alert broadcasts.

        Expected payload:  { "role": "admin" }    (basic, extend with JWT)
        """
        join_room('admin_room')
        emit('admin_joined', {'message': 'Connected to SOS alert stream.'})
        print(f"[SOS] Admin client joined admin_room  sid={request.sid}")

    @socketio.on('leave_admin')
    def handle_leave_admin(data):
        leave_room('admin_room')
        print(f"[SOS] Admin client left admin_room  sid={request.sid}")

    # ── Mobile / Guest client emits this to trigger an emergency ────────────
    @socketio.on('sos_trigger')
    def handle_sos_trigger(data):
        """
        Receives an SOS trigger from a connected client (Flutter, etc.).

        Expected payload:
        {
            "room_number":  "304",
            "timestamp":    "2026-04-21T19:45:00+05:30",   // ISO-8601
            "guest_name":   "Priya Sharma"                  // optional
        }

        Actions:
          1. Validate the payload.
          2. Persist alert to database.
          3. Broadcast 'emergency_alert' to the 'admin_room' channel.
          4. Acknowledge back to the triggering client.
        """
        print(f"[SOS] sos_trigger received: {data}")

        room_number = data.get('room_number', '').strip()
        timestamp   = data.get('timestamp',   '').strip()
        guest_name  = data.get('guest_name',  '').strip()

        # ── Validation ───────────────────────────────────────────────────────
        if not room_number or not timestamp:
            emit('sos_error', {
                'error': 'room_number and timestamp are required fields.'
            })
            return

        # ── Persist to database ──────────────────────────────────────────────
        try:
            alert = SosAlert(
                room_number=room_number,
                guest_name=guest_name or None,
                timestamp=timestamp,
                received_at=datetime.utcnow(),
                status='active'
            )
            db.session.add(alert)
            db.session.commit()
            alert_dict = alert.to_dict()
        except Exception as e:
            db.session.rollback()
            print(f"[SOS] DB error: {e}")
            emit('sos_error', {'error': f'Database error: {str(e)}'})
            return

        # ── Broadcast to ALL admin dashboard clients ─────────────────────────
        socketio.emit(
            'emergency_alert',
            {
                'alert_id':    alert_dict['id'],
                'room_number': room_number,
                'guest_name':  guest_name or 'Unknown Guest',
                'timestamp':   timestamp,
                'received_at': alert_dict['received_at'],
                'status':      'active',
                'message':     f'🚨 EMERGENCY in Room {room_number}! Immediate assistance required.',
            },
            to='admin_room'        # only admins receive this
        )

        # ── Acknowledge back to the mobile client ────────────────────────────
        emit('sos_acknowledged', {
            'alert_id': alert_dict['id'],
            'message':  'SOS received. Help is on the way.',
            'status':   'active'
        })

        print(f"[SOS] emergency_alert broadcast → admin_room  (alert_id={alert_dict['id']})")


# ─────────────────────────────────────────────────────────────────────────────
#  REST endpoints  (Admin Dashboard HTTP calls)
# ─────────────────────────────────────────────────────────────────────────────

@sos_bp.route('/api/sos/alerts', methods=['GET'])
def get_all_alerts():
    """
    GET /api/sos/alerts
    Returns all SOS alerts (newest first).
    Query params:
      ?status=active|acknowledged|resolved   (optional filter)
    """
    status_filter = request.args.get('status')
    query = SosAlert.query.order_by(SosAlert.received_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    alerts = [a.to_dict() for a in query.all()]
    return jsonify({'alerts': alerts, 'count': len(alerts)}), 200


@sos_bp.route('/api/sos/alerts/<int:alert_id>/acknowledge', methods=['PATCH'])
def acknowledge_alert(alert_id):
    """
    PATCH /api/sos/alerts/<id>/acknowledge
    Marks an alert as 'acknowledged' and optionally adds staff notes.

    Body (JSON):  { "notes": "Security team dispatched to room 304" }
    """
    alert = SosAlert.query.get_or_404(alert_id)
    data  = request.get_json(silent=True) or {}

    alert.status = 'acknowledged'
    if data.get('notes'):
        alert.notes = data['notes']

    db.session.commit()
    return jsonify({'message': 'Alert acknowledged.', 'alert': alert.to_dict()}), 200


@sos_bp.route('/api/sos/alerts/<int:alert_id>/resolve', methods=['PATCH'])
def resolve_alert(alert_id):
    """
    PATCH /api/sos/alerts/<id>/resolve
    Marks an alert as 'resolved'.

    Body (JSON):  { "notes": "Situation cleared. False alarm." }
    """
    alert = SosAlert.query.get_or_404(alert_id)
    data  = request.get_json(silent=True) or {}

    alert.status = 'resolved'
    if data.get('notes'):
        alert.notes = data['notes']

    db.session.commit()
    return jsonify({'message': 'Alert resolved.', 'alert': alert.to_dict()}), 200


@sos_bp.route('/api/sos/test', methods=['POST'])
def test_sos():
    """
    POST /api/sos/test
    Developer-only endpoint to simulate an SOS event from a browser
    (no WebSocket client needed for testing).

    Body (JSON):
    {
        "room_number": "101",
        "timestamp":   "2026-04-21T19:45:00Z",
        "guest_name":  "Test Guest"
    }
    """
    from .. import socketio as _socketio
    data = request.get_json()

    room_number = data.get('room_number', 'TEST-101')
    timestamp   = data.get('timestamp',   datetime.utcnow().isoformat() + 'Z')
    guest_name  = data.get('guest_name',  'Test Guest')

    alert = SosAlert(
        room_number=room_number,
        guest_name=guest_name,
        timestamp=timestamp,
        received_at=datetime.utcnow(),
        status='active'
    )
    db.session.add(alert)
    db.session.commit()

    _socketio.emit(
        'emergency_alert',
        {
            'alert_id':    alert.id,
            'room_number': room_number,
            'guest_name':  guest_name,
            'timestamp':   timestamp,
            'received_at': alert.received_at.isoformat() + 'Z',
            'status':      'active',
            'message':     f'🚨 EMERGENCY in Room {room_number}! Immediate assistance required.',
        },
        to='admin_room'
    )

    return jsonify({'message': 'Test SOS fired.', 'alert_id': alert.id}), 201
