"""Trips = ADK sessions. Each trip is one planning conversation with its own state.

This wraps the ADK Runner and session service so the routes stay thin, and turns
the agent's event stream into Server-Sent Events for the frontend:

    progress  {"step", "status": "started"|"done", "message", "ok"?}: a specialist or the planner
    message   the coordinator's reply text
    trip      trip data that changed this turn (itinerary, hotels, weather, ...)
    done      the turn finished
    error     the turn failed; {"code", "message"}

A ": keep-alive" comment is sent every 15 seconds while the agents work, so
proxies and browsers don't drop a connection that is quiet for a minute.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from google.adk.agents.run_config import RunConfig
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.base_session_service import GetSessionConfig
from google.genai import types

from travel_agent.plan_updates import PlanUpdateError, choose_hotel

from ..errors import ApiError

logger = logging.getLogger(__name__)

APP_NAME = "travel_agent"
APP_AUTHOR = "travel_app"  # author of state changes made by the API itself (hotel swaps)
TRIP_STATE_KEYS = frozenset(
    {"trip_request", "weather", "hotels", "hotels_nearby", "attractions", "itinerary", "itinerary_review"}
)
STEPS = {  # coordinator tool -> (started message, done message)
    "weather_agent": ("Checking the weather", "Weather checked"),
    "hotel_agent": ("Searching for hotels", "Hotels found"),
    "places_agent": ("Finding things to do", "Things to do found"),
    "plan_itinerary": ("Building your day-by-day plan", "Day-by-day plan ready"),
}
MAX_LISTED_TRIPS = 50
HEARTBEAT_SECONDS = 15.0
_END = object()


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _text(content: types.Content | None) -> str:
    if not content or not content.parts:
        return ""
    return "".join(part.text for part in content.parts if part.text and not part.thought).strip()


def _title(state: dict[str, Any]) -> str:
    trip = state.get("trip_request") or {}
    if trip.get("city"):
        return f"{trip['city']}, {trip.get('start_date', '?')} to {trip.get('end_date', '?')}"
    return "New trip"


def _chain(exc: BaseException | None):
    """The exception and its causes (ADK wraps model errors in its own exceptions)."""
    for _ in range(10):
        if exc is None:
            return
        yield exc
        exc = exc.__cause__ or exc.__context__


def classify_error(exc: BaseException) -> tuple[str, str]:
    """Turn a failure into a (code, user-facing message) pair. Never leaks internals."""
    for err in _chain(exc):
        status = getattr(err, "code", None)
        status = status if isinstance(status, int) else getattr(err, "status_code", None)
        text = str(err)
        if status == 429 or "RESOURCE_EXHAUSTED" in text:
            return "ai_quota_exceeded", "The AI service's request limit has been reached. Please try again later."
        if status in (500, 502, 503, 504) or "503 UNAVAILABLE" in text:
            return "ai_unavailable", "The AI service is busy right now. Please try again in a minute."
        if type(err).__name__ == "LlmCallsLimitExceededError":
            return "too_many_steps", "This request needed too many steps. Please ask something more specific."
    return "internal_error", "Something went wrong while planning. Please try again."


class TripService:
    def __init__(self, runner: Runner, sessions: BaseSessionService, max_llm_calls: int,
                 heartbeat_seconds: float = HEARTBEAT_SECONDS):
        self.runner = runner
        self.sessions = sessions
        self.max_llm_calls = max_llm_calls
        self.heartbeat_seconds = heartbeat_seconds
        self.coordinator = runner.agent.name
        self._busy: set[str] = set()  # trips with a turn or update in progress (per process)

    # --- trips -------------------------------------------------------------

    async def create(self, user_id: str) -> dict:
        session = await self.sessions.create_session(app_name=APP_NAME, user_id=user_id)
        return self._summary(session)

    async def list_trips(self, user_id: str) -> list[dict]:
        listed = await self.sessions.list_sessions(app_name=APP_NAME, user_id=user_id)
        newest = sorted(listed.sessions, key=lambda s: s.last_update_time, reverse=True)[:MAX_LISTED_TRIPS]
        trips = []
        for item in newest:  # list_sessions has no state; fetch it (without events) for the title
            session = await self._session(user_id, item.id, with_events=False)
            trips.append(self._summary(session or item))
        return trips

    async def get(self, user_id: str, trip_id: str) -> dict:
        session = await self._existing(user_id, trip_id, with_events=True)
        return {
            **self._summary(session),
            "busy": trip_id in self._busy,
            "messages": self._messages(session),
            "trip": {key: session.state[key] for key in TRIP_STATE_KEYS if key in session.state},
        }

    async def delete(self, user_id: str, trip_id: str) -> None:
        await self._existing(user_id, trip_id, with_events=False)
        self._ensure_idle(trip_id)
        await self.sessions.delete_session(app_name=APP_NAME, user_id=user_id, session_id=trip_id)

    async def require(self, user_id: str, trip_id: str) -> None:
        """404 if the trip does not exist for this user, 409 if a turn is already running."""
        await self._existing(user_id, trip_id, with_events=False)
        self._ensure_idle(trip_id)

    async def choose_hotel(self, user_id: str, trip_id: str, hotel_name: str) -> dict:
        """Swap the plan's hotel in code (no Gemini requests) and save it."""
        session = await self._existing(user_id, trip_id, with_events=False)
        self._ensure_idle(trip_id)
        try:
            plan, review = choose_hotel(session.state, hotel_name)
        except PlanUpdateError as exc:
            status = {"no_itinerary": 404, "invalid_itinerary": 409}.get(exc.code, 422)
            raise ApiError(status, exc.code, exc.message) from exc

        self._busy.add(trip_id)
        try:
            update = Event(
                author=APP_AUTHOR,
                invocation_id=f"app-{uuid.uuid4().hex}",
                actions=EventActions(state_delta={"itinerary": plan, "itinerary_review": review}),
            )
            await self.sessions.append_event(session, update)
        finally:
            self._busy.discard(trip_id)
        return {"itinerary": plan, "itinerary_review": review}

    # --- conversation ------------------------------------------------------

    async def reply(self, user_id: str, trip_id: str, text: str) -> AsyncIterator[str]:
        """Run one turn of the conversation and stream it as SSE frames."""
        if trip_id in self._busy:  # lost a race with another request for the same trip
            yield sse("error", {"code": "trip_busy", "message": "This trip is still answering the previous message."})
            return
        self._busy.add(trip_id)
        queue: asyncio.Queue = asyncio.Queue()
        producer = asyncio.create_task(self._run_turn(user_id, trip_id, text, queue))
        try:
            changed: set[str] = set()
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=self.heartbeat_seconds)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if item is _END:
                    break
                if isinstance(item, BaseException):
                    code, user_message = classify_error(item)
                    logger.error("Turn failed for trip %s (%s)", trip_id, code, exc_info=item)
                    yield sse("error", {"code": code, "message": user_message})
                    return
                for frame in self._frames(item, changed):
                    yield frame

            if changed:
                session = await self._session(user_id, trip_id, with_events=False)
                state = session.state if session else {}
                yield sse("trip", {key: state.get(key) for key in sorted(changed)})
            yield sse("done", {"trip_id": trip_id})
        finally:
            if not producer.done():  # the client went away: stop the agents too
                producer.cancel()
            try:
                await producer
            except BaseException:
                pass
            self._busy.discard(trip_id)

    async def _run_turn(self, user_id: str, trip_id: str, text: str, queue: asyncio.Queue) -> None:
        try:
            events = self.runner.run_async(
                user_id=user_id,
                session_id=trip_id,
                new_message=types.Content(role="user", parts=[types.Part(text=text)]),
                run_config=RunConfig(max_llm_calls=self.max_llm_calls),
            )
            async for event in events:
                await queue.put(event)
            await queue.put(_END)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # handed to the streaming side, which reports it
            await queue.put(exc)

    def _frames(self, event: Event, changed: set[str]) -> list[str]:
        changed |= TRIP_STATE_KEYS & set(event.actions.state_delta or {})
        if event.author != self.coordinator or event.branch:
            return []
        frames = []
        for call in event.get_function_calls():
            if call.name in STEPS:
                frames.append(sse("progress", {"step": call.name, "status": "started", "message": STEPS[call.name][0]}))
        for response in event.get_function_responses():
            if response.name in STEPS:
                ok = (response.response or {}).get("status") != "error"
                frames.append(sse("progress", {"step": response.name, "status": "done", "ok": ok,
                                               "message": STEPS[response.name][1]}))
        if event.is_final_response() and (reply := _text(event.content)):
            frames.append(sse("message", {"role": "assistant", "text": reply}))
        return frames

    # --- helpers -----------------------------------------------------------

    async def _session(self, user_id: str, trip_id: str, *, with_events: bool) -> Session | None:
        config = None if with_events else GetSessionConfig(num_recent_events=0)
        return await self.sessions.get_session(app_name=APP_NAME, user_id=user_id, session_id=trip_id, config=config)

    async def _existing(self, user_id: str, trip_id: str, *, with_events: bool) -> Session:
        session = await self._session(user_id, trip_id, with_events=with_events)
        if session is None:
            raise ApiError(404, "trip_not_found", "Trip not found.")
        return session

    def _ensure_idle(self, trip_id: str) -> None:
        if trip_id in self._busy:
            raise ApiError(409, "trip_busy", "This trip is still answering the previous message.")

    def _summary(self, session: Session) -> dict:
        return {"id": session.id, "title": _title(session.state or {}), "updated_at": session.last_update_time}

    def _messages(self, session: Session) -> list[dict]:
        """The visible conversation: user messages and the coordinator's replies (no agent internals).

        A user message with no reply after it (the turn failed) has answered=False,
        so the app can offer to retry it.
        """
        messages: list[dict] = []
        for event in session.events:
            if event.branch:  # sub-agent and tool activity
                continue
            if event.author == "user" and (text := _text(event.content)):
                messages.append({"role": "user", "text": text, "at": event.timestamp, "answered": False})
            elif event.author == self.coordinator and event.is_final_response() and (text := _text(event.content)):
                if messages and messages[-1]["role"] == "user":
                    messages[-1]["answered"] = True
                messages.append({"role": "assistant", "text": text, "at": event.timestamp})
        return messages
