"""Shared storage helpers."""

from datetime import UTC, datetime

SNAPSHOTS_DIRNAME = "snapshots"


def timestamp_for_snapshot() -> str:
    """Return a UTC timestamp suitable for snapshot filenames."""

    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
