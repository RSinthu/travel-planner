from tests.itinerary_fixtures import activity, good_plan, itinerary, research_state
from travel_agent.review import review_itinerary, trip_dates


def test_good_plan_passes_with_cost_estimate():
    review = review_itinerary(itinerary(), research_state())

    assert review["errors"] == []
    assert review["warnings"] == []
    cost = review["cost"]
    # hotel 250 + tickets 60 + 50/person/day * 2 people * 3 days = 610
    assert cost["estimated_total"] == 610
    assert cost["within_budget"] is True and cost["remaining"] == 390
    assert cost["hotel_included"] is True


def test_missing_or_extra_days():
    plan = good_plan()
    plan["days"] = plan["days"][:2]

    errors = review_itinerary(itinerary(days=plan["days"]), research_state())["errors"]

    assert errors == ["The plan must have exactly one day for each date, in order: 2026-10-07, 2026-10-08, 2026-10-09."]


def test_invented_place_is_an_error_but_local_name_is_fine():
    days = good_plan()["days"]
    days[0]["activities"].append(activity("afternoon", "Colosseum", "Colosseum"))
    days[2]["activities"].append(activity("afternoon", "Musei Capitolini", "Musei Capitolini", indoor=True))

    review = review_itinerary(itinerary(days=days), research_state())

    assert len(review["errors"]) == 1 and "'Colosseum' is not in the attractions list" in review["errors"][0]
    # The Italian name is accepted, and recognised as the same museum as on day 2.
    assert review["warnings"] == ["Capitoline Museums is planned twice (2026-10-08 and 2026-10-09)."]


def test_empty_day_is_an_error():
    days = good_plan()["days"]
    days[1]["activities"] = []

    assert "2026-10-08 has no activities." in review_itinerary(itinerary(days=days), research_state())["errors"]


def test_outdoor_sight_on_rainy_day_is_a_warning():
    days = good_plan()["days"]
    days[1]["activities"].append(activity("afternoon", "Roman Forum ruins", "Temple of Saturn", indoor=False))
    days[2]["activities"] = [activity("morning", "Free morning in Monti")]

    review = review_itinerary(itinerary(days=days), research_state())

    assert review["errors"] == []
    assert review["warnings"] == ["Temple of Saturn on 2026-10-08 is outdoors and rain is likely that day."]


def test_unknown_hotel_is_an_error():
    errors = review_itinerary(itinerary(hotel="Hotel Imaginary"), research_state())["errors"]

    assert errors == ["The hotel 'Hotel Imaginary' is not in the hotel results. Pick one of: "
                      "Holiday Inn Rome, Aparthotel Colombo."]


def test_no_hotels_found_allows_empty_hotel():
    state = research_state(hotels={"error": "LiteAPI unavailable"})

    review = review_itinerary(itinerary(hotel=""), state)

    assert review["errors"] == []
    assert review["cost"]["hotel_included"] is False


def test_over_budget_is_an_error():
    state = research_state()
    state["trip_request"]["total_budget"] = 500

    errors = review_itinerary(itinerary(), state)["errors"]

    assert errors == ["The estimated total 610.0 EUR is over the 500.0 EUR budget by 110.0. "
                      "Choose a cheaper hotel or lower the activity costs."]


def test_no_budget_gives_estimate_only():
    state = research_state()
    state["trip_request"]["total_budget"] = 0

    cost = review_itinerary(itinerary(), state)["cost"]

    assert cost["estimated_total"] == 610
    assert "within_budget" not in cost and "remaining" not in cost


def test_trip_dates():
    assert trip_dates({"start_date": "2026-12-30", "end_date": "2027-01-01"}) == [
        "2026-12-30", "2026-12-31", "2027-01-01"]
    assert trip_dates({"start_date": "bad"}) == []
