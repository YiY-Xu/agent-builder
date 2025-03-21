from flask import Flask, request, jsonify, Response
import random
import datetime
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
logger = logging.getLogger('car_rental_service')

app = Flask(__name__)

# Service configuration
SERVICE_NAME = "car-rental"
SERVICE_VERSION = "1.0.0"
SERVICE_DESCRIPTION = "Car rental service for travel planning"
SERVICE_BASE_URL = "http://localhost:5002"

# Mock database of available cars
cars = {
    "SanFrancisco": [
        {
            "car_id": "SF-ECO-001",
            "type": "Economy",
            "make": "Toyota",
            "model": "Corolla",
            "year": 2023,
            "daily_rate": 49.99,
            "available": True,
            "features": ["GPS", "Bluetooth", "Fuel Efficient"]
        },
        {
            "car_id": "SF-ECO-002",
            "type": "Economy",
            "make": "Honda",
            "model": "Civic",
            "year": 2022,
            "daily_rate": 45.99,
            "available": True,
            "features": ["GPS", "Bluetooth", "Backup Camera"]
        },
        {
            "car_id": "SF-MID-001",
            "type": "Midsize",
            "make": "Mazda",
            "model": "6",
            "year": 2023,
            "daily_rate": 69.99,
            "available": True,
            "features": ["Leather Seats", "Sunroof", "Advanced Safety Features"]
        },
        {
            "car_id": "SF-MID-002",
            "type": "Midsize",
            "make": "Ford",
            "model": "Fusion",
            "year": 2022,
            "daily_rate": 65.99,
            "available": True,
            "features": ["Apple CarPlay", "Android Auto", "Power Seats"]
        },
        {
            "car_id": "SF-SUV-001",
            "type": "SUV",
            "make": "Jeep",
            "model": "Grand Cherokee",
            "year": 2023,
            "daily_rate": 89.99,
            "available": True,
            "features": ["4WD", "Spacious Cargo", "Towing Package"]
        },
        {
            "car_id": "SF-SUV-002",
            "type": "SUV",
            "make": "Toyota",
            "model": "RAV4",
            "year": 2023,
            "daily_rate": 79.99,
            "available": True,
            "features": ["Hybrid Engine", "Panoramic View", "Advanced Safety"]
        }
    ],
    "NewYork": [
        {
            "car_id": "NY-ECO-001",
            "type": "Economy",
            "make": "Nissan",
            "model": "Versa",
            "year": 2023,
            "daily_rate": 54.99,
            "available": True,
            "features": ["Fuel Efficient", "Compact for City Parking", "Bluetooth"]
        },
        {
            "car_id": "NY-ECO-002",
            "type": "Economy",
            "make": "Hyundai",
            "model": "Accent",
            "year": 2022,
            "daily_rate": 49.99,
            "available": True,
            "features": ["USB Ports", "Backup Camera", "Cruise Control"]
        },
        {
            "car_id": "NY-MID-001",
            "type": "Midsize",
            "make": "Chevrolet",
            "model": "Malibu",
            "year": 2023,
            "daily_rate": 74.99,
            "available": True,
            "features": ["Spacious Interior", "Wifi Hotspot", "Heated Seats"]
        },
        {
            "car_id": "NY-MID-002",
            "type": "Midsize",
            "make": "Kia",
            "model": "Optima",
            "year": 2022,
            "daily_rate": 69.99,
            "available": True,
            "features": ["Push Button Start", "Blind Spot Detection", "Apple CarPlay"]
        },
        {
            "car_id": "NY-SUV-001",
            "type": "SUV",
            "make": "Ford",
            "model": "Explorer",
            "year": 2023,
            "daily_rate": 94.99,
            "available": True,
            "features": ["Third Row Seating", "Adaptive Cruise Control", "Premium Sound"]
        },
        {
            "car_id": "NY-SUV-002",
            "type": "SUV",
            "make": "Honda",
            "model": "CR-V",
            "year": 2023,
            "daily_rate": 84.99,
            "available": True,
            "features": ["Efficient Engine", "Cargo Space", "Heated Steering Wheel"]
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
    service_id = "710c2ef8-e916-4698-ac18-f08c38242d21"  # In a real system, this would be persistent
    
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
            "search_cars",
            "get_car_details",
            "reserve_car",
            "get_car_types"
        ],
        "endpoints": [
            {
                "path": "/api/cars/available",
                "methods": ["GET"],
                "description": "Search for available cars by location and type",
                "queryParams": ["location", "type"],
                "capability": "search_cars"
            },
            {
                "path": "/api/cars/{car_id}/details",
                "methods": ["GET"],
                "description": "Get detailed information about a specific car",
                "pathParams": ["car_id"],
                "capability": "get_car_details"
            },
            {
                "path": "/api/cars/reserve",
                "methods": ["POST"],
                "description": "Reserve a car for a specific date range",
                "bodyParams": ["car_id", "start_date", "end_date"],
                "capability": "reserve_car"
            },
            {
                "path": "/api/cars/types",
                "methods": ["GET"],
                "description": "Get list of available car types",
                "capability": "get_car_types"
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

@app.route('/api/cars/available', methods=['GET'])
def available_cars():
    """
    Search for available cars by location and optionally by type.
    
    Query parameters:
    - location: City name (required)
    - type: Car type (economy, midsize, suv) (optional)
    
    Returns:
    - List of available cars matching the criteria
    """
    location = request.args.get('location')
    car_type = request.args.get('type')  # Optional filter by car type
    
    if not location:
        return jsonify({"error": "Location is required"}), 400
    
    # Normalize location name
    location = location.replace(" ", "")
    
    if location.lower() not in ['sanfrancisco', 'newyork']:
        return jsonify({"error": "Location not supported. Available locations: SanFrancisco, NewYork"}), 400
    
    # Map normalized location to proper format
    location_map = {
        "sanfrancisco": "SanFrancisco",
        "newyork": "NewYork"
    }
    location = location_map[location.lower()]
    
    # Filter by car type if provided
    if car_type:
        car_type = car_type.lower()
        filtered_cars = [car for car in cars[location] if car["type"].lower() == car_type and car["available"]]
        return jsonify({"location": location, "type": car_type, "cars": filtered_cars})
    
    # Return all available cars for the location
    available_cars = [car for car in cars[location] if car["available"]]
    return jsonify({"location": location, "cars": available_cars})

@app.route('/api/cars/<car_id>/details', methods=['GET'])
def car_details(car_id):
    """
    Get detailed information about a specific car.
    
    Path parameters:
    - car_id: Car identifier
    
    Returns:
    - Detailed car information
    """
    # Search for the car in our mock database
    for location, location_cars in cars.items():
        for car in location_cars:
            if car['car_id'] == car_id:
                return jsonify(car)
    
    return jsonify({"error": "Car not found"}), 404

@app.route('/api/cars/reserve', methods=['POST'])
def reserve_car():
    """
    Reserve a car for a specific date range.
    
    Request body:
    - car_id: Car identifier (required)
    - start_date: Start date in YYYY-MM-DD format (required)
    - end_date: End date in YYYY-MM-DD format (required)
    
    Returns:
    - Reservation confirmation with details and total price
    """
    data = request.get_json()
    
    if not data or 'car_id' not in data or 'start_date' not in data or 'end_date' not in data:
        return jsonify({"error": "Car ID, start date, and end date are required"}), 400
    
    car_id = data['car_id']
    start_date = data['start_date']  # Format expected: YYYY-MM-DD
    end_date = data['end_date']      # Format expected: YYYY-MM-DD
    
    # Validate car exists and is available
    car_found = False
    total_days = 0
    car_details = None
    
    try:
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        total_days = (end - start).days
        
        if total_days < 1:
            return jsonify({"error": "End date must be after start date"}), 400
            
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    for location, location_cars in cars.items():
        for car in location_cars:
            if car['car_id'] == car_id:
                car_found = True
                car_details = car
                if not car['available']:
                    return jsonify({"error": "Car is not available for the selected dates"}), 400
                break
    
    if not car_found:
        return jsonify({"error": "Car not found"}), 404
    
    # Generate a mock reservation ID
    reservation_id = f"RES-{random.randint(10000, 99999)}"
    
    return jsonify({
        "status": "success",
        "reservation_id": reservation_id,
        "car_id": car_id,
        "car_details": {
            "make": car_details["make"],
            "model": car_details["model"],
            "type": car_details["type"]
        },
        "start_date": start_date,
        "end_date": end_date,
        "total_days": total_days,
        "daily_rate": car_details["daily_rate"],
        "total_price": round(total_days * car_details["daily_rate"], 2)
    })

@app.route('/api/cars/types', methods=['GET'])
def car_types():
    """
    Get list of available car types.
    
    Returns:
    - List of car types with descriptions
    """
    return jsonify({
        "types": [
            {
                "id": "economy",
                "name": "Economy",
                "description": "Fuel-efficient compact cars ideal for city driving and budget-conscious travelers."
            },
            {
                "id": "midsize",
                "name": "Midsize",
                "description": "Comfortable sedans with additional features and space for passengers and luggage."
            },
            {
                "id": "suv",
                "name": "SUV",
                "description": "Spacious vehicles with higher ground clearance, suitable for families or groups."
            }
        ]
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
    - List of capabilities supported by this service
    """
    return get_service_info()

if __name__ == '__main__':
    logger.info(f"Starting {SERVICE_NAME} service on {SERVICE_BASE_URL}")
    app.run(host='0.0.0.0', port=5002, debug=True, threaded=True)
