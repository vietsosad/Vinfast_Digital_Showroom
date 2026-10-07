from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.services.support_chat import (
    ChatActor,
    ChatForbiddenError,
    ChatValidationError,
    Conversation,
    SupportChatService,
)


class FakeRepository:
    def __init__(self):
        self.conversations = {}

    async def create_conversation(self, customer_id, subject):
        now = datetime.now(timezone.utc)
        conversation = Conversation(uuid4(), customer_id, None, subject, "open", now, now)
        self.conversations[conversation.conversation_id] = conversation
        return conversation

    async def get_conversation(self, conversation_id):
        return self.conversations.get(conversation_id)

    async def list_for_customer(self, customer_id):
        return [item for item in self.conversations.values() if item.customer_id == customer_id]

    async def list_for_staff(self):
        return list(self.conversations.values())


@pytest.mark.asyncio
async def test_only_customer_can_open_conversation():
    service = SupportChatService(FakeRepository())
    with pytest.raises(ChatForbiddenError):
        await service.create_conversation(ChatActor(uuid4(), "consultant"), "Cần hỗ trợ")


@pytest.mark.asyncio
async def test_subject_is_validated_in_business_layer():
    service = SupportChatService(FakeRepository())
    with pytest.raises(ChatValidationError):
        await service.create_conversation(ChatActor(uuid4(), "customer"), "x")


@pytest.mark.asyncio
async def test_customer_only_lists_own_conversations():
    repository = FakeRepository()
    service = SupportChatService(repository)
    first = ChatActor(uuid4(), "customer")
    second = ChatActor(uuid4(), "customer")
    await service.create_conversation(first, "Hỗ trợ xe VF 6")
    await service.create_conversation(second, "Hỗ trợ xe VF 8")
    result = await service.list_conversations(first)
    assert len(result) == 1
    assert result[0].customer_id == first.user_id
