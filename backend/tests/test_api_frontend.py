"""API features the frontend relies on: keep-alives, retry flags, hotel swaps, Better Auth tokens."""

import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from jwt.algorithms import OKPAlgorithm

from app.main import create_app
from tests.test_api import FakeCoordinator, client, make_settings, new_trip, sse_events, token  # noqa: F401

# --- streaming and history --------------------------------------------------


def test_keep_alive_while_the_agents_work(client):
    client.app.state.trips.heartbeat_seconds = 0.1
    trip_id = new_trip(client)

    body = client.post(f"/api/trips/{trip_id}/messages", json={"text": "slow"}, headers=token()).text

    assert ": keep-alive" in body
    assert sse_events(body)[-1][0] == "done"


def test_unanswered_messages_are_marked(client):
    trip_id = new_trip(client)
    client.post(f"/api/trips/{trip_id}/messages", json={"text": "crash"}, headers=token())
    client.post(f"/api/trips/{trip_id}/messages", json={"text": "Rome"}, headers=token())

    messages = client.get(f"/api/trips/{trip_id}", headers=token()).json()["messages"]

    assert [(m["role"], m["text"], m["answered"]) for m in messages] == [
        ("user", "crash", False), ("user", "Rome", True), ("assistant", "Here is your plan for: Rome", None)]


# --- hotel swap (no AI) ----------------------------------------------------------


def planned_trip(client) -> str:
    trip_id = new_trip(client)
    client.post(f"/api/trips/{trip_id}/messages", json={"text": "plan"}, headers=token())
    return trip_id


def test_choose_another_hotel_recalculates_cost_without_ai(client):
    trip_id = planned_trip(client)

    response = client.patch(f"/api/trips/{trip_id}/itinerary", json={"hotel": "aparthotel colombo"}, headers=token())

    assert response.status_code == 200
    body = response.json()
    assert body["itinerary"]["hotel"] == "Aparthotel Colombo"
    assert body["itinerary"]["hotel_details"]["total_price"] == 328
    # hotel 328 + tickets 60 + 50/person/day * 2 people * 3 days
    assert body["itinerary_review"]["cost"]["estimated_total"] == 688
    assert body["itinerary"]["days"][0]["activities"][0]["details"]["name"] == "Pantheon"

    detail = client.get(f"/api/trips/{trip_id}", headers=token()).json()
    assert detail["trip"]["itinerary"]["hotel"] == "Aparthotel Colombo"
    assert detail["trip"]["itinerary_review"]["cost"]["estimated_total"] == 688
    assert len(detail["messages"]) == 2  # the swap adds no chat message


def test_choose_hotel_errors(client):
    planned = planned_trip(client)
    empty = new_trip(client)

    unknown = client.patch(f"/api/trips/{planned}/itinerary", json={"hotel": "Hotel Imaginary"}, headers=token())
    no_plan = client.patch(f"/api/trips/{empty}/itinerary", json={"hotel": "Aparthotel Colombo"}, headers=token())
    other_user = client.patch(f"/api/trips/{planned}/itinerary", json={"hotel": "Aparthotel Colombo"},
                              headers=token("mallory"))

    assert (unknown.status_code, unknown.json()["error"]["code"]) == (422, "unknown_hotel")
    assert (no_plan.status_code, no_plan.json()["error"]["code"]) == (404, "no_itinerary")
    assert other_user.status_code == 404

    client.app.state.trips._busy.add(planned)
    busy = client.patch(f"/api/trips/{planned}/itinerary", json={"hotel": "Aparthotel Colombo"}, headers=token())
    assert busy.status_code == 409


# --- Better Auth tokens (EdDSA, checked against the frontend's public keys) ---

JWKS_URL = "http://auth.test/api/auth/jwks"
ISSUER, AUDIENCE = "http://localhost:3000", "travel-planner-api"
PRIVATE_KEY = Ed25519PrivateKey.generate()


def better_auth_token(user="ba_user_123", audience=AUDIENCE, issuer=ISSUER, minutes=15, key=PRIVATE_KEY):
    now = datetime.now(UTC)
    claims = {"sub": user, "aud": audience, "iss": issuer, "iat": now, "exp": now + timedelta(minutes=minutes)}
    signed = jwt.encode(claims, key, algorithm="EdDSA", headers={"kid": "key-1"})
    return {"Authorization": f"Bearer {signed}"}


@pytest.fixture
def jwks(monkeypatch):
    public = json.loads(OKPAlgorithm.to_jwk(PRIVATE_KEY.public_key()))
    keys = {"keys": [{**public, "kid": "key-1", "alg": "EdDSA", "use": "sig"}]}
    state = {"down": False}

    def fetch_data(self):
        if state["down"]:
            raise jwt.PyJWKClientConnectionError("connection refused")
        return keys

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fetch_data)
    return state


def jwks_app(tmp_path, **overrides) -> TestClient:
    settings = make_settings(tmp_path, auth_jwks_url=JWKS_URL, auth_issuer=ISSUER, auth_audience=AUDIENCE, **overrides)
    return TestClient(create_app(settings, agent=FakeCoordinator(name="travel_coordinator")))


def test_better_auth_token_accepted(tmp_path, jwks):
    with jwks_app(tmp_path) as api:
        assert api.post("/api/trips", headers=better_auth_token()).status_code == 201
        assert len(api.get("/api/trips", headers=better_auth_token()).json()) == 1
        assert api.get("/api/trips", headers=better_auth_token("someone_else")).json() == []


@pytest.mark.parametrize("kwargs, code", [
    ({"audience": "wrong"}, "invalid_token"),
    ({"issuer": "https://evil.example"}, "invalid_token"),
    ({"minutes": -1}, "token_expired"),
    ({"key": Ed25519PrivateKey.generate()}, "invalid_token"),  # signed by someone else
])
def test_bad_better_auth_tokens_rejected(tmp_path, jwks, kwargs, code):
    with jwks_app(tmp_path) as api:
        response = api.get("/api/trips", headers=better_auth_token(**kwargs))
    assert response.status_code == 401 and response.json()["error"]["code"] == code


def test_auth_server_down_is_503(tmp_path, jwks):
    jwks["down"] = True
    with jwks_app(tmp_path) as api:
        response = api.get("/api/trips", headers=better_auth_token())
    assert response.status_code == 503 and response.json()["error"]["code"] == "auth_unavailable"


def test_production_with_better_auth_refuses_hs256_tokens(tmp_path, jwks):
    with jwks_app(tmp_path, app_env="production", jwt_secret="") as api:
        assert api.get("/api/trips", headers=token()).status_code == 401
        assert api.get("/api/trips", headers=better_auth_token()).status_code == 200


def test_eddsa_token_without_jwks_configured_is_rejected(client):
    assert client.get("/api/trips", headers=better_auth_token()).status_code == 401
