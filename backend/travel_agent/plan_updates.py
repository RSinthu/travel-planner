"""Code-only changes to a saved itinerary (no Gemini requests).

- enrich_itinerary: attach coordinates, address and opening hours from the saved
  research to each planned place and to the hotel, for the map and day cards.
- choose_hotel: swap the plan's hotel for another one from the search results,
  then re-run the review so the cost and budget are recalculated.
"""

import copy
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from .review import review_itinerary
from .schemas import Itinerary

PLACE_FIELDS = ("name", "latitude", "longitude", "address", "opening_hours", "types", "unesco", "website")
HOTEL_FIELDS = (
    "name", "address", "latitude", "longitude", "stars", "rating", "review_count", "price_per_night",
    "total_price", "refundable", "board", "thumbnail_url", "photo_url", "offer_id",
)


class PlanUpdateError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _hotels(state: Mapping[str, Any]) -> list[dict]:
    return (state.get("hotels") or {}).get("hotels") or []


def _find_hotel(state: Mapping[str, Any], name: str) -> dict | None:
    wanted = name.strip().casefold()
    return next((h for h in _hotels(state) if h.get("name", "").casefold() == wanted), None)


def enrich_itinerary(plan: dict, state: Mapping[str, Any]) -> dict:
    """A copy of the plan with "details" on each activity and "hotel_details" (None when unknown)."""
    places: dict[str, dict] = {}
    for place in (state.get("attractions") or {}).get("attractions") or []:
        for key in ("name", "local_name"):
            if place.get(key):
                places[place[key].casefold()] = place

    enriched = copy.deepcopy(plan)
    for day in enriched.get("days") or []:
        for activity in day.get("activities") or []:
            place = places.get((activity.get("place") or "").casefold()) if activity.get("place") else None
            activity["details"] = {key: place.get(key) for key in PLACE_FIELDS} if place else None

    hotel = _find_hotel(state, enriched.get("hotel") or "") if enriched.get("hotel") else None
    enriched["hotel_details"] = {key: hotel.get(key) for key in HOTEL_FIELDS} if hotel else None
    return enriched


def choose_hotel(state: Mapping[str, Any], hotel_name: str) -> tuple[dict, dict]:
    """Return (enriched plan, review) with the new hotel. Raises PlanUpdateError."""
    plan = state.get("itinerary")
    if not plan:
        raise PlanUpdateError("no_itinerary", "This trip has no day-by-day plan yet.")
    hotel = _find_hotel(state, hotel_name)
    if hotel is None:
        raise PlanUpdateError("unknown_hotel", "That hotel is not in this trip's hotel results.")

    try:
        itinerary = Itinerary.model_validate({**plan, "hotel": hotel["name"]})
    except ValidationError as exc:
        raise PlanUpdateError("invalid_itinerary", "The saved plan is incomplete. Ask for a new plan.") from exc
    review = review_itinerary(itinerary, state)
    return enrich_itinerary(itinerary.model_dump(), state), review
