from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.chat import Conversation, ConversationStatus, Message
from src.domain.workflow import parse_enum
from src.infrastructure.orm import AccountRow, SupportConversationRow, SupportMessageRow


# Chuyển đổi giữa các thực thể hội thoại/tin nhắn của domain và SQLAlchemy.
class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession):
        # Chia sẻ phiên database để transaction do UnitOfWork quản lý.
        self.session = session

    # Tạo hội thoại mới rồi ánh xạ bản ghi ORM sang đối tượng domain.
    async def create_conversation(self, customer_id: UUID, subject: str) -> Conversation:
        row = SupportConversationRow(customer_id=customer_id, subject=subject, status=ConversationStatus.OPEN.value)
        self.session.add(row)
        # Flush để ORM nhận các giá trị do cơ sở dữ liệu tạo trước khi ánh xạ sang domain.
        await self.session.flush()
        return await self._conversation_record(row)

    # Tìm một hội thoại theo ID; trả None nếu không tồn tại.
    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        row = await self.session.get(SupportConversationRow, conversation_id, populate_existing=True)
        return await self._conversation_record(row) if row else None

    # Liệt kê hội thoại của khách hàng, gần cập nhật nhất đứng trước.
    async def list_for_customer(self, customer_id: UUID) -> list[Conversation]:
        rows = await self.session.scalars(
            select(SupportConversationRow)
            .where(SupportConversationRow.customer_id == customer_id)
            .order_by(SupportConversationRow.updated_at.desc())
        )
        return [await self._conversation_record(row) for row in rows.all()]

    # Liệt kê hàng đợi hội thoại cho nhân viên hỗ trợ.
    async def list_for_staff(self) -> list[Conversation]:
        rows = await self.session.scalars(
            select(SupportConversationRow).order_by(SupportConversationRow.updated_at.desc())
        )
        return [await self._conversation_record(row) for row in rows.all()]

    # Gán nhân viên phụ trách và cập nhật thời điểm hoạt động của hội thoại.
    async def assign_staff(self, conversation_id: UUID, staff_id: UUID) -> Conversation:
        row = await self._required_conversation(conversation_id)
        row.assigned_staff_id = staff_id
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return await self._conversation_record(row)

    # Đánh dấu hội thoại đã đóng và trả về dữ liệu domain đã cập nhật.
    async def close_conversation(self, conversation_id: UUID) -> Conversation:
        row = await self._required_conversation(conversation_id)
        row.status = ConversationStatus.CLOSED.value
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return await self._conversation_record(row)

    # Xóa tin nhắn và hội thoại tương ứng khỏi phiên database.
    async def delete_conversation(self, conversation_id: UUID) -> None:
        # Xóa tin nhắn trước để tránh vi phạm khóa ngoại tham chiếu đến hội thoại.
        await self.session.execute(delete(SupportMessageRow).where(SupportMessageRow.conversation_id == conversation_id))
        await self.session.execute(
            delete(SupportConversationRow).where(SupportConversationRow.conversation_id == conversation_id)
        )

    # Lấy lịch sử tin nhắn theo thứ tự gửi, kèm tên và vai trò người gửi nếu còn.
    async def list_messages(self, conversation_id: UUID) -> list[Message]:
        rows = await self.session.execute(
            select(SupportMessageRow, AccountRow)
            # Dùng outer join để vẫn trả về tin nhắn nếu tài khoản người gửi không còn tồn tại.
            .join(AccountRow, AccountRow.user_id == SupportMessageRow.sender_id, isouter=True)
            .where(SupportMessageRow.conversation_id == conversation_id)
            # Sắp xếp theo ID để thứ tự tin nhắn vẫn ổn định khi cùng thời điểm gửi.
            .order_by(SupportMessageRow.sent_at.asc(), SupportMessageRow.message_id.asc())
        )
        return [self._message_record(message, sender) for message, sender in rows.all()]

    # Lưu tin nhắn, cập nhật hoạt động hội thoại và tạo đối tượng domain kết quả.
    async def create_message(self, conversation_id: UUID, sender_id: UUID, content: str) -> Message:
        now = datetime.now(timezone.utc)
        row = SupportMessageRow(conversation_id=conversation_id, sender_id=sender_id, content=content, sent_at=now)
        self.session.add(row)
        conversation = await self._required_conversation(conversation_id)
        # Cập nhật thời gian hội thoại để danh sách hỗ trợ ưu tiên các cuộc trò chuyện mới hoạt động.
        conversation.updated_at = now
        await self.session.flush()
        sender = await self.session.get(AccountRow, sender_id)
        return self._message_record(row, sender)

    # Lấy hội thoại bắt buộc phải tồn tại, báo lỗi nếu không tìm thấy.
    async def _required_conversation(self, conversation_id: UUID) -> SupportConversationRow:
        row = await self.session.get(SupportConversationRow, conversation_id, populate_existing=True)
        if row is None:
            # Không trả về giá trị mặc định vì thao tác gọi hàm yêu cầu hội thoại phải tồn tại.
            raise LookupError("Conversation not found")
        return row

    # Ánh xạ bản ghi hội thoại cùng tên khách hàng/nhân viên sang domain.
    async def _conversation_record(self, row: SupportConversationRow) -> Conversation:
        customer = await self.session.get(AccountRow, row.customer_id)
        staff = await self.session.get(AccountRow, row.assigned_staff_id) if row.assigned_staff_id else None
        return Conversation(
            conversation_id=row.conversation_id,
            customer_id=row.customer_id,
            assigned_staff_id=row.assigned_staff_id,
            subject=row.subject,
            status=parse_enum(ConversationStatus, row.status, ConversationStatus.OPEN),
            created_at=row.created_at,
            updated_at=row.updated_at,
            customer_name=customer.full_name if customer else None,
            assigned_staff_name=staff.full_name if staff else None,
        )

    # Ánh xạ bản ghi tin nhắn và thông tin người gửi sang domain.
    @staticmethod
    def _message_record(row: SupportMessageRow, sender: AccountRow | None) -> Message:
        return Message(
            message_id=row.message_id,
            conversation_id=row.conversation_id,
            sender_id=row.sender_id,
            content=row.content,
            sent_at=row.sent_at,
            sender_name=sender.full_name if sender else None,
            sender_role=sender.role if sender else None,
        )
