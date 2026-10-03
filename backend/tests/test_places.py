from tools import find_attractions
from tools.places import OPENTRIPMAP_RADIUS_URL


async def test_best_rated_first_and_cleaned(api, paris_geocode):
    route = api.get(url__startswith=OPENTRIPMAP_RADIUS_URL).respond(200, json=[
        {"xid": "W1", "name": "Small Museum", "rate": 2, "dist": 300.4, "kinds": "museums,cultural",
         "point": {"lon": 2.35, "lat": 48.86}},
        {"xid": "W2", "name": "", "rate": 3, "dist": 100, "kinds": "historic"},
        {"xid": "W3", "name": "Eiffel Tower", "rate": 3, "dist": 4100.9, "kinds": "architecture,towers",
         "point": {"lon": 2.29, "lat": 48.85}, "wikidata": "Q243"},
        {"xid": "W4", "name": "eiffel tower", "rate": 3, "dist": 4200, "kinds": "architecture"},
    ])

    result = await find_attractions("Paris", categories="museums, architecture", min_rating=2)

    assert result["status"] == "success"
    attractions = result["data"]["attractions"]
    assert [a["name"] for a in attractions] == ["Eiffel Tower", "Small Museum"]
    assert attractions[0]["distance_m"] == 4101
    assert attractions[0]["wikidata"] == "Q243"
    params = route.calls.last.request.url.params
    assert params["kinds"] == "museums,architecture"
    assert params["rate"] == "2"


async def test_bad_categories_rejected(api):
    result = await find_attractions("Paris", categories="museums; DROP TABLE")

    assert result["status"] == "error"
    assert not api.calls
