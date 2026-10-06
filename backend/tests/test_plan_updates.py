import pytest

from tests.itinerary_fixtures import good_plan, research_state
from travel_agent.plan_updates import PlanUpdateError, choose_hotel, enrich_itinerary


def test_enrich_adds_place_and_hotel_details():
    state = research_state()
    state["attractions"]["attractions"][0].update(latitude=41.9, longitude=12.48, address="Piazza della Rotonda")
    state["hotels"]["hotels"][0].update(latitude=41.8, longitude=12.4)

    plan = enrich_itinerary(good_plan(), state)

    pantheon = plan["days"][0]["activities"][0]["details"]
    assert (pantheon["name"], pantheon["latitude"], pantheon["address"]) == ("Pantheon", 41.9, "Piazza della Rotonda")
    assert plan["days"][0]["activities"][1]["details"] is None  # dinner: no place
    assert plan["hotel_details"]["name"] == "Holiday Inn Rome" and plan["hotel_details"]["latitude"] == 41.8


def test_enrich_does_not_change_the_input():
    plan = good_plan()
    enrich_itinerary(plan, research_state())
    assert "details" not in plan["days"][0]["activities"][0]


def test_enrich_matches_local_names():
    plan = good_plan()
    plan["days"][1]["activities"][0]["place"] = "Musei Capitolini"

    details = enrich_itinerary(plan, research_state())["days"][1]["activities"][0]["details"]

    assert details["name"] == "Capitoline Museums"


def test_choose_hotel_recalculates():
    state = {**research_state(), "itinerary": enrich_itinerary(good_plan(), research_state())}

    plan, review = choose_hotel(state, "Aparthotel Colombo")

    assert plan["hotel"] == "Aparthotel Colombo"
    assert review["cost"]["estimated_total"] == 688 and review["errors"] == []


def test_choose_hotel_over_budget_is_reported_not_blocked():
    state = {**research_state(), "itinerary": good_plan()}
    state["trip_request"]["total_budget"] = 650

    plan, review = choose_hotel(state, "Aparthotel Colombo")

    assert plan["hotel"] == "Aparthotel Colombo"
    assert "over the 650.0 EUR budget" in review["errors"][0]


@pytest.mark.parametrize("with_plan, hotel, code", [
    (False, "Holiday Inn Rome", "no_itinerary"),
    (True, "Hotel Imaginary", "unknown_hotel"),
])
def test_choose_hotel_errors(with_plan, hotel, code):
    state = {**research_state(), **({"itinerary": good_plan()} if with_plan else {})}

    with pytest.raises(PlanUpdateError) as info:
        choose_hotel(state, hotel)

    assert info.value.code == code


def test_damaged_saved_plan_is_a_clear_error():
    state = {**research_state(), "itinerary": {"title": "half a plan", "days": []}}

    with pytest.raises(PlanUpdateError) as info:
        choose_hotel(state, "Aparthotel Colombo")

    assert info.value.code == "invalid_itinerary"
