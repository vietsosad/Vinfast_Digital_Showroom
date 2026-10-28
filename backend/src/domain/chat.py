from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol
from uuid import UUID


class ConversationStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True)
class Conversation:
    conversation_id: UUID
    customer_id: UUID
    assigned_staff_id: UUID | None
    subject: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    customer_name: str | None = None
    assigned_staff_name: str | None = None


@dataclass(frozen=True)
class Message:
    message_id: UUID
    conversation_id: UUID
    sender_id: UUID
    content: str
    sent_at: datetime
    sender_name: str | None = None
    sender_role: str | None = None


class ConversationRepository(Protocol):
    async def create_conversation(self, customer_id: UUID, subject: str) -> Conversation: ...

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None: ...

    async def list_for_customer(self, customer_id: UUID) -> list[Conversation]: ...

    async def list_for_staff(self) -> list[Conversation]: ...

    async def assign_staff(self, conversation_id: UUID, staff_id: UUID) -> Conversation: ...

    async def close_conversation(self, conversation_id: UUID) -> Conversation: ...

    async def delete_conversation(self, conversation_id: UUID) -> None: ...

    async def list_messages(self, conversation_id: UUID) -> list[Message]: ...

    async def create_message(self, conversation_id: UUID, sender_id: UUID, content: str) -> Message: ...
