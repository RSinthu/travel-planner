"""Structured data passed between agents.

TripRequest is the input every specialist sub-agent receives from the
coordinator, so they all work from the same trip details. Itinerary is the
day-by-day plan the itinerary agent must return.
"""

from typing import Literal

from pydantic import BaseModel, Field


class TripRequest(BaseModel):
    city: str = Field(description='Destination city, for example "Paris".')
    country_code: str = Field(description='2-letter ISO country code of the city, for example "FR".')
    start_date: str = Field(description="First day of the trip / check-in date, YYYY-MM-DD.")
    end_date: str = Field(description="Last day of the trip / check-out date, YYYY-MM-DD.")
    adults: int = Field(default=2, description="Number of adult travellers.")
    currency: str = Field(default="USD", description='3-letter currency code, for example "EUR".')
    max_price_per_night: float = Field(default=0, description="Hotel budget per night. 0 means no limit.")
    total_budget: float = Field(
        default=0,
        description="Budget for the whole trip (hotel, food, local transport, tickets). 0 means not given.",
    )
    interests: str = Field(
        default="",
        description='What the travellers enjoy, for example "museums, history, parks". Empty if unknown.',
    )
    notes: str = Field(
        default="",
        description='Extra wishes for this search, for example "refundable only" or "cheaper than last time".',
    )


class PlannedActivity(BaseModel):
    time_of_day: Literal["morning", "afternoon", "evening"]
    title: str = Field(description='Short description, for example "Explore the Pantheon".')
    place: str = Field(
        default="",
        description="Exact attraction name from the research list, or empty for meals, walks and free time.",
    )
    indoor: bool = Field(description="True if the activity is mainly indoors.")


class DayPlan(BaseModel):
    date: str = Field(description="YYYY-MM-DD.")
    weather: str = Field(description='One-line weather summary, for example "Thunderstorm, 19-23°C".')
    activities: list[PlannedActivity]


class Itinerary(BaseModel):
    title: str = Field(description='Short trip title, for example "4 days of history in Rome".')
    hotel: str = Field(description="Exact name of the chosen hotel from the research list, or empty if none.")
    days: list[DayPlan] = Field(description="One entry per date, from the first to the last day of the trip.")
    daily_spend_per_person: float = Field(
        description="Estimated food and local transport per person per day, in the trip currency."
    )
    activities_total: float = Field(
        description="Estimated entrance tickets for all travellers for the whole trip, in the trip currency."
    )
    tips: list[str] = Field(default_factory=list, description="Up to 3 short practical tips.")
