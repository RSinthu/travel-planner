import httpx
import pytest

from tools._http import ToolError, request_json

URL = "https://api.example.com/thing"


async def test_retries_rate_limit_then_succeeds(api):
    route = api.get(URL)
    route.side_effect = [httpx.Response(429), httpx.Response(200, json={"ok": True})]

    assert await request_json("GET", URL, service="Example") == {"ok": True}
    assert route.call_count == 2


async def test_client_errors_fail_immediately(api):
    route = api.get(URL).respond(404, json={"message": "not here"})

    with pytest.raises(ToolError, match="HTTP 404.*not here"):
        await request_json("GET", URL, service="Example")
    assert route.call_count == 1


async def test_timeouts_reported_without_url_or_key(api):
    api.get(URL).mock(side_effect=httpx.ConnectTimeout("boom"))

    with pytest.raises(ToolError) as info:
        await request_json("GET", URL, service="Example", params={"apiKey": "secret"}, retries=1)
    assert "timed out" in str(info.value)
    assert "secret" not in str(info.value) and "example.com" not in str(info.value)
