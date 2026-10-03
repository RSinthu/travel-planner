"""Shared Geoapify Places call used by the hotel and attraction tools.

Free plan: 3,000 credits/day (20 places = 1 credit), commercial use allowed.
Any page showing these results must credit "Powered by Geoapify".
"""

from ._http import ToolError, request_json

GEOAPIFY_PLACES_URL = "https://api.geoapify.com/v2/places"
GEOAPIFY_GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
GEOAPIFY_TIMEOUT = 30.0  # Places searches can take 4-16 s in busy city centres


async def geocode_city(api_key: str, city: str, country_code: str = "") -> dict:
    """City name -> its central point.

    Used instead of Open-Meteo's geocoder for place searches because it gives the
    historic centre (e.g. Piazza Venezia for Rome, not a point 2.5 km east).
    """
    city = city.strip()
    if not city:
        raise ToolError("city must not be empty.")

    params = {"text": city, "type": "city", "limit": 1, "format": "json", "apiKey": api_key}
    if country_code:
        params["filter"] = f"countrycode:{country_code.lower()}"

    payload = await request_json("GET", GEOAPIFY_GEOCODE_URL, service="Geoapify geocoding", params=params)
    results = payload.get("results") or []
    if not results:
        where = f" in {country_code}" if country_code else ""
        raise ToolError(f"Could not find a city called '{city}'{where}.")

    top = results[0]
    return {
        "name": top.get("city") or city,
        "country": top.get("country", ""),
        "country_code": (top.get("country_code") or "").upper(),
        "latitude": top["lat"],
        "longitude": top["lon"],
        "timezone": (top.get("timezone") or {}).get("name", ""),
    }


async def search_places(api_key: str, categories: str, location: dict, radius_km: float, limit: int) -> list[dict]:
    """Return named places of the given Geoapify categories around a location, nearest first.

    Each result has: name (English when available), local_name, address, latitude,
    longitude, distance_m, categories, website, opening_hours, wikidata, place_id.
    Duplicate names are dropped.
    """
    lon, lat = location["longitude"], location["latitude"]

    payload = await request_json(
        "GET",
        GEOAPIFY_PLACES_URL,
        service="Geoapify",
        params={
            "categories": categories,
            "conditions": "named",
            "filter": f"circle:{lon},{lat},{int(radius_km * 1000)}",
            "bias": f"proximity:{lon},{lat}",
            "limit": limit,
            "lang": "en",
            "apiKey": api_key,
        },
        timeout=GEOAPIFY_TIMEOUT,
    )

    places, seen = [], set()
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        local_name = (props.get("name") or "").strip()
        name = ((props.get("name_international") or {}).get("en") or local_name).strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        places.append({
            "name": name,
            "local_name": local_name,
            "address": props.get("formatted", ""),
            "latitude": props.get("lat"),
            "longitude": props.get("lon"),
            "distance_m": props.get("distance"),
            "categories": props.get("categories") or [],
            "website": props.get("website", ""),
            "opening_hours": props.get("opening_hours", ""),
            "wikidata": (props.get("wiki_and_media") or {}).get("wikidata", ""),
            "place_id": props.get("place_id", ""),
        })
    return places
