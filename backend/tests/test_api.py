"""API tests: real FastAPI app, ADK Runner and database sessions (SQLite), fake agent (no Gemini)."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.genai import types

from app.config import Settings
from app.main import create_app
from tests.itinerary_fixtures import good_plan, research_state

SECRET = "test-secret-" + "x" * 40
ITINERARY = {"title": "3 days in Rome", "days": []}


class QuotaError(Exception):
    code = 429


class FakeCoordinator(BaseAgent):
    """Behaves like travel_coordinator: one progress call, saves trip data, replies."""

    async def _run_async_impl(self, ctx):
        text = ctx.user_content.parts[0].text
        if text == "use up the quota":
            raise QuotaError("429 RESOURCE_EXHAUSTED")
        if text == "crash":
            raise RuntimeError("database password is hunter2")  # must not reach the client
        if text == "slow":
            await asyncio.sleep(0.4)
        if text == "plan":  # save full research and a plan, like the real agents do
            yield Event(author=self.name, invocation_id=ctx.invocation_id,
                        actions=EventActions(state_delta={**research_state(), "itinerary": good_plan()}))
            yield Event(author=self.name, invocation_id=ctx.invocation_id,
                        content=types.Content(role="model", parts=[types.Part(text="Your plan is ready.")]))
            return
        call = types.FunctionCall(id="call-1", name="weather_agent", args={"city": "Rome"})
        yield Event(author=self.name, invocation_id=ctx.invocation_id,
                    content=types.Content(role="model", parts=[types.Part(function_call=call)]))
        response = types.FunctionResponse(id="call-1", name="weather_agent", response={"result": "sunny"})
        yield Event(author=self.name, invocation_id=ctx.invocation_id,
                    content=types.Content(role="user", parts=[types.Part(function_response=response)]),
                    actions=EventActions(state_delta={"weather": {"days": ["sunny"]}, "itinerary": ITINERARY,
                                                      "temp:internal": 1}))
        yield Event(author=self.name, invocation_id=ctx.invocation_id,
                    content=types.Content(role="model", parts=[types.Part(text=f"Here is your plan for: {text}")]))


def make_settings(tmp_path, **overrides) -> Settings:
    values = dict(
        _env_file=None, app_env="development", jwt_secret=SECRET,
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
        cors_origins="http://localhost:3000", rate_limit_per_minute=50, rate_limit_per_day=500,
        max_message_chars=200, max_llm_calls=30,
    )
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def client(tmp_path):
    app = create_app(make_settings(tmp_path), agent=FakeCoordinator(name="travel_coordinator"))
    with TestClient(app) as test_client:
        yield test_client


def token(user="alice", minutes=60, secret=SECRET, audience="travel-planner"):
    now = datetime.now(UTC)
    claims = {"sub": user, "aud": audience, "iat": now, "exp": now + timedelta(minutes=minutes)}
    return {"Authorization": f"Bearer {jwt.encode(claims, secret, algorithm='HS256')}"}


def sse_events(body: str) -> list[tuple[str, dict]]:
    events = []
    for frame in body.strip().split("\n\n"):
        if frame.startswith(":"):  # keep-alive comment
            continue
        lines = dict(line.split(": ", 1) for line in frame.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def new_trip(client, user="alice") -> str:
    response = client.post("/api/trips", headers=token(user))
    assert response.status_code == 201
    return response.json()["id"]


# --- system ---------------------------------------------------------------

def test_health_and_ready(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/health/ready").json() == {"status": "ready"}


def test_request_id_header(client):
    assert client.get("/api/health", headers={"X-Request-ID": "abc"}).headers["X-Request-ID"] == "abc"
    assert len(client.get("/api/health").headers["X-Request-ID"]) == 32


def test_dev_token_works(client):
    issued = client.post("/api/auth/dev-token", json={"user_id": "bob"}).json()
    headers = {"Authorization": f"Bearer {issued['access_token']}"}

    assert client.get("/api/trips", headers=headers).status_code == 200


def test_production_hides_dev_token_and_docs(tmp_path):
    app = create_app(make_settings(tmp_path, app_env="production"), agent=FakeCoordinator(name="travel_coordinator"))
    with TestClient(app) as prod:
        assert prod.post("/api/auth/dev-token", json={"user_id": "bob"}).status_code == 404
        assert prod.get("/docs").status_code == 404


def test_production_requires_a_real_secret(tmp_path):
    with pytest.raises(ValueError, match="AUTH_JWKS_URL, or JWT_SECRET"):
        make_settings(tmp_path, app_env="production", jwt_secret="short")


# --- auth -----------------------------------------------------------------

@pytest.mark.parametrize("headers, code", [
    ({}, "not_authenticated"),
    ({"Authorization": "Bearer not-a-jwt"}, "invalid_token"),
    (token(secret="wrong-secret-" + "y" * 40), "invalid_token"),
    (token(audience="someone-else"), "invalid_token"),
    (token(minutes=-1), "token_expired"),
    (token(user="bad user!"), "invalid_token"),
])
def test_bad_tokens_rejected(client, headers, code):
    response = client.get("/api/trips", headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == code


def test_users_cannot_see_each_others_trips(client):
    trip_id = new_trip(client, "alice")

    assert client.get(f"/api/trips/{trip_id}", headers=token("mallory")).status_code == 404
    assert client.delete(f"/api/trips/{trip_id}", headers=token("mallory")).status_code == 404
    assert client.post(f"/api/trips/{trip_id}/messages", json={"text": "hi"},
                       headers=token("mallory")).status_code == 404
    assert client.get("/api/trips", headers=token("mallory")).json() == []


# --- trips ----------------------------------------------------------------

def test_create_list_get_delete(client):
    trip_id = new_trip(client)

    listed = client.get("/api/trips", headers=token()).json()
    assert [(t["id"], t["title"]) for t in listed] == [(trip_id, "New trip")]
    assert client.get(f"/api/trips/{trip_id}", headers=token()).json()["messages"] == []

    assert client.delete(f"/api/trips/{trip_id}", headers=token()).status_code == 204
    assert client.get(f"/api/trips/{trip_id}", headers=token()).status_code == 404


def test_invalid_trip_id_rejected(client):
    assert client.get("/api/trips/not%20valid!", headers=token()).status_code == 422


# --- messages -------------------------------------------------------------

def test_message_streams_progress_reply_and_trip_data(client):
    trip_id = new_trip(client)

    response = client.post(f"/api/trips/{trip_id}/messages", json={"text": "Rome in October"}, headers=token())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = sse_events(response.text)
    assert [name for name, _ in events] == ["progress", "progress", "message", "trip", "done"]
    assert events[0][1] == {"step": "weather_agent", "status": "started", "message": "Checking the weather"}
    assert events[1][1] == {"step": "weather_agent", "status": "done", "ok": True, "message": "Weather checked"}
    assert events[2][1] == {"role": "assistant", "text": "Here is your plan for: Rome in October"}
    assert events[3][1] == {"itinerary": ITINERARY, "weather": {"days": ["sunny"]}}  # temp: keys never sent
    assert events[4][1] == {"trip_id": trip_id}

    detail = client.get(f"/api/trips/{trip_id}", headers=token()).json()
    assert [(m["role"], m["text"]) for m in detail["messages"]] == [
        ("user", "Rome in October"), ("assistant", "Here is your plan for: Rome in October")]
    assert detail["trip"] == {"itinerary": ITINERARY, "weather": {"days": ["sunny"]}}


def test_conversation_survives_a_restart(tmp_path):
    settings = make_settings(tmp_path)
    with TestClient(create_app(settings, agent=FakeCoordinator(name="travel_coordinator"))) as first:
        trip_id = new_trip(first)
        first.post(f"/api/trips/{trip_id}/messages", json={"text": "Rome"}, headers=token())

    with TestClient(create_app(settings, agent=FakeCoordinator(name="travel_coordinator"))) as second:
        detail = second.get(f"/api/trips/{trip_id}", headers=token()).json()

    assert len(detail["messages"]) == 2
    assert detail["trip"]["itinerary"] == ITINERARY


@pytest.mark.parametrize("text, status, code", [
    ("   ", 422, "invalid_request"),
    ("", 422, "invalid_request"),
    ("x" * 201, 422, "message_too_long"),
])
def test_bad_messages_rejected(client, text, status, code):
    trip_id = new_trip(client)

    response = client.post(f"/api/trips/{trip_id}/messages", json={"text": text}, headers=token())

    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_message_to_unknown_trip(client):
    response = client.post("/api/trips/does-not-exist/messages", json={"text": "hi"}, headers=token())
    assert response.status_code == 404 and response.json()["error"]["code"] == "trip_not_found"


def test_busy_trip_returns_409(client):
    trip_id = new_trip(client)
    client.app.state.trips._busy.add(trip_id)

    response = client.post(f"/api/trips/{trip_id}/messages", json={"text": "hi"}, headers=token())

    assert response.status_code == 409 and response.json()["error"]["code"] == "trip_busy"
    assert client.delete(f"/api/trips/{trip_id}", headers=token()).status_code == 409


def test_rate_limit(tmp_path):
    app = create_app(make_settings(tmp_path, rate_limit_per_minute=2), agent=FakeCoordinator(name="travel_coordinator"))
    with TestClient(app) as limited:
        trip_id = new_trip(limited)
        for _ in range(2):
            assert limited.post(f"/api/trips/{trip_id}/messages", json={"text": "hi"}, headers=token()).status_code == 200

        response = limited.post(f"/api/trips/{trip_id}/messages", json={"text": "hi"}, headers=token())
        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) > 0
        # another user is not affected
        other_trip = new_trip(limited, "bob")
        assert limited.post(f"/api/trips/{other_trip}/messages", json={"text": "hi"},
                            headers=token("bob")).status_code == 200


@pytest.mark.parametrize("text, code", [("use up the quota", "ai_quota_exceeded"), ("crash", "internal_error")])
def test_agent_failure_streams_an_error_and_frees_the_trip(client, text, code):
    trip_id = new_trip(client)

    events = sse_events(client.post(f"/api/trips/{trip_id}/messages", json={"text": text}, headers=token()).text)

    assert events[-1][0] == "error" and events[-1][1]["code"] == code
    assert "hunter2" not in json.dumps(events)
    # the trip is usable again
    retry = sse_events(client.post(f"/api/trips/{trip_id}/messages", json={"text": "hi"}, headers=token()).text)
    assert retry[-1][0] == "done"


def test_validation_error_shape(client):
    trip_id = new_trip(client)

    response = client.post(f"/api/trips/{trip_id}/messages", json={}, headers=token())

    assert response.status_code == 422
    assert response.json()["error"]["problems"][0]["field"] == "text"


def test_cors_allows_the_frontend(client):
    response = client.options("/api/trips", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    blocked = client.options("/api/trips", headers={"Origin": "https://evil.example",
                                                     "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in blocked.headers


def test_unreachable_database_fails_at_startup_without_leaking_password(tmp_path):
    settings = make_settings(tmp_path, database_url="postgresql+asyncpg://travel:s3cret@127.0.0.1:1/nowhere")
    app = create_app(settings, agent=FakeCoordinator(name="travel_coordinator"))

    with pytest.raises(RuntimeError) as info:
        with TestClient(app):
            pass

    assert "Cannot use the database at postgresql+asyncpg://travel:***@127.0.0.1:1/nowhere" in str(info.value)
    assert "s3cret" not in str(info.value)


def test_empty_database_url_means_sqlite(tmp_path):
    assert make_settings(tmp_path, database_url="  ").database_url.startswith("sqlite+aiosqlite:///")
