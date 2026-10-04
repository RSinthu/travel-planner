"""Gemini models used by the agents.

Two tiers: the coordinator talks to the user and reasons about the whole trip,
so it gets the stronger model; specialists only call one tool and summarise,
so they get the cheaper, faster one. Both are pinned versions so behaviour does
not change silently; override them in .env.
"""

import os

from google.adk.models.google_llm import Gemini
from google.genai import types

COORDINATOR_MODEL = os.getenv("TRAVEL_AGENT_MODEL", "").strip() or "gemini-3.5-flash"
SPECIALIST_MODEL = os.getenv("TRAVEL_SPECIALIST_MODEL", "").strip() or "gemini-3.5-flash-lite"

# Gemini sometimes answers 429/503 ("high demand"). Retry with backoff:
# waits of about 2, 4 and 8 seconds before giving up.
RETRY = types.HttpRetryOptions(attempts=4, initial_delay=2, max_delay=16)


def gemini(model: str) -> Gemini:
    return Gemini(model=model, retry_options=RETRY)
