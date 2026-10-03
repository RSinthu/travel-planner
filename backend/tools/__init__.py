"""Tools the travel agents can call. Each returns {"status": "success", "data": ...}
or {"status": "error", "error_message": ...} and never raises."""

from .budget import calculate_trip_budget
from .flights import search_flights
from .hotels import find_hotels_near, search_hotels
from .places import find_attractions
from .weather import get_weather_forecast

__all__ = [
    "calculate_trip_budget",
    "find_attractions",
    "find_hotels_near",
    "get_weather_forecast",
    "search_flights",
    "search_hotels",
]
