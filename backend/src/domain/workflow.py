from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import TypeVar

from src.domain.errors import InvalidStateTransitionError

StatusT = TypeVar("StatusT", bound=Enum)


def ensure_transition(
    current: StatusT,
    target: StatusT,
    transitions: Mapping[StatusT, frozenset[StatusT]],
    label: str,
) -> None:
    """Allow staying in the same state; otherwise require an explicit edge."""
    if target == current:
        return
    if target not in transitions.get(current, frozenset()):
        raise InvalidStateTransitionError(
            f"Không thể chuyển {label} từ '{current.value}' sang '{target.value}'"
        )


def parse_enum(enum_type: type[StatusT], value: str | None, default: StatusT) -> StatusT:
    """Read a stored value tolerantly so legacy rows never break a listing."""
    try:
        return enum_type(value)
    except ValueError:
        return default
