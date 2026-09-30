"""One clock for the whole backend: naive UTC datetimes.

SQLite returns naive datetimes, so every stored and compared timestamp is naive
UTC to avoid mixing aware and naive values."""

from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def naive(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
