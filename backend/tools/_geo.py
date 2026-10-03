"""City name -> coordinates, using Open-Meteo's free geocoding API (no key)."""

from ._http import ToolError, request_json

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


async def geocode_city(city: str, country_code: str = "") -> dict:
    """Return the best match for a city: name, country, coordinates and timezone."""
    city = city.strip()
    if not city:
        raise ToolError("city must not be empty.")

    params = {"name": city, "count": 1, "language": "en", "format": "json"}
    if country_code:
        params["countryCode"] = country_code

    payload = await request_json("GET", GEOCODING_URL, params=params, service="Open-Meteo geocoding")
    results = payload.get("results") or []
    if not results:
        where = f" in {country_code}" if country_code else ""
        raise ToolError(f"Could not find a place called '{city}'{where}.")

    top = results[0]
    return {
        "name": top.get("name", city),
        "country": top.get("country", ""),
        "country_code": top.get("country_code", ""),
        "latitude": top["latitude"],
        "longitude": top["longitude"],
        "timezone": top.get("timezone", "auto"),
    }
