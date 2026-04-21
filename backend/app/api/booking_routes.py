from flask import Blueprint, request, jsonify
from datetime import datetime
from ..models.base import db
from ..models.room import Room
from ..models.booking import Booking
from ..services.pricing_service import get_dynamic_price

booking_bp = Blueprint('booking_bp', __name__)

@booking_bp.route('/api/book-room', methods=['POST'])
def book_room():
    data = request.get_json()
    try:
        user_id = data.get('user_id')
        room_id = data.get('room_id')
        check_in_str = data.get('check_in_date')
        check_out_str = data.get('check_out_date')

        if not all([user_id, room_id, check_in_str, check_out_str]):
            return jsonify({'error': 'Missing required fields'}), 400

        check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()

        room = Room.query.get(room_id)
        if not room:
            return jsonify({'error': 'Room not found'}), 404

        nights = (check_out_date - check_in_date).days
        if nights <= 0:
            return jsonify({'error': 'Check-out date must be after check-in date'}), 400

        # Run Dynamic Pricing Engine
        # Evaluates the occupancy on the check-in date to determine the price multiplier
        final_price_per_night = get_dynamic_price(room, check_in_date)
        total_cost = final_price_per_night * nights
        surcharge_applied = final_price_per_night > float(room.base_price)

        # Build and Save Booking
        booking = Booking(
            user_id=user_id,
            room_id=room_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status='confirmed',
            total_cost=total_cost
        )

        db.session.add(booking)
        db.session.commit()

        return jsonify({
            'message': 'Booking successful',
            'booking_id': booking.id,
            'base_price_per_night': float(room.base_price),
            'final_price_per_night': round(final_price_per_night, 2),
            'surcharge_applied': surcharge_applied,
            'total_nights': nights,
            'total_cost': round(total_cost, 2)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
