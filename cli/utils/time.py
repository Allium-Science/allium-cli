from datetime import UTC, datetime, timedelta

RANGE_START_TIMESTAMP_HELP = (
    "Range start; e.g. 2026-03-21T00:00:00Z (ISO 8601, Z) or Unix epoch seconds. "
    "Default: 30 days ago (UTC)."
)
RANGE_END_TIMESTAMP_HELP = (
    "Range end; e.g. 2026-03-21T23:59:59Z (ISO 8601, Z) or Unix epoch seconds. "
    "Default: now (UTC)."
)


def default_range_start_timestamp_utc() -> str:
    dt = datetime.now(UTC) - timedelta(days=30)
    return dt.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_range_end_timestamp_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
