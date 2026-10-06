"""Shared HTTP helper and result format used by every tool."""

import asyncio
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15.0
RETRY_STATUSES = {429, 500, 502, 503, 504}
_sleep = asyncio.sleep  # the tests replace this to skip retry waits

_SECRET_PARAM = re.compile(r"(?i)\b(api_?key|key|token|access_token)=[^&\s\"']+")


class _RedactSecrets(logging.Filter):
    """httpx logs every request URL at INFO level. Some APIs (Geoapify) take the
    key as a URL parameter, so hide its value before the line is written."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = _SECRET_PARAM.sub(r"\1=REDACTED", message)
        if redacted != message:
            record.msg, record.args = redacted, ()
        return True


logging.getLogger("httpx").addFilter(_RedactSecrets())


class ToolError(Exception):
    """An expected failure whose message is safe to show to the agent."""


def ok(data: Any, **extra: Any) -> dict:
    """Successful tool result."""
    return {"status": "success", "data": data, **extra}


def error(message: str) -> dict:
    """Failed tool result. The agent reads error_message and can tell the user."""
    return {"status": "error", "error_message": message}


def require_env(name: str) -> str:
    """Read a required setting (usually an API key) from the environment."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ToolError(f"{name} is not set. Add it to backend/.env.")
    return value


def _error_detail(response: httpx.Response) -> str:
    """Pull a short, human-readable message out of an API error response."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict):
        errors = body.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            return str(errors[0].get("message") or errors[0].get("title") or "")[:200]
        err = body.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("description") or "")[:200]
        if isinstance(err, str):
            return err[:200]
        if "message" in body:
            return str(body["message"])[:200]
        if "reason" in body:
            return str(body["reason"])[:200]
    return ""


async def request_json(
    method: str,
    url: str,
    *,
    service: str,
    params: dict | None = None,
    json: dict | None = None,
    headers: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = 2,
) -> Any:
    """Call an API and return the decoded JSON.

    Retries timeouts, network errors, rate limits (429) and server errors (5xx)
    with exponential backoff. Other errors fail immediately. Raises ToolError
    with a message that never contains URLs or API keys.
    """
    last_problem = "unknown error"
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method, url, params=params, json=json, headers=headers
                )
        except httpx.TimeoutException:
            last_problem = "the request timed out"
        except httpx.HTTPError as exc:
            last_problem = f"a network error occurred ({type(exc).__name__})"
        else:
            if response.status_code < 400:
                try:
                    return response.json()
                except ValueError as exc:
                    raise ToolError(f"{service} returned an unreadable response.") from exc
            detail = _error_detail(response)
            if response.status_code not in RETRY_STATUSES:
                message = f"{service} rejected the request (HTTP {response.status_code})"
                raise ToolError(f"{message}: {detail}" if detail else f"{message}.")
            last_problem = f"it returned HTTP {response.status_code}"

        if attempt < retries:
            logger.warning("%s call failed (%s), retrying", service, last_problem)
            await _sleep(0.5 * 2**attempt)

    raise ToolError(f"{service} is unavailable right now: {last_problem}.")
