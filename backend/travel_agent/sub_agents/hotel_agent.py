"""Hotel specialist - uses tools/hotels.py."""

from tools import find_hotels_near, search_hotels

from ..prompts import hotel_instruction
from ._specialist import specialist

hotel_agent = specialist(
    name="hotel_agent",
    description="Finds available hotels with prices for the trip's city, dates, guests and budget.",
    instruction=hotel_instruction,
    tools=[search_hotels, find_hotels_near],
)
