# VinFast Digital Showroom — Backend

VinFast Digital Showroom là hệ thống backend cho showroom số, cung cấp API để tra cứu xe, quản lý yêu cầu tư vấn và hỗ trợ khách hàng theo thời gian thực.

Repository này là bản backend Pha 1, tập trung vào kiến trúc, nghiệp vụ, API và kiểm thử. Giao diện web, media sản phẩm, dữ liệu seed và database runtime chưa được public trong phiên bản hiện tại.

## Sản phẩm làm gì?

Hệ thống phục vụ ba nhóm người dùng:

- `customer`: xem danh mục xe, tính chi phí sở hữu, gửi yêu cầu báo giá, đặt lịch lái thử và trao đổi với nhân viên.
- `consultant`: tiếp nhận báo giá, lịch lái thử, hồ sơ khách hàng và hội thoại hỗ trợ.
- `admin`: có toàn bộ quyền của nhân viên, đồng thời quản lý tài khoản và dữ liệu danh mục.

Các nhóm nghiệp vụ chính:

- Đăng ký, đăng nhập bằng JWT và quản lý hồ sơ tài khoản.
- Danh mục ô tô, xe máy điện và media của xe.
- Danh sách showroom/trạm sạc và tính tổng chi phí sở hữu (TCO).
- Yêu cầu báo giá, đặt lịch lái thử và CRM gọn nhẹ.
- Chat trực tiếp giữa khách hàng và nhân viên qua REST + WebSocket.

Chat được lưu trong database và không sử dụng chatbot, mô hình ngôn ngữ, vector database hoặc API key của dịch vụ AI.

## Kiến trúc tổng quan

```text
Swagger / Web client / HTTP client
                 │
                 │  JSON/REST + WebSocket
                 ▼
API layer                         backend/src/api/
                 │
                 │  gọi use case
                 ▼
Business services                 backend/src/services/
                 │
                 │  repository interface/adapter
                 ▼
Data access                       backend/src/repositories/
                 │
                 ▼
SQLAlchemy ORM → SQLite hoặc PostgreSQL
```

Nguyên tắc chính:

- API layer xử lý HTTP/WebSocket và validation; nghiệp vụ nằm trong service.
- Repository cô lập truy cập dữ liệu khỏi nghiệp vụ.
- Danh tính người dùng được lấy từ JWT, không tin `user_id` do client tự gửi.
- Quyền truy cập được kiểm tra theo vai trò và quyền sở hữu tài nguyên.
- SQLite phù hợp chạy local; PostgreSQL dùng cho môi trường chia sẻ.
- WebSocket phát sự kiện realtime trong một process; REST vẫn là đường gửi và tải lịch sử tin cậy.

Xem chi tiết tại [Tài liệu kiến trúc](docs/ARCHITECTURE.md).

## Cấu trúc hiện tại

```text
api/                          entrypoint API cho môi trường serverless
backend/
├── src/
│   ├── api/                  REST/WebSocket adapters
│   ├── models/               ORM models và API schemas
│   ├── repositories/         data-access adapters
│   └── services/             nghiệp vụ và dịch vụ ứng dụng
├── tests/                    unit/integration tests
├── Dockerfile                backend-only production image
└── requirements.txt
docs/                         đặc tả API và tài liệu kiến trúc
static/.gitkeep               placeholder, chưa chứa media
docker-compose.yml            cấu hình chạy Docker
render.yaml                   cấu hình triển khai Render
```

## Yêu cầu

- Python 3.10 trở lên.
- Docker Desktop hoặc Docker Engine nếu chạy bằng container.
- Không cần API key bên thứ ba để chạy backend.

## Chạy cục bộ

Từ thư mục gốc repository, dùng PowerShell:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Set-Location backend
uvicorn src.main:app --reload --port 8000
```

Sau khi server khởi động:

- API base URL: `http://localhost:8000/api/v1`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

Ứng dụng tự tạo schema database khi khởi động. Do dataset seed chưa được public, danh mục xe ban đầu có thể trống và có thể được tạo qua API bằng tài khoản đủ quyền.

## Chạy bằng Docker

Từ thư mục gốc repository:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Backend được phục vụ tại `http://localhost:8000`. SQLite runtime được lưu trong `./data` và không được commit.

Dừng hệ thống:

```powershell
docker compose down
```

## Đặc tả endpoint

Base URL chuẩn: `/api/v1`. Các endpoint cần xác thực sử dụng:

```http
Authorization: Bearer <access_token>
```

| Nhóm | Endpoint chính | Quyền | Mục đích |
|---|---|---|---|
| System | `GET /health` | Public | Kiểm tra API và database |
| Auth | `POST /api/v1/auth/register` | Public | Đăng ký khách hàng |
| Auth | `POST /api/v1/auth/login` | Public | Đăng nhập và nhận JWT |
| Auth | `GET, PUT /api/v1/auth/me` | Đã đăng nhập | Xem hoặc cập nhật tài khoản hiện tại |
| Cars | `GET /api/v1/cars` | Public | Danh sách ô tô |
| Cars | `POST, PUT, DELETE /api/v1/cars/...` | Consultant/Admin; xóa: Admin | Quản trị danh mục ô tô |
| Motorbikes | `GET /api/v1/motorbikes` | Public | Danh sách xe máy điện |
| Motorbikes | `POST, PUT, DELETE /api/v1/motorbikes/...` | Consultant/Admin; xóa: Admin | Quản trị danh mục xe máy điện |
| Locations | `GET /api/v1/locations` | Public | Showroom và trạm sạc |
| TCO | `POST /api/v1/tco/calculate` | Public | Tính chi phí sở hữu |
| Quotes | `GET, POST /api/v1/quotes` | Đã đăng nhập | Xem hoặc tạo yêu cầu báo giá |
| Bookings | `GET, POST /api/v1/bookings` | Đã đăng nhập | Xem hoặc đặt lịch lái thử |
| CRM | `/api/v1/customer-profiles` | Theo vai trò | Hồ sơ và ghi chú khách hàng |
| Chat | `/api/v1/conversations` | Theo vai trò | Mở, nhận xử lý và đóng hội thoại |
| Media | `/api/v1/catalog-media/...` | Theo vai trò | Xem hoặc quản lý media của xe |

WebSocket chat:

```text
ws://localhost:8000/api/v1/conversations/{conversation_id}/ws?token=<jwt>
```

Danh sách đầy đủ, quyền truy cập, payload và mã lỗi nằm trong [Đặc tả API](docs/API.md). Schema thực tế luôn có tại `/openapi.json`.

## Tài khoản demo

Trong môi trường development, hệ thống tự tạo các tài khoản sau nếu chưa tồn tại:

| Vai trò | Email | Mật khẩu |
|---|---|---|
| Admin | `admin@vinfast.vn` | `admin123` |
| Nhân viên | `staff@vinfast.vn` | `staff123` |
| Khách hàng | `customer@gmail.com` | `123456` |

Các tài khoản này chỉ dùng để demo cục bộ. Không sử dụng mật khẩu mẫu hoặc `SECRET_KEY` mặc định trong production.

## Kiểm thử và chất lượng mã

```powershell
Set-Location backend
pytest -q
ruff check src tests
```

Test suite bao phủ xác thực, phân quyền, catalog, CRM, chat, contract OpenAPI và ranh giới giữa các tầng.

## Cấu hình môi trường

Các biến chính nằm trong `.env.example`:

| Biến | Ý nghĩa |
|---|---|
| `APP_ENV` | `development`, `test` hoặc `production` |
| `APP_HOST`, `APP_PORT` | Địa chỉ và cổng chạy API |
| `SECRET_KEY` | Khóa ký JWT; bắt buộc thay trong production |
| `DATABASE_URL` | URL kết nối SQLite hoặc PostgreSQL async |
| `CORS_ORIGINS` | Danh sách origin được phép gọi API |

Ví dụ PostgreSQL:

```dotenv
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
```

Không commit `.env`, token, private key, database hoặc credential thật.

## Tài liệu

- [Đặc tả API và WebSocket](docs/API.md)
- [Kiến trúc và thuộc tính chất lượng](docs/ARCHITECTURE.md)
- [Phân công backend Pha 1](docs/PHASE1_BACKEND_ASSIGNMENT.md)
- [Bản phân công one-page](docs/PHASE1_BACKEND_REPORT_ONE_PAGE.md)
- [Kế hoạch Pha 1 và Pha 2](docs/PHASE_PLAN.md)
- [Quy trình load test trên Kaggle](docs/KAGGLE_LOAD_TEST.md)

## Giới hạn của bản hiện tại

- Chưa public frontend và media sản phẩm.
- Chưa kèm dataset catalog hoặc script seed/load test.
- Realtime WebSocket dùng connection manager trong một process, phù hợp demo và kiểm thử Pha 1; khi scale nhiều instance cần message broker/pub-sub.
