from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.chat import ConversationStatus


class ConversationCreate(BaseModel):
    # Tiêu đề cuộc hội thoại; giới hạn độ dài để dữ liệu nhất quán.
    subject: str = Field(min_length=3, max_length=160, examples=["Tư vấn lịch lái thử VF 6"])


class MessageCreate(BaseModel):
    # Nội dung tin nhắn không được để trống và tối đa 2.000 ký tự.
    content: str = Field(min_length=1, max_length=2_000, examples=["Tôi muốn đặt lịch vào sáng thứ Bảy."])


class ConversationResponse(BaseModel):
    # Cho phép Pydantic tạo response trực tiếp từ đối tượng domain/ORM.
    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    customer_id: UUID
    assigned_staff_id: UUID | None
    subject: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    # Tên hiển thị có thể không có nếu thông tin liên quan chưa được tải.
    customer_name: str | None = None
    assigned_staff_name: str | None = None


class MessageResponse(BaseModel):
    # Cho phép Pydantic tạo response trực tiếp từ đối tượng domain/ORM.
    model_config = ConfigDict(from_attributes=True)

    message_id: UUID
    conversation_id: UUID
    sender_id: UUID
    content: str
    sent_at: datetime
    # Thông tin người gửi bổ sung để hiển thị trong giao diện chat.
    sender_name: str | None = None
    sender_role: str | None = None
