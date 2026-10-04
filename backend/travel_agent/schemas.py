"""Structured data passed between agents.

TripRequest is the input every specialist sub-agent receives from the
coordinator, so they all work from the same trip details.
"""

from pydantic import BaseModel, Field


class TripRequest(BaseModel):
    city: str = Field(description='Destination city, for example "Paris".')
    country_code: str = Field(description='2-letter ISO country code of the city, for example "FR".')
    start_date: str = Field(description="First day of the trip / check-in date, YYYY-MM-DD.")
    end_date: str = Field(description="Last day of the trip / check-out date, YYYY-MM-DD.")
    adults: int = Field(default=2, description="Number of adult travellers.")
    currency: str = Field(default="USD", description='3-letter currency code, for example "EUR".')
    max_price_per_night: float = Field(default=0, description="Hotel budget per night. 0 means no limit.")
    interests: str = Field(
        default="",
        description='What the travellers enjoy, for example "museums, history, parks". Empty if unknown.',
    )
    notes: str = Field(
        default="",
        description='Extra wishes for this search, for example "refundable only" or "cheaper than last time".',
    )
