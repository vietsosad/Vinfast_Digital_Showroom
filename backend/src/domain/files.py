from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class UploadedFile:
    """Transport-neutral representation of a file received by an adapter."""

    filename: str
    content_type: str | None
    content: bytes = field(repr=False)


class FileStorage(Protocol):
    def save(self, folder: str, filename: str, content: bytes) -> str:
        """Persist content and return its public URL."""
        ...

    def delete(self, url: str) -> None:
        """Remove a file previously returned by ``save``; missing files are ignored."""
        ...
