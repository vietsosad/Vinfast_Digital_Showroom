from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.domain import Account, SupportConversation, SupportMessage
from src.services.support_chat import Conversation, Message


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(self, customer_id: UUID, subject: str) -> Conversation:
        row = SupportConversation(customer_id=customer_id, subject=subject, status="open")
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return await self._conversation_record(row)

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        row = await self.session.scalar(
            select(SupportConversation).where(SupportConversation.conversation_id == conversation_id)
        )
        return await self._conversation_record(row) if row else None

    async def list_for_customer(self, customer_id: UUID) -> list[Conversation]:
        rows = (
            await self.session.scalars(
                select(SupportConversation)
                .where(SupportConversation.customer_id == customer_id)
                .order_by(SupportConversation.updated_at.desc())
            )
        ).all()
        return [await self._conversation_record(row) for row in rows]

    async def list_for_staff(self) -> list[Conversation]:
        rows = (
            await self.session.scalars(
                select(SupportConversation).order_by(SupportConversation.updated_at.desc())
            )
        ).all()
        return [await self._conversation_record(row) for row in rows]

    async def assign_staff(self, conversation_id: UUID, staff_id: UUID) -> Conversation:
        row = await self._required_conversation(conversation_id)
        row.assigned_staff_id = staff_id
        row.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(row)
        return await self._conversation_record(row)

    async def close_conversation(self, conversation_id: UUID) -> Conversation:
        row = await self._required_conversation(conversation_id)
        row.status = "closed"
        row.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(row)
        return await self._conversation_record(row)

    async def delete_conversation(self, conversation_id: UUID) -> None:
        await self.session.execute(
            delete(SupportMessage).where(SupportMessage.conversation_id == conversation_id)
        )
        row = await self._required_conversation(conversation_id)
        await self.session.delete(row)
        await self.session.commit()

    async def list_messages(self, conversation_id: UUID) -> list[Message]:
        rows = (
            await self.session.scalars(
                select(SupportMessage)
                .where(SupportMessage.conversation_id == conversation_id)
                .order_by(SupportMessage.sent_at.asc(), SupportMessage.message_id.asc())
            )
        ).all()
        records: list[Message] = []
        for row in rows:
            sender = await self.session.get(Account, row.sender_id)
            records.append(
                Message(
                    message_id=row.message_id,
                    conversation_id=row.conversation_id,
                    sender_id=row.sender_id,
                    content=row.content,
                    sent_at=row.sent_at,
                    sender_name=sender.full_name if sender else None,
                    sender_role=sender.role if sender else None,
                )
            )
        return records

    async def create_message(self, conversation_id: UUID, sender_id: UUID, content: str) -> Message:
        row = SupportMessage(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            sent_at=datetime.now(timezone.utc),
        )
        self.session.add(row)
        conversation = await self._required_conversation(conversation_id)
        conversation.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(row)
        sender = await self.session.get(Account, sender_id)
        return Message(
            message_id=row.message_id,
            conversation_id=row.conversation_id,
            sender_id=row.sender_id,
            content=row.content,
            sent_at=row.sent_at,
            sender_name=sender.full_name if sender else None,
            sender_role=sender.role if sender else None,
        )

    async def _required_conversation(self, conversation_id: UUID) -> SupportConversation:
        row = await self.session.scalar(
            select(SupportConversation).where(SupportConversation.conversation_id == conversation_id)
        )
        if row is None:
            raise LookupError("Conversation not found")
        return row

    async def _conversation_record(self, row: SupportConversation) -> Conversation:
        customer = await self.session.get(Account, row.customer_id)
        staff = await self.session.get(Account, row.assigned_staff_id) if row.assigned_staff_id else None
        return Conversation(
            conversation_id=row.conversation_id,
            customer_id=row.customer_id,
            assigned_staff_id=row.assigned_staff_id,
            subject=row.subject,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
            customer_name=customer.full_name if customer else None,
            assigned_staff_name=staff.full_name if staff else None,
        )
