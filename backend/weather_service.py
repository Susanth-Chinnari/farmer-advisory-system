"""
weather_service.py - Weather Information & Agricultural Recommendations

Beginner-Friendly Explanation:
Weather drastically dictates farming choices: when to irrigate, spray pesticides,
or harvest. This service fetches current weather metrics from the OpenWeatherMap API.
If the API key is not yet configured or the network is unavailable, it gracefully
switches to a "Simulated / Demo Mode" so the college project works offline and during reviews.
Secrets (API keys) are kept strictly on the backend and are NEVER exposed to client JavaScript.
"""

import requests
from typing import Dict, Any, Optional
from backend.config import WEATHER_API_KEY, DEFAULT_CITY


def get_farming_weather_advisory(temp_c: float, humidity_pct: int, condition: str, wind_kph: float) -> str:
    """
    Generates beginner-friendly, practical agricultural advice based on current weather.
    """
    condition_lower = condition.lower()
    advisory_points = []

    # Rain / Storm advisory
    if 'rain' in condition_lower or 'drizzle' in condition_lower or 'thunder' in condition_lower:
        advisory_points.append("Rain is occurring or expected. Delay pesticide/fertilizer spraying to avoid chemical runoff.")
        advisory_points.append("Ensure drainage channels in waterlogged fields are clear.")
    elif humidity_pct > 80:
        advisory_points.append("High humidity increases risk of fungal blight and leaf spots. Monitor lower leaves closely.")
    elif humidity_pct < 30 and temp_c > 30:
        advisory_points.append("Hot, dry conditions accelerate soil moisture loss. Schedule drip irrigation during cooler early morning or evening hours.")

    # Wind advisory
    if wind_kph > 20:
        advisory_points.append("High winds detected (>20 km/h). Postpone foliar spraying to prevent spray drift.")

    # General fallback advisory if conditions are mild
    if not advisory_points:
        advisory_points.append("Favorable weather conditions for routine field maintenance, weeding, and normal irrigation.")

    return " ".join(advisory_points)


def get_simulated_weather(city: str) -> Dict[str, Any]:
    """
    Returns realistic simulated agricultural weather data when no API key is available
    or when external network requests fail.
    Clearly labeled with is_simulated=True.
    """
    clean_city = city.split(',')[0].title() if city else "Delhi"
    temp_c = 28.0
    humidity = 58
    condition = "Partly Cloudy"
    wind_kph = 12.0

    advisory = get_farming_weather_advisory(temp_c, humidity, condition, wind_kph)

    return {
        "success": True,
        "is_simulated": True,
        "city": clean_city,
        "temperature_c": temp_c,
        "condition": condition,
        "humidity_pct": humidity,
        "wind_speed_kph": wind_kph,
        "advisory": advisory,
        "status_badge": "Simulated / Demo Mode",
        "notice": "Running in offline demo mode. To show live regional data, add WEATHER_API_KEY to .env."
    }


def fetch_weather(city: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches real-time weather from OpenWeatherMap API using server-side credentials.
    Falls back gracefully to simulated data on any network or configuration error.
    """
    target_city = (city or DEFAULT_CITY).strip()

    # If no API key configured, use simulated demo weather
    if not WEATHER_API_KEY or WEATHER_API_KEY == "your_openweathermap_api_key_here":
        return get_simulated_weather(target_city)

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": target_city,
        "appid": WEATHER_API_KEY,
        "units": "metric"
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code != 200:
            # Handle invalid city, invalid key, or rate limit
            simulated = get_simulated_weather(target_city)
            simulated["notice"] = f"OpenWeatherMap returned status {response.status_code}. Displaying simulated weather."
            return simulated

        data = response.json()
        temp_c = round(data.get("main", {}).get("temp", 25.0), 1)
        humidity = data.get("main", {}).get("humidity", 50)
        condition = data.get("weather", [{}])[0].get("main", "Clear")
        wind_mps = data.get("wind", {}).get("speed", 3.0)
        wind_kph = round(wind_mps * 3.6, 1)

        advisory = get_farming_weather_advisory(temp_c, humidity, condition, wind_kph)

        return {
            "success": True,
            "is_simulated": False,
            "city": data.get("name", target_city),
            "temperature_c": temp_c,
            "condition": condition,
            "humidity_pct": humidity,
            "wind_speed_kph": wind_kph,
            "advisory": advisory,
            "status_badge": "Live Data",
            "notice": None
        }

    except requests.exceptions.RequestException as e:
        # Gracefully handle network timeouts or DNS resolution issues
        simulated = get_simulated_weather(target_city)
        simulated["notice"] = f"Network error connecting to weather API ({str(e)}). Showing simulated data."
        return simulated
