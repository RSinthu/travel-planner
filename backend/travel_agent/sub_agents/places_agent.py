"""Sightseeing specialist - uses tools/places.py."""

from tools import find_attractions

from ..prompts import places_instruction
from ._specialist import specialist

places_agent = specialist(
    name="places_agent",
    description="Finds sights, museums and other things to do in the trip's city, matched to the travellers' interests.",
    instruction=places_instruction,
    tools=[find_attractions],
)
