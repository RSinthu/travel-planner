"""Checks an itinerary against the research saved in session state.

Plain Python on purpose: it is exact, free, and does not use Gemini quota.

- errors: the plan is wrong and is sent back to the itinerary agent once
  (wrong dates, empty days, places or hotel not in the search results, over budget)
- warnings: worth telling the user, not worth a re-plan
  (outdoor sights on rainy days, the same place twice)
"""

from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

from tools import calculate_trip_budget

from .schemas import Itinerary


def trip_dates(trip: Mapping[str, Any]) -> list[str]:
    """All dates from start_date to end_date inclusive, or [] if they are invalid."""
    try:
        start = date.fromisoformat(trip["start_date"])
        end = date.fromisoformat(trip["end_date"])
    except (KeyError, TypeError, ValueError):
        return []
    return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]


def _names(places: list[dict]) -> dict[str, str]:
    """Every known spelling (English and local name, case-insensitive) -> the place's main name."""
    names = {}
    for place in places:
        for key in ("name", "local_name"):
            if place.get(key):
                names[place[key].casefold()] = place["name"]
    return names


def _section(state: Mapping[str, Any], key: str, items: str) -> list[dict]:
    return (state.get(key) or {}).get(items) or []


def review_itinerary(itinerary: Itinerary, state: Mapping[str, Any]) -> dict:
    """Return {"errors": [...], "warnings": [...], "cost": {...} or None}."""
    trip = state.get("trip_request") or {}
    errors: list[str] = []
    warnings: list[str] = []

    expected = trip_dates(trip)
    got = [day.date for day in itinerary.days]
    if expected and got != expected:
        errors.append(f"The plan must have exactly one day for each date, in order: {', '.join(expected)}.")

    known_places = _names(_section(state, "attractions", "attractions"))
    rainy = {d["date"] for d in _section(state, "weather", "days") if d.get("rain_likely")}
    visited: dict[str, str] = {}
    for day in itinerary.days:
        if not day.activities:
            errors.append(f"{day.date} has no activities.")
        for activity in day.activities:
            if not activity.place:
                continue
            canonical = known_places.get(activity.place.casefold())
            if canonical is None:
                errors.append(
                    f"'{activity.place}' is not in the attractions list. Use an exact name from the list, "
                    "or leave place empty and mention it in the title."
                )
            elif canonical in visited:
                warnings.append(f"{canonical} is planned twice ({visited[canonical]} and {day.date}).")
            else:
                visited[canonical] = day.date
            if day.date in rainy and not activity.indoor:
                warnings.append(f"{activity.place} on {day.date} is outdoors and rain is likely that day.")

    hotels = _section(state, "hotels", "hotels")
    chosen = next((h for h in hotels if h.get("name", "").casefold() == itinerary.hotel.casefold()), None)
    if hotels and not chosen:
        errors.append(f"The hotel '{itinerary.hotel}' is not in the hotel results. Pick one of: "
                      + ", ".join(h["name"] for h in hotels) + ".")
    elif not hotels and itinerary.hotel:
        if itinerary.hotel.casefold() not in _names(_section(state, "hotels_nearby", "hotels")):
            errors.append(f"The hotel '{itinerary.hotel}' is not in the search results. Leave hotel empty.")

    cost = _cost(itinerary, trip, expected, chosen)
    if cost and cost.get("within_budget") is False:
        errors.append(
            f"The estimated total {cost['estimated_total']} {cost['currency']} is over the "
            f"{cost['budget']} {cost['currency']} budget by {-cost['remaining']}. "
            "Choose a cheaper hotel or lower the activity costs."
        )
    return {"errors": errors, "warnings": warnings, "cost": cost}


def _cost(itinerary: Itinerary, trip: Mapping[str, Any], dates: list[str], hotel: dict | None) -> dict | None:
    nights = len(dates) - 1
    if nights < 1:
        return None
    budget = float(trip.get("total_budget") or 0)
    result = calculate_trip_budget(
        total_budget=budget,
        nights=nights,
        travellers=int(trip.get("adults") or 1),
        hotel_total=float(hotel["total_price"]) if hotel else 0,
        activities_total=max(itinerary.activities_total, 0),
        daily_spend_per_person=max(itinerary.daily_spend_per_person, 0),
        currency=trip.get("currency") or "USD",
    )
    if result["status"] != "success":
        return None
    cost = result["data"]
    cost["hotel_included"] = hotel is not None
    if budget <= 0:  # no budget given: report the estimate only
        for key in ("budget", "remaining", "within_budget"):
            cost.pop(key)
    return cost
