from tests.conftest import days_from_now
from tools import get_weather_forecast
from tools.weather import FORECAST_URL


def forecast_payload(dates):
    n = len(dates)
    return {
        "daily": {
            "time": dates,
            "weather_code": [0, 63][:n],
            "temperature_2m_max": [24.1, 18.0][:n],
            "temperature_2m_min": [14.2, 12.5][:n],
            "precipitation_sum": [0.0, 6.4][:n],
            "precipitation_probability_max": [5, 80][:n],
            "wind_speed_10m_max": [12.0, 25.3][:n],
        }
    }


async def test_returns_daily_forecast(api, paris_geocode):
    start, end = days_from_now(1), days_from_now(2)
    route = api.get(url__startswith=FORECAST_URL).respond(200, json=forecast_payload([start, end]))

    result = await get_weather_forecast("Paris", start, end, "fr")

    assert result["status"] == "success"
    days = result["data"]["days"]
    assert [d["condition"] for d in days] == ["Clear sky", "Rain"]
    assert [d["rain_likely"] for d in days] == [False, True]
    assert result["data"]["location"]["name"] == "Paris"
    params = route.calls.last.request.url.params
    assert params["start_date"] == start and params["end_date"] == end
    assert params["timezone"] == "Europe/Paris"
    assert paris_geocode.calls.last.request.url.params["countryCode"] == "FR"


async def test_dates_beyond_forecast_range_fail_without_calling_api(api):
    result = await get_weather_forecast("Paris", days_from_now(10), days_from_now(20))

    assert result["status"] == "error"
    assert "16 days" in result["error_message"]
    assert not api.calls


async def test_past_dates_rejected():
    result = await get_weather_forecast("Paris", days_from_now(-3), days_from_now(1))
    assert result["status"] == "error"
    assert "in the past" in result["error_message"]


async def test_unknown_city(api):
    api.get(url__startswith="https://geocoding-api.open-meteo.com").respond(200, json={})

    result = await get_weather_forecast("Nowhereville", days_from_now(1), days_from_now(2))

    assert result == {"status": "error", "error_message": "Could not find a place called 'Nowhereville'."}


async def test_server_errors_are_retried_then_reported(api, paris_geocode):
    route = api.get(url__startswith=FORECAST_URL).respond(503)

    result = await get_weather_forecast("Paris", days_from_now(1), days_from_now(1))

    assert result["status"] == "error"
    assert "Open-Meteo is unavailable" in result["error_message"]
    assert route.call_count == 3  # first try + 2 retries
