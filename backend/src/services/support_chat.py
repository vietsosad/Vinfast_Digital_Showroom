"""Business rules for customer-to-staff support conversations.

This module deliberately imports neither FastAPI nor SQLAlchemy. Persistence is
provided through the repository protocol so the rules can be unit-tested in
memory and reused by another transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ChatActor:
    user_id: UUID
    role: str


@dataclass(frozen=True)
class Conversation:
    conversation_id: UUID
    customer_id: UUID
    assigned_staff_id: UUID | None
    subject: str
    status: str
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


class ChatError(Exception):
    pass


class ChatNotFoundError(ChatError):
    pass


class ChatForbiddenError(ChatError):
    pass


class ChatValidationError(ChatError):
    pass


class SupportChatService:
    STAFF_ROLES = {"consultant", "admin"}

    def __init__(self, repository: ConversationRepository):
        self.repository = repository

    async def create_conversation(self, actor: ChatActor, subject: str) -> Conversation:
        if actor.role != "customer":
            raise ChatForbiddenError("Chỉ khách hàng có thể mở cuộc hội thoại hỗ trợ")
        cleaned = " ".join(subject.split())
        if not 3 <= len(cleaned) <= 160:
            raise ChatValidationError("Chủ đề phải có từ 3 đến 160 ký tự")
        return await self.repository.create_conversation(actor.user_id, cleaned)

    async def list_conversations(self, actor: ChatActor) -> list[Conversation]:
        if actor.role == "customer":
            return await self.repository.list_for_customer(actor.user_id)
        if actor.role in self.STAFF_ROLES:
            return await self.repository.list_for_staff()
        raise ChatForbiddenError("Vai trò không được phép truy cập hội thoại")

    async def get_conversation(self, actor: ChatActor, conversation_id: UUID) -> Conversation:
        conversation = await self.repository.get_conversation(conversation_id)
        if conversation is None:
            raise ChatNotFoundError("Không tìm thấy hội thoại")
        self._ensure_access(actor, conversation)
        return conversation

    async def list_messages(self, actor: ChatActor, conversation_id: UUID) -> list[Message]:
        await self.get_conversation(actor, conversation_id)
        return await self.repository.list_messages(conversation_id)

    async def send_message(self, actor: ChatActor, conversation_id: UUID, content: str) -> Message:
        conversation = await self.get_conversation(actor, conversation_id)
        if conversation.status != "open":
            raise ChatValidationError("Hội thoại đã đóng")
        if actor.role == "consultant" and conversation.assigned_staff_id != actor.user_id:
            raise ChatForbiddenError("Nhân viên cần nhận hội thoại trước khi trả lời")
        cleaned = content.strip()
        if not cleaned:
            raise ChatValidationError("Nội dung tin nhắn không được để trống")
        if len(cleaned) > 2_000:
            raise ChatValidationError("Tin nhắn không được vượt quá 2.000 ký tự")
        return await self.repository.create_message(conversation_id, actor.user_id, cleaned)

    async def assign_to_me(self, actor: ChatActor, conversation_id: UUID) -> Conversation:
        if actor.role not in self.STAFF_ROLES:
            raise ChatForbiddenError("Chỉ nhân viên có thể nhận hội thoại")
        conversation = await self.get_conversation(actor, conversation_id)
        if conversation.status != "open":
            raise ChatValidationError("Không thể nhận hội thoại đã đóng")
        if conversation.assigned_staff_id not in (None, actor.user_id) and actor.role != "admin":
            raise ChatForbiddenError("Hội thoại đã được nhân viên khác tiếp nhận")
        return await self.repository.assign_staff(conversation_id, actor.user_id)

    async def close(self, actor: ChatActor, conversation_id: UUID) -> Conversation:
        conversation = await self.get_conversation(actor, conversation_id)
        if actor.role == "consultant" and conversation.assigned_staff_id != actor.user_id:
            raise ChatForbiddenError("Chỉ nhân viên đang phụ trách mới có thể đóng hội thoại")
        return await self.repository.close_conversation(conversation.conversation_id)

    async def delete(self, actor: ChatActor, conversation_id: UUID) -> None:
        conversation = await self.get_conversation(actor, conversation_id)
        if actor.role != "admin" and conversation.customer_id != actor.user_id:
            raise ChatForbiddenError("Chỉ khách hàng sở hữu hoặc quản trị viên có thể xóa hội thoại")
        await self.repository.delete_conversation(conversation_id)

    def _ensure_access(self, actor: ChatActor, conversation: Conversation) -> None:
        if actor.role == "customer" and conversation.customer_id != actor.user_id:
            raise ChatForbiddenError("Bạn không có quyền truy cập hội thoại này")
        if actor.role not in self.STAFF_ROLES and actor.role != "customer":
            raise ChatForbiddenError("Vai trò không được phép truy cập hội thoại")
