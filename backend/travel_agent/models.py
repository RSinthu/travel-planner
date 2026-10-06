"""Gemini models used by the agents.

Two tiers: the coordinator talks to the user and reasons about the whole trip,
so it gets the stronger model; specialists only call one tool and summarise,
so they get the cheaper, faster one. Both are pinned versions so behaviour does
not change silently; override them in .env.

Each tier also has fallback models. Gemini regularly answers 503 "high demand"
(and 429 when a model's free quota is used up); after the retries, the request
moves to the next model instead of failing the user's message.
"""

import logging
import os
from collections.abc import AsyncGenerator

from google.adk.models.google_llm import Gemini
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import Field

logger = logging.getLogger(__name__)


def _models(env: str, default: str) -> list[str]:
    return [m.strip() for m in (os.getenv(env, "").strip() or default).split(",") if m.strip()]


COORDINATOR_MODEL = os.getenv("TRAVEL_AGENT_MODEL", "").strip() or "gemini-3.5-flash"
SPECIALIST_MODEL = os.getenv("TRAVEL_SPECIALIST_MODEL", "").strip() or "gemini-3.5-flash-lite"
COORDINATOR_FALLBACKS = _models("TRAVEL_AGENT_FALLBACK_MODELS", "gemini-3.8-flash,gemini-3.6-flash")
SPECIALIST_FALLBACKS = _models("TRAVEL_SPECIALIST_FALLBACK_MODELS", "gemini-3.1-flash-lite")

# Retry each model once (after about 2 seconds) before falling back to the next one.
RETRY = types.HttpRetryOptions(attempts=2, initial_delay=2, max_delay=8)

FALLBACK_STATUSES = {429, 500, 502, 503, 504}


def _status(exc: BaseException) -> int | None:
    seen = 0
    while exc is not None and seen < 10:
        code = getattr(exc, "code", None)
        if isinstance(code, int):
            return code
        exc, seen = exc.__cause__ or exc.__context__, seen + 1
    return None


class FallbackGemini(Gemini):
    """Gemini that moves to the next model when one is overloaded or out of quota."""

    fallback_models: list[str] = Field(default_factory=list)

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        primary = llm_request.model or self.model
        candidates = [primary, *[m for m in self.fallback_models if m != primary]]
        for index, model in enumerate(candidates):
            llm_request.model = model
            sent_output = False
            try:
                async for response in super().generate_content_async(llm_request, stream):
                    sent_output = True
                    yield response
                return
            except Exception as exc:
                is_last = index == len(candidates) - 1
                if is_last or sent_output or _status(exc) not in FALLBACK_STATUSES:
                    raise
                logger.warning("%s failed (%s); falling back to %s", model, _status(exc), candidates[index + 1])


def gemini(model: str, fallbacks: list[str] | None = None) -> FallbackGemini:
    return FallbackGemini(model=model, retry_options=RETRY, fallback_models=fallbacks or [])


def coordinator_model() -> FallbackGemini:
    return gemini(COORDINATOR_MODEL, COORDINATOR_FALLBACKS)


def specialist_model() -> FallbackGemini:
    return gemini(SPECIALIST_MODEL, SPECIALIST_FALLBACKS)


def planner_model() -> FallbackGemini:
    """Coordinator models, then the lighter specialist model as a last resort.

    A plan from the lighter model is still safe to show: review.py checks every
    plan in code (dates, places, hotel, budget) whichever model wrote it.
    """
    return gemini(COORDINATOR_MODEL, [*COORDINATOR_FALLBACKS, SPECIALIST_MODEL])
