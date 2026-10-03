"""Attractions tool using OpenTripMap (free for non-commercial use)."""

import re

from ._geo import geocode_city
from ._http import ToolError, error, ok, request_json, require_env
from ._validate import country_code as check_country, int_between, number_between

OPENTRIPMAP_RADIUS_URL = "https://api.opentripmap.com/0.1/en/places/radius"
_KINDS = re.compile(r"^[a-z_]+(,[a-z_]+)*$")


async def find_attractions(
    city: str,
    country_code: str = "",
    categories: str = "interesting_places",
    min_rating: int = 2,
    radius_km: float = 5.0,
    max_results: int = 10,
) -> dict:
    """Find sightseeing attractions around a city centre, best rated first.

    Args:
        city: City name, for example "Paris".
        country_code: Optional 2-letter country code, for example "FR".
        categories: Comma-separated OpenTripMap kinds, for example "museums",
            "historic", "architecture", "natural", "cultural", "amusements",
            "religion" or "foods". "interesting_places" means all sightseeing.
        min_rating: 1 = any, 2 = notable, 3 = top attractions only.
        radius_km: Search radius around the city centre in km (0.5-30).
        max_results: How many attractions to return (1-30).

    Returns:
        On success: {"status": "success", "data": {"location": {...}, "attractions":
        [{"name", "categories", "rating", "distance_m", "latitude", "longitude",
        "xid", "wikidata"}, ...]}}.
        On failure: {"status": "error", "error_message": "..."}.
    """
    try:
        categories = categories.strip().lower().replace(" ", "")
        if not _KINDS.match(categories):
            raise ToolError("categories must be comma-separated words like 'museums,historic'.")
        int_between(min_rating, 1, 3, "min_rating")
        number_between(radius_km, 0.5, 30, "radius_km")
        int_between(max_results, 1, 30, "max_results")
        api_key = require_env("OPENTRIPMAP_API_KEY")
        location = await geocode_city(city, check_country(country_code, required=False))

        payload = await request_json(
            "GET",
            OPENTRIPMAP_RADIUS_URL,
            service="OpenTripMap",
            params={
                "radius": int(radius_km * 1000),
                "lon": location["longitude"],
                "lat": location["latitude"],
                "kinds": categories,
                "rate": str(min_rating),
                "format": "json",
                # Ask for extra because many results have no name and are dropped.
                "limit": max_results * 3,
                "apikey": api_key,
            },
        )
        if not isinstance(payload, list):
            raise ToolError("OpenTripMap returned an unexpected response.")

        seen, attractions = set(), []
        for place in payload:
            name = (place.get("name") or "").strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            point = place.get("point") or {}
            attractions.append({
                "name": name,
                "categories": [k for k in (place.get("kinds") or "").split(",") if k][:5],
                "rating": place.get("rate"),
                "distance_m": round(place["dist"]) if place.get("dist") is not None else None,
                "latitude": point.get("lat"),
                "longitude": point.get("lon"),
                "xid": place.get("xid"),
                "wikidata": place.get("wikidata", ""),
            })
        attractions.sort(key=lambda a: (-(a["rating"] or 0), a["distance_m"] or 0))
        return ok({"location": location, "attractions": attractions[:max_results]})
    except ToolError as exc:
        return error(str(exc))
