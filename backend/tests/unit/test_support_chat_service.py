from uuid import uuid4

import pytest

from src.application.support_chat import SupportChatService
from src.domain.errors import NotFoundError, PermissionDeniedError, ValidationError
from src.domain.identity import Actor, Role
from tests.unit.fakes import FakeUnitOfWork, InMemoryConversationRepository


def make_service():
    uow = FakeUnitOfWork(conversations=InMemoryConversationRepository())
    return SupportChatService(uow), uow


def customer():
    return Actor(uuid4(), Role.CUSTOMER)


async def test_only_customer_can_open_conversation():
    service, uow = make_service()
    with pytest.raises(PermissionDeniedError):
        await service.create_conversation(Actor(uuid4(), Role.CONSULTANT), "Cần hỗ trợ")
    assert uow.commits == 0


async def test_subject_is_validated_and_creation_commits_once():
    service, uow = make_service()
    with pytest.raises(ValidationError):
        await service.create_conversation(customer(), "x")
    conversation = await service.create_conversation(customer(), "  Hỗ trợ   xe VF 6 ")
    assert conversation.subject == "Hỗ trợ xe VF 6"
    assert uow.commits == 1


async def test_customer_only_lists_own_conversations():
    service, _ = make_service()
    first, second = customer(), customer()
    await service.create_conversation(first, "Hỗ trợ xe VF 6")
    await service.create_conversation(second, "Hỗ trợ xe VF 8")
    result = await service.list_conversations(first)
    assert [item.customer_id for item in result] == [first.user_id]


async def test_consultant_must_claim_before_replying_and_cannot_steal():
    service, _ = make_service()
    owner = customer()
    conversation = await service.create_conversation(owner, "Báo giá VF 7")
    first_staff = Actor(uuid4(), Role.CONSULTANT)
    second_staff = Actor(uuid4(), Role.CONSULTANT)

    with pytest.raises(PermissionDeniedError):
        await service.send_message(first_staff, conversation.conversation_id, "Xin chào")
    await service.assign_to_me(first_staff, conversation.conversation_id)
    with pytest.raises(PermissionDeniedError):
        await service.assign_to_me(second_staff, conversation.conversation_id)
    message = await service.send_message(first_staff, conversation.conversation_id, "  Xin chào  ")
    assert message.content == "Xin chào"


async def test_closed_conversation_rejects_messages_and_unknown_id_is_not_found():
    service, _ = make_service()
    owner = customer()
    conversation = await service.create_conversation(owner, "Đóng hội thoại")
    await service.close(owner, conversation.conversation_id)
    with pytest.raises(ValidationError):
        await service.send_message(owner, conversation.conversation_id, "Còn đó không?")
    with pytest.raises(NotFoundError):
        await service.list_messages(owner, uuid4())


async def test_only_owner_or_admin_can_delete():
    service, _ = make_service()
    owner = customer()
    conversation = await service.create_conversation(owner, "Xóa hội thoại")
    with pytest.raises(PermissionDeniedError):
        await service.delete(Actor(uuid4(), Role.CONSULTANT), conversation.conversation_id)
    await service.delete(Actor(uuid4(), Role.ADMIN), conversation.conversation_id)
    with pytest.raises(NotFoundError):
        await service.get_conversation(owner, conversation.conversation_id)
