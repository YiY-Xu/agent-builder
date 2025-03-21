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
logger = logging.getLogger('flight_ticket_service')

app = Flask(__name__)

# Service configuration
SERVICE_NAME = "flight-booking"
SERVICE_VERSION = "1.0.0"
SERVICE_DESCRIPTION = "Flight booking service for travel planning"
SERVICE_BASE_URL = "http://localhost:5001"

# Mock database of flights
flights = {
    "SanFrancisco-NewYork": [
        {
            "flight_id": "SF-NY-001",
            "airline": "Pacific Air",
            "departure_city": "San Francisco",
            "arrival_city": "New York",
            "departure_time": "08:00 AM",
            "arrival_time": "04:30 PM",
            "price": 349.99,
            "seats_available": 42
        },
        {
            "flight_id": "SF-NY-002",
            "airline": "Golden Gate Airways",
            "departure_city": "San Francisco",
            "arrival_city": "New York",
            "departure_time": "11:30 AM",
            "arrival_time": "08:00 PM",
            "price": 299.99,
            "seats_available": 28
        },
        {
            "flight_id": "SF-NY-003",
            "airline": "American Eagle",
            "departure_city": "San Francisco",
            "arrival_city": "New York",
            "departure_time": "02:15 PM",
            "arrival_time": "10:45 PM",
            "price": 389.99,
            "seats_available": 15
        },
        {
            "flight_id": "SF-NY-004",
            "airline": "West Coast Express",
            "departure_city": "San Francisco",
            "arrival_city": "New York",
            "departure_time": "06:00 PM",
            "arrival_time": "02:30 AM",
            "price": 279.99,
            "seats_available": 32
        }
    ],
    "NewYork-SanFrancisco": [
        {
            "flight_id": "NY-SF-001",
            "airline": "Empire State Airways",
            "departure_city": "New York",
            "arrival_city": "San Francisco",
            "departure_time": "07:00 AM",
            "arrival_time": "10:30 AM",
            "price": 369.99,
            "seats_available": 22
        },
        {
            "flight_id": "NY-SF-002",
            "airline": "Liberty Flights",
            "departure_city": "New York",
            "arrival_city": "San Francisco",
            "departure_time": "10:45 AM",
            "arrival_time": "02:15 PM",
            "price": 329.99,
            "seats_available": 18
        },
        {
            "flight_id": "NY-SF-003",
            "airline": "Transcontinental",
            "departure_city": "New York",
            "arrival_city": "San Francisco",
            "departure_time": "01:30 PM",
            "arrival_time": "05:00 PM",
            "price": 359.99,
            "seats_available": 25
        },
        {
            "flight_id": "NY-SF-004",
            "airline": "East-West Connect",
            "departure_city": "New York",
            "arrival_city": "San Francisco",
            "departure_time": "05:15 PM",
            "arrival_time": "08:45 PM",
            "price": 309.99,
            "seats_available": 30
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
    service_id = "1c35e4ce-1dac-4f18-b4db-cdbbcda0d66e"  # In a real system, this would be persistent
    
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
            "search_flights",
            "get_flight_details",
            "book_flight"
        ],
        "endpoints": [
            {
                "path": "/api/flights/search",
                "methods": ["GET"],
                "description": "Search for flights between origin and destination",
                "queryParams": ["origin", "destination", "date"],
                "capability": "search_flights"
            },
            {
                "path": "/api/flights/{flight_id}/details",
                "methods": ["GET"],
                "description": "Get detailed information about a specific flight",
                "pathParams": ["flight_id"],
                "capability": "get_flight_details"
            },
            {
                "path": "/api/flights/book",
                "methods": ["POST"],
                "description": "Book a flight for one or more passengers",
                "bodyParams": ["flight_id", "passengers"],
                "capability": "book_flight"
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

@app.route('/api/flights/search', methods=['GET'])
def search_flights():
    """
    Search for flights between origin and destination on a specific date.
    
    Query parameters:
    - origin: Origin city (required)
    - destination: Destination city (required)
    - date: Flight date in YYYY-MM-DD format (optional)
    
    Returns:
    - List of available flights matching the criteria
    """
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    date = request.args.get('date')  # Format: YYYY-MM-DD
    
    if not origin or not destination:
        return jsonify({"error": "Origin and destination are required"}), 400
    
    # Normalize city names
    origin = origin.replace(" ", "").lower()
    destination = destination.replace(" ", "").lower()
    
    # Map normalized names to proper format for lookup
    city_map = {
        "sanfrancisco": "SanFrancisco",
        "newyork": "NewYork"
    }
    
    if origin.lower() in city_map:
        origin = city_map[origin.lower()]
    
    if destination.lower() in city_map:
        destination = city_map[destination.lower()]
    
    route_key = f"{origin}-{destination}"
    
    if route_key not in flights:
        return jsonify({"error": "No flights available for this route"}), 404
    
    # If date is provided, we can pretend to filter by date (though we're returning all flights)
    if date:
        try:
            # Validate date format
            datetime.datetime.strptime(date, '%Y-%m-%d')
            # We're not actually filtering by date in this mock
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    return jsonify({
        "route": route_key,
        "date": date,
        "flights": flights[route_key]
    })

@app.route('/api/flights/<flight_id>/details', methods=['GET'])
def flight_details(flight_id):
    """
    Get detailed information about a specific flight.
    
    Path parameters:
    - flight_id: Flight identifier
    
    Returns:
    - Detailed flight information
    """
    # Search for the flight in our mock database
    for route in flights.values():
        for flight in route:
            if flight['flight_id'] == flight_id:
                return jsonify(flight)
    
    return jsonify({"error": "Flight not found"}), 404

@app.route('/api/flights/book', methods=['POST'])
def book_flight():
    """
    Book a flight for one or more passengers.
    
    Request body:
    - flight_id: Flight identifier (required)
    - passengers: List of passenger information (required)
    
    Returns:
    - Booking confirmation with reference number
    """
    data = request.get_json()
    
    if not data or 'flight_id' not in data or 'passengers' not in data:
        return jsonify({"error": "Flight ID and passenger information required"}), 400
    
    flight_id = data['flight_id']
    passengers = data['passengers']
    
    # Validate flight exists
    flight_found = False
    for route in flights.values():
        for flight in route:
            if flight['flight_id'] == flight_id:
                flight_found = True
                if len(passengers) > flight['seats_available']:
                    return jsonify({"error": "Not enough seats available"}), 400
                # In a real application, we would decrease available seats
                break
    
    if not flight_found:
        return jsonify({"error": "Flight not found"}), 404
    
    # Generate a mock booking reference
    booking_reference = f"BK-{random.randint(10000, 99999)}"
    
    return jsonify({
        "status": "success",
        "booking_reference": booking_reference,
        "flight_id": flight_id,
        "passengers": passengers,
        "total_price": len(passengers) * next(
            (flight['price'] for route in flights.values() for flight in route if flight['flight_id'] == flight_id), 
            0
        )
    })

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
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
