"""Callbacks that keep the latest trip data in session state.

Agents talk to each other in short text summaries, but the raw tool data is
saved in state too, so later steps (itinerary, frontend) can use exact numbers:

    trip_request    the TripRequest the coordinator last sent to a specialist
    weather         get_weather_forecast data
    hotels          search_hotels data
    hotels_nearby   find_hotels_near data
    attractions     find_attractions data

A failed tool call stores {"error": ...}, so an old trip's data never lingers.
"""

from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

TOOL_STATE_KEYS = {
    "get_weather_forecast": "weather",
    "search_hotels": "hotels",
    "find_hotels_near": "hotels_nearby",
    "find_attractions": "attractions",
}

SPECIALIST_NAMES = {"weather_agent", "hotel_agent", "places_agent"}


def save_tool_data(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: Any
) -> None:
    """after_tool_callback for specialists: copy the tool's data into state."""
    key = TOOL_STATE_KEYS.get(tool.name)
    if not key or not isinstance(tool_response, dict):
        return None
    if tool_response.get("status") == "success":
        value = dict(tool_response.get("data") or {})
        if tool_response.get("note"):
            value["note"] = tool_response["note"]
    else:
        value = {"error": tool_response.get("error_message", "unknown error")}
    tool_context.state[key] = value
    return None  # keep the tool's response unchanged


def limit_specialist_calls(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> dict | None:
    """before_tool_callback for the coordinator: each specialist at most once per user message.

    Every specialist call costs several Gemini requests, and the free tier allows
    only about 20 a day per model, so a retry loop would burn it in one message.
    """
    if tool.name not in SPECIALIST_NAMES:
        return None
    calls = tool_context.state.get("temp:specialist_calls") or {}
    called = calls.get("names", []) if calls.get("invocation") == tool_context.invocation_id else []
    if tool.name in called:
        return {
            "error": f"{tool.name} was already called for this message. "
            "Use its earlier answer; if it was empty or failed, tell the user that part is unavailable."
        }
    tool_context.state["temp:specialist_calls"] = {
        "invocation": tool_context.invocation_id,
        "names": [*called, tool.name],
    }
    return None


def remember_trip_request(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: Any
) -> None:
    """after_tool_callback for the coordinator: store the trip it sent to a specialist."""
    if tool.name in SPECIALIST_NAMES:
        tool_context.state["trip_request"] = dict(args)
    return None
