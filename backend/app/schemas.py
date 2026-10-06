"""Request and response bodies of the HTTP API."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class TripSummary(BaseModel):
    id: str
    title: str
    updated_at: float = Field(description="Unix timestamp of the last change.")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    at: float
    answered: bool | None = Field(
        default=None, description="User messages only: False if the turn failed and got no reply."
    )


class TripDetail(TripSummary):
    busy: bool = Field(description="True while a message is being answered.")
    messages: list[ChatMessage]
    trip: dict[str, Any] = Field(
        description="Saved trip data: trip_request, weather, hotels, hotels_nearby, attractions, "
        "itinerary, itinerary_review (only the keys that exist so far)."
    )


class ChooseHotelIn(BaseModel):
    hotel: str = Field(min_length=1, max_length=300, description="Exact hotel name from the trip's hotel results.")


class ItineraryUpdate(BaseModel):
    itinerary: dict[str, Any]
    itinerary_review: dict[str, Any]


class MessageIn(BaseModel):
    text: str = Field(min_length=1, description="The user's message.")


class DevTokenIn(BaseModel):
    user_id: str = Field(pattern=r"^[A-Za-z0-9_.@-]{1,128}$", examples=["alice"])


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until the token expires.")
