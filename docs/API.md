# Đặc tả API

Base URL chuẩn: `/api/v1`. Mọi request và response dùng **JSON**, trừ ba endpoint tải ảnh nhận `multipart/form-data` (đánh dấu 📎 bên dưới). Schema chi tiết của từng request/response luôn lấy từ OpenAPI.

## Đặc tả OpenAPI và cách xem trước

[openapi.json](openapi.json) là đặc tả OpenAPI 3.1 máy đọc được (46 operation, 51 schema, security scheme `HTTPBearer`). `tests/test_openapi_snapshot.py` bảo đảm file luôn khớp với runtime; khi đổi API, chạy `python backend/scripts/export_openapi.py` để cập nhật.

| Cách xem | Địa chỉ |
|---|---|
| ReDoc, không cần chạy server | <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/vietsosad/Vinfast_Digital_Showroom/main/docs/openapi.json> |
| Swagger Editor, không cần chạy server | <https://editor.swagger.io/?url=https://raw.githubusercontent.com/vietsosad/Vinfast_Digital_Showroom/main/docs/openapi.json> |
| Swagger UI khi chạy server (gọi thử được) | `http://localhost:8000/docs` |
| ReDoc khi chạy server | `http://localhost:8000/redoc` |
| JSON runtime | `http://localhost:8000/openapi.json` |

## Xác thực

`POST /api/v1/auth/login` trả JWT; gửi kèm mọi request được bảo vệ:

```http
Authorization: Bearer <access_token>
```

OpenAPI khai báo security scheme `HTTPBearer`. Một dependency dùng chung (`get_current_user`) đọc token, kiểm tra tài khoản còn hoạt động; `require_roles` áp dụng role. Không endpoint nào tự đọc token. Client không thể gửi `user_id`, tên, số điện thoại hay giá để giả danh/tác động: backend lấy danh tính từ token và tên/giá xe từ catalog.

Role:

- `customer`: khách hàng.
- `consultant`: nhân viên tư vấn (UI có thể hiển thị là `staff`).
- `admin`: quản trị viên.

## Endpoint

Ký hiệu quyền: `Public`, `C` customer, `S` consultant, `A` admin, `Auth` mọi tài khoản đăng nhập.

| Method | Path | Quyền | Mục đích |
|---|---|---:|---|
| GET | `/health` | Public | Trạng thái API và database (503 khi DB lỗi) |
| POST | `/api/v1/auth/register` | Public | Đăng ký customer (email, số điện thoại là duy nhất) |
| POST | `/api/v1/auth/login` | Public | Nhận JWT |
| GET | `/api/v1/auth/me` | Auth | Tài khoản hiện tại |
| PUT | `/api/v1/auth/me` | Auth | Sửa họ tên, số điện thoại (bắt buộc, duy nhất), mật khẩu (bỏ trống = giữ nguyên) |
| GET | `/api/v1/auth/users` | A | Danh sách tài khoản |
| POST | `/api/v1/auth/create-staff` | A | Tạo `consultant` hoặc `admin` |
| PUT | `/api/v1/auth/users/{id}` | Chủ tài khoản/A | Sửa tài khoản; chỉ A đổi `role`/`is_active` |
| DELETE | `/api/v1/auth/users/{id}` | A | Xóa tài khoản (không tự xóa) |
| GET | `/api/v1/cars` | Public | Danh sách ô tô, lọc `?category=` |
| GET | `/api/v1/cars/{id-or-code}` | Public | Chi tiết ô tô theo UUID hoặc mã dòng xe |
| POST | `/api/v1/cars` | S/A | Tạo ô tô (JSON) |
| PUT | `/api/v1/cars/{id}` | S/A | Cập nhật một phần (JSON) |
| POST 📎 | `/api/v1/cars/{id}/image` | S/A | Tải ảnh đại diện (field `image`) |
| DELETE | `/api/v1/cars/{id}` | A | Xóa ô tô |
| GET | `/api/v1/motorbikes` | Public | Danh sách xe máy điện |
| GET | `/api/v1/motorbikes/{id-or-code}` | Public | Chi tiết xe máy điện |
| POST | `/api/v1/motorbikes` | S/A | Tạo xe máy điện (JSON) |
| PUT | `/api/v1/motorbikes/{id}` | S/A | Cập nhật một phần (JSON) |
| POST 📎 | `/api/v1/motorbikes/{id}/image` | S/A | Tải ảnh đại diện (field `image`) |
| DELETE | `/api/v1/motorbikes/{id}` | A | Xóa xe máy điện |
| GET | `/api/v1/catalog-media/{vehicle-type}/{vehicle-id}` | Public | Thư viện ảnh của xe |
| POST | `/api/v1/catalog-media/{vehicle-type}/{vehicle-id}/links` | S/A | Thêm tối đa 100 URL ảnh (JSON) |
| POST 📎 | `/api/v1/catalog-media/{vehicle-type}/{vehicle-id}/upload` | S/A | Tải tối đa 20 ảnh (field `files`) |
| PUT | `/api/v1/catalog-media/{media-id}` | S/A | Cập nhật metadata hoặc ảnh chính |
| DELETE | `/api/v1/catalog-media/{media-id}` | S/A | Xóa ảnh |
| GET | `/api/v1/locations` | Public | Showroom/trạm sạc, lọc `demand_type`, `province`, `search` |
| POST | `/api/v1/locations/sync` | A | Nạp lại dataset địa điểm (idempotent) |
| POST | `/api/v1/tco/calculate` | Public | Ước tính chi phí lăn bánh và vận hành |
| GET | `/api/v1/quotes` | Auth | C: luôn chỉ của mình; S/A: lọc `user_id`, `email`, `phone`, `status` |
| POST | `/api/v1/quotes` | Auth | Yêu cầu báo giá cho chính mình |
| PUT | `/api/v1/quotes/{id}` | S/A | Đổi trạng thái, ghi chú, chiết khấu |
| GET | `/api/v1/bookings` | Auth | C: luôn chỉ của mình; S/A: lọc `phone`, `status` |
| POST | `/api/v1/bookings` | Auth | Đặt lịch lái thử cho chính mình |
| PUT | `/api/v1/bookings/{id}` | S/A | Đổi trạng thái lịch |
| GET | `/api/v1/customer-profiles/me` | Auth | Hồ sơ CRM của mình |
| GET | `/api/v1/customer-profiles` | S/A | Tra cứu hồ sơ CRM |
| GET | `/api/v1/customer-profiles/{id}` | S/A | Chi tiết hồ sơ CRM |
| PUT | `/api/v1/customer-profiles/{id}` | S/A | Cập nhật lead/ghi chú thủ công |
| POST | `/api/v1/conversations` | C | Mở hội thoại hỗ trợ |
| GET | `/api/v1/conversations` | Auth | C: của mình; S/A: hàng đợi |
| GET | `/api/v1/conversations/{id}/messages` | Thành viên/S/A | Lịch sử tin nhắn |
| POST | `/api/v1/conversations/{id}/messages` | Thành viên/S/A | Gửi và phát tin nhắn |
| POST | `/api/v1/conversations/{id}/assign` | S/A | Nhận xử lý hội thoại |
| POST | `/api/v1/conversations/{id}/close` | Thành viên/S/A | Đóng hội thoại |
| DELETE | `/api/v1/conversations/{id}` | Chủ sở hữu/A | Xóa hội thoại và tin nhắn |

`/api/...` (không có `v1`) là alias ẩn khỏi OpenAPI cho client web cũ.

## Ví dụ

Đặt lịch lái thử — chỉ cần xe, ngày, giờ, ghi chú:

```http
POST /api/v1/bookings
Authorization: Bearer <customer-token>
Content-Type: application/json

{"vehicle_id": "9c5c27b7-0f05-49eb-b90b-49c10c0577fe", "preferred_date": "2026-10-22", "preferred_time": "09:30", "notes": "Showroom Long Biên"}
```

```json
{
  "id": "0df6a8a1-dba9-4d34-b829-9f85bda48e7f",
  "user_id": "e79a958d-08b1-415f-96f7-e8433911e93b",
  "customer_name": "Khách hàng Demo",
  "customer_phone": "0900000003",
  "vehicle_id": "9c5c27b7-0f05-49eb-b90b-49c10c0577fe",
  "vehicle_name": "VinFast VF 2 Tiêu chuẩn",
  "preferred_date": "2026-10-22",
  "preferred_time": "09:30",
  "status": "pending",
  "notes": "Showroom Long Biên",
  "created_at": "2026-10-15T16:14:40"
}
```

Quy tắc: ngày (theo giờ Việt Nam, UTC+7) không ở quá khứ và không quá 180 ngày; giờ dạng `HH:MM`; xe phải tồn tại và đang kinh doanh.

Yêu cầu báo giá — giá và tên xe do backend lấy từ catalog:

```http
POST /api/v1/quotes
Content-Type: application/json

{"vehicle_id": "9c5c27b7-0f05-49eb-b90b-49c10c0577fe", "request_note": "Muốn nhận giá lăn bánh tại Hà Nội"}
```

Nhân viên duyệt và áp chiết khấu. `base_price` luôn là giá catalog. Nếu không gửi `final_price` thì `final_price = base_price − discount` (`0 ≤ discount ≤ base_price`); nếu gửi `final_price` (giá lăn bánh đã gồm phí, ≥ 0) thì backend lưu đúng giá nhân viên chốt:

```http
PUT /api/v1/quotes/{id}
Content-Type: application/json

{"status": "approved", "discount": 10000000, "notes": "Ưu đãi tháng 10"}
```

Tạo ô tô (JSON) rồi tải ảnh:

```http
POST /api/v1/cars
Content-Type: application/json

{"model_name": "VinFast VF 6 Plus", "version": "Plus", "list_price": 765000000, "range_km": 460, "additional_specs": {"colors": ["Trắng", "Đen"]}}
```

```http
POST /api/v1/cars/{id}/image
Content-Type: multipart/form-data; boundary=...

image=<file .jpg|.jpeg|.png|.webp|.avif, tối đa 8 MB>
```

Ảnh bị từ chối nếu phần mở rộng, MIME khai báo và chữ ký tệp (magic bytes) không khớp nhau.

## Trạng thái nghiệp vụ

| Đối tượng | Giá trị | Chuyển hợp lệ |
|---|---|---|
| Quote | `pending`, `contacted`, `approved`, `completed`, `rejected`, `cancelled` | `pending → contacted/approved/rejected/cancelled`; `contacted → approved/rejected/cancelled`; `approved → completed/cancelled` |
| Booking | `pending`, `confirmed`, `completed`, `cancelled` | `pending → confirmed/cancelled`; `confirmed → completed/cancelled` |
| Lead score | `HOT`, `WARM`, `COLD` | tự do (nhân viên) |
| Lead status | `NEW`, `CONTACTED`, `TEST_DRIVEN`, `QUOTED`, `WON`, `LOST` | tự do (nhân viên); hệ thống tự cập nhật khi có quote/booking |

Gửi lại đúng trạng thái hiện tại được chấp nhận (để chỉ sửa ghi chú/chiết khấu).

## Luồng hội thoại

```http
POST /api/v1/conversations
Authorization: Bearer <customer-token>
Content-Type: application/json

{"subject": "Đặt lịch lái thử VF 6"}
```

```http
POST /api/v1/conversations/{conversation_id}/messages
Content-Type: application/json

{"content": "Tôi muốn lái thử vào sáng thứ Bảy."}
```

Realtime channel:

```text
ws://localhost:8000/api/v1/conversations/{conversation_id}/ws?token=<jwt>
```

Client gửi `{"content": "..."}`; server phát:

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

Các event khác: `conversation_updated`, `conversation_deleted`, `error`. Quy tắc:

- Chỉ customer mở hội thoại; subject 3–160 ký tự. Customer chỉ đọc hội thoại của mình.
- Consultant phải nhận hội thoại trước khi trả lời và không giành hội thoại người khác đã nhận; admin có thể.
- Tin nhắn không rỗng, tối đa 2.000 ký tự, chỉ gửi khi `open`.
- WebSocket xác thực JWT trước khi `accept`: đóng `4401` khi token/tài khoản không hợp lệ, `4403` khi không có quyền với hội thoại.

## Mã lỗi

Mọi lỗi có dạng `{"detail": "..."}` (lỗi validation của FastAPI trả `detail` là danh sách).

| HTTP | Ý nghĩa |
|---:|---|
| 401 | Thiếu, sai, hết hạn token hoặc tài khoản bị khóa (kèm `WWW-Authenticate: Bearer`) |
| 403 | Đã đăng nhập nhưng không đủ quyền; hoặc đăng nhập vào tài khoản bị khóa |
| 404 | Không tìm thấy tài nguyên |
| 409 | Xung đột: email/số điện thoại đã tồn tại, chuyển trạng thái không hợp lệ, admin tự hạ quyền/tự xóa |
| 413 | Tệp tải lên vượt giới hạn |
| 422 | Payload sai schema hoặc vi phạm quy tắc nghiệp vụ (ngày quá khứ, chiết khấu vượt giá, ảnh giả…) |
| 500 | Lỗi không dự kiến; trả thông báo chung, không lộ stack trace |
| 503 | `/health`: database không truy cập được |
