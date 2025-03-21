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
logger = logging.getLogger('weather_forecast_service')

app = Flask(__name__)

# Service configuration
SERVICE_NAME = "weather-forecast"
SERVICE_VERSION = "1.0.0"
SERVICE_DESCRIPTION = "Weather forecast service for travel planning"
SERVICE_BASE_URL = "http://localhost:5003"

# Weather conditions for variety
weather_conditions = [
    "Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Heavy Rain", 
    "Thunderstorm", "Foggy", "Windy", "Clear"
]

# Temperature ranges for each city by season (min, max in °F)
temp_ranges = {
    "SanFrancisco": {
        "winter": (45, 60),
        "spring": (50, 65),
        "summer": (60, 75),
        "fall": (55, 70)
    },
    "NewYork": {
        "winter": (25, 40),
        "spring": (45, 65),
        "summer": (70, 90),
        "fall": (50, 70)
    }
}

# Probability of precipitation by condition
precip_prob = {
    "Sunny": (0, 5),
    "Partly Cloudy": (5, 20),
    "Cloudy": (20, 40),
    "Light Rain": (60, 80),
    "Heavy Rain": (80, 100),
    "Thunderstorm": (70, 100),
    "Foggy": (10, 30),
    "Windy": (5, 25),
    "Clear": (0, 5)
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
    service_id = str(uuid.uuid4())  # In a real system, this would be persistent
    
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
            "get_forecast",
            "get_current_weather",
            "get_available_cities"
        ],
        "endpoints": [
            {
                "path": "/api/weather/forecast",
                "methods": ["GET"],
                "description": "Get weather forecast for a city",
                "queryParams": ["city", "days"],
                "capability": "get_forecast"
            },
            {
                "path": "/api/weather/current",
                "methods": ["GET"],
                "description": "Get current weather for a city",
                "queryParams": ["city"],
                "capability": "get_current_weather"
            },
            {
                "path": "/api/weather/cities",
                "methods": ["GET"],
                "description": "Get list of available cities for forecasts",
                "capability": "get_available_cities"
            }
        ]
    }

def get_season(date):
    month = date.month
    if 3 <= month <= 5:
        return "spring"
    elif 6 <= month <= 8:
        return "summer"
    elif 9 <= month <= 11:
        return "fall"
    else:
        return "winter"

def generate_weather(city, date):
    season = get_season(date)
    temp_range = temp_ranges[city][season]
    
    # Generate a random condition with seasonal weighting
    if season == "summer":
        weights = [0.4, 0.3, 0.1, 0.1, 0.05, 0.05, 0, 0, 0]  # More sunny, less rain
    elif season == "winter":
        weights = [0.1, 0.2, 0.3, 0.2, 0.1, 0.05, 0.05, 0, 0]  # More cloudy/rainy
    else:
        weights = [0.25, 0.25, 0.2, 0.1, 0.05, 0.05, 0.05, 0.05, 0]  # Mixed
        
    # Adjust for specific city characteristics
    if city == "SanFrancisco" and season == "summer":
        # SF often has summer fog
        weights[6] = 0.3  # Increase foggy probability
        weights[0] -= 0.15  # Reduce sunny probability
        weights[1] -= 0.15  # Reduce partly cloudy probability
    
    # Generate a somewhat consistent pattern (not totally random)
    day_seed = date.day + date.month * 31 + city.count("a") * 7
    random.seed(day_seed)
    condition_idx = random.choices(range(len(weather_conditions)), weights=weights, k=1)[0]
    condition = weather_conditions[condition_idx]
    
    # Temperature based on condition and seasonal range
    if condition in ["Sunny", "Clear"]:
        temp_min = temp_range[0] + (temp_range[1] - temp_range[0]) * 0.4
        temp_max = temp_range[1]
    elif condition in ["Light Rain", "Heavy Rain", "Thunderstorm"]:
        temp_min = temp_range[0]
        temp_max = temp_range[0] + (temp_range[1] - temp_range[0]) * 0.7
    else:
        temp_min = temp_range[0] + (temp_range[1] - temp_range[0]) * 0.2
        temp_max = temp_range[0] + (temp_range[1] - temp_range[0]) * 0.9
    
    # Generate the high and low temps for the day
    high_temp = round(random.uniform(temp_min + 5, temp_max), 1)
    low_temp = round(random.uniform(temp_range[0], temp_min + 5), 1)
    
    # Generate precipitation probability
    precip_range = precip_prob[condition]
    precipitation_prob = random.randint(precip_range[0], precip_range[1])
    
    # Generate humidity
    if condition in ["Foggy", "Heavy Rain", "Thunderstorm"]:
        humidity = random.randint(70, 95)
    elif condition in ["Light Rain", "Cloudy"]:
        humidity = random.randint(60, 85)
    else:
        humidity = random.randint(40, 70)
    
    # Generate wind speed
    if condition == "Windy":
        wind_speed = random.randint(15, 30)
    else:
        wind_speed = random.randint(2, 15)
    
    return {
        "date": date.strftime("%Y-%m-%d"),
        "condition": condition,
        "high_temp_f": high_temp,
        "low_temp_f": low_temp,
        "high_temp_c": round((high_temp - 32) * 5/9, 1),
        "low_temp_c": round((low_temp - 32) * 5/9, 1),
        "precipitation_probability": precipitation_prob,
        "humidity": humidity,
        "wind_speed_mph": wind_speed,
        "wind_speed_kph": round(wind_speed * 1.60934, 1)
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

@app.route('/api/weather/forecast', methods=['GET'])
def get_forecast():
    """
    Get weather forecast for a city.
    
    Query parameters:
    - city: City name (required)
    - days: Number of days for forecast (optional, default: 5, max: 10)
    
    Returns:
    - Weather forecast for the specified number of days
    """
    city = request.args.get('city')
    days = request.args.get('days', default=5, type=int)
    
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
    
    # Limit forecast to maximum 10 days
    days = min(days, 10)
    
    # Generate forecast starting from today
    today = datetime.datetime.now()
    forecast = []
    
    for i in range(days):
        forecast_date = today + datetime.timedelta(days=i)
        forecast.append(generate_weather(city, forecast_date))
    
    return jsonify({
        "city": city,
        "forecast_generated": today.strftime("%Y-%m-%d %H:%M:%S"),
        "days": days,
        "forecast": forecast
    })

@app.route('/api/weather/current', methods=['GET'])
def get_current_weather():
    """
    Get current weather for a city.
    
    Query parameters:
    - city: City name (required)
    
    Returns:
    - Current weather conditions
    """
    city = request.args.get('city')
    
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
    
    # Generate current weather
    now = datetime.datetime.now()
    weather = generate_weather(city, now)
    
    # Add current temperature between high and low
    current_temp_f = round(random.uniform(weather["low_temp_f"], weather["high_temp_f"]), 1)
    
    return jsonify({
        "city": city,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "condition": weather["condition"],
        "current_temp_f": current_temp_f,
        "current_temp_c": round((current_temp_f - 32) * 5/9, 1),
        "feels_like_f": round(current_temp_f - random.uniform(-3, 3), 1),
        "high_temp_f": weather["high_temp_f"],
        "low_temp_f": weather["low_temp_f"],
        "precipitation_probability": weather["precipitation_probability"],
        "humidity": weather["humidity"],
        "wind_speed_mph": weather["wind_speed_mph"],
        "sunrise": "06:45 AM" if city == "SanFrancisco" else "06:30 AM",
        "sunset": "07:30 PM" if city == "SanFrancisco" else "07:15 PM"
    })

@app.route('/api/weather/cities', methods=['GET'])
def get_available_cities():
    """
    Get list of available cities for forecasts.
    
    Returns:
    - List of cities with geographical information
    """
    return jsonify({
        "cities": [
            {
                "id": "SanFrancisco",
                "name": "San Francisco",
                "state": "California",
                "country": "United States",
                "latitude": 37.7749,
                "longitude": -122.4194
            },
            {
                "id": "NewYork",
                "name": "New York",
                "state": "New York",
                "country": "United States",
                "latitude": 40.7128,
                "longitude": -74.0060
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
    - Service information including capabilities and endpoints
    """
    return get_service_info()

if __name__ == '__main__':
    logger.info(f"Starting {SERVICE_NAME} service on {SERVICE_BASE_URL}")
    app.run(host='0.0.0.0', port=5003, debug=True, threaded=True)
