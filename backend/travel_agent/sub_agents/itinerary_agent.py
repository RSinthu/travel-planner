"""Itinerary agent - no tools, structured output.

Not a sub-agent of the coordinator: it is run by the plan_itinerary tool
(travel_agent/workflows.py), which checks its plan and asks for one fix.
It reads the research from session state through its instruction.
"""

from google.adk.agents import Agent

from ..models import COORDINATOR_MODEL, gemini
from ..prompts import itinerary_instruction
from ..schemas import Itinerary

itinerary_agent = Agent(
    name="itinerary_agent",
    model=gemini(COORDINATOR_MODEL),  # planning needs the stronger model
    mode="single_turn",
    description="Turns the trip research into a day-by-day itinerary.",
    instruction=itinerary_instruction,
    output_schema=Itinerary,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)
