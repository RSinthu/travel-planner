"""Trip endpoints. A trip is one planning conversation; all of them need a bearer token."""

from typing import Annotated

from fastapi import APIRouter, Path, Request, Response
from fastapi.responses import StreamingResponse

from ..auth import CurrentUser
from ..errors import ApiError
from ..schemas import ChooseHotelIn, ItineraryUpdate, MessageIn, TripDetail, TripSummary
from ..services.trips import TripService

router = APIRouter(prefix="/api/trips", tags=["trips"])

TripId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


def _trips(request: Request) -> TripService:
    return request.app.state.trips


@router.post("", status_code=201, response_model=TripSummary)
async def create_trip(request: Request, user: CurrentUser):
    """Start a new planning conversation."""
    return await _trips(request).create(user)


@router.get("", response_model=list[TripSummary])
async def list_trips(request: Request, user: CurrentUser):
    """The user's trips, most recently updated first (up to 50)."""
    return await _trips(request).list_trips(user)


@router.get("/{trip_id}", response_model=TripDetail)
async def get_trip(request: Request, user: CurrentUser, trip_id: TripId):
    """A trip's conversation and saved data (itinerary, hotels, weather, ...)."""
    return await _trips(request).get(user, trip_id)


@router.delete("/{trip_id}", status_code=204)
async def delete_trip(request: Request, user: CurrentUser, trip_id: TripId):
    await _trips(request).delete(user, trip_id)
    return Response(status_code=204)


@router.patch("/{trip_id}/itinerary", response_model=ItineraryUpdate)
async def choose_hotel(request: Request, user: CurrentUser, trip_id: TripId, body: ChooseHotelIn):
    """Switch the plan to another hotel from the results. Recalculates the cost in code: no AI requests."""
    return await _trips(request).choose_hotel(user, trip_id, body.hotel)


@router.post(
    "/{trip_id}/messages",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}, "description": "Server-Sent Events: "
                     "progress, message, trip, done or error."}},
)
async def send_message(request: Request, user: CurrentUser, trip_id: TripId, body: MessageIn):
    """Send a message and stream the planner's progress and reply."""
    settings = request.app.state.settings
    text = body.text.strip()
    if not text:
        raise ApiError(422, "invalid_request", "The message is empty.")
    if len(text) > settings.max_message_chars:
        raise ApiError(422, "message_too_long", f"Messages can be at most {settings.max_message_chars} characters.")

    trips = _trips(request)
    await trips.require(user, trip_id)  # 404 / 409 before starting the stream

    wait = request.app.state.rate_limiter.check(user)
    if wait is not None:
        raise ApiError(429, "rate_limited", "Too many messages. Please wait a little.",
                       headers={"Retry-After": str(int(wait) + 1)})

    return StreamingResponse(
        trips.reply(user, trip_id, text),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
