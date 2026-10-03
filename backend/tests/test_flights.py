import json

from tests.conftest import days_from_now
from tools import search_flights
from tools.flights import DUFFEL_OFFER_REQUESTS_URL


def offer(offer_id, amount, segments_per_slice=(1, 1)):
    slices = []
    for count in segments_per_slice:
        segments = [
            {
                "origin": {"iata_code": "LHR"},
                "destination": {"iata_code": "CDG"},
                "departing_at": "2026-11-01T08:00:00",
                "arriving_at": "2026-11-01T10:15:00",
                "marketing_carrier": {"iata_code": "ZZ"},
                "marketing_carrier_flight_number": f"{100 + i}",
            }
            for i in range(count)
        ]
        slices.append({"duration": "PT1H15M", "segments": segments})
    return {"id": offer_id, "total_amount": str(amount), "total_currency": "GBP",
            "owner": {"name": "Duffel Airways"}, "slices": slices}


async def test_round_trip_cheapest_first(api):
    route = api.post(url__startswith=DUFFEL_OFFER_REQUESTS_URL).respond(201, json={
        "data": {"offers": [offer("off_b", 310.5, (2, 1)), offer("off_a", 199.99)]}
    })
    depart, back = days_from_now(20), days_from_now(24)

    result = await search_flights("lhr", "cdg", depart, back, adults=2)

    assert result["status"] == "success"
    offers = result["data"]["offers"]
    assert [o["offer_id"] for o in offers] == ["off_a", "off_b"]
    assert offers[1]["slices"][0]["stops"] == 1
    assert offers[1]["slices"][0]["flight_numbers"] == ["ZZ100", "ZZ101"]
    assert "test mode" in result["note"]

    request = route.calls.last.request
    assert request.headers["Duffel-Version"] == "v2"
    assert request.headers["Authorization"] == "Bearer duffel_test_fake"
    body = json.loads(request.content)["data"]
    assert body["slices"] == [
        {"origin": "LHR", "destination": "CDG", "departure_date": depart},
        {"origin": "CDG", "destination": "LHR", "departure_date": back},
    ]
    assert body["passengers"] == [{"type": "adult"}, {"type": "adult"}]


async def test_one_way_has_single_slice(api):
    route = api.post(url__startswith=DUFFEL_OFFER_REQUESTS_URL).respond(201, json={"data": {"offers": []}})

    result = await search_flights("LHR", "CDG", days_from_now(20))

    assert result["data"]["offers"] == []
    assert len(json.loads(route.calls.last.request.content)["data"]["slices"]) == 1


async def test_invalid_airport_code(api):
    result = await search_flights("Paris", "LHR", days_from_now(20))

    assert result["status"] == "error"
    assert "IATA" in result["error_message"]
    assert not api.calls


async def test_api_validation_error_is_explained(api):
    api.post(url__startswith=DUFFEL_OFFER_REQUESTS_URL).respond(422, json={
        "errors": [{"title": "Invalid", "message": "Field 'origin' is not a valid airport"}]
    })

    result = await search_flights("XXX", "CDG", days_from_now(20))

    assert result["status"] == "error"
    assert "not a valid airport" in result["error_message"]
