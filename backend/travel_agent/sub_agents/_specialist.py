"""Shared setup for the specialist sub-agents."""

from typing import Callable

from google.adk.agents import Agent

from ..callbacks import save_tool_data
from ..models import specialist_model
from ..schemas import TripRequest


def specialist(name: str, description: str, instruction: Callable, tools: list) -> Agent:
    """A single-turn sub-agent: takes a TripRequest, calls its tools, replies once.

    ADK hides the transfer instructions from single-turn agents but still offers
    them a transfer_to_agent tool back to the parent. If they use it, their reply
    is empty and the coordinator calls them again, so transfers are disabled.
    """
    return Agent(
        name=name,
        model=specialist_model(),
        mode="single_turn",
        description=description,
        instruction=instruction,
        input_schema=TripRequest,
        tools=tools,
        after_tool_callback=save_tool_data,
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
