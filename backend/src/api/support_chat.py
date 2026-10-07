from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.domain import Account
from src.repositories.support_chat import SqlAlchemyConversationRepository
from src.services.database import SessionLocal, get_db
from src.services.security import decode_access_token, get_current_user
from src.services.support_chat import (
    ChatActor,
    ChatForbiddenError,
    ChatNotFoundError,
    ChatValidationError,
    Conversation,
    Message,
    SupportChatService,
)

router = APIRouter()


class ConversationCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=160, examples=["Tư vấn lịch lái thử VF 6"])


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2_000, examples=["Tôi muốn đặt lịch vào sáng thứ Bảy."])


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    customer_id: UUID
    assigned_staff_id: UUID | None
    subject: str
    status: str
    created_at: datetime
    updated_at: datetime
    customer_name: str | None = None
    assigned_staff_name: str | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: UUID
    conversation_id: UUID
    sender_id: UUID
    content: str
    sent_at: datetime
    sender_name: str | None = None
    sender_role: str | None = None


def get_service(db: AsyncSession = Depends(get_db)) -> SupportChatService:
    return SupportChatService(SqlAlchemyConversationRepository(db))


def actor_from_account(account: Account) -> ChatActor:
    return ChatActor(user_id=account.user_id, role=account.role)


def handle_chat_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ChatNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ChatForbiddenError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ChatValidationError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="Không thể xử lý hội thoại")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, conversation_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[conversation_id].add(websocket)

    def disconnect(self, conversation_id: UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(conversation_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(conversation_id, None)

    async def broadcast(self, conversation_id: UUID, payload: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in tuple(self._connections.get(conversation_id, ())):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(conversation_id, websocket)


manager = ConnectionManager()


def message_payload(message: Message) -> dict:
    return MessageResponse.model_validate(message).model_dump(mode="json")


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mở hội thoại hỗ trợ",
    description="Customer tạo một hội thoại mới để trao đổi trực tiếp với nhân viên.",
)
async def create_conversation(
    payload: ConversationCreate,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_service),
) -> Conversation:
    try:
        return await service.create_conversation(actor_from_account(current_user), payload.subject)
    except Exception as exc:
        raise handle_chat_error(exc) from exc


@router.get(
    "",
    response_model=list[ConversationResponse],
    summary="Danh sách hội thoại",
    description="Customer chỉ thấy hội thoại của mình; consultant và admin thấy hàng đợi hỗ trợ.",
)
async def list_conversations(
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_service),
) -> list[Conversation]:
    try:
        return await service.list_conversations(actor_from_account(current_user))
    except Exception as exc:
        raise handle_chat_error(exc) from exc


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Lịch sử tin nhắn",
)
async def list_messages(
    conversation_id: UUID,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_service),
) -> list[Message]:
    try:
        return await service.list_messages(actor_from_account(current_user), conversation_id)
    except Exception as exc:
        raise handle_chat_error(exc) from exc


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gửi tin nhắn",
    description="Lưu tin nhắn vào database và phát ngay tới các kết nối WebSocket đang mở.",
)
async def send_message(
    conversation_id: UUID,
    payload: MessageCreate,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_service),
) -> Message:
    try:
        message = await service.send_message(actor_from_account(current_user), conversation_id, payload.content)
        await manager.broadcast(conversation_id, {"type": "message", "message": message_payload(message)})
        return message
    except Exception as exc:
        raise handle_chat_error(exc) from exc


@router.post(
    "/{conversation_id}/assign",
    response_model=ConversationResponse,
    summary="Nhận xử lý hội thoại",
    description="Consultant hoặc admin tự nhận một hội thoại đang mở.",
)
async def assign_conversation(
    conversation_id: UUID,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_service),
) -> Conversation:
    try:
        conversation = await service.assign_to_me(actor_from_account(current_user), conversation_id)
        await manager.broadcast(conversation_id, {"type": "conversation_updated", "status": conversation.status})
        return conversation
    except Exception as exc:
        raise handle_chat_error(exc) from exc


@router.post(
    "/{conversation_id}/close",
    response_model=ConversationResponse,
    summary="Đóng hội thoại",
)
async def close_conversation(
    conversation_id: UUID,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_service),
) -> Conversation:
    try:
        conversation = await service.close(actor_from_account(current_user), conversation_id)
        await manager.broadcast(conversation_id, {"type": "conversation_updated", "status": "closed"})
        return conversation
    except Exception as exc:
        raise handle_chat_error(exc) from exc


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa hội thoại",
    description="Customer sở hữu hoặc admin có thể xóa hội thoại và toàn bộ tin nhắn.",
)
async def delete_conversation(
    conversation_id: UUID,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_service),
) -> None:
    try:
        await service.delete(actor_from_account(current_user), conversation_id)
        await manager.broadcast(conversation_id, {"type": "conversation_deleted"})
    except Exception as exc:
        raise handle_chat_error(exc) from exc


@router.websocket("/{conversation_id}/ws")
async def conversation_socket(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str = Query(..., description="JWT access token returned by /auth/login"),
) -> None:
    try:
        user_id = decode_access_token(token)
    except ValueError:
        await websocket.close(code=4401, reason="Token không hợp lệ hoặc đã hết hạn")
        return

    async with SessionLocal() as session:
        account = await session.get(Account, user_id)
        if account is None or not account.is_active:
            await websocket.close(code=4401, reason="Tài khoản không hợp lệ")
            return

        actor = actor_from_account(account)
        service = SupportChatService(SqlAlchemyConversationRepository(session))
        try:
            await service.get_conversation(actor, conversation_id)
        except (ChatNotFoundError, ChatForbiddenError):
            await websocket.close(code=4403, reason="Không có quyền truy cập hội thoại")
            return

        await manager.connect(conversation_id, websocket)
        try:
            while True:
                payload = await websocket.receive_json()
                content = str(payload.get("content") or "")
                try:
                    message = await service.send_message(actor, conversation_id, content)
                    await manager.broadcast(
                        conversation_id,
                        {"type": "message", "message": message_payload(message)},
                    )
                except (ChatValidationError, ChatForbiddenError, ChatNotFoundError) as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
        except WebSocketDisconnect:
            manager.disconnect(conversation_id, websocket)
