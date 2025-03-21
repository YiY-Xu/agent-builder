from flask import Flask, request, jsonify, Response
import datetime
import random
import json
import time
import threading
import queue
import uuid
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('hotel_booking_service')

app = Flask(__name__)

# Service configuration
SERVICE_NAME = "hotel-booking"
SERVICE_VERSION = "1.0.0"
SERVICE_DESCRIPTION = "Hotel booking service for travel planning"
SERVICE_BASE_URL = "http://localhost:5004"

# Mock database of hotels and reservations
reservations = []
hotels = {
    "SanFrancisco": [
        {
            "hotel_id": "SF-LUXURY-01",
            "name": "Golden Gate Grand Hotel",
            "category": "Luxury",
            "address": "1234 Bay Street, San Francisco, CA 94111",
            "amenities": ["Spa", "Pool", "Fine Dining", "Fitness Center", "Concierge", "Room Service"],
            "rating": 4.8,
            "image_url": "https://example.com/gg_grand.jpg",
            "rooms": [
                {
                    "room_type": "Standard",
                    "price": 299.99,
                    "capacity": 2,
                    "features": ["King Bed", "City View", "Free Wifi", "Coffee Maker"]
                },
                {
                    "room_type": "Deluxe",
                    "price": 399.99,
                    "capacity": 2,
                    "features": ["King Bed", "Bay View", "Free Wifi", "Mini Bar", "Premium Toiletries"]
                },
                {
                    "room_type": "Suite",
                    "price": 599.99,
                    "capacity": 4,
                    "features": ["Two Queen Beds", "Bay View", "Free Wifi", "Mini Bar", "Living Area", "Jacuzzi"]
                }
            ]
        },
        {
            "hotel_id": "SF-BOUTIQUE-01",
            "name": "Mission District Boutique",
            "category": "Boutique",
            "address": "567 Valencia Street, San Francisco, CA 94110",
            "amenities": ["Artisan Breakfast", "Rooftop Lounge", "Bike Rentals", "Local Art Gallery"],
            "rating": 4.6,
            "image_url": "https://example.com/mission_boutique.jpg",
            "rooms": [
                {
                    "room_type": "Artist Room",
                    "price": 249.99,
                    "capacity": 2,
                    "features": ["Queen Bed", "Local Artwork", "Organic Toiletries", "Record Player"]
                },
                {
                    "room_type": "Curator Suite",
                    "price": 349.99,
                    "capacity": 2,
                    "features": ["King Bed", "Private Balcony", "Craft Minibar", "Smart Home Features"]
                }
            ]
        },
        {
            "hotel_id": "SF-BUDGET-01",
            "name": "Bay Budget Inn",
            "category": "Budget",
            "address": "789 Market Street, San Francisco, CA 94103",
            "amenities": ["Free Breakfast", "Self-Service Laundry", "Wifi", "24-Hour Reception"],
            "rating": 3.9,
            "image_url": "https://example.com/bay_budget.jpg",
            "rooms": [
                {
                    "room_type": "Standard",
                    "price": 149.99,
                    "capacity": 2,
                    "features": ["Queen Bed", "Cable TV", "Free Wifi"]
                },
                {
                    "room_type": "Double",
                    "price": 179.99,
                    "capacity": 4,
                    "features": ["Two Double Beds", "Cable TV", "Free Wifi", "Mini Fridge"]
                }
            ]
        }
    ],
    "NewYork": [
        {
            "hotel_id": "NY-LUXURY-01",
            "name": "Manhattan Skyline Hotel",
            "category": "Luxury",
            "address": "123 5th Avenue, New York, NY 10010",
            "amenities": ["Michelin Star Restaurant", "Spa", "Rooftop Pool", "Fitness Center", "Concierge", "Limo Service"],
            "rating": 4.9,
            "image_url": "https://example.com/manhattan_skyline.jpg",
            "rooms": [
                {
                    "room_type": "Premium",
                    "price": 399.99,
                    "capacity": 2,
                    "features": ["King Bed", "City View", "Premium Wifi", "Smart TV", "Nespresso Machine"]
                },
                {
                    "room_type": "Executive",
                    "price": 499.99,
                    "capacity": 2,
                    "features": ["King Bed", "Skyline View", "Premium Wifi", "Smart TV", "Tablet Control", "Premium Bar"]
                },
                {
                    "room_type": "Penthouse",
                    "price": 899.99,
                    "capacity": 4,
                    "features": ["Two King Beds", "Panoramic View", "Premium Wifi", "Home Theater", "Kitchen", "Private Terrace"]
                }
            ]
        },
        {
            "hotel_id": "NY-BOUTIQUE-01",
            "name": "SoHo Artist Loft",
            "category": "Boutique",
            "address": "456 Broadway, New York, NY 10013",
            "amenities": ["Art Gallery", "Wine Bar", "Library", "Roof Garden", "Designer Bicycles"],
            "rating": 4.7,
            "image_url": "https://example.com/soho_loft.jpg",
            "rooms": [
                {
                    "room_type": "Loft Room",
                    "price": 299.99,
                    "capacity": 2,
                    "features": ["Queen Bed", "High Ceilings", "Original Artwork", "Vinyl Collection", "Espresso Machine"]
                },
                {
                    "room_type": "Gallery Suite",
                    "price": 399.99,
                    "capacity": 2,
                    "features": ["King Bed", "Studio Space", "Art Supplies", "Projection System", "Soaking Tub"]
                }
            ]
        },
        {
            "hotel_id": "NY-BUDGET-01",
            "name": "Times Square Express",
            "category": "Budget",
            "address": "789 8th Avenue, New York, NY 10019",
            "amenities": ["Continental Breakfast", "Wifi", "Luggage Storage", "Tour Desk"],
            "rating": 3.8,
            "image_url": "https://example.com/times_express.jpg",
            "rooms": [
                {
                    "room_type": "Basic",
                    "price": 189.99,
                    "capacity": 2,
                    "features": ["Queen Bed", "Cable TV", "Free Wifi"]
                },
                {
                    "room_type": "Family",
                    "price": 209.99,
                    "capacity": 4,
                    "features": ["Two Double Beds", "Cable TV", "Free Wifi", "Mini Fridge"]
                }
            ]
        }
    ]
}

# SSE Implementation
sse_clients = set()

def generate_sse_event(event_type, data):
    """Format data as an SSE event"""
    # Don't add event type and timestamp to the data
    event_json = json.dumps(data)
    return f"event: {event_type}\ndata: {event_json}\n\n"

def get_service_info():
    """Generate service information for discovery"""
    service_id = "8551e521-338b-4bc6-b4d8-13fe6cf8cc0a"  # In a real system, this would be persistent
    
    return {
        "id": service_id,
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "description": SERVICE_DESCRIPTION,
        "baseUrl": SERVICE_BASE_URL,
        "health": "HEALTHY",
        "registered": time.time(),
        "lastUpdated": time.time(),
        "capabilities": [
            "search_hotels",
            "get_hotel_details",
            "book_hotel",
            "get_hotel_categories",
            "get_booking"
        ],
        "endpoints": [
            {
                "path": "/api/hotels/search",
                "methods": ["GET"],
                "description": "Search for hotels by city, dates, and guest count",
                "queryParams": ["city", "check_in", "check_out", "guests", "category"],
                "capability": "search_hotels"
            },
            {
                "path": "/api/hotels/{hotel_id}/details",
                "methods": ["GET"],
                "description": "Get detailed information about a specific hotel",
                "pathParams": ["hotel_id"],
                "capability": "get_hotel_details"
            },
            {
                "path": "/api/hotels/book",
                "methods": ["POST"],
                "description": "Book a hotel room",
                "bodyParams": ["hotel_id", "room_type", "check_in", "check_out", "guest_name", "guest_email"],
                "capability": "book_hotel"
            },
            {
                "path": "/api/hotels/categories",
                "methods": ["GET"],
                "description": "Get list of available hotel categories",
                "capability": "get_hotel_categories"
            },
            {
                "path": "/api/bookings/{booking_reference}",
                "methods": ["GET"],
                "description": "Get details of a specific booking",
                "pathParams": ["booking_reference"],
                "capability": "get_booking"
            }
        ]
    }

@app.route('/api/events', methods=['GET'])
def sse_stream():
    """SSE endpoint for service discovery"""
    def generate():
        # Create a client-specific queue
        client_queue = queue.Queue()
        sse_clients.add(client_queue)
        
        try:
            # Send initial catalog with this service's info
            service_info = get_service_info()
            initial_catalog = {
                "type": "INITIAL_CATALOG",
                "data": [service_info],
                "timestamp": time.time()
            }
            client_queue.put(generate_sse_event("INITIAL_CATALOG", initial_catalog))
            
            # Keep connection open
            while True:
                # Check if there are any events in the queue
                if not client_queue.empty():
                    yield client_queue.get()
                else:
                    # Send a heartbeat every 30 seconds
                    yield ":heartbeat\n\n"
                
                time.sleep(30)  # Sleep to prevent high CPU usage
        except GeneratorExit:
            # Client disconnected
            sse_clients.remove(client_queue)
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/hotels/search', methods=['GET'])
def search_hotels():
    """
    Search for hotels by city, dates, and guest count.
    
    Query parameters:
    - city: City name (required)
    - check_in: Check-in date in YYYY-MM-DD format (optional)
    - check_out: Check-out date in YYYY-MM-DD format (optional)
    - guests: Number of guests (optional, default: 1)
    - category: Hotel category (luxury, boutique, budget) (optional)
    
    Returns:
    - List of hotels matching the search criteria
    """
    city = request.args.get('city')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    guests = request.args.get('guests', default=1, type=int)
    category = request.args.get('category')  # Optional filter by hotel category
    
    if not city:
        return jsonify({"error": "City parameter is required"}), 400
    
    # Normalize city name
    city = city.replace(" ", "")
    
    if city.lower() not in ['sanfrancisco', 'newyork']:
        return jsonify({"error": "City not supported. Available cities: SanFrancisco, NewYork"}), 400
    
    # Map normalized city to proper format
    city_map = {
        "sanfrancisco": "SanFrancisco",
        "newyork": "NewYork"
    }
    city = city_map[city.lower()]
    
    # Validate dates if provided
    if check_in and check_out:
        try:
            check_in_date = datetime.datetime.strptime(check_in, '%Y-%m-%d')
            check_out_date = datetime.datetime.strptime(check_out, '%Y-%m-%d')
            
            if check_in_date >= check_out_date:
                return jsonify({"error": "Check-out date must be after check-in date"}), 400
                
            # In a real application, filter available rooms by date
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    # Get all hotels for the city
    city_hotels = hotels.get(city, [])
    
    # Filter by category if provided
    if category:
        city_hotels = [hotel for hotel in city_hotels if hotel["category"].lower() == category.lower()]
    
    # Add availability information based on capacity
    result_hotels = []
    for hotel in city_hotels:
        # Filter rooms that can accommodate the number of guests
        available_rooms = [room for room in hotel["rooms"] if room["capacity"] >= guests]
        
        if available_rooms:
            hotel_copy = hotel.copy()
            hotel_copy["rooms"] = available_rooms
            result_hotels.append(hotel_copy)
    
    return jsonify({
        "city": city,
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests,
        "results": result_hotels
    })

@app.route('/api/hotels/<hotel_id>/details', methods=['GET'])
def hotel_details(hotel_id):
    """
    Get detailed information about a specific hotel.
    
    Path parameters:
    - hotel_id: Hotel identifier
    
    Returns:
    - Detailed hotel information
    """
    for city_hotels in hotels.values():
        for hotel in city_hotels:
            if hotel['hotel_id'] == hotel_id:
                return jsonify(hotel)
    
    return jsonify({"error": "Hotel not found"}), 404

@app.route('/api/hotels/book', methods=['POST'])
def book_hotel():
    """
    Book a hotel room.
    
    Request body:
    - hotel_id: Hotel identifier (required)
    - room_type: Type of room to book (required)
    - check_in: Check-in date in YYYY-MM-DD format (required)
    - check_out: Check-out date in YYYY-MM-DD format (required)
    - guest_name: Name of the guest (required)
    - guest_email: Email of the guest (required)
    
    Returns:
    - Booking confirmation with reference number and details
    """
    data = request.get_json()
    
    required_fields = ['hotel_id', 'room_type', 'check_in', 'check_out', 'guest_name', 'guest_email']
    
    # Validate request data
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    hotel_id = data['hotel_id']
    room_type = data['room_type']
    check_in = data['check_in']
    check_out = data['check_out']
    guest_name = data['guest_name']
    guest_email = data['guest_email']
    
    # Validate dates
    try:
        check_in_date = datetime.datetime.strptime(check_in, '%Y-%m-%d')
        check_out_date = datetime.datetime.strptime(check_out, '%Y-%m-%d')
        
        if check_in_date >= check_out_date:
            return jsonify({"error": "Check-out date must be after check-in date"}), 400
            
        stay_duration = (check_out_date - check_in_date).days
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    # Find the hotel and room
    hotel_found = False
    room_found = False
    room_price = 0
    room_info = None
    hotel_name = ""
    
    for city_hotels in hotels.values():
        for hotel in city_hotels:
            if hotel['hotel_id'] == hotel_id:
                hotel_found = True
                hotel_name = hotel['name']
                
                for room in hotel['rooms']:
                    if room['room_type'] == room_type:
                        room_found = True
                        room_price = room['price']
                        room_info = room
                        break
                break
    
    if not hotel_found:
        return jsonify({"error": "Hotel not found"}), 404
    
    if not room_found:
        return jsonify({"error": "Room type not available at this hotel"}), 400
    
    # In a real application, check if room is available for the selected dates
    
    # Generate booking reference and confirmation
    booking_reference = f"BK-{random.randint(100000, 999999)}"
    total_price = stay_duration * room_price
    
    # Store the reservation
    reservation = {
        "booking_reference": booking_reference,
        "hotel_id": hotel_id,
        "hotel_name": hotel_name,
        "room_type": room_type,
        "room_info": room_info,
        "check_in": check_in,
        "check_out": check_out,
        "guest_name": guest_name,
        "guest_email": guest_email,
        "stay_duration": stay_duration,
        "total_price": total_price,
        "status": "confirmed",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    reservations.append(reservation)
    
    return jsonify({
        "status": "success",
        "booking_reference": booking_reference,
        "hotel_name": hotel_name,
        "room_type": room_type,
        "check_in": check_in,
        "check_out": check_out,
        "guest_name": guest_name,
        "stay_duration": stay_duration,
        "total_price": total_price
    })

@app.route('/api/hotels/categories', methods=['GET'])
def hotel_categories():
    """
    Get list of available hotel categories.
    
    Returns:
    - List of hotel categories with descriptions
    """
    return jsonify({
        "categories": [
            {
                "id": "luxury",
                "name": "Luxury",
                "description": "High-end accommodations with premium amenities and services."
            },
            {
                "id": "boutique",
                "name": "Boutique",
                "description": "Unique, stylish hotels with personalized service and distinctive character."
            },
            {
                "id": "budget",
                "name": "Budget",
                "description": "Affordable accommodations with essential amenities for cost-conscious travelers."
            }
        ]
    })

@app.route('/api/bookings/<booking_reference>', methods=['GET'])
def get_booking(booking_reference):
    """
    Get details of a specific booking.
    
    Path parameters:
    - booking_reference: Booking reference number
    
    Returns:
    - Detailed booking information
    """
    for reservation in reservations:
        if reservation['booking_reference'] == booking_reference:
            return jsonify(reservation)
    
    return jsonify({"error": "Booking not found"}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint.
    
    Returns:
    - Health status of the service
    """
    return jsonify({
        "status": "HEALTHY",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "timestamp": datetime.datetime.now().isoformat()
    })

@app.route('/api/capabilities', methods=['GET'])
def capabilities():
    """
    Get service capabilities.
    
    Returns:
    - Service information including capabilities and endpoints
    """
    return get_service_info()

if __name__ == '__main__':
    logger.info(f"Starting {SERVICE_NAME} service on {SERVICE_BASE_URL}")
    app.run(host='0.0.0.0', port=5004, debug=True, threaded=True)
