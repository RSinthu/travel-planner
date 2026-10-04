from datetime import date
from types import SimpleNamespace

from google.adk.flows.llm_flows.extensions._agent_transfer import _get_transfer_targets

from travel_agent.agent import root_agent
from travel_agent.callbacks import limit_specialist_calls, remember_trip_request, save_tool_data
from travel_agent.prompts import coordinator_instruction
from travel_agent.schemas import TripRequest

SPECIALIST_TOOLS = {
    "weather_agent": {"get_weather_forecast"},
    "hotel_agent": {"search_hotels", "find_hotels_near"},
    "places_agent": {"find_attractions"},
}


def tool(name):
    return SimpleNamespace(name=name)


def context(invocation="inv-1"):
    return SimpleNamespace(state={}, invocation_id=invocation)


def test_coordinator_has_three_single_turn_specialists():
    assert root_agent.name == "travel_coordinator"
    specialists = {agent.name: agent for agent in root_agent.sub_agents}
    assert set(specialists) == set(SPECIALIST_TOOLS)
    for name, agent in specialists.items():
        assert agent.mode == "single_turn"
        assert agent.input_schema is TripRequest
        assert {t.__name__ for t in agent.tools} == SPECIALIST_TOOLS[name]


def test_specialists_cannot_transfer_away():
    # Regression: places_agent once called transfer_to_agent instead of answering,
    # which made the coordinator call all three specialists again.
    for agent in root_agent.sub_agents:
        assert _get_transfer_targets(agent) == []


def test_coordinator_instruction_contains_todays_date():
    assert date.today().isoformat() in coordinator_instruction(None)


def test_save_tool_data_stores_data_and_note():
    ctx = context()
    response = {"status": "success", "data": {"nights": 3, "hotels": []}, "note": "sandbox"}

    assert save_tool_data(tool("search_hotels"), {}, ctx, response) is None
    assert ctx.state == {"hotels": {"nights": 3, "hotels": [], "note": "sandbox"}}


def test_save_tool_data_replaces_old_data_with_error():
    ctx = context()
    ctx.state["weather"] = {"days": ["old trip"]}

    save_tool_data(tool("get_weather_forecast"), {}, ctx, {"status": "error", "error_message": "too far ahead"})

    assert ctx.state["weather"] == {"error": "too far ahead"}


def test_save_tool_data_ignores_other_tools():
    ctx = context()
    save_tool_data(tool("transfer_to_agent"), {}, ctx, {"status": "success", "data": {}})
    assert ctx.state == {}


def test_each_specialist_called_once_per_message():
    ctx = context("inv-1")

    assert limit_specialist_calls(tool("hotel_agent"), {}, ctx) is None
    assert limit_specialist_calls(tool("weather_agent"), {}, ctx) is None
    blocked = limit_specialist_calls(tool("hotel_agent"), {}, ctx)
    assert "already called" in blocked["error"]

    ctx.invocation_id = "inv-2"  # next user message
    assert limit_specialist_calls(tool("hotel_agent"), {}, ctx) is None


def test_call_limit_ignores_non_specialist_tools():
    ctx = context()
    assert limit_specialist_calls(tool("transfer_to_agent"), {}, ctx) is None
    assert limit_specialist_calls(tool("transfer_to_agent"), {}, ctx) is None


def test_remember_trip_request():
    ctx = context()
    request = {"city": "Rome", "country_code": "IT", "start_date": "2026-10-07", "end_date": "2026-10-10"}

    remember_trip_request(tool("places_agent"), request, ctx, "some answer")

    assert ctx.state["trip_request"] == request
