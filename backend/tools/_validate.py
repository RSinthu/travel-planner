"""Input checks shared by the tools. All raise ToolError with a clear message."""

import re
from datetime import date

from ._http import ToolError

_IATA = re.compile(r"^[A-Za-z]{3}$")
_COUNTRY = re.compile(r"^[A-Za-z]{2}$")
_CURRENCY = re.compile(r"^[A-Za-z]{3}$")


def parse_date(value: str, field: str) -> date:
    """Parse a YYYY-MM-DD string."""
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError) as exc:
        raise ToolError(f"{field} must be a date in YYYY-MM-DD format, got '{value}'.") from exc


def not_in_past(day: date, field: str) -> None:
    if day < date.today():
        raise ToolError(f"{field} ({day.isoformat()}) is in the past.")


def date_range(start: str, end: str, start_field: str, end_field: str, *, same_day_ok: bool) -> tuple[date, date]:
    """Parse two dates, check the start is not in the past and the end comes after it."""
    start_day = parse_date(start, start_field)
    end_day = parse_date(end, end_field)
    not_in_past(start_day, start_field)
    if end_day < start_day or (end_day == start_day and not same_day_ok):
        raise ToolError(f"{end_field} must be after {start_field}.")
    return start_day, end_day


def iata_code(value: str, field: str) -> str:
    if not _IATA.match(value.strip()):
        raise ToolError(f"{field} must be a 3-letter IATA airport or city code (e.g. 'CDG'), got '{value}'.")
    return value.strip().upper()


def country_code(value: str, *, required: bool) -> str:
    value = value.strip()
    if not value and not required:
        return ""
    if not _COUNTRY.match(value):
        raise ToolError(f"country_code must be a 2-letter ISO code (e.g. 'FR'), got '{value}'.")
    return value.upper()


def currency_code(value: str) -> str:
    if not _CURRENCY.match(value.strip()):
        raise ToolError(f"currency must be a 3-letter code (e.g. 'USD'), got '{value}'.")
    return value.strip().upper()


def int_between(value: int, low: int, high: int, field: str) -> int:
    if not low <= value <= high:
        raise ToolError(f"{field} must be between {low} and {high}, got {value}.")
    return value


def number_between(value: float, low: float, high: float, field: str) -> float:
    if not low <= value <= high:
        raise ToolError(f"{field} must be between {low} and {high}, got {value}.")
    return value
