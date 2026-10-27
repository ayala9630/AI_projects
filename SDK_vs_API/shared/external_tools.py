"""External tool example: current weather via Open-Meteo (no API key required).
The HTTP function is injectable so tests can run offline.
"""
from __future__ import annotations
from typing import Any
import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

def get_weather(city: str, http_get=requests.get) -> dict[str, Any]:
    city = city.strip()
    if not city:
        raise ValueError("city must not be empty")
    geo = http_get(GEOCODE_URL, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=10)
    geo.raise_for_status()
    locations = geo.json().get("results", [])
    if not locations:
        return {"city": city, "error": "City not found"}
    place = locations[0]
    weather = http_get(
        WEATHER_URL,
        params={"latitude": place["latitude"], "longitude": place["longitude"],
                "current": "temperature_2m,precipitation,wind_speed_10m"},
        timeout=10,
    )
    weather.raise_for_status()
    current = weather.json().get("current", {})
    return {
        "city": place.get("name", city),
        "country": place.get("country"),
        "temperature_c": current.get("temperature_2m"),
        "precipitation_mm": current.get("precipitation"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "source": "Open-Meteo",
    }
