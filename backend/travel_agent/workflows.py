"""The plan -> review -> fix loop, exposed to the coordinator as the plan_itinerary tool.

The loop is code, not an LLM decision, so the review always runs and the
itinerary agent gets at most one retry (each attempt costs a Gemini request).
"""

import json
import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel, ValidationError

from .review import review_itinerary
from .schemas import Itinerary
from .sub_agents.itinerary_agent import itinerary_agent

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
FIRST_REQUEST = "Plan the trip."


async def plan_itinerary(tool_context: ToolContext) -> dict:
    """Build the day-by-day itinerary from the research gathered for the current trip, then check it.

    Call this once, after weather_agent, hotel_agent and places_agent have answered.

    Returns:
        On success: {"status": "success", "data": {"itinerary": {...}, "estimated_cost": {...},
        "warnings": [...], "unresolved_problems": [...], "attempts": int}}.
        On failure: {"status": "error", "error_message": "..."}.
    """
    state = tool_context.state
    if not state.get("trip_request"):
        return {"status": "error", "error_message": "No trip researched yet. Call the specialists first."}

    request = FIRST_REQUEST
    itinerary: Itinerary | None = None
    review: dict = {}
    attempt = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            output = await tool_context.run_node(itinerary_agent, node_input=request)
            candidate = Itinerary.model_validate(_as_dict(output))
        except (ValidationError, ValueError) as exc:  # ValueError: not JSON at all
            logger.warning("Itinerary attempt %d did not match the schema: %s", attempt, exc)
            continue
        except Exception as exc:  # model or framework failure: stop, the coordinator falls back
            logger.exception("Itinerary agent failed")
            return {"status": "error", "error_message": f"The itinerary planner failed: {exc}"}

        itinerary, review = candidate, review_itinerary(candidate, state)
        if not review["errors"]:
            break
        request = _fix_request(itinerary, review["errors"])

    if itinerary is None:
        return {"status": "error", "error_message": "The itinerary planner did not return a valid plan."}

    plan = itinerary.model_dump()
    tool_context.state["itinerary"] = plan
    tool_context.state["itinerary_review"] = review
    return {
        "status": "success",
        "data": {
            "itinerary": plan,
            "estimated_cost": review["cost"],
            "warnings": review["warnings"],
            "unresolved_problems": review["errors"],
            "attempts": attempt,
        },
    }


def _as_dict(output: Any) -> Any:
    if isinstance(output, BaseModel):
        return output.model_dump()
    if isinstance(output, str):
        return json.loads(output)
    return output


def _fix_request(itinerary: Itinerary, errors: list[str]) -> str:
    problems = "\n".join(f"- {error}" for error in errors)
    return (
        "Your earlier plan has these problems:\n"
        f"{problems}\n\n"
        "Fix all of them and keep everything else the same. Earlier plan:\n"
        f"{itinerary.model_dump_json()}"
    )
