from google.adk.models.google_llm import Gemini
from google.adk.models.llm_request import LlmRequest

from travel_agent.models import FallbackGemini


class Coded(Exception):
    def __init__(self, code):
        super().__init__(f"error {code}")
        self.code = code


def fake_gemini(monkeypatch, behaviour):
    """Replace the real Gemini call: behaviour[model] is an exception to raise or a list of outputs."""
    tried = []

    async def generate(self, llm_request, stream=False):
        tried.append(llm_request.model)
        outcome = behaviour[llm_request.model]
        for item in outcome if isinstance(outcome, list) else [outcome]:
            if isinstance(item, Exception):
                raise item
            yield item

    monkeypatch.setattr(Gemini, "generate_content_async", generate)
    return tried


async def collect(model, request):
    return [r async for r in model.generate_content_async(request)]


async def test_overloaded_model_falls_back(monkeypatch):
    tried = fake_gemini(monkeypatch, {"main": Coded(503), "backup": ["ok"]})
    model = FallbackGemini(model="main", fallback_models=["backup"])

    assert await collect(model, LlmRequest(model="main")) == ["ok"]
    assert tried == ["main", "backup"]


async def test_quota_error_falls_back(monkeypatch):
    tried = fake_gemini(monkeypatch, {"main": Coded(429), "backup": ["ok"]})

    assert await collect(FallbackGemini(model="main", fallback_models=["backup"]), LlmRequest(model="main")) == ["ok"]
    assert tried == ["main", "backup"]


async def test_other_errors_do_not_fall_back(monkeypatch):
    tried = fake_gemini(monkeypatch, {"main": Coded(400), "backup": ["ok"]})

    try:
        await collect(FallbackGemini(model="main", fallback_models=["backup"]), LlmRequest(model="main"))
        raise AssertionError("expected the 400 to be raised")
    except Coded as exc:
        assert exc.code == 400
    assert tried == ["main"]


async def test_no_fallback_after_partial_output(monkeypatch):
    tried = fake_gemini(monkeypatch, {"main": ["partial", Coded(503)], "backup": ["ok"]})
    received = []

    try:
        async for response in FallbackGemini(model="main", fallback_models=["backup"]).generate_content_async(
                LlmRequest(model="main")):
            received.append(response)
        raise AssertionError("expected the 503 to be raised")
    except Coded:
        pass
    assert received == ["partial"] and tried == ["main"]


async def test_last_model_error_is_raised(monkeypatch):
    fake_gemini(monkeypatch, {"main": Coded(503), "backup": Coded(503)})

    try:
        await collect(FallbackGemini(model="main", fallback_models=["backup"]), LlmRequest(model="main"))
        raise AssertionError("expected the 503 to be raised")
    except Coded as exc:
        assert exc.code == 503


def test_planner_falls_back_to_the_lighter_model_last():
    from travel_agent.models import COORDINATOR_FALLBACKS, COORDINATOR_MODEL, SPECIALIST_MODEL
    from travel_agent.sub_agents.itinerary_agent import itinerary_agent

    assert itinerary_agent.model.model == COORDINATOR_MODEL
    assert itinerary_agent.model.fallback_models == [*COORDINATOR_FALLBACKS, SPECIALIST_MODEL]
