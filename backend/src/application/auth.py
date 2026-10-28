from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.clock import Clock, utc_now
from src.domain.accounts import (
    Account,
    NewAccount,
    PasswordHasher,
    TokenService,
    normalize_email,
    normalize_full_name,
    normalize_phone,
    validate_password,
)
from src.domain.customers import CustomerProfile
from src.domain.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from src.domain.identity import Actor, Role
from src.domain.unit_of_work import UnitOfWork

# thông tin đăng ký tài khoản mới, được gửi từ client đến server
@dataclass(frozen=True)
class Registration:
    email: str
    phone: str
    password: str
    full_name: str

# thông tin thay đổi tài khoản, được gửi từ client đến server
@dataclass(frozen=True)
class AccountChanges:
    full_name: str | None = None
    phone: str | None = None
    password: str | None = None
    role: Role | None = None
    is_active: bool | None = None

# kết quả đăng nhập, được trả về cho client sau khi xác thực thành công
@dataclass(frozen=True)
class LoginResult:
    access_token: str
    account: Account

# dịch vụ xác thực, cung cấp các phương thức để đăng ký, đăng nhập, xác thực token, quản lý tài khoản
class AuthService:
    def __init__(
        self,
        uow: UnitOfWork,
        hasher: PasswordHasher,
        tokens: TokenService,
        clock: Clock = utc_now,
    ):
        self.uow = uow
        self.hasher = hasher
        self.tokens = tokens
        self.clock = clock

    # Đăng ký tài khoản khách hàng mới, luôn tạo một hồ sơ CRM cho khách hàng, thực hiện trong một giao dịch
    async def register_customer(self, data: Registration) -> Account:
        """Public sign-up always yields a customer with a CRM profile, atomically."""
        account = await self._create_account(data, Role.CUSTOMER)
        await self.uow.customer_profiles.add(CustomerProfile.new_for(account.user_id, self.clock()))
        await self.uow.commit()
        return account

    # Tạo tài khoản nhân viên mới, chỉ quản trị viên mới có quyền thực hiện, vai trò phải là consultant hoặc admin
    async def create_staff(self, actor: Actor, data: Registration, role: Role) -> Account:
        if not actor.is_admin:
            raise PermissionDeniedError("Chỉ quản trị viên được tạo tài khoản nhân viên")
        if role not in (Role.CONSULTANT, Role.ADMIN):
            raise ValidationError("Tài khoản nhân viên phải có vai trò consultant hoặc admin")
        account = await self._create_account(data, role)
        await self.uow.commit()
        return account

    # Đăng nhập bằng email và mật khẩu, trả về access token và thông tin tài khoản nếu thành công
    async def login(self, email: str, password: str) -> LoginResult:
        account = await self.uow.accounts.get_by_email(normalize_email(email))
        if account is None or not self.hasher.verify(password, account.password_hash):
            raise AuthenticationError("Email hoặc mật khẩu không chính xác")
        if not account.is_active:
            raise PermissionDeniedError("Tài khoản đã bị khóa")
        return LoginResult(access_token=self.tokens.issue(account), account=account)

    # Xác thực token, trả về thông tin tài khoản nếu token hợp lệ và tài khoản đang hoạt động
    async def authenticate(self, token: str) -> Account:
        """Resolve a bearer token to an active account (used by HTTP and WebSocket)."""
        user_id = self.tokens.decode_subject(token)
        account = await self.uow.accounts.get(user_id)
        if account is None or not account.is_active:
            raise AuthenticationError("Tài khoản không tồn tại hoặc đã bị khóa")
        return account

    # Danh sách tất cả tài khoản, chỉ quản trị viên mới có quyền xem
    async def list_accounts(self, actor: Actor) -> list[Account]:
        if not actor.is_admin:
            raise PermissionDeniedError("Chỉ quản trị viên được xem danh sách tài khoản")
        return await self.uow.accounts.list_all()

    # Cập nhật thông tin tài khoản, chỉ quản trị viên mới có quyền thay đổi vai trò hoặc trạng thái tài khoản, người dùng không thể tự hạ quyền hoặc tự khóa tài khoản của mình
    async def update_account(self, actor: Actor, user_id: UUID, changes: AccountChanges) -> Account:
        if actor.user_id != user_id and not actor.is_admin:
            raise PermissionDeniedError("Bạn không có quyền sửa thông tin của tài khoản khác")
        if (changes.role is not None or changes.is_active is not None) and not actor.is_admin:
            raise PermissionDeniedError("Chỉ quản trị viên được đổi vai trò hoặc trạng thái tài khoản")
        if actor.user_id == user_id and (
            (changes.role is not None and changes.role is not actor.role) or changes.is_active is False
        ):
            raise ConflictError("Quản trị viên không thể tự hạ quyền hoặc tự khóa tài khoản")

        account = await self.uow.accounts.get(user_id)
        if account is None:
            raise NotFoundError("Không tìm thấy tài khoản")

        if changes.full_name is not None:
            account.full_name = normalize_full_name(changes.full_name)
        if changes.phone is not None:
            phone = normalize_phone(changes.phone)
            if await self.uow.accounts.phone_in_use(phone, exclude_user_id=account.user_id):
                raise ConflictError("Số điện thoại đã được sử dụng bởi tài khoản khác")
            account.phone = phone
        if changes.password:
            account.password_hash = self.hasher.hash(validate_password(changes.password))
        if changes.role is not None:
            account.role = changes.role
        if changes.is_active is not None:
            account.is_active = changes.is_active

        account = await self.uow.accounts.save(account)
        await self.uow.commit()
        return account

    # Xóa tài khoản, chỉ quản trị viên mới có quyền xóa, không thể tự xóa tài khoản đang đăng nhập
    async def delete_account(self, actor: Actor, user_id: UUID) -> None:
        if not actor.is_admin:
            raise PermissionDeniedError("Chỉ quản trị viên được xóa tài khoản")
        if actor.user_id == user_id:
            raise ConflictError("Không thể tự xóa tài khoản đang đăng nhập")
        if await self.uow.accounts.get(user_id) is None:
            raise NotFoundError("Không tìm thấy tài khoản")
        await self.uow.accounts.delete(user_id)
        await self.uow.commit()

    # Tạo tài khoản mới, kiểm tra email và số điện thoại chưa được sử dụng, băm mật khẩu, trả về đối tượng Account mới
    async def _create_account(self, data: Registration, role: Role) -> Account:
        email = normalize_email(data.email)
        phone = normalize_phone(data.phone)
        if await self.uow.accounts.get_by_email(email) is not None:
            raise ConflictError("Email này đã được đăng ký")
        if await self.uow.accounts.phone_in_use(phone):
            raise ConflictError("Số điện thoại này đã được đăng ký")
        return await self.uow.accounts.add(
            NewAccount(
                email=email,
                phone=phone,
                full_name=normalize_full_name(data.full_name),
                role=role,
                password_hash=self.hasher.hash(validate_password(data.password)),
            )
        )
