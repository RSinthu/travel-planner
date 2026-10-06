"""Root agent, exposed as root_agent for `adk web`.

travel_coordinator chats with the user and calls three single-turn specialist
sub-agents. ADK turns each single_turn sub-agent into a tool on the coordinator,
so the coordinator keeps the conversation and can call all three at once.
Then plan_itinerary turns their research into a checked day-by-day plan.
"""

from google.adk.agents import Agent

from .callbacks import limit_repeat_calls, remember_trip_request
from .models import coordinator_model
from .prompts import coordinator_instruction
from .sub_agents import hotel_agent, places_agent, weather_agent
from .workflows import plan_itinerary

root_agent = Agent(
    name="travel_coordinator",
    model=coordinator_model(),
    description="Plans trips: talks with the traveller, gathers weather, hotels and things to do, and builds a day-by-day plan.",
    instruction=coordinator_instruction,
    tools=[plan_itinerary],
    sub_agents=[weather_agent, hotel_agent, places_agent],
    before_tool_callback=limit_repeat_calls,
    after_tool_callback=remember_trip_request,
)
