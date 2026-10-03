"""Attractions tool using Geoapify Places (free plan, commercial use allowed)."""

from ._geoapify import geocode_city, search_places
from ._http import ToolError, error, ok, require_env
from ._validate import country_code as check_country, int_between, number_between

# Notable kinds of sight. tourism.sights.memorial is left out on purpose: in big
# cities it is mostly small plaques that crowd out the real landmarks.
SIGHT_TYPES = [
    "archaeological_site", "bridge", "castle", "city_gate", "city_hall", "fort",
    "lighthouse", "manor", "monastery", "place_of_worship", "ruines", "tower", "windmill",
]

# Friendly names the agent uses -> Geoapify category names.
CATEGORY_GROUPS = {
    "sights": [f"tourism.sights.{t}" for t in SIGHT_TYPES],
    "museums": ["entertainment.museum"],
    "culture": ["entertainment.culture"],
    "unesco": ["heritage.unesco"],
    "viewpoints": ["tourism.attraction.viewpoint"],
    "parks": ["leisure.park"],
    "nature": ["natural"],
    "zoos": ["entertainment.zoo", "entertainment.aquarium"],
    "theme_parks": ["entertainment.theme_park", "entertainment.water_park"],
}
DEFAULT_CATEGORIES = "sights,museums,unesco"

# Geoapify returns the nearest places, not the most important ones, so we fetch
# a wide pool and rank it ourselves. 200 places = 10 credits per search.
CANDIDATES = 200


async def find_attractions(
    city: str,
    country_code: str = "",
    categories: str = DEFAULT_CATEGORIES,
    radius_km: float = 5.0,
    max_results: int = 15,
) -> dict:
    """Find sightseeing attractions around a city centre.

    Ranked: UNESCO World Heritage sites first, then notable places (those with a
    Wikidata entry), each nearest first. There is no popularity score, so use
    your own knowledge of the city to pick the real highlights from the list.

    Args:
        city: City name, for example "Paris".
        country_code: Optional 2-letter country code, for example "FR".
        categories: Comma-separated list from: sights, museums, culture, unesco,
            viewpoints, parks, nature, zoos, theme_parks.
            Default "sights,museums,unesco".
        radius_km: Search radius around the city centre in km (0.5-30).
        max_results: How many attractions to return (1-30).

    Returns:
        On success: {"status": "success", "data": {"location": {...}, "attractions":
        [{"name" (English if known), "local_name", "types", "unesco", "notable", "address", "distance_m",
        "latitude", "longitude", "opening_hours", "website", "place_id"}, ...]}}.
        On failure: {"status": "error", "error_message": "..."}.
    """
    try:
        groups = _parse_categories(categories)
        number_between(radius_km, 0.5, 30, "radius_km")
        int_between(max_results, 1, 30, "max_results")
        api_key = require_env("GEOAPIFY_API_KEY")
        location = await geocode_city(api_key, city, check_country(country_code, required=False))

        geoapify_categories = ",".join(c for group in groups for c in CATEGORY_GROUPS[group])
        places = await search_places(api_key, geoapify_categories, location, radius_km, CANDIDATES)

        attractions = []
        for place in places:
            types = _types(place["categories"], groups)
            attractions.append({
                "name": place["name"],
                "local_name": place["local_name"],
                "types": types,
                "unesco": "heritage.unesco" in place["categories"],
                "notable": bool(place["wikidata"]),
                "address": place["address"],
                "distance_m": place["distance_m"],
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "opening_hours": place["opening_hours"],
                "website": place["website"],
                "place_id": place["place_id"],
            })
        attractions.sort(key=lambda a: (not a["unesco"], not a["notable"], a["distance_m"] or 0))
        return ok({"location": location, "attractions": attractions[:max_results]})
    except ToolError as exc:
        return error(str(exc))


def _parse_categories(categories: str) -> list[str]:
    groups = [c.strip().lower() for c in categories.split(",") if c.strip()]
    unknown = [g for g in groups if g not in CATEGORY_GROUPS]
    if not groups or unknown:
        raise ToolError(f"categories must be a comma-separated list from: {', '.join(CATEGORY_GROUPS)}.")
    return list(dict.fromkeys(groups))  # drop duplicates, keep order


def _types(place_categories: list[str], groups: list[str]) -> list[str]:
    """Which of the requested friendly groups this place belongs to."""
    return [
        group for group in groups
        if any(pc == gc or pc.startswith(gc + ".") for gc in CATEGORY_GROUPS[group] for pc in place_categories)
    ]
