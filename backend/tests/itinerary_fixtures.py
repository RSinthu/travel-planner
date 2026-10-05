"""Shared research state and itineraries for the itinerary tests."""

from travel_agent.schemas import Itinerary

TRIP = {
    "city": "Rome", "country_code": "IT", "start_date": "2026-10-07", "end_date": "2026-10-09",
    "adults": 2, "currency": "EUR", "max_price_per_night": 200, "total_budget": 1000,
    "interests": "history, museums",
}


def research_state(**overrides) -> dict:
    state = {
        "trip_request": dict(TRIP),
        "weather": {"days": [
            {"date": "2026-10-07", "condition": "Overcast", "temp_min_c": 15, "temp_max_c": 26, "rain_likely": False},
            {"date": "2026-10-08", "condition": "Thunderstorm", "temp_min_c": 17, "temp_max_c": 23, "rain_likely": True},
            {"date": "2026-10-09", "condition": "Partly cloudy", "temp_min_c": 14, "temp_max_c": 21, "rain_likely": False},
        ]},
        "hotels": {"nights": 2, "currency": "EUR", "hotels": [
            {"name": "Holiday Inn Rome", "stars": 4, "rating": 8, "price_per_night": 125, "total_price": 250,
             "refundable": False},
            {"name": "Aparthotel Colombo", "stars": 4, "rating": 8.9, "price_per_night": 164, "total_price": 328,
             "refundable": False},
        ]},
        "attractions": {"attractions": [
            {"name": "Pantheon", "local_name": "Pantheon", "types": ["sights", "unesco"], "unesco": True,
             "opening_hours": "Mo-Su 09:00-19:00"},
            {"name": "Capitoline Museums", "local_name": "Musei Capitolini", "types": ["museums"], "unesco": False,
             "opening_hours": ""},
            {"name": "Temple of Saturn", "local_name": "Tempio di Saturno", "types": ["sights"], "unesco": False},
        ]},
    }
    state.update(overrides)
    return state


def activity(time_of_day, title, place="", indoor=False):
    return {"time_of_day": time_of_day, "title": title, "place": place, "indoor": indoor}


def good_plan(**overrides) -> dict:
    plan = {
        "title": "3 days of history in Rome",
        "hotel": "Holiday Inn Rome",
        "days": [
            {"date": "2026-10-07", "weather": "Overcast, 15-26°C", "activities": [
                activity("morning", "Explore the Pantheon", "Pantheon"),
                activity("evening", "Dinner in Trastevere"),
            ]},
            {"date": "2026-10-08", "weather": "Thunderstorm, 17-23°C", "activities": [
                activity("morning", "Capitoline Museums", "Capitoline Museums", indoor=True),
            ]},
            {"date": "2026-10-09", "weather": "Partly cloudy, 14-21°C", "activities": [
                activity("morning", "Roman Forum ruins", "Temple of Saturn"),
            ]},
        ],
        "daily_spend_per_person": 50,
        "activities_total": 60,
        "tips": ["Book the museums ahead."],
    }
    plan.update(overrides)
    return plan


def itinerary(**overrides) -> Itinerary:
    return Itinerary.model_validate(good_plan(**overrides))
