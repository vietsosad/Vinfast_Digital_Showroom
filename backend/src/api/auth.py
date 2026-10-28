import uuid

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_auth_service, get_current_user, require_admin
from src.api.schemas.auth import (
    ProfileUpdate,
    StaffCreate,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from src.api.schemas.common import MessageResponse, errors
from src.application.auth import AccountChanges, AuthService, Registration
from src.domain.accounts import Account
from src.domain.identity import Role

router = APIRouter()


def _registration(payload: UserRegister) -> Registration:
    return Registration(
        email=payload.email, phone=payload.phone, password=payload.password, full_name=payload.full_name
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản khách hàng",
    responses=errors(409),
)
async def register(payload: UserRegister, auth: AuthService = Depends(get_auth_service)) -> Account:
    return await auth.register_customer(_registration(payload))


@router.post("/login", response_model=TokenResponse, summary="Đăng nhập và nhận JWT", responses=errors(401, 403))
async def login(payload: UserLogin, auth: AuthService = Depends(get_auth_service)) -> TokenResponse:
    result = await auth.login(payload.email, payload.password)
    return TokenResponse(access_token=result.access_token, user=UserResponse.model_validate(result.account))


@router.get("/me", response_model=UserResponse, summary="Tài khoản hiện tại", responses=errors(401))
async def get_me(current_user: Account = Depends(get_current_user)) -> Account:
    return current_user


@router.put("/me", response_model=UserResponse, summary="Cập nhật hồ sơ cá nhân", responses=errors(401, 409))
async def update_my_profile(
    payload: ProfileUpdate,
    current_user: Account = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
) -> Account:
    changes = AccountChanges(**payload.model_dump(exclude_unset=True))
    return await auth.update_account(current_user.actor, current_user.user_id, changes)


@router.get("/users", response_model=list[UserResponse], summary="Danh sách tài khoản", responses=errors(401, 403))
async def list_users(
    current_user: Account = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
) -> list[Account]:
    return await auth.list_accounts(current_user.actor)


@router.post(
    "/create-staff",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin tạo tài khoản nhân viên",
    responses=errors(401, 403, 409),
)
async def create_staff(
    payload: StaffCreate,
    current_user: Account = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
) -> Account:
    return await auth.create_staff(current_user.actor, _registration(payload), Role(payload.role))


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Sửa tài khoản (chính mình hoặc admin)",
    responses=errors(401, 403, 404, 409),
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: Account = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
) -> Account:
    changes = AccountChanges(**payload.model_dump(exclude_unset=True))
    return await auth.update_account(current_user.actor, user_id, changes)


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Admin xóa tài khoản",
    responses=errors(401, 403, 404, 409),
)
async def delete_user(
    user_id: uuid.UUID,
    current_user: Account = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await auth.delete_account(current_user.actor, user_id)
    return MessageResponse(message="Đã xóa tài khoản thành công")
