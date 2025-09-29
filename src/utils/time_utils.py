"""Timezone-aware time utilities for consistent temporal context.

Provides helpers to compute an aware "now" and formatted date/time strings
using the configured timezone. Also exposes a concise system message that can
be injected into model contexts so relative phrases like "yesterday" resolve
correctly.
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime

import pytz

from src.config.settings import settings


def _get_timezone():
    """Return a pytz timezone object from settings or default to UTC."""
    tz_name = getattr(settings, "TIMEZONE", None) or "UTC"
    try:
        return pytz.timezone(tz_name)
    except Exception:
        return pytz.UTC


def get_now() -> datetime:
    """Get the current aware datetime in the configured timezone.

    If FIXED_NOW_ISO is provided in settings, parse and use it for deterministic
    behavior in tests/demos. If the parsed value is naive, localize it to the
    configured timezone.
    """
    tz = _get_timezone()

    fixed_iso: Optional[str] = getattr(settings, "FIXED_NOW_ISO", None)
    if fixed_iso:
        try:
            parsed = datetime.fromisoformat(fixed_iso)
            if parsed.tzinfo is None:
                return tz.localize(parsed)
            # Convert to configured timezone
            return parsed.astimezone(tz)
        except Exception:
            pass

    # Default to current time in configured timezone
    return datetime.now(tz)


def get_today_date_str() -> str:
    """Return today's date as YYYY-MM-DD in the configured timezone."""
    now = get_now()
    return now.strftime("%Y-%m-%d")


def get_time_str_hhmm() -> str:
    """Return current time as HH:MM (24-hour) in the configured timezone."""
    now = get_now()
    return now.strftime("%H:%M")


def get_tz_abbreviation() -> str:
    """Return the timezone abbreviation (e.g., EDT) for the configured timezone."""
    now = get_now()
    return now.strftime("%Z") or "UTC"


def create_temporal_context_system_message() -> str:
    """Create a concise system message with the current temporal context.

    Example: "Temporal context: Today is 2025-09-25 (Thu) at 15:42 EDT; timezone: America/New_York. Interpret relative dates like 'yesterday' using this context."
    """
    tz_name = getattr(settings, "TIMEZONE", None) or "UTC"
    now = get_now()
    today = now.strftime("%Y-%m-%d")
    dow = now.strftime("%a")
    time_hhmm = now.strftime("%H:%M")
    tz_abbr = now.strftime("%Z") or "UTC"
    return (
        f"Temporal context: Today is {today} ({dow}) at {time_hhmm} {tz_abbr}; "
        f"timezone: {tz_name}. Interpret relative dates like 'yesterday' using this context."
    )


