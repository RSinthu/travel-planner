"""Flight search tool using Duffel (free test mode with sample airline data)."""

import os

from ._http import ToolError, error, ok, request_json, require_env
from ._validate import date_range, iata_code, int_between, not_in_past, parse_date

DUFFEL_OFFER_REQUESTS_URL = "https://api.duffel.com/air/offer_requests"
DUFFEL_VERSION = "v2"
CABIN_CLASSES = {"economy", "premium_economy", "business", "first"}
SUPPLIER_TIMEOUT_MS = 20_000


async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = "",
    adults: int = 1,
    cabin_class: str = "economy",
    max_results: int = 5,
) -> dict:
    """Search flight offers, cheapest first. Leave return_date empty for one-way.

    Args:
        origin: 3-letter IATA airport or city code to fly from, for example "LHR" or "LON".
        destination: 3-letter IATA airport or city code to fly to, for example "CDG" or "PAR".
        departure_date: Outbound date, YYYY-MM-DD.
        return_date: Optional return date, YYYY-MM-DD. Empty string means one-way.
        adults: Number of adult passengers (1-9).
        cabin_class: One of "economy", "premium_economy", "business", "first".
        max_results: How many offers to return (1-20).

    Returns:
        On success: {"status": "success", "data": {"offers": [{"offer_id", "airline",
        "total_price", "currency", "slices": [{"origin", "destination", "departing_at",
        "arriving_at", "duration", "stops", "flight_numbers"}, ...]}, ...]}}.
        In Duffel test mode the result also has a "note" saying the data is not real.
        On failure: {"status": "error", "error_message": "..."}.
    """
    try:
        origin = iata_code(origin, "origin")
        destination = iata_code(destination, "destination")
        if origin == destination:
            raise ToolError("origin and destination must be different.")
        if return_date.strip():
            depart, back = date_range(departure_date, return_date, "departure_date", "return_date", same_day_ok=True)
        else:
            depart, back = parse_date(departure_date, "departure_date"), None
            not_in_past(depart, "departure_date")
        int_between(adults, 1, 9, "adults")
        int_between(max_results, 1, 20, "max_results")
        cabin_class = cabin_class.strip().lower()
        if cabin_class not in CABIN_CLASSES:
            raise ToolError(f"cabin_class must be one of {sorted(CABIN_CLASSES)}.")
        token = require_env("DUFFEL_ACCESS_TOKEN")

        slices = [{"origin": origin, "destination": destination, "departure_date": depart.isoformat()}]
        if back:
            slices.append({"origin": destination, "destination": origin, "departure_date": back.isoformat()})

        payload = await request_json(
            "POST",
            DUFFEL_OFFER_REQUESTS_URL,
            service="Duffel",
            params={"return_offers": "true", "supplier_timeout": SUPPLIER_TIMEOUT_MS},
            headers={
                "Authorization": f"Bearer {token}",
                "Duffel-Version": DUFFEL_VERSION,
                "Accept": "application/json",
            },
            json={
                "data": {
                    "slices": slices,
                    "passengers": [{"type": "adult"} for _ in range(adults)],
                    "cabin_class": cabin_class,
                    "max_connections": 1,
                }
            },
            timeout=SUPPLIER_TIMEOUT_MS / 1000 + 15,
            retries=1,
        )
        offers = [_offer(o) for o in (payload.get("data") or {}).get("offers") or []]
        offers.sort(key=lambda o: o["total_price"])

        extra = {}
        if token.startswith("duffel_test_"):
            extra["note"] = "Duffel test mode: sample flights from 'Duffel Airways', not real schedules or prices."
        return ok({"offers": offers[:max_results]}, **extra)
    except ToolError as exc:
        return error(str(exc))


def _offer(offer: dict) -> dict:
    slices = []
    for part in offer.get("slices") or []:
        segments = part.get("segments") or []
        first, last = (segments[0], segments[-1]) if segments else ({}, {})
        slices.append({
            "origin": (first.get("origin") or {}).get("iata_code"),
            "destination": (last.get("destination") or {}).get("iata_code"),
            "departing_at": first.get("departing_at"),
            "arriving_at": last.get("arriving_at"),
            "duration": part.get("duration"),
            "stops": max(len(segments) - 1, 0),
            "flight_numbers": [
                f"{(s.get('marketing_carrier') or {}).get('iata_code', '')}"
                f"{s.get('marketing_carrier_flight_number', '')}"
                for s in segments
            ],
        })
    return {
        "offer_id": offer.get("id"),
        "airline": (offer.get("owner") or {}).get("name", ""),
        "total_price": float(offer.get("total_amount") or 0),
        "currency": offer.get("total_currency", ""),
        "slices": slices,
    }
