from datetime import date, timedelta

import pytest
import respx

from tools import _geo, _geoapify

FAKE_KEYS = {
    "LITEAPI_KEY": "test-liteapi-key",
    "GEOAPIFY_API_KEY": "test-geoapify-key",
}

PARIS = {
    "name": "Paris",
    "country": "France",
    "country_code": "FR",
    "latitude": 48.85341,
    "longitude": 2.3488,
    "timezone": "Europe/Paris",
}


def days_from_now(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


@pytest.fixture(autouse=True)
def fake_keys(monkeypatch):
    for name, value in FAKE_KEYS.items():
        monkeypatch.setenv(name, value)


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch):
    async def instant(_seconds):
        return None

    monkeypatch.setattr("tools._http._sleep", instant)  # only the tools' retry waits, not asyncio itself


@pytest.fixture
def api():
    """Block real network calls; each test registers the fake responses it needs."""
    with respx.mock(assert_all_called=False) as mock:
        yield mock


@pytest.fixture
def paris_geocode(api):
    """Open-Meteo geocoder (used by the weather tool)."""
    return api.get(url__startswith=_geo.GEOCODING_URL).respond(200, json={"results": [PARIS]})


@pytest.fixture
def paris_city_centre(api):
    """Geoapify geocoder (used by the hotel-location and attraction tools)."""
    return api.get(url__startswith=_geoapify.GEOAPIFY_GEOCODE_URL).respond(200, json={"results": [{
        "city": "Paris", "country": "France", "country_code": "fr",
        "lat": PARIS["latitude"], "lon": PARIS["longitude"], "timezone": {"name": "Europe/Paris"},
    }]})
