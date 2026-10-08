# VinFast Digital Showroom — Backend

Backend cho showroom số VinFast, cung cấp API danh mục xe, báo giá, lịch lái thử, CRM và chat trực tiếp giữa khách hàng với nhân viên.

Đây là bản public của **Backend Pha 1**. Frontend, media sản phẩm, dữ liệu seed và database runtime chưa nằm trong repository này.

## Đặc tả bài toán nghiệp vụ

Showroom truyền thống thường xử lý việc hỏi xe, báo giá, đặt lịch và chăm sóc khách hàng qua nhiều kênh rời rạc. Thông tin dễ bị thất lạc, nhân viên khó theo dõi hàng đợi và khách hàng không có lịch sử xử lý thống nhất.

Trong bài toán này, **số hóa** nghĩa là chuyển các thao tác đó thành quy trình có dữ liệu, trạng thái, phân quyền và lịch sử rõ ràng:

| Cách làm thủ công | Quy trình trên hệ thống |
|---|---|
| Hỏi xe qua điện thoại/tin nhắn | Tra cứu danh mục xe qua API |
| Ghi báo giá bằng bảng tính hoặc ghi chú | Tạo và theo dõi yêu cầu báo giá |
| Đặt lịch bằng trao đổi riêng lẻ | Tạo lịch lái thử có trạng thái |
| Nhân viên tự giữ lịch sử hội thoại | Chat được lưu và phát realtime |
| Không rõ ai được xem dữ liệu nào | JWT, vai trò và quyền sở hữu tài nguyên |

### Câu hỏi nghiệp vụ trung tâm

Làm thế nào để chuyển sự quan tâm trực tuyến của khách hàng thành một quy trình bán hàng có thể theo dõi từ lúc xem xe, yêu cầu báo giá, đặt lịch lái thử đến khi được nhân viên tư vấn, mà mỗi người chỉ truy cập đúng dữ liệu thuộc quyền của mình?

### Luồng nghiệp vụ chính

```text
Khách xem xe
    → gửi yêu cầu báo giá hoặc đặt lịch lái thử
    → nhân viên tiếp nhận trong hàng đợi CRM
    → hai bên trao đổi qua chat
    → cập nhật trạng thái và lưu lại lịch sử xử lý
```

Pha 1 chỉ chứng minh luồng backend, dữ liệu và phân quyền cho quy trình này; không bao gồm chatbot AI, frontend hoàn chỉnh hay hệ thống bán hàng production.

## Phạm vi nghiệp vụ

- `customer`: xem xe, tính chi phí sở hữu, yêu cầu báo giá, đặt lịch lái thử và chat với nhân viên.
- `consultant`: xử lý báo giá, lịch lái thử, hồ sơ khách hàng và hội thoại hỗ trợ.
- `admin`: quản lý tài khoản, danh mục và toàn bộ nghiệp vụ của nhân viên.
- Xác thực bằng JWT; dữ liệu riêng được lọc theo tài khoản và vai trò.
- Chat được lưu trong database và cập nhật realtime bằng WebSocket.

Hệ thống không dùng chatbot, mô hình ngôn ngữ, vector database hoặc API key của dịch vụ AI.

## Kiến trúc

```text
HTTP/JSON + WebSocket
          │
          ▼
API layer                 backend/src/api/
          │
          ▼
Business services         backend/src/services/
          │
          ▼
Repository adapters       backend/src/repositories/
          │
          ▼
SQLAlchemy → SQLite / PostgreSQL
```

API layer chỉ tiếp nhận request và validation. Nghiệp vụ nằm trong service; repository cô lập truy cập dữ liệu. Danh tính người dùng lấy từ JWT thay vì tin `user_id` do client gửi.

Chi tiết: [Kiến trúc và thuộc tính chất lượng](docs/ARCHITECTURE.md).

## Cấu trúc chính

```text
api/                       entrypoint API
backend/src/               mã nguồn backend
backend/tests/             unit/integration tests
backend/Dockerfile         production image
docs/                      tài liệu API và kiến trúc
docker-compose.yml         cấu hình Docker
render.yaml                cấu hình Render
```

## Chạy cục bộ

Yêu cầu Python 3.10 trở lên. Chạy từ thư mục gốc bằng PowerShell:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Set-Location backend
uvicorn src.main:app --reload --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

Schema database được tạo tự động. Vì dữ liệu seed chưa public, danh mục ban đầu có thể trống.

## Chạy bằng Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

API chạy tại `http://localhost:8000`; SQLite runtime được lưu trong `./data` và không được commit.

## Endpoint chính

Base URL: `/api/v1`. Endpoint cần đăng nhập sử dụng `Authorization: Bearer <access_token>`.

| Nhóm | Endpoint | Mục đích |
|---|---|---|
| System | `GET /health` | Kiểm tra API và database |
| Auth | `/api/v1/auth` | Đăng ký, đăng nhập, tài khoản và phân quyền |
| Cars | `/api/v1/cars` | Danh mục ô tô |
| Motorbikes | `/api/v1/motorbikes` | Danh mục xe máy điện |
| Locations | `/api/v1/locations` | Showroom và trạm sạc |
| TCO | `POST /api/v1/tco/calculate` | Tính chi phí sở hữu |
| Quotes | `/api/v1/quotes` | Yêu cầu báo giá |
| Bookings | `/api/v1/bookings` | Đặt lịch lái thử |
| CRM | `/api/v1/customer-profiles` | Hồ sơ khách hàng |
| Chat | `/api/v1/conversations` | Hội thoại REST và WebSocket |

WebSocket chat:

```text
ws://localhost:8000/api/v1/conversations/{conversation_id}/ws?token=<jwt>
```

Quyền truy cập, payload và mã lỗi: [Đặc tả API](docs/API.md).

## Kiểm thử

```powershell
Set-Location backend
pytest -q
ruff check src tests
```

Test suite bao phủ xác thực, phân quyền, catalog, CRM, chat, OpenAPI contract và ranh giới kiến trúc.

## Kiểm thử tải trên Kaggle CPU

Mục tiêu là tạo baseline Pha 1 trong môi trường CPU cố định:

1. Chạy API với một Uvicorn worker và kiểm tra `/health` trả `200`.
2. Chạy cùng một kịch bản lần lượt với concurrency `1`, `4` và `8`.
3. Ghi lại CPU, RAM, throughput, p50/p95 và tỷ lệ lỗi.
4. Giữ nguyên dataset, thời lượng và cấu hình giữa các lần đo.

SQLite và một process Uvicorn là cấu hình cơ sở, không phải kiến trúc production cuối cùng. Xem [quy trình Kaggle CPU](docs/KAGGLE_LOAD_TEST.md).

## Kế hoạch Pha 2

| Thuộc tính | Vấn đề cần kiểm chứng | Hướng cải tiến |
|---|---|---|
| Hiệu năng | Danh sách lớn, ghi đồng thời | Phân trang, index, PostgreSQL |
| Tin cậy | SQLite và chưa có migration | PostgreSQL, Alembic, kiểm tra phục hồi |
| Bảo mật | Token chưa thu hồi, chưa rate limit | Refresh/revocation, rate limit, xoay secret |
| Bảo trì | Chức năng tăng dần | Tách module, mở rộng test và CI |

Ưu tiên Pha 2 sẽ được chọn dựa trên số liệu benchmark thay vì giả định.

## Tài liệu

- [Đặc tả API và WebSocket](docs/API.md)
- [Kiến trúc hệ thống](docs/ARCHITECTURE.md)
- [Phân công backend Pha 1](docs/PHASE1_BACKEND_ASSIGNMENT.md)
- [Kế hoạch Pha 1 và Pha 2](docs/PHASE_PLAN.md)
- [Quy trình load test trên Kaggle](docs/KAGGLE_LOAD_TEST.md)

## Lưu ý bảo mật

Không commit `.env`, token, private key, database hoặc credential thật. `.env.example` chỉ chứa giá trị mẫu.
