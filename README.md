# VinFast Digital Showroom — Backend Pha 1

Đây là bản phát hành **backend tối giản** của VinFast Digital Showroom phục vụ Pha 1 môn Kiến trúc phần mềm. Repository hiện tập trung vào API, nghiệp vụ, kiểm thử và tài liệu kiến trúc; chưa chứa toàn bộ sản phẩm hoàn chỉnh.

## Phạm vi hiện đã public

- REST API và WebSocket xây dựng bằng FastAPI.
- Xác thực JWT và phân quyền `customer`, `consultant`, `admin`.
- API danh mục ô tô và xe máy điện.
- Yêu cầu báo giá, đặt lịch lái thử và hồ sơ khách hàng.
- Tính chi phí sở hữu (TCO).
- Chat thời gian thực giữa khách hàng và nhân viên; không sử dụng chatbot hoặc mô hình ngôn ngữ.
- SQLite cho local, hỗ trợ PostgreSQL qua `asyncpg`.
- Unit/integration test, Docker và cấu hình triển khai Render.
- Tài liệu API, kiến trúc và kế hoạch Pha 1 trong `docs/`.

## Chưa có trong bản public này

Các thành phần sau vẫn được giữ trong dự án nội bộ và sẽ chỉ được bổ sung khi cần:

- Giao diện `frontend/`.
- Ảnh, video và các media tĩnh của showroom.
- Dữ liệu catalog/seed và các script import, seed, load test.
- Database và dữ liệu runtime.

Vì vậy, repository này hiện phù hợp để đọc kiến trúc, chạy API, kiểm thử backend và phát triển nghiệp vụ; chưa phải bản showroom đầy đủ có giao diện và dữ liệu sản phẩm hoàn chỉnh.

## Kiến trúc

```text
HTTP client / Swagger / WebSocket
                │
                ▼
FastAPI adapters             backend/src/api/
                │
                ▼
Business services            backend/src/services/
                │
                ▼
Repository adapters          backend/src/repositories/
                │
                ▼
SQLAlchemy → SQLite hoặc PostgreSQL
```

Nghiệp vụ được tách khỏi lớp HTTP và data access. Chi tiết xem tại [Tài liệu kiến trúc](docs/ARCHITECTURE.md).

## Cấu trúc repository

```text
api/                          entrypoint API tương thích môi trường serverless
backend/src/api/              REST/WebSocket adapters
backend/src/services/         business use cases
backend/src/repositories/     data-access adapters
backend/src/models/           ORM models và API schemas
backend/tests/                unit/integration tests
backend/Dockerfile            backend-only production image
docs/                         tài liệu API và kiến trúc
static/.gitkeep               placeholder; chưa public media
docker-compose.yml            cấu hình chạy backend bằng Docker
render.yaml                   cấu hình triển khai Render
```

## Công nghệ

- Python 3.10+
- FastAPI, Pydantic
- SQLAlchemy async, SQLite/PostgreSQL
- WebSocket
- pytest, pytest-asyncio, HTTPX
- Docker multi-stage

## Chạy local

Yêu cầu Python 3.10 trở lên. Từ thư mục gốc repository:

```powershell
Set-Location backend
Copy-Item ..\.env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

Sau khi server khởi động:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

Ứng dụng tự tạo schema database khi khởi động. Do dữ liệu seed chưa nằm trong bản public này, danh mục ban đầu có thể trống.

## Tài khoản demo

Trong môi trường development, các tài khoản sau được tạo tự động nếu chưa tồn tại:

| Vai trò | Email | Mật khẩu |
|---|---|---|
| Admin | `admin@vinfast.vn` | `admin123` |
| Nhân viên | `staff@vinfast.vn` | `staff123` |
| Khách hàng | `customer@gmail.com` | `123456` |

Các mật khẩu này chỉ dùng cho local/demo. Khi triển khai production, đặt `APP_ENV=production` và cung cấp `SECRET_KEY` ngẫu nhiên có độ dài an toàn.

## Chạy bằng Docker

Từ thư mục gốc repository:

```powershell
docker compose up --build
```

API được phục vụ tại `http://localhost:8000`. Dữ liệu SQLite runtime được tạo trong thư mục `data/` ở máy local và không được commit.

## Kiểm thử và lint

```powershell
Set-Location backend
pytest -q
ruff check src tests
```

Test suite hiện có 30 bài kiểm thử cho API, phân quyền, nghiệp vụ, contract và ranh giới kiến trúc.

## Tài liệu

- [Đặc tả API và WebSocket](docs/API.md)
- [Kiến trúc và các thuộc tính chất lượng](docs/ARCHITECTURE.md)
- [Phân công backend Pha 1](docs/PHASE1_BACKEND_ASSIGNMENT.md)
- [Bản phân công one-page](docs/PHASE1_BACKEND_REPORT_ONE_PAGE.md)
- [Kế hoạch Pha 1 và Pha 2](docs/PHASE_PLAN.md)
- [Quy trình load test trên Kaggle](docs/KAGGLE_LOAD_TEST.md)

## Lưu ý bảo mật

- Không commit `.env`, database hoặc credential thật.
- Đổi `SECRET_KEY` trước khi chạy production.
- Không sử dụng các tài khoản demo cho dữ liệu thật.
- Repository không yêu cầu API key của dịch vụ AI hoặc bên thứ ba.
