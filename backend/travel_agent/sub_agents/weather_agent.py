"""Weather specialist - uses tools/weather.py."""

from tools import get_weather_forecast

from ..prompts import weather_instruction
from ._specialist import specialist

weather_agent = specialist(
    name="weather_agent",
    description="Gets the daily weather forecast for the trip's city and dates.",
    instruction=weather_instruction,
    tools=[get_weather_forecast],
)
