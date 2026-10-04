"""Hotel tools.

- search_hotels: real prices and availability from LiteAPI (free sandbox key).
- find_hotels_near: hotel locations from Geoapify (free tier, no prices).
"""

from ._geoapify import geocode_city, search_places
from ._http import ToolError, error, ok, request_json, require_env
from ._validate import country_code as check_country, currency_code, date_range, int_between, number_between

LITEAPI_RATES_URL = "https://api.liteapi.travel/v3.0/hotels/rates"

LITEAPI_CANDIDATES = 50  # hotels requested from LiteAPI before filtering and sorting


async def search_hotels(
    city: str,
    country_code: str,
    check_in: str,
    check_out: str,
    adults: int = 2,
    currency: str = "USD",
    max_price_per_night: float = 0,
    guest_nationality: str = "US",
    max_results: int = 5,
) -> dict:
    """Search available hotels with live prices for one room, cheapest first.

    Args:
        city: City name, for example "Paris".
        country_code: 2-letter country code of the city, for example "FR".
        check_in: Check-in date, YYYY-MM-DD.
        check_out: Check-out date, YYYY-MM-DD (must be after check_in).
        adults: Number of adults in the room (1-8).
        currency: 3-letter currency for prices, for example "USD" or "EUR".
        max_price_per_night: Highest acceptable price per night. 0 means no limit.
        guest_nationality: 2-letter nationality of the lead guest (some rates depend on it).
        max_results: How many hotels to return (1-20).

    Returns:
        On success: {"status": "success", "data": {"nights": int, "currency": str,
        "hotels": [{"hotel_id", "name", "address", "stars", "rating", "photo_url",
        "room_name", "board", "refundable", "total_price", "price_per_night",
        "offer_id"}, ...]}}. An empty hotels list means nothing matched.
        With a sandbox key the result also has a "note" saying prices are test data.
        On failure: {"status": "error", "error_message": "..."}.
    """
    try:
        if not city.strip():
            raise ToolError("city must not be empty.")
        start, end = date_range(check_in, check_out, "check_in", "check_out", same_day_ok=False)
        nights = (end - start).days
        int_between(adults, 1, 8, "adults")
        int_between(max_results, 1, 20, "max_results")
        number_between(max_price_per_night, 0, 1_000_000, "max_price_per_night")
        currency = currency_code(currency)
        api_key = require_env("LITEAPI_KEY")

        payload = await request_json(
            "POST",
            LITEAPI_RATES_URL,
            service="LiteAPI",
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            json={
                "cityName": city.strip(),
                "countryCode": check_country(country_code, required=True),
                "checkin": start.isoformat(),
                "checkout": end.isoformat(),
                "currency": currency,
                "guestNationality": check_country(guest_nationality, required=True),
                "occupancies": [{"adults": adults}],
                "limit": LITEAPI_CANDIDATES,
                "maxRatesPerHotel": 1,
                "includeHotelData": True,
                "timeout": 10,
            },
            timeout=25,
        )
        if isinstance(payload.get("error"), dict):
            raise ToolError(f"LiteAPI: {payload['error'].get('message', 'unknown error')}")

        hotels = _cheapest_offers(payload, nights)
        if max_price_per_night > 0:
            hotels = [h for h in hotels if h["price_per_night"] <= max_price_per_night]
        hotels.sort(key=lambda h: h["total_price"])
        extra = {}
        if payload.get("sandbox"):
            extra["note"] = "LiteAPI sandbox: test prices for development, not real bookable rates."
        return ok({"nights": nights, "currency": currency, "hotels": hotels[:max_results]}, **extra)
    except ToolError as exc:
        return error(str(exc))


def _cheapest_offers(payload: dict, nights: int) -> list[dict]:
    """Turn LiteAPI's nested response into one flat entry per hotel (its cheapest rate)."""
    info = {h.get("id"): h for h in payload.get("hotels") or []}
    results = []
    for entry in payload.get("data") or []:
        best = None
        for room in entry.get("roomTypes") or []:
            for rate in room.get("rates") or []:
                totals = (rate.get("retailRate") or {}).get("total") or []
                if not totals or totals[0].get("amount") is None:
                    continue
                amount = float(totals[0]["amount"])
                if best is None or amount < best[0]:
                    best = (amount, room, rate)
        if best is None:
            continue

        amount, room, rate = best
        hotel = info.get(entry.get("hotelId"), {})
        results.append({
            "hotel_id": entry.get("hotelId"),
            "name": hotel.get("name", "Unknown hotel"),
            "address": hotel.get("address", ""),
            "stars": hotel.get("stars"),
            "rating": hotel.get("rating"),
            "photo_url": hotel.get("main_photo", ""),
            "room_name": rate.get("name", ""),
            "board": rate.get("boardName", ""),
            "refundable": (rate.get("cancellationPolicies") or {}).get("refundableTag") == "RFN",
            "total_price": round(amount, 2),
            "price_per_night": round(amount / nights, 2),
            "offer_id": room.get("offerId"),
        })
    return results


async def find_hotels_near(city: str, country_code: str = "", radius_km: float = 5.0, max_results: int = 10) -> dict:
    """List hotels around a city centre with addresses and map coordinates.

    This has NO prices or availability. Use search_hotels for bookable prices;
    use this for showing hotels on a map or when search_hotels finds nothing.

    Args:
        city: City name, for example "Paris".
        country_code: Optional 2-letter country code, for example "FR".
        radius_km: Search radius around the city centre in km (0.5-30).
        max_results: How many hotels to return (1-50).

    Returns:
        On success: {"status": "success", "data": {"location": {...}, "hotels":
        [{"name", "address", "latitude", "longitude", "distance_m", "website", "place_id"}, ...]}}.
        On failure: {"status": "error", "error_message": "..."}.
    """
    try:
        number_between(radius_km, 0.5, 30, "radius_km")
        int_between(max_results, 1, 50, "max_results")
        api_key = require_env("GEOAPIFY_API_KEY")
        location = await geocode_city(api_key, city, check_country(country_code, required=False))

        places = await search_places(api_key, "accommodation.hotel", location, radius_km, max_results)
        fields = ("name", "address", "latitude", "longitude", "distance_m", "website", "place_id")
        hotels = [{k: place[k] for k in fields} for place in places]
        return ok({"location": location, "hotels": hotels})
    except ToolError as exc:
        return error(str(exc))
