from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.accounts import PasswordHasher
from src.domain.identity import Role
from src.infrastructure.orm import AccountRow, CustomerProfileRow

# Local/demo credentials only. Never seeded when APP_ENV=production.
# Mỗi dòng gồm email, số điện thoại, mật khẩu ban đầu, tên hiển thị và vai trò.
# Mật khẩu ở đây là mật khẩu mẫu; hàm bên dưới chỉ lưu chuỗi đã được băm.
DEMO_ACCOUNTS = (
    ("admin@vinfast.vn", "0900000001", "admin123", "Quản trị viên VinFast", Role.ADMIN),
    ("staff@vinfast.vn", "0900000002", "staff123", "Tư vấn viên VinFast", Role.CONSULTANT),
    ("customer@gmail.com", "0900000003", "123456", "Khách hàng Demo", Role.CUSTOMER),
)


async def seed_demo_accounts(session: AsyncSession, hasher: PasswordHasher) -> int:
    """Create missing demo accounts without touching user-managed data."""
    created = 0
    for email, phone, password, full_name, role in DEMO_ACCOUNTS:
        # Bỏ qua nếu email đã tồn tại để không ghi đè tài khoản do người dùng tạo.
        if await session.scalar(select(AccountRow.user_id).where(AccountRow.email == email)) is not None:
            continue
        # Số điện thoại cũng là duy nhất; kiểm tra riêng để tránh xung đột khóa trong cơ sở dữ liệu.
        if await session.scalar(select(AccountRow.user_id).where(AccountRow.phone == phone)) is not None:
            continue
        # Tạo bản ghi tài khoản và băm mật khẩu trước khi lưu, không lưu mật khẩu dạng chữ thường.
        account = AccountRow(
            email=email,
            phone=phone,
            hashed_password=hasher.hash(password),
            full_name=full_name,
            role=role.value,
            is_active=True,
        )
        session.add(account)
        # Gửi INSERT để cơ sở dữ liệu cấp user_id trước khi tạo hồ sơ CRM liên kết.
        await session.flush()
        if role is Role.CUSTOMER:
            # Chỉ khách hàng có hồ sơ CRM; hồ sơ tham chiếu tài khoản vừa được tạo.
            session.add(CustomerProfileRow(user_id=account.user_id))
        created += 1
    # Lưu tất cả tài khoản và hồ sơ trong cùng một giao dịch; trả về số tài khoản mới tạo.
    await session.commit()
    return created
