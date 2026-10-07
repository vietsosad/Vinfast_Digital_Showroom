# VinFast Digital Showroom

Backend showroom số gồm danh mục ô tô/xe máy điện, yêu cầu báo giá, đặt lịch lái thử, CRM gọn nhẹ và chat thời gian thực giữa khách hàng với nhân viên. Sản phẩm không dùng chatbot, mô hình ngôn ngữ, vector database hoặc API key của bên thứ ba.

Pha 1 của môn Kiến trúc phần mềm chỉ đánh giá backend. Thư mục `frontend/` được giữ làm client tham khảo cho API, không nằm trong artefact Docker hoặc tiêu chí nghiệm thu Pha 1.

## Phạm vi sản phẩm

Ba vai trò được hỗ trợ:

- `customer`: xem xe, so sánh, tính chi phí sở hữu, tạo báo giá/lịch lái thử và chat với nhân viên.
- `consultant`: xử lý báo giá, lịch lái thử, hồ sơ khách hàng và hàng đợi hội thoại.
- `admin`: toàn bộ quyền của nhân viên, quản lý tài khoản và dữ liệu danh mục.

Chat hỗ trợ được lưu trong database. REST API dùng để tải lịch sử và gửi tin tin cậy; WebSocket phát sự kiện mới theo thời gian thực. Pha 1 dùng bộ quản lý kết nối trong một process, phù hợp demo và kiểm thử trên một máy.

## Kiến trúc

```text
Swagger / HTTP client
    │  JSON/REST + WebSocket
    ▼
FastAPI API layer          backend/src/api/
    │  gọi use case
    ▼
Business layer             backend/src/services/support_chat.py
    │  ConversationRepository (Protocol)
    ▼
Data access layer          backend/src/repositories/support_chat.py
    │
    ▼
SQLAlchemy → SQLite hoặc PostgreSQL
```

`SupportChatService` là lõi nghiệp vụ của phạm vi mới. Module này không import FastAPI hoặc SQLAlchemy; kiểm thử unit chạy với repository in-memory. Xác thực JWT và phân quyền được đặt tại dependency dùng chung, không lặp logic đọc token trong từng endpoint.

Chi tiết quyết định kiến trúc: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Công nghệ

- Backend: Python 3.10+, FastAPI, Pydantic, SQLAlchemy async.
- Database: SQLite cho phát triển; PostgreSQL qua `asyncpg` cho môi trường dùng chung.
- Client tham khảo: React 18, TypeScript, Vite, Tailwind CSS; không thuộc phạm vi Pha 1.
- Realtime: WebSocket của FastAPI.
- Kiểm thử: pytest, pytest-asyncio, HTTPX.
- Đóng gói: Docker multi-stage, chạy bằng user không phải root.

## Chạy local

Backend:

```powershell
Copy-Item .env.example .env
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/seed_catalog_from_frontend.py
uvicorn src.main:app --reload --port 8000
```

Nếu cần thử client tham khảo, chạy ở terminal khác:

```powershell
cd frontend
npm install
npm run dev
```

Mở `http://localhost:5173`. Swagger UI ở `http://localhost:8000/docs`, OpenAPI JSON ở `http://localhost:8000/openapi.json`.

Tài khoản demo được tạo tự động nếu chưa tồn tại:

| Vai trò | Email | Mật khẩu |
|---|---|---|
| Admin | `admin@vinfast.vn` | `admin123` |
| Nhân viên | `staff@vinfast.vn` | `staff123` |
| Khách hàng | `customer@gmail.com` | `123456` |

Các mật khẩu trên chỉ dùng cho local/demo. Đặt `APP_ENV=production` và thay `SECRET_KEY` bằng chuỗi ngẫu nhiên dài khi triển khai.

## PostgreSQL

Đặt URL async trong `.env`, không commit thông tin xác thực:

```dotenv
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
```

Ứng dụng tự tạo các bảng còn thiếu khi khởi động. Script seed catalog dùng upsert, không xóa dữ liệu đã có:

```powershell
Set-Location backend
python scripts/seed_catalog_from_frontend.py
```

## Docker

```powershell
docker compose up --build
```

Container chỉ đóng gói backend và phục vụ API tại `http://localhost:8000`; dữ liệu SQLite được lưu ở `./data`. File `.env` là tùy chọn cho local nhưng bắt buộc phải cung cấp `SECRET_KEY` riêng khi đặt `APP_ENV=production`.

## Kiểm thử và kiểm tra chất lượng

```powershell
Set-Location backend
pytest -q
ruff check src tests
```

Load test không cần cài thêm thư viện:

```powershell
Set-Location backend
python scripts/load_test.py --base-url http://127.0.0.1:8000 --duration 120 --concurrency 20
```

Quy trình cố định cấu hình Kaggle CPU và cách báo cáo trước/sau nằm tại [docs/KAGGLE_LOAD_TEST.md](docs/KAGGLE_LOAD_TEST.md).

## Tài liệu

- [Đặc tả API và WebSocket](docs/API.md)
- [Kiến trúc và các thuộc tính chất lượng](docs/ARCHITECTURE.md)
- [Phân công backend Pha 1](docs/PHASE1_BACKEND_ASSIGNMENT.md)
- [Bản phân công one-page](docs/PHASE1_BACKEND_REPORT_ONE_PAGE.md)
- [Kế hoạch Pha 1 và Pha 2](docs/PHASE_PLAN.md)
- [Quy trình load test Kaggle](docs/KAGGLE_LOAD_TEST.md)

## Cấu trúc chính

```text
backend/src/api/              HTTP/WebSocket adapters
backend/src/services/         business use cases và dịch vụ ứng dụng
backend/src/repositories/     data-access adapters
backend/src/models/           ORM models và API schemas
backend/tests/                unit/integration tests
backend/scripts/              seed dữ liệu và load test
backend/Dockerfile            backend-only production image
data/                         catalog seed có thể review
static/                       ảnh và tệp media do backend phục vụ
docs/                         tài liệu chuẩn của sản phẩm
frontend/src/                 client tham khảo, ngoài Pha 1
```

## Nhóm phát triển

- Lê Hoàng Việt — Lead, kiến trúc và tích hợp.
- Hoàng Lê Minh — backend nghiệp vụ, dữ liệu và kiểm thử tải.
- Nguyễn Văn Toán — realtime chat, supporting API và kiểm thử tích hợp.

Phân công theo deliverable và tiêu chí nghiệm thu được mô tả trong [docs/PHASE_PLAN.md](docs/PHASE_PLAN.md).
