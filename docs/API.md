# Đặc tả API

Base URL chuẩn: `/api/v1`. Dữ liệu HTTP dùng JSON, ngoại trừ API quản trị catalog nhận `multipart/form-data` để hỗ trợ tải ảnh. Swagger UI được sinh tự động tại `/docs`.

## Xác thực

Đăng nhập trả về JWT Bearer token:

```http
Authorization: Bearer <access_token>
```

Middleware/dependency dùng chung đọc token, kiểm tra tài khoản còn hoạt động và áp dụng role. Client không được gửi `user_id`, tên hoặc số điện thoại để giả danh chủ thể; backend lấy danh tính từ token cho báo giá, lịch lái thử và hội thoại.

Role trong backend:

- `customer`: khách hàng.
- `consultant`: nhân viên tư vấn; UI có thể hiển thị nhãn `staff`.
- `admin`: quản trị viên.

## Endpoint

Ký hiệu quyền: `Public`, `C` customer, `S` consultant, `A` admin, `Auth` mọi tài khoản đăng nhập.

| Method | Path | Quyền | Mục đích |
|---|---|---:|---|
| GET | `/health` | Public | Kiểm tra API và database |
| POST | `/api/v1/auth/register` | Public | Đăng ký customer |
| POST | `/api/v1/auth/login` | Public | Nhận JWT |
| GET | `/api/v1/auth/me` | Auth | Lấy tài khoản hiện tại |
| PUT | `/api/v1/auth/me` | Auth | Sửa hồ sơ cá nhân |
| GET | `/api/v1/auth/users` | A | Danh sách tài khoản |
| POST | `/api/v1/auth/create-staff` | A | Tạo consultant/admin |
| PUT | `/api/v1/auth/users/{id}` | Chủ tài khoản/A | Sửa tài khoản |
| DELETE | `/api/v1/auth/users/{id}` | A | Xóa tài khoản |
| GET | `/api/v1/cars` | Public | Danh sách ô tô |
| GET | `/api/v1/cars/{id-or-code}` | Public | Chi tiết ô tô |
| POST | `/api/v1/cars` | S/A | Tạo ô tô |
| PUT | `/api/v1/cars/{id}` | S/A | Cập nhật ô tô |
| DELETE | `/api/v1/cars/{id}` | A | Xóa ô tô |
| GET | `/api/v1/motorbikes` | Public | Danh sách xe máy điện |
| GET | `/api/v1/motorbikes/{id-or-code}` | Public | Chi tiết xe máy điện |
| POST | `/api/v1/motorbikes` | S/A | Tạo xe máy điện |
| PUT | `/api/v1/motorbikes/{id}` | S/A | Cập nhật xe máy điện |
| DELETE | `/api/v1/motorbikes/{id}` | A | Xóa xe máy điện |
| GET | `/api/v1/catalog-media/{vehicle-type}/{vehicle-id}` | Public | Danh sách media của xe |
| POST | `/api/v1/catalog-media/{vehicle-type}/{vehicle-id}/links` | S/A | Thêm tối đa 100 URL media |
| POST | `/api/v1/catalog-media/{vehicle-type}/{vehicle-id}/upload` | S/A | Tải tối đa 20 ảnh, mỗi ảnh tối đa 8 MB |
| PUT | `/api/v1/catalog-media/{media-id}` | S/A | Cập nhật metadata hoặc ảnh chính |
| DELETE | `/api/v1/catalog-media/{media-id}` | S/A | Xóa media |
| GET | `/api/v1/locations` | Public | Showroom/trạm sạc |
| POST | `/api/v1/locations/sync` | A | Nạp lại dataset địa điểm |
| POST | `/api/v1/tco/calculate` | Public | Tính chi phí sở hữu theo tham số |
| GET | `/api/v1/quotes` | Auth | C xem của mình; S/A xem hàng đợi |
| POST | `/api/v1/quotes` | Auth | Tạo yêu cầu báo giá cho chính mình |
| PUT | `/api/v1/quotes/{id}` | S/A | Cập nhật trạng thái/giá cuối |
| GET | `/api/v1/bookings` | Auth | C xem của mình; S/A xem hàng đợi |
| POST | `/api/v1/bookings` | Auth | Đặt lịch lái thử cho chính mình |
| PUT | `/api/v1/bookings/{id}` | S/A | Cập nhật trạng thái lịch |
| GET | `/api/v1/customer-profiles/me` | Auth | Xem hồ sơ CRM của mình |
| GET | `/api/v1/customer-profiles` | S/A | Tra cứu hồ sơ CRM |
| GET | `/api/v1/customer-profiles/{id}` | S/A | Chi tiết hồ sơ CRM |
| PUT | `/api/v1/customer-profiles/{id}` | S/A | Cập nhật lead/ghi chú thủ công |
| POST | `/api/v1/conversations` | C | Mở hội thoại hỗ trợ |
| GET | `/api/v1/conversations` | Auth | C xem của mình; S/A xem hàng đợi |
| GET | `/api/v1/conversations/{id}/messages` | Thành viên/S/A | Lịch sử tin nhắn |
| POST | `/api/v1/conversations/{id}/messages` | Thành viên/S/A | Gửi và phát tin nhắn |
| POST | `/api/v1/conversations/{id}/assign` | S/A | Nhận xử lý hội thoại |
| POST | `/api/v1/conversations/{id}/close` | Thành viên/S/A | Đóng hội thoại |
| DELETE | `/api/v1/conversations/{id}` | Chủ sở hữu/A | Xóa hội thoại và tin nhắn |

## Luồng hội thoại

Tạo hội thoại:

```http
POST /api/v1/conversations
Authorization: Bearer <customer-token>
Content-Type: application/json

{"subject":"Đặt lịch lái thử VF 6"}
```

Gửi tin qua REST:

```http
POST /api/v1/conversations/{conversation_id}/messages
Authorization: Bearer <token>
Content-Type: application/json

{"content":"Tôi muốn lái thử vào sáng thứ Bảy."}
```

Mở realtime channel:

```text
ws://localhost:8000/api/v1/conversations/{conversation_id}/ws?token=<jwt>
```

Client gửi:

```json
{"content":"Nội dung tin nhắn"}
```

Server phát:

```json
{
  "type": "message",
  "message": {
    "message_id": "uuid",
    "conversation_id": "uuid",
    "sender_id": "uuid",
    "content": "Nội dung tin nhắn",
    "sent_at": "2026-10-05T08:00:00Z",
    "sender_name": "Tên người gửi",
    "sender_role": "customer"
  }
}
```

Các event khác: `conversation_updated`, `conversation_deleted`, `error`. REST vẫn là đường gửi dự phòng nếu WebSocket mất kết nối.

## Quy tắc nghiệp vụ chat

- Chỉ customer được mở hội thoại; subject dài 3–160 ký tự.
- Customer chỉ đọc hội thoại do mình sở hữu.
- Consultant/admin xem hàng đợi; consultant phải nhận hội thoại trước khi trả lời và không thể giành hội thoại đã được người khác nhận.
- Tin nhắn không rỗng, tối đa 2.000 ký tự, chỉ gửi khi trạng thái `open`.
- Customer chủ sở hữu và admin được xóa. Xóa hội thoại xóa toàn bộ message liên quan.
- WebSocket xác thực JWT trước khi `accept`; mã đóng `4401` cho token/tài khoản không hợp lệ và `4403` khi không có quyền.

## Mã lỗi chung

| HTTP | Ý nghĩa |
|---:|---|
| 400 | Dữ liệu xung đột hoặc thao tác không hợp lệ |
| 401 | Thiếu, sai hoặc hết hạn token |
| 403 | Đã đăng nhập nhưng không có quyền |
| 404 | Không tìm thấy tài nguyên |
| 422 | Payload không đạt validation/quy tắc nghiệp vụ |
| 500 | Lỗi không dự kiến; không trả stack trace cho client |

Schema chi tiết, ví dụ request và response luôn lấy từ `/openapi.json` để tránh tài liệu lệch mã nguồn.
