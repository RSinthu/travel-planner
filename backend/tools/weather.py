"""Open-Meteo forecast tool (free, no API key, non-commercial use)."""

from datetime import date, timedelta

from ._geo import geocode_city
from ._http import ToolError, error, ok, request_json
from ._validate import country_code as check_country, date_range

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MAX_FORECAST_DAYS = 16  # Open-Meteo forecasts today + 15 days

DAILY_VARIABLES = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
]

# WMO weather interpretation codes used by Open-Meteo.
WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Freezing fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Light freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Violent showers",
    85: "Light snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}

# A day is "rain likely" at this % chance, or when at least this much rain is expected.
RAIN_PROBABILITY_THRESHOLD = 50
RAIN_AMOUNT_THRESHOLD_MM = 1.0


async def get_weather_forecast(city: str, start_date: str, end_date: str, country_code: str = "") -> dict:
    """Get the daily weather forecast for a city between two dates (inclusive).

    Forecasts only reach 16 days ahead (today plus 15 days). For later trips this
    returns an error, and you should describe typical seasonal weather instead.
    Temperatures are in °C, precipitation in mm, wind in km/h.

    Args:
        city: City name, for example "Paris".
        start_date: First day of the trip, YYYY-MM-DD.
        end_date: Last day of the trip, YYYY-MM-DD.
        country_code: Optional 2-letter country code to pick the right city, for example "FR".

    Returns:
        On success: {"status": "success", "data": {"location": {...}, "days": [{"date",
        "condition", "temp_max_c", "temp_min_c", "precipitation_mm",
        "rain_probability_pct", "wind_max_kmh", "rain_likely"}, ...]}}.
        On failure: {"status": "error", "error_message": "..."}.
    """
    try:
        start, end = date_range(start_date, end_date, "start_date", "end_date", same_day_ok=True)
        last_forecast_day = date.today() + timedelta(days=MAX_FORECAST_DAYS - 1)
        if end > last_forecast_day:
            raise ToolError(
                f"Forecasts only cover the next {MAX_FORECAST_DAYS} days "
                f"(until {last_forecast_day.isoformat()}). Describe typical weather for that season instead."
            )

        location = await geocode_city(city, check_country(country_code, required=False))
        payload = await request_json(
            "GET",
            FORECAST_URL,
            service="Open-Meteo",
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "daily": ",".join(DAILY_VARIABLES),
                "timezone": location["timezone"],
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
        )
        daily = payload.get("daily") or {}
        if not daily.get("time"):
            raise ToolError("Open-Meteo returned no forecast for those dates.")
        return ok({"location": location, "days": _days(daily)})
    except ToolError as exc:
        return error(str(exc))


def _days(daily: dict) -> list[dict]:
    def column(name: str) -> list:
        return daily.get(name) or [None] * len(daily["time"])

    days = []
    for day, code, t_max, t_min, rain_mm, rain_pct, wind in zip(
        daily["time"],
        column("weather_code"),
        column("temperature_2m_max"),
        column("temperature_2m_min"),
        column("precipitation_sum"),
        column("precipitation_probability_max"),
        column("wind_speed_10m_max"),
    ):
        days.append({
            "date": day,
            "condition": WMO_CODES.get(code, "Unknown"),
            "temp_max_c": t_max,
            "temp_min_c": t_min,
            "precipitation_mm": rain_mm,
            "rain_probability_pct": rain_pct,
            "wind_max_kmh": wind,
            "rain_likely": (rain_pct or 0) >= RAIN_PROBABILITY_THRESHOLD
            or (rain_mm or 0) >= RAIN_AMOUNT_THRESHOLD_MM,
        })
    return days
