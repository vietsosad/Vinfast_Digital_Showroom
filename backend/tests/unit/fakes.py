"""In-memory doubles: business rules are tested without FastAPI or a database."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.chat import Conversation, ConversationStatus, Message
from src.domain.media import MediaRecord


class FakeUnitOfWork:
    def __init__(self, **repositories):
        self.commits = 0
        self.rollbacks = 0
        for name, repository in repositories.items():
            setattr(self, name, repository)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class InMemoryConversationRepository:
    def __init__(self):
        self.conversations: dict = {}
        self.messages: list[Message] = []

    async def create_conversation(self, customer_id, subject):
        now = datetime.now(timezone.utc)
        conversation = Conversation(uuid4(), customer_id, None, subject, ConversationStatus.OPEN, now, now)
        self.conversations[conversation.conversation_id] = conversation
        return conversation

    async def get_conversation(self, conversation_id):
        return self.conversations.get(conversation_id)

    async def list_for_customer(self, customer_id):
        return [item for item in self.conversations.values() if item.customer_id == customer_id]

    async def list_for_staff(self):
        return list(self.conversations.values())

    async def assign_staff(self, conversation_id, staff_id):
        updated = replace(self.conversations[conversation_id], assigned_staff_id=staff_id)
        self.conversations[conversation_id] = updated
        return updated

    async def close_conversation(self, conversation_id):
        updated = replace(self.conversations[conversation_id], status=ConversationStatus.CLOSED)
        self.conversations[conversation_id] = updated
        return updated

    async def delete_conversation(self, conversation_id):
        self.conversations.pop(conversation_id, None)

    async def list_messages(self, conversation_id):
        return [message for message in self.messages if message.conversation_id == conversation_id]

    async def create_message(self, conversation_id, sender_id, content):
        message = Message(uuid4(), conversation_id, sender_id, content, datetime.now(timezone.utc))
        self.messages.append(message)
        return message


class InMemoryMediaRepository:
    def __init__(self, *, vehicle_exists: bool = True, fail_on_create: bool = False):
        self.exists = vehicle_exists
        self.fail_on_create = fail_on_create
        self.records: list[MediaRecord] = []

    async def vehicle_exists(self, vehicle_type, vehicle_id):
        return self.exists

    async def list_media(self, vehicle_type, vehicle_id):
        return list(self.records)

    async def create_media(self, vehicle_type, vehicle_id, drafts):
        if self.fail_on_create:
            raise RuntimeError("database unavailable")
        created = [
            MediaRecord(**draft.__dict__, media_id=uuid4(), vehicle_type=vehicle_type, vehicle_id=vehicle_id)
            for draft in drafts
        ]
        self.records.extend(created)
        return created

    async def update_media(self, media_id, changes):
        return None

    async def delete_media(self, media_id):
        return False


class InMemoryFileStorage:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    def save(self, folder, filename, content):
        url = f"/static/{folder}/{filename}"
        self.files[url] = content
        return url

    def delete(self, url):
        self.files.pop(url, None)
