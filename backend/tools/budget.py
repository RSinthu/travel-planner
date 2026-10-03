"""Trip cost calculator tool (pure maths, no API)."""

from ._http import ToolError, error, ok
from ._validate import currency_code, int_between


def calculate_trip_budget(
    total_budget: float,
    nights: int,
    travellers: int,
    hotel_total: float = 0,
    flights_total: float = 0,
    activities_total: float = 0,
    daily_spend_per_person: float = 0,
    currency: str = "USD",
) -> dict:
    """Add up the trip costs and check them against the budget.

    All amounts must already be in the same currency. Daily spending (food, local
    transport) is counted for nights + 1 days, per traveller.

    Args:
        total_budget: The traveller's total budget for the whole trip.
        nights: Number of nights (1-60).
        travellers: Number of people (1-20).
        hotel_total: Total hotel cost for the whole stay.
        flights_total: Total flight cost for all travellers.
        activities_total: Total cost of tickets and activities.
        daily_spend_per_person: Estimated food and local transport per person per day.
        currency: 3-letter currency code of all the amounts.

    Returns:
        On success: {"status": "success", "data": {"currency", "budget", "breakdown":
        {...}, "estimated_total", "remaining", "within_budget", "per_person", "per_day"}}.
        On failure: {"status": "error", "error_message": "..."}.
    """
    try:
        int_between(nights, 1, 60, "nights")
        int_between(travellers, 1, 20, "travellers")
        amounts = {
            "total_budget": total_budget,
            "hotel_total": hotel_total,
            "flights_total": flights_total,
            "activities_total": activities_total,
            "daily_spend_per_person": daily_spend_per_person,
        }
        for field, value in amounts.items():
            if value < 0:
                raise ToolError(f"{field} must not be negative.")
        currency = currency_code(currency)

        days = nights + 1
        breakdown = {
            "hotel": round(hotel_total, 2),
            "flights": round(flights_total, 2),
            "activities": round(activities_total, 2),
            "food_and_local_transport": round(daily_spend_per_person * travellers * days, 2),
        }
        total = round(sum(breakdown.values()), 2)
        return ok({
            "currency": currency,
            "budget": round(total_budget, 2),
            "breakdown": breakdown,
            "estimated_total": total,
            "remaining": round(total_budget - total, 2),
            "within_budget": total <= total_budget,
            "per_person": round(total / travellers, 2),
            "per_day": round(total / days, 2),
        })
    except ToolError as exc:
        return error(str(exc))
