from datetime import date
from ..models.room import Room
from ..models.booking import Booking

def calculate_occupancy_rate(target_date: date) -> float:
    """Calculates the hotel occupancy rate (0.0 to 1.0) on a specific date."""
    total_rooms = Room.query.count()
    if total_rooms == 0:
        return 0.0
        
    booked_rooms = Booking.query.filter(
        Booking.check_in_date <= target_date,
        Booking.check_out_date > target_date,
        Booking.status != 'cancelled'
    ).count()
    
    return booked_rooms / total_rooms

def get_dynamic_price(room: Room, target_date: date) -> float:
    """
    Returns the dynamic price. 
    If occupancy > 70%, applies 15% surcharge.
    """
    base_price = float(room.base_price)
    occupancy_rate = calculate_occupancy_rate(target_date)
    
    if occupancy_rate > 0.70:
        return base_price * 1.15  # 15% Surcharge
    
    return base_price
