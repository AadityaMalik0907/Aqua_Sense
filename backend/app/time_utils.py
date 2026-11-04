"""Timestamp validation, UTC normalization, and freshness utilities for AquaSense."""

from datetime import datetime, timezone, timedelta
import os
from typing import Any

# Five-minute future timestamp tolerance (configurable via env, defaults to 300 seconds)
FUTURE_TIMESTAMP_TOLERANCE_SECONDS: int = int(
    os.getenv("AQUASENSE_FUTURE_TOLERANCE_SECONDS", 5 * 60)
)

# Device staleness threshold (configurable via env, defaults to 24 hours)
STALE_AFTER_SECONDS: int = int(
    os.getenv("AQUASENSE_STALE_SECONDS", 24 * 60 * 60)
)

# Reading staleness threshold (configurable via env, defaults to 24 hours)
READING_STALE_AFTER_SECONDS: int = int(
    os.getenv("AQUASENSE_READING_STALE_SECONDS", 24 * 60 * 60)
)


def get_current_utc_time() -> datetime:
    """Return the current system time in UTC with timezone awareness.
    
    Supports an optional AQUASENSE_REFERENCE_TIME environment variable for
    deterministic test environments and historical dataset replays.
    """
    ref = os.getenv("AQUASENSE_REFERENCE_TIME")
    if ref:
        return parse_and_normalize_timestamp(ref)
    return datetime.now(timezone.utc)


def parse_and_normalize_timestamp(
    value: str | datetime,
) -> datetime:
    """Parse an input timestamp and normalize it to a timezone-aware UTC datetime.
    
    Rules:
    - Timezone-aware datetimes/strings are converted directly to UTC.
    - Naive timestamps are strictly rejected with ValueError to prevent silent
      misinterpretation of local times as UTC.
    
    Raises:
        ValueError: If value is an unparseable format or is timezone-naive.
    """
    if isinstance(value, str):
        normalized_str = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized_str)
        except ValueError as exc:
            raise ValueError(f"Malformed ISO timestamp string: {value}") from exc
    elif isinstance(value, datetime):
        dt = value
    else:
        raise ValueError(f"Expected str or datetime, received {type(value).__name__}")

    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(
            f"Timezone offset is required; timezone-naive timestamp '{value}' is not permitted."
        )

    # Convert to UTC representation
    return dt.astimezone(timezone.utc)


def validate_not_future(
    dt: datetime,
    tolerance_seconds: int = FUTURE_TIMESTAMP_TOLERANCE_SECONDS,
    reference_time: datetime | None = None,
) -> datetime:
    """Ensure a UTC datetime is not beyond the allowable future tolerance window.
    
    Raises:
        ValueError: If dt is ahead of (reference_time + tolerance_seconds).
    """
    now_utc = reference_time or get_current_utc_time()
    diff_seconds = (dt - now_utc).total_seconds()
    if diff_seconds > tolerance_seconds:
        raise ValueError(
            f"Timestamp {dt.isoformat()} is {int(diff_seconds)}s in the future, "
            f"exceeding the allowed tolerance of {tolerance_seconds}s."
        )
    return dt


def is_timestamp_stale(
    dt: datetime,
    stale_threshold_seconds: int = STALE_AFTER_SECONDS,
    reference_time: datetime | None = None,
) -> bool:
    """Determine whether a normalized UTC timestamp exceeds the staleness window."""
    now_utc = reference_time or get_current_utc_time()
    age_seconds = (now_utc - dt).total_seconds()
    return age_seconds > stale_threshold_seconds
