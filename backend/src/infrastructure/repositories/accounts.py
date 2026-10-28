from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.accounts import Account, NewAccount
from src.domain.identity import parse_role
from src.infrastructure.orm import (
    AccountRow,
    CustomerDemandRow,
    CustomerProfileRow,
    SupportConversationRow,
    SupportMessageRow,
    TestDriveBookingRow,
)

# Chuyển đổi từ AccountRow sang Account
def to_account(row: AccountRow) -> Account:
    return Account(
        user_id=row.user_id,
        email=row.email,
        phone=row.phone,
        full_name=row.full_name,
        role=parse_role(row.role),
        is_active=row.is_active,
        password_hash=row.hashed_password,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )

# Kho lưu trữ tài khoản sử dụng SQLAlchemy
class SqlAlchemyAccountRepository:
    # Khởi tạo kho lưu trữ với phiên làm việc SQLAlchemy bất đồng bộ.
    def __init__(self, session: AsyncSession):
        self.session = session

    # Các phương thức truy xuất và thao tác dữ liệu tài khoản
    async def get(self, user_id: UUID) -> Account | None:
        row = await self.session.get(AccountRow, user_id)
        return to_account(row) if row else None

    # Lấy tài khoản theo email
    async def get_by_email(self, email: str) -> Account | None:
        row = await self.session.scalar(select(AccountRow).where(AccountRow.email == email))
        return to_account(row) if row else None

    # Lấy tài khoản theo số điện thoại
    async def phone_in_use(self, phone: str, *, exclude_user_id: UUID | None = None) -> bool:
        statement = select(AccountRow.user_id).where(AccountRow.phone == phone)
        if exclude_user_id is not None:
            statement = statement.where(AccountRow.user_id != exclude_user_id)
        return await self.session.scalar(statement.limit(1)) is not None

    # Danh sách tất cả tài khoản
    async def list_all(self) -> list[Account]:
        rows = await self.session.scalars(select(AccountRow).order_by(AccountRow.created_at.desc()))
        return [to_account(row) for row in rows]

    # Thêm tài khoản mới vào cơ sở dữ liệu
    async def add(self, account: NewAccount) -> Account:
        row = AccountRow(
            email=account.email,
            phone=account.phone,
            full_name=account.full_name,
            role=account.role.value,
            hashed_password=account.password_hash,
            is_active=True,
        )
        self.session.add(row)
        await self.session.flush()
        return to_account(row)

    # Cập nhật thông tin tài khoản hiện có
    async def save(self, account: Account) -> Account:
        row = await self.session.get(AccountRow, account.user_id)
        if row is None:
            raise LookupError(f"Account {account.user_id} does not exist")
        row.full_name = account.full_name
        row.phone = account.phone
        row.role = account.role.value
        row.is_active = account.is_active
        row.hashed_password = account.password_hash
        await self.session.flush()
        return to_account(row)

    # Xóa tài khoản và các bản ghi liên quan không thể tồn tại độc lập, bất kể hỗ trợ cascade của cơ sở dữ liệu.
    async def delete(self, user_id: UUID) -> None:
        """Remove an account and the rows that cannot outlive it, independent of DB cascade support."""
        conversations = select(SupportConversationRow.conversation_id).where(
            SupportConversationRow.customer_id == user_id
        )
        await self.session.execute(
            delete(SupportMessageRow).where(
                or_(SupportMessageRow.sender_id == user_id, SupportMessageRow.conversation_id.in_(conversations))
            )
        )
        await self.session.execute(delete(SupportConversationRow).where(SupportConversationRow.customer_id == user_id))
        await self.session.execute(
            update(SupportConversationRow)
            .where(SupportConversationRow.assigned_staff_id == user_id)
            .values(assigned_staff_id=None)
        )
        await self.session.execute(
            update(TestDriveBookingRow).where(TestDriveBookingRow.user_id == user_id).values(user_id=None)
        )
        await self.session.execute(delete(CustomerDemandRow).where(CustomerDemandRow.user_id == user_id))
        await self.session.execute(delete(CustomerProfileRow).where(CustomerProfileRow.user_id == user_id))
        await self.session.execute(delete(AccountRow).where(AccountRow.user_id == user_id))
