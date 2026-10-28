from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status

from src.api.dependencies import (
    build_auth_service,
    build_chat_service,
    get_chat_service,
    get_current_user,
    unit_of_work_scope,
)
from src.api.schemas.chat import ConversationCreate, ConversationResponse, MessageCreate, MessageResponse
from src.api.schemas.common import errors
from src.application.support_chat import SupportChatService
from src.domain.accounts import Account
from src.domain.chat import Conversation, Message
from src.domain.errors import AuthenticationError, DomainError, NotFoundError, PermissionDeniedError

router = APIRouter()

WS_UNAUTHORIZED = 4401
WS_FORBIDDEN = 4403


# Quản lý các WebSocket đang kết nối theo từng hội thoại để phát sự kiện trực tiếp.
class ConnectionManager:
    """In-process fan-out of chat events (single worker in Phase 1)."""

    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    # Chấp nhận kết nối và lưu socket vào nhóm của hội thoại tương ứng.
    async def connect(self, conversation_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[conversation_id].add(websocket)

    # Gỡ socket khỏi nhóm và xóa nhóm khi không còn kết nối nào.
    def disconnect(self, conversation_id: UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(conversation_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(conversation_id, None)

    # Phát một sự kiện đến mọi socket đang theo dõi hội thoại.
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


# Chuyển tin nhắn domain thành dict JSON theo schema API.
def message_payload(message: Message) -> dict:
    return MessageResponse.model_validate(message).model_dump(mode="json")


# Mở hội thoại hỗ trợ cho khách hàng đã đăng nhập.
@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mở hội thoại hỗ trợ",
    description="Customer tạo một hội thoại mới để trao đổi trực tiếp với nhân viên.",
    responses=errors(401, 403),
)
async def create_conversation(
    payload: ConversationCreate,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_chat_service),
) -> Conversation:
    return await service.create_conversation(current_user.actor, payload.subject)


# Liệt kê hội thoại mà người dùng hiện tại có quyền xem.
@router.get(
    "",
    response_model=list[ConversationResponse],
    summary="Danh sách hội thoại",
    description="Customer chỉ thấy hội thoại của mình; consultant và admin thấy hàng đợi hỗ trợ.",
    responses=errors(401),
)
async def list_conversations(
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_chat_service),
) -> list[Conversation]:
    return await service.list_conversations(current_user.actor)


# Trả lịch sử tin nhắn sau khi service xác nhận quyền truy cập hội thoại.
@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Lịch sử tin nhắn",
    responses=errors(401, 403, 404),
)
async def list_messages(
    conversation_id: UUID,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_chat_service),
) -> list[Message]:
    return await service.list_messages(current_user.actor, conversation_id)


# Lưu tin nhắn qua service rồi phát sự kiện cho các kết nối WebSocket.
@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gửi tin nhắn",
    description="Lưu tin nhắn vào database rồi phát tới các kết nối WebSocket đang mở.",
    responses=errors(401, 403, 404),
)
async def send_message(
    conversation_id: UUID,
    payload: MessageCreate,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_chat_service),
) -> Message:
    message = await service.send_message(current_user.actor, conversation_id, payload.content)
    await manager.broadcast(conversation_id, {"type": "message", "message": message_payload(message)})
    return message


# Cho nhân viên nhận phụ trách hội thoại và thông báo cập nhật trạng thái.
@router.post(
    "/{conversation_id}/assign",
    response_model=ConversationResponse,
    summary="Nhận xử lý hội thoại",
    description="Consultant hoặc admin tự nhận một hội thoại đang mở.",
    responses=errors(401, 403, 404),
)
async def assign_conversation(
    conversation_id: UUID,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_chat_service),
) -> Conversation:
    conversation = await service.assign_to_me(current_user.actor, conversation_id)
    await manager.broadcast(conversation_id, {"type": "conversation_updated", "status": conversation.status.value})
    return conversation


# Đóng hội thoại theo quy tắc phân quyền của service rồi phát trạng thái mới.
@router.post(
    "/{conversation_id}/close",
    response_model=ConversationResponse,
    summary="Đóng hội thoại",
    responses=errors(401, 403, 404),
)
async def close_conversation(
    conversation_id: UUID,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_chat_service),
) -> Conversation:
    conversation = await service.close(current_user.actor, conversation_id)
    await manager.broadcast(conversation_id, {"type": "conversation_updated", "status": "closed"})
    return conversation


# Xóa hội thoại và thông báo sự kiện xóa tới các socket đang kết nối.
@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa hội thoại",
    description="Customer sở hữu hoặc admin có thể xóa hội thoại và toàn bộ tin nhắn.",
    responses=errors(401, 403, 404),
)
async def delete_conversation(
    conversation_id: UUID,
    current_user: Account = Depends(get_current_user),
    service: SupportChatService = Depends(get_chat_service),
) -> None:
    await service.delete(current_user.actor, conversation_id)
    await manager.broadcast(conversation_id, {"type": "conversation_deleted"})


# Xác thực, kiểm tra quyền truy cập rồi nhận và phát tin nhắn qua WebSocket.
@router.websocket("/{conversation_id}/ws")
async def conversation_socket(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str = Query(..., description="JWT access token returned by /auth/login"),
) -> None:
    """Authenticate with the same AuthService as HTTP, authorize via the chat use case, then accept."""
    async with unit_of_work_scope() as uow:
        # Từ chối kết nối nếu token không hợp lệ hoặc tài khoản không còn được xác thực.
        try:
            account = await build_auth_service(uow).authenticate(token)
        except AuthenticationError:
            await websocket.close(code=WS_UNAUTHORIZED, reason="Token hoặc tài khoản không hợp lệ")
            return

        actor = account.actor
        service = build_chat_service(uow)
        # Chỉ chấp nhận socket nếu actor có quyền truy cập cuộc hội thoại này.
        try:
            await service.get_conversation(actor, conversation_id)
        except (NotFoundError, PermissionDeniedError):
            await websocket.close(code=WS_FORBIDDEN, reason="Không có quyền truy cập hội thoại")
            return

        # Lắng nghe tin nhắn mới, xử lý qua cùng service nghiệp vụ với HTTP rồi phát cho nhóm.
        await manager.connect(conversation_id, websocket)
        try:
            while True:
                payload = await websocket.receive_json()
                content = str(payload.get("content") or "") if isinstance(payload, dict) else ""
                try:
                    message = await service.send_message(actor, conversation_id, content)
                except DomainError as exc:
                    await websocket.send_json({"type": "error", "message": exc.message})
                    continue
                await manager.broadcast(conversation_id, {"type": "message", "message": message_payload(message)})
        except WebSocketDisconnect:
            pass
        finally:
            # Luôn gỡ socket khỏi manager khi client ngắt kết nối hoặc luồng xử lý kết thúc.
            manager.disconnect(conversation_id, websocket)
