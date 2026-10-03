import json

from tests.conftest import days_from_now
from tools import find_hotels_near, search_hotels
from tools.hotels import GEOAPIFY_PLACES_URL, LITEAPI_RATES_URL


def rate(amount, name="Double Room", refundable=True):
    return {
        "name": name,
        "boardName": "Room Only",
        "retailRate": {"total": [{"amount": amount, "currency": "USD"}]},
        "cancellationPolicies": {"refundableTag": "RFN" if refundable else "NRFN"},
    }


LITEAPI_RESPONSE = {
    "data": [
        {"hotelId": "h1", "roomTypes": [{"offerId": "o1", "rates": [rate(900.0)]}]},
        {"hotelId": "h2", "roomTypes": [
            {"offerId": "o2a", "rates": [rate(500.0, "Twin", refundable=False)]},
            {"offerId": "o2b", "rates": [rate(450.0, "Small Double")]},
        ]},
        {"hotelId": "h3", "roomTypes": [{"offerId": "o3", "rates": []}]},  # no price -> skipped
    ],
    "hotels": [
        {"id": "h1", "name": "Grand Hotel", "address": "1 Rue A", "stars": 5, "rating": 9.1, "main_photo": "p1.jpg"},
        {"id": "h2", "name": "Budget Inn", "address": "2 Rue B", "stars": 3, "rating": 8.0, "main_photo": "p2.jpg"},
    ],
}


async def test_search_hotels_returns_cheapest_first(api):
    route = api.post(LITEAPI_RATES_URL).respond(200, json=LITEAPI_RESPONSE)
    check_in, check_out = days_from_now(30), days_from_now(33)

    result = await search_hotels("Paris", "fr", check_in, check_out, adults=2)

    assert result["status"] == "success"
    data = result["data"]
    assert data["nights"] == 3
    assert [h["name"] for h in data["hotels"]] == ["Budget Inn", "Grand Hotel"]
    budget = data["hotels"][0]
    assert budget["total_price"] == 450.0
    assert budget["price_per_night"] == 150.0
    assert budget["offer_id"] == "o2b"
    assert budget["refundable"] is True

    request = route.calls.last.request
    assert request.headers["X-API-Key"] == "test-liteapi-key"
    body = json.loads(request.content)
    assert body["cityName"] == "Paris" and body["countryCode"] == "FR"
    assert body["checkin"] == check_in and body["checkout"] == check_out
    assert body["occupancies"] == [{"adults": 2}]


async def test_search_hotels_max_price_filter(api):
    api.post(LITEAPI_RATES_URL).respond(200, json=LITEAPI_RESPONSE)

    result = await search_hotels("Paris", "FR", days_from_now(30), days_from_now(33), max_price_per_night=200)

    assert [h["name"] for h in result["data"]["hotels"]] == ["Budget Inn"]


async def test_search_hotels_rejects_checkout_before_checkin(api):
    result = await search_hotels("Paris", "FR", days_from_now(10), days_from_now(10))

    assert result["status"] == "error"
    assert "check_out must be after check_in" in result["error_message"]
    assert not api.calls


async def test_search_hotels_missing_key(api, monkeypatch):
    monkeypatch.delenv("LITEAPI_KEY")

    result = await search_hotels("Paris", "FR", days_from_now(10), days_from_now(12))

    assert result == {"status": "error", "error_message": "LITEAPI_KEY is not set. Add it to backend/.env."}


async def test_search_hotels_api_rejection_is_explained(api):
    api.post(LITEAPI_RATES_URL).respond(401, json={"error": {"code": 401, "message": "Invalid API key"}})

    result = await search_hotels("Paris", "FR", days_from_now(10), days_from_now(12))

    assert result["status"] == "error"
    assert "HTTP 401" in result["error_message"] and "Invalid API key" in result["error_message"]
    assert "test-liteapi-key" not in result["error_message"]


async def test_find_hotels_near(api, paris_geocode):
    route = api.get(url__startswith=GEOAPIFY_PLACES_URL).respond(200, json={
        "type": "FeatureCollection",
        "features": [
            {"properties": {"name": "Hotel Lumiere", "formatted": "3 Rue C, Paris", "lat": 48.86, "lon": 2.35,
                            "distance": 420, "place_id": "abc"}},
            {"properties": {"formatted": "Unnamed building"}},
        ],
    })

    result = await find_hotels_near("Paris", radius_km=2)

    hotels = result["data"]["hotels"]
    assert [h["name"] for h in hotels] == ["Hotel Lumiere"]
    assert hotels[0]["distance_m"] == 420
    params = route.calls.last.request.url.params
    assert params["filter"] == "circle:2.3488,48.85341,2000"
    assert params["categories"] == "accommodation.hotel"
