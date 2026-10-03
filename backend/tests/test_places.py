from tools import find_attractions
from tools._geoapify import GEOAPIFY_GEOCODE_URL, GEOAPIFY_PLACES_URL


def feature(name, categories, distance, wikidata=None, **extra):
    props = {"name": name, "categories": categories, "distance": distance,
             "formatted": f"{name}, Paris", "lat": 48.86, "lon": 2.34, **extra}
    if wikidata:
        props["wiki_and_media"] = {"wikidata": wikidata}
    return {"properties": props}


async def test_unesco_then_notable_then_nearest(api, paris_city_centre):
    route = api.get(url__startswith=GEOAPIFY_PLACES_URL).respond(200, json={"features": [
        feature("Small Gallery", ["entertainment", "entertainment.museum"], 200),
        feature("Old Tower", ["tourism", "tourism.sights", "tourism.sights.tower"], 900, wikidata="Q1"),
        feature("Banks of the Seine", ["heritage", "heritage.unesco", "tourism.sights"], 1500),
        feature("Grand Museum", ["entertainment.museum"], 600, wikidata="Q2", opening_hours="Mo-Su 09:00-18:00"),
        feature("small gallery", ["entertainment.museum"], 250),  # duplicate name, dropped
        {"properties": {"formatted": "No name", "categories": ["tourism.sights"]}},  # unnamed, dropped
    ]})

    result = await find_attractions("Paris", max_results=5)

    assert result["status"] == "success"
    attractions = result["data"]["attractions"]
    assert [a["name"] for a in attractions] == ["Banks of the Seine", "Grand Museum", "Old Tower", "Small Gallery"]
    assert attractions[0]["unesco"] is True and attractions[0]["types"] == ["unesco"]
    assert attractions[1]["notable"] is True and attractions[1]["opening_hours"] == "Mo-Su 09:00-18:00"
    assert attractions[2]["types"] == ["sights"]
    assert attractions[3]["notable"] is False

    params = route.calls.last.request.url.params
    categories = params["categories"].split(",")
    assert "tourism.sights.castle" in categories and "entertainment.museum" in categories
    assert "heritage.unesco" in categories
    assert not any("memorial" in c for c in categories)
    assert params["conditions"] == "named"
    assert params["filter"] == "circle:2.3488,48.85341,5000"
    assert params["limit"] == "200"


async def test_friendly_categories_are_mapped(api, paris_city_centre):
    route = api.get(url__startswith=GEOAPIFY_PLACES_URL).respond(200, json={"features": []})

    result = await find_attractions("Paris", categories="Parks, zoos, parks")

    assert result["data"]["attractions"] == []
    assert route.calls.last.request.url.params["categories"] == (
        "leisure.park,entertainment.zoo,entertainment.aquarium"
    )


async def test_unknown_category_rejected_without_api_call(api):
    result = await find_attractions("Paris", categories="museums,nightclubs")

    assert result["status"] == "error"
    assert "sights, museums, culture" in result["error_message"]
    assert not api.calls


async def test_missing_key_fails_before_geocoding(api, monkeypatch):
    monkeypatch.delenv("GEOAPIFY_API_KEY")

    result = await find_attractions("Paris")

    assert result == {"status": "error", "error_message": "GEOAPIFY_API_KEY is not set. Add it to backend/.env."}
    assert not api.calls


async def test_city_centre_lookup_uses_country_filter(api, paris_city_centre):
    api.get(url__startswith=GEOAPIFY_PLACES_URL).respond(200, json={"features": []})

    await find_attractions("Paris", country_code="fr")

    params = paris_city_centre.calls.last.request.url.params
    assert params["type"] == "city" and params["filter"] == "countrycode:fr"


async def test_unknown_city(api):
    api.get(url__startswith=GEOAPIFY_GEOCODE_URL).respond(200, json={"results": []})

    result = await find_attractions("Nowhereville")

    assert result == {"status": "error", "error_message": "Could not find a city called 'Nowhereville'."}


async def test_english_name_preferred(api, paris_city_centre):
    api.get(url__startswith=GEOAPIFY_PLACES_URL).respond(200, json={"features": [
        feature("東京国立博物館", ["entertainment.museum"], 100, name_international={"en": "Tokyo National Museum"}),
    ]})

    attraction = (await find_attractions("Paris"))["data"]["attractions"][0]

    assert attraction["name"] == "Tokyo National Museum"
    assert attraction["local_name"] == "東京国立博物館"
