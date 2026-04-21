"""
room_routes.py
────────────────────────────────────────────────────────────────────────────
Rooms Blueprint – The Grand Aurelia Hotel Management System

Endpoints:
  GET  /api/rooms/available   – list rooms with status='available'
                                Optional query: ?room_type=Suite&max_price=500
  GET  /api/rooms             – list ALL rooms (admin use)
  GET  /api/rooms/<id>        – get a single room by ID
────────────────────────────────────────────────────────────────────────────
"""

import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from ..models.room import Room

logger   = logging.getLogger(__name__)
rooms_bp = Blueprint("rooms_bp", __name__)


def _room_to_dict(room: Room) -> dict:
    """Serialize a Room ORM object to a JSON-safe dictionary."""
    return {
        "id":          room.id,
        "room_number": room.room_number,
        "room_type":   room.room_type,
        "capacity":    room.capacity,
        "base_price":  float(room.base_price),
        "status":      room.status,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/rooms/available
# ─────────────────────────────────────────────────────────────────────────────

@rooms_bp.route("/api/rooms/available", methods=["GET"])
@jwt_required(optional=True)     # works with or without a token
def get_available_rooms():
    """
    Return all rooms whose status is 'available'.

    Optional query parameters:
        room_type  – filter by type  (e.g. Suite, Deluxe, Standard)
        max_price  – filter by maximum base_price per night

    Response 200:
        { "rooms": [ ...room objects... ], "count": int }
    """
    room_type = request.args.get("room_type", "").strip()
    max_price = request.args.get("max_price", "").strip()

    query = Room.query.filter_by(status="available")

    if room_type:
        query = query.filter(Room.room_type.ilike(f"%{room_type}%"))

    if max_price:
        try:
            query = query.filter(Room.base_price <= float(max_price))
        except ValueError:
            return jsonify({"error": "max_price must be a number."}), 400

    rooms = query.order_by(Room.base_price).all()

    logger.info("[Rooms] /available → %d rooms returned", len(rooms))
    return jsonify({
        "rooms": [_room_to_dict(r) for r in rooms],
        "count": len(rooms),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/rooms
# ─────────────────────────────────────────────────────────────────────────────

@rooms_bp.route("/api/rooms", methods=["GET"])
@jwt_required()
def get_all_rooms():
    """
    Return ALL rooms regardless of status (admin / manager use).
    Requires a valid JWT.
    """
    rooms = Room.query.order_by(Room.room_number).all()
    return jsonify({
        "rooms": [_room_to_dict(r) for r in rooms],
        "count": len(rooms),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/rooms/<id>
# ─────────────────────────────────────────────────────────────────────────────

@rooms_bp.route("/api/rooms/<int:room_id>", methods=["GET"])
@jwt_required(optional=True)
def get_room(room_id: int):
    """
    Return a single room by its database ID.

    Response 200:  { ...room object... }
    Response 404:  { "error": "Room not found." }
    """
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"error": "Room not found."}), 404

    return jsonify(_room_to_dict(room)), 200
