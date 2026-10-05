from types import SimpleNamespace

from tests.itinerary_fixtures import good_plan, research_state
from travel_agent.prompts import itinerary_instruction
from travel_agent.sub_agents.itinerary_agent import itinerary_agent
from travel_agent.workflows import FIRST_REQUEST, plan_itinerary


def fake_context(state, *outputs):
    """A ToolContext whose run_node returns the given itinerary-agent outputs in turn."""
    calls = []

    async def run_node(node, node_input=None, **_):
        calls.append({"node": node, "input": node_input})
        output = outputs[len(calls) - 1]
        if isinstance(output, Exception):
            raise output
        return output

    return SimpleNamespace(state=state, run_node=run_node, calls=calls)


async def test_good_plan_accepted_first_time():
    ctx = fake_context(research_state(), good_plan())

    result = await plan_itinerary(ctx)

    assert result["status"] == "success"
    assert result["data"]["attempts"] == 1
    assert result["data"]["unresolved_problems"] == []
    assert result["data"]["estimated_cost"]["estimated_total"] == 610
    assert ctx.calls == [{"node": itinerary_agent, "input": FIRST_REQUEST}]
    assert ctx.state["itinerary"]["hotel"] == "Holiday Inn Rome"
    assert ctx.state["itinerary_review"]["errors"] == []


async def test_bad_plan_is_sent_back_once_with_the_problems():
    ctx = fake_context(research_state(), good_plan(hotel="Hotel Imaginary"), good_plan())

    result = await plan_itinerary(ctx)

    assert result["data"]["attempts"] == 2
    assert result["data"]["unresolved_problems"] == []
    fix_request = ctx.calls[1]["input"]
    assert "Hotel Imaginary' is not in the hotel results" in fix_request
    assert '"hotel":"Hotel Imaginary"' in fix_request  # the earlier plan is included


async def test_problems_left_after_retry_are_reported_not_looped():
    bad = good_plan(hotel="Hotel Imaginary")
    ctx = fake_context(research_state(), bad, bad)

    result = await plan_itinerary(ctx)

    assert len(ctx.calls) == 2
    assert result["status"] == "success"
    assert "Hotel Imaginary" in result["data"]["unresolved_problems"][0]


async def test_json_text_output_is_accepted():
    import json

    ctx = fake_context(research_state(), json.dumps(good_plan()))

    assert (await plan_itinerary(ctx))["status"] == "success"


async def test_invalid_output_twice_is_an_error():
    ctx = fake_context(research_state(), "not json", {"title": "missing fields"})

    result = await plan_itinerary(ctx)

    assert result == {"status": "error", "error_message": "The itinerary planner did not return a valid plan."}


async def test_agent_failure_is_an_error():
    ctx = fake_context(research_state(), RuntimeError("503 UNAVAILABLE"))

    result = await plan_itinerary(ctx)

    assert result["status"] == "error" and "503 UNAVAILABLE" in result["error_message"]


async def test_needs_research_first():
    ctx = fake_context({})

    result = await plan_itinerary(ctx)

    assert result["status"] == "error" and not ctx.calls


def test_itinerary_prompt_contains_the_research():
    prompt = itinerary_instruction(SimpleNamespace(state=research_state()))

    assert "Rome (IT), 2026-10-07 to 2026-10-09, 2 adults, currency EUR" in prompt
    assert "- 2026-10-08: Thunderstorm, 17-23°C, rain likely" in prompt
    assert "- Holiday Inn Rome: 4 stars, rating 8, 125 / 250, non-refundable" in prompt
    assert "- Capitoline Museums | museums | indoor | hours unknown" in prompt
    assert "- Pantheon | sights, unesco, UNESCO | outdoor or mixed | Mo-Su 09:00-19:00" in prompt
