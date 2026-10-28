from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
