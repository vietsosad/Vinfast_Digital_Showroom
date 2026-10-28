# VinFast Digital Showroom — Backend

Backend cho showroom số VinFast, cung cấp API danh mục xe, báo giá, lịch lái thử, CRM và chat trực tiếp giữa khách hàng với nhân viên.

Đây là bản public của **Backend Pha 1**. Frontend, ảnh sản phẩm và database runtime không nằm trong repository này; dữ liệu catalog tham chiếu nằm trong `data/catalog/` và được nạp tự động khi database rỗng.

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

## Đáp ứng yêu cầu Pha 1

| Yêu cầu Pha 1 | Cách đáp ứng | Bằng chứng |
|---|---|---|
| REST + JSON, có GET/POST/DELETE | 46 operation (16 GET, 17 POST, 8 PUT, 5 DELETE); mọi request/response JSON, trừ 3 endpoint tải ảnh `multipart/form-data` | [docs/openapi.json](docs/openapi.json), `tests/test_openapi_contract.py` |
| Tài liệu OpenAPI/Swagger | `/docs`, `/openapi.json`; snapshot commit trong repo và được test so khớp runtime | `tests/test_openapi_snapshot.py` |
| API → Nghiệp vụ → Truy cập dữ liệu | 4 package `api/`, `application/`, `domain/`, `infrastructure/`; tầng nghiệp vụ không import FastAPI/SQLAlchemy/Pydantic | `tests/test_architecture.py` (quét toàn bộ backend) |
| Repository/DAL dùng ORM | 9 repository SQLAlchemy sau các protocol ở `domain/`; Unit of Work giữ 1 transaction/use case | `backend/src/infrastructure/repositories/` |
| Đăng nhập, GET/POST cần xác thực | JWT Bearer; mọi GET/POST được bảo vệ trả 401 khi thiếu/sai token | contract test lặp qua **tất cả** operation có security |
| Xác thực qua middleware/dependency | `get_current_user` + `require_roles` dùng chung tại `api/dependencies.py` | không endpoint nào tự đọc token |
| Docker | Multi-stage, non-root (uid 10001), healthcheck trả 503 khi DB lỗi, seed dữ liệu khi DB rỗng | CI job `docker`: build → smoke → restart → healthy |
| Kiểm thử tải Kaggle CPU | Notebook + script đo + script tổng hợp median | [loadtest/](loadtest/README.md), [docs/KAGGLE_LOAD_TEST.md](docs/KAGGLE_LOAD_TEST.md) |

Chi tiết từng tiêu chí và trạng thái nghiệm thu: [docs/PHASE1_ACCEPTANCE.md](docs/PHASE1_ACCEPTANCE.md).

## Kiến trúc

```text
HTTP / WebSocket client
        │  JSON
        ▼
api/              FastAPI router, Pydantic schema, status code, auth dependency, map lỗi → HTTP
        │  gọi use case
        ▼
application/      Use case: điều phối repository, phân quyền nghiệp vụ, commit đúng 1 lần
        │
        ▼
domain/           Entity, enum trạng thái + bảng chuyển trạng thái, lỗi nghiệp vụ, Repository/UnitOfWork protocol
        ▲  implements
        │
infrastructure/   SQLAlchemy ORM + repository, Unit of Work, JWT, PBKDF2, lưu file, migration, seed
        │
        ▼
SQLite (local, Docker) hoặc PostgreSQL (asyncpg)
```

Quy tắc phụ thuộc (được kiểm tra tự động):

- `domain/` và `application/` là Python thuần: không import `fastapi`, `starlette`, `pydantic`, `sqlalchemy`, driver DB, `jwt`, `passlib`, và không import `api/` hay `infrastructure/`.
- `api/` không import SQLAlchemy. Chỉ `api/dependencies.py` (composition root) được import `infrastructure/` để gắn repository vào use case.
- `infrastructure/` không import tầng web.

Danh tính người dùng lấy từ JWT thay vì tin `user_id` do client gửi. Một use case = một transaction: ví dụ tạo báo giá ghi `quotes` và cập nhật `customer_profiles` rồi mới commit; nếu bước CRM lỗi thì báo giá cũng rollback (`tests/test_transactions.py`).

Chi tiết: [Kiến trúc và thuộc tính chất lượng](docs/ARCHITECTURE.md).

## Cấu trúc chính

```text
api/index.py                     adapter ASGI import backend/src/main.py
backend/src/api/                 Router HTTP/WebSocket, schema Pydantic, dependencies (composition root), map lỗi
backend/src/application/         Use case (auth, catalog, quote, booking, CRM, location, chat, media, TCO, upload)
backend/src/domain/              Entity, enum trạng thái, quy tắc, lỗi, repository & unit-of-work protocol
backend/src/infrastructure/      ORM, repository SQLAlchemy, unit of work, JWT/PBKDF2, file storage, migration, seed
backend/src/main.py              Tạo FastAPI app, middleware CORS, mount /static, lifespan
backend/tests/                   unit/, test_api/, kiến trúc, contract, migration, transaction
backend/scripts/                 smoke test, load test + tổng hợp, export OpenAPI/catalog, công cụ seed
backend/Dockerfile               Image backend Pha 1
data/catalog/vehicles.json       Dữ liệu catalog tham chiếu, nạp khi bảng rỗng
loadtest/                        Notebook Kaggle và kết quả đo
docs/                            Tài liệu API, kiến trúc và nghiệm thu
docker-compose.yml               Cấu hình Docker
render.yaml                      cấu hình Render
```

## Chạy cục bộ

Yêu cầu Python 3.10 trở lên. Chạy từ thư mục gốc bằng PowerShell:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements-dev.txt -c backend/constraints.txt
Set-Location backend
uvicorn src.main:app --reload --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

Khi khởi động, ứng dụng tự tạo bảng còn thiếu, chạy migration idempotent và nạp catalog từ `data/catalog/vehicles.json` cùng mạng lưới địa điểm **nếu bảng đang rỗng**. Ngoài môi trường production, ứng dụng tạo thêm tài khoản demo cho từng vai trò.

Cấu hình qua biến môi trường (xem [.env.example](.env.example)): `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `STATIC_DIR`, `SEED_DATA_DIR`, `SEED_REFERENCE_DATA`, `SEED_DEMO_ACCOUNTS`, `MAX_UPLOAD_BYTES`. Với `APP_ENV=production`, ứng dụng từ chối khởi động nếu `SECRET_KEY` yếu (< 32 ký tự hoặc giá trị mẫu) hoặc `CORS_ORIGINS` chứa `*`.

## Chạy bằng Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

- API chạy tại `http://localhost:8000` (đổi cổng host bằng biến `HOST_PORT`).
- Image chỉ chứa `backend/src`, dữ liệu `data/catalog` và `static/`; container chạy bằng user không phải root (uid 10001).
- SQLite runtime nằm trong named volume `showroom-data`, giữ nguyên sau `docker compose restart` và không được commit.
- Healthcheck gọi `/health`; endpoint trả **503** khi không truy cập được database nên container không báo khỏe giả.

Kiểm tra nhanh container đang chạy:

```powershell
python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

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
| Media | `/api/v1/catalog-media` | Ảnh của mẫu xe trong danh mục |

WebSocket chat:

```text
ws://localhost:8000/api/v1/conversations/{conversation_id}/ws?token=<jwt>
```

Quyền truy cập, payload và mã lỗi: [Đặc tả API](docs/API.md).

## Kiểm thử

```powershell
Set-Location backend
ruff check src tests scripts
pytest -q
```

Mỗi test chạy trên database mới được tạo lại và seed lại, không phụ thuộc thứ tự. Bộ test gồm unit test nghiệp vụ (fake in-memory, không FastAPI/DB) và integration test cho xác thực, phân quyền, catalog, upload, báo giá, lịch lái thử, CRM, địa điểm, chat REST/WebSocket, migration, transaction, ranh giới kiến trúc và hợp đồng OpenAPI.

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) chạy theo thứ tự: **Ruff → pytest → architecture → OpenAPI contract → Docker build → container smoke test** (kiểm tra non-root, dữ liệu còn sau restart và trạng thái `healthy`).

Khi đổi API, cập nhật snapshot: `python scripts/export_openapi.py`.

## Kiểm thử tải trên Kaggle CPU

Notebook [loadtest/kaggle_phase1_baseline.ipynb](loadtest/kaggle_phase1_baseline.ipynb) clone đúng commit, ghi metadata (commit, Python, CPU, RAM, database, dataset), warm-up 30 giây, chạy **3 lần × 120 giây ở concurrency 20** với một Uvicorn worker, lưu raw JSON từng lần và bảng median RPS/p50/p95/p99/max/error rate. Kết quả được commit tại `loadtest/results/phase1-baseline/`.

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

- [Đặc tả API và WebSocket](docs/API.md) · [OpenAPI snapshot](docs/openapi.json)
- [Kiến trúc hệ thống](docs/ARCHITECTURE.md)
- [Bảng nghiệm thu Pha 1](docs/PHASE1_ACCEPTANCE.md)
- [Phân công backend Pha 1](docs/PHASE1_BACKEND_ASSIGNMENT.md)
- [Kế hoạch Pha 1 và Pha 2](docs/PHASE_PLAN.md)
- [Quy trình load test trên Kaggle](docs/KAGGLE_LOAD_TEST.md)

## Lưu ý bảo mật

Không commit `.env`, token, private key, database hoặc credential thật. `.env.example` chỉ chứa giá trị mẫu.
