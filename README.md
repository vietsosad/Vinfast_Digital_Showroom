# VinFast Digital Showroom — Backend Pha 1

[![CI](https://github.com/vietsosad/Vinfast_Digital_Showroom/actions/workflows/ci.yml/badge.svg)](https://github.com/vietsosad/Vinfast_Digital_Showroom/actions/workflows/ci.yml)

Dịch vụ backend REST/JSON cho showroom số VinFast: tra cứu ô tô và xe máy điện, yêu cầu báo giá, đặt lịch lái thử, CRM khách hàng và chat thời gian thực giữa khách hàng với nhân viên. Repository chỉ chứa **backend Pha 1**; frontend, ảnh sản phẩm và database runtime không nằm trong repo. Hệ thống không dùng chatbot hay API key của dịch vụ AI.

## 1. Bài toán

Showroom truyền thống xử lý hỏi xe, báo giá, đặt lịch và chăm sóc khách qua nhiều kênh rời rạc (điện thoại, tin nhắn, bảng tính). Lead dễ thất lạc, nhân viên khó theo dõi hàng đợi, khách không biết yêu cầu của mình đang ở đâu, và không rõ ai được xem dữ liệu nào.

> **Câu hỏi trung tâm:** làm thế nào để biến sự quan tâm trực tuyến thành một quy trình bán hàng theo dõi được — từ xem xe, báo giá, lái thử đến tư vấn — mà mỗi người chỉ truy cập đúng dữ liệu thuộc quyền của mình?

| Cách làm thủ công | Trên hệ thống |
|---|---|
| Hỏi xe qua điện thoại/tin nhắn | Tra cứu danh mục xe công khai qua API |
| Báo giá bằng bảng tính, mỗi người một giá | Giá lấy từ catalog, chiết khấu có giới hạn, có trạng thái xử lý |
| Hẹn lái thử bằng trao đổi riêng | Lịch lái thử có kiểm tra ngày giờ và trạng thái |
| Lịch sử chat nằm trên máy nhân viên | Hội thoại lưu trong database, phát realtime |
| Không rõ ai được xem gì | JWT, vai trò và quyền sở hữu theo tài khoản |

## 2. Nghiệp vụ

```text
Khách xem xe → yêu cầu báo giá / đặt lịch lái thử → hồ sơ CRM tự cập nhật
            → nhân viên tiếp nhận, trao đổi qua chat → cập nhật trạng thái, lưu lịch sử
```

| Vai trò | Được làm |
|---|---|
| `customer` | Xem xe, tính chi phí sở hữu, yêu cầu báo giá, đặt lịch lái thử, chat với nhân viên — chỉ thấy dữ liệu của mình |
| `consultant` | Xử lý báo giá, lịch lái thử, hồ sơ CRM, nhận và trả lời hội thoại; quản trị danh mục |
| `admin` | Toàn quyền của nhân viên, quản lý tài khoản, xóa xe |

| Đối tượng | Trạng thái và chuyển hợp lệ (chuyển sai → `409`) |
|---|---|
| Báo giá | `pending → contacted/approved/rejected/cancelled`; `contacted → approved/rejected/cancelled`; `approved → completed/cancelled` |
| Lịch lái thử | `pending → confirmed/cancelled`; `confirmed → completed/cancelled` |
| Hội thoại | `open → closed` |
| Lead CRM | `NEW`, `CONTACTED`, `TEST_DRIVEN`, `QUOTED`, `WON`, `LOST`; điểm `HOT/WARM/COLD` |

Mô tả chi tiết bài toán, các vấn đề dễ thấy và cách xử lý: [docs/PHASE1_PRESENTATION.md](docs/PHASE1_PRESENTATION.md).

## 3. Đáp ứng yêu cầu Pha 1

| Yêu cầu | Cách đáp ứng | Bằng chứng |
|---|---|---|
| REST + JSON, có POST/GET/DELETE | 46 operation: 17 POST, 16 GET, 8 PUT, 5 DELETE; mọi body là JSON trừ 3 endpoint tải ảnh `multipart/form-data` | `tests/test_openapi_contract.py` |
| Tài liệu OpenAPI/Swagger | [docs/openapi.json](docs/openapi.json) (OpenAPI 3.1), `/docs`, `/redoc` | `tests/test_openapi_snapshot.py` khóa snapshot với runtime |
| API → Nghiệp vụ → Truy cập dữ liệu | `api/` → `application/` → `domain/` ← `infrastructure/`; nghiệp vụ không import FastAPI/Pydantic/SQLAlchemy | `tests/test_architecture.py` quét mọi file |
| Repository/DAL dùng ORM | 9 repository SQLAlchemy 2.0 sau protocol ở `domain/`; Unit of Work một transaction/use case | `tests/test_transactions.py` |
| Đăng nhập; ≥1 GET và ≥1 POST cần xác thực | `POST /api/v1/auth/login` trả JWT; 9 GET và 14 POST yêu cầu token | contract test gọi **mọi** GET/POST được bảo vệ, kỳ vọng 401 |
| Xác thực qua cơ chế của framework | Dependency dùng chung `get_current_user` + `require_roles` ([api/dependencies.py](backend/src/api/dependencies.py)); không endpoint nào tự đọc token | `test_security_declarations_match_the_access_policy` |
| Đóng gói Docker | Multi-stage, user không phải root, healthcheck trả 503 khi DB lỗi | CI: build → smoke → restart giữ dữ liệu → `healthy` |
| Kiểm thử tải trên Kaggle CPU | Notebook + script đo + script tổng hợp median | [loadtest/](loadtest/README.md), [docs/KAGGLE_LOAD_TEST.md](docs/KAGGLE_LOAD_TEST.md) |

Trạng thái nghiệm thu từng mục: [docs/PHASE1_ACCEPTANCE.md](docs/PHASE1_ACCEPTANCE.md).

## 4. Kiến trúc

```text
HTTP / WebSocket client
        │ JSON
        ▼
api/              FastAPI router, Pydantic schema, dependency xác thực, map lỗi nghiệp vụ → HTTP
        │ gọi đúng một use case
        ▼
application/      Use case: kiểm tra quyền nghiệp vụ, điều phối repository, commit đúng một lần
        │
        ▼
domain/           Entity, enum + bảng chuyển trạng thái, lỗi nghiệp vụ, protocol Repository/UnitOfWork
        ▲ implements
infrastructure/   SQLAlchemy ORM + repository, Unit of Work, JWT, PBKDF2, lưu file, migration, seed
        │
        ▼
SQLite (local, Docker, Kaggle) hoặc PostgreSQL (asyncpg)
```

- `domain/` và `application/` là Python thuần, không import `fastapi`, `pydantic`, `sqlalchemy`, `jwt`, `passlib`, `api/` hay `infrastructure/`.
- `api/` không import SQLAlchemy; chỉ `api/dependencies.py` (composition root) gắn repository vào use case.
- Danh tính lấy từ JWT, không tin `user_id`, tên hay giá do client gửi.
- Một use case = một transaction: tạo báo giá ghi `quotes` và cập nhật hồ sơ CRM rồi mới commit; lỗi ở bước nào thì rollback toàn bộ.

Quyết định thiết kế, mô hình dữ liệu và ADR: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 5. Tổ chức mã nguồn và công nghệ

```text
backend/src/api/             Router HTTP/WebSocket, schema Pydantic, dependencies, map lỗi
backend/src/application/     9 use case service: auth, catalog ô tô/xe máy, quote, booking, CRM, location, chat, media (+ TCO)
backend/src/domain/          Entity, trạng thái, quy tắc, lỗi, protocol
backend/src/infrastructure/  ORM, 9 repository, unit of work, JWT/PBKDF2, file storage, migration, seed
backend/src/main.py          Khởi tạo FastAPI, CORS, /static, lifespan
backend/tests/               120 test: unit/, test_api/, kiến trúc, contract, migration, transaction
backend/scripts/             smoke test, load test, tổng hợp kết quả, export OpenAPI, công cụ seed
backend/Dockerfile           Image backend
data/catalog/vehicles.json   Dữ liệu catalog tham chiếu, nạp khi bảng rỗng
docs/                        Đặc tả API, kiến trúc, nghiệm thu, thuyết trình
loadtest/                    Notebook Kaggle và kết quả đo
```

Python 3.11 · FastAPI 0.141 · Pydantic 2.13 · SQLAlchemy 2.0 async (aiosqlite/asyncpg) · PyJWT (HS256) · passlib PBKDF2-SHA256 · pytest + HTTPX · Ruff · Docker · GitHub Actions. Phiên bản khóa trong `backend/requirements.txt` và `backend/constraints.txt`.

## 6. Đặc tả API

- **File đặc tả:** [docs/openapi.json](docs/openapi.json) — OpenAPI 3.1, 46 operation, 51 schema, security scheme `HTTPBearer`. Test bảo đảm file luôn khớp với code; cập nhật bằng `python backend/scripts/export_openapi.py`.
- **Xem trước không cần chạy server:** [ReDoc](https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/vietsosad/Vinfast_Digital_Showroom/main/docs/openapi.json) hoặc [Swagger Editor](https://editor.swagger.io/?url=https://raw.githubusercontent.com/vietsosad/Vinfast_Digital_Showroom/main/docs/openapi.json).
- **Khi chạy server:** Swagger UI `/docs`, ReDoc `/redoc`, JSON `/openapi.json`.
- **Bản đọc cho người:** [docs/API.md](docs/API.md) — quyền từng endpoint, ví dụ request/response, quy tắc nghiệp vụ, mã lỗi.

Base URL `/api/v1`; endpoint được bảo vệ cần `Authorization: Bearer <access_token>`.

| Nhóm | Endpoint chính | Quyền |
|---|---|---|
| Hệ thống | `GET /health` | Public |
| Xác thực | `POST /auth/register`, `POST /auth/login`, `GET/PUT /auth/me`, `/auth/users` | Public / đăng nhập / admin |
| Danh mục | `GET/POST /cars`, `GET/PUT/DELETE /cars/{id}`, tương tự `/motorbikes`, `/catalog-media` | Đọc public; ghi staff/admin; xóa xe admin |
| Báo giá | `GET/POST /quotes`, `PUT /quotes/{id}` | Đăng nhập; cập nhật staff/admin |
| Lái thử | `GET/POST /bookings`, `PUT /bookings/{id}` | Đăng nhập; cập nhật staff/admin |
| CRM | `GET /customer-profiles/me`, `GET/PUT /customer-profiles/{id}` | Chủ hồ sơ; staff/admin |
| Chat | `/conversations`, `/{id}/messages`, `/assign`, `/close`, `DELETE`, `WS /{id}/ws?token=` | Thành viên hội thoại; staff/admin |
| Tiện ích | `GET /locations`, `POST /tco/calculate` | Public |

Lỗi luôn có dạng `{"detail": "..."}` với mã `401`, `403`, `404`, `409`, `413`, `422`; lỗi không dự kiến trả `500` không lộ stack trace.

## 7. Bảo mật

Mật khẩu băm PBKDF2-SHA256; JWT HS256 có `exp`. RBAC tập trung tại `require_roles`; customer chỉ nhận dữ liệu của chính mình theo UUID trong token. Upload ảnh kiểm tra kích thước, phần mở rộng, MIME và chữ ký tệp. Với `APP_ENV=production`, ứng dụng từ chối khởi động nếu `SECRET_KEY` yếu hoặc `CORS_ORIGINS` chứa `*`. Không commit `.env`, token hay database; `.env.example` chỉ chứa giá trị mẫu.

## 8. Chạy hệ thống

Docker (khuyến nghị):

```powershell
Copy-Item .env.example .env
docker compose up --build        # API tại http://localhost:8000, đổi cổng bằng HOST_PORT
python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

Local (Python 3.10+):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r backend/requirements-dev.txt -c backend/constraints.txt
Set-Location backend; uvicorn src.main:app --reload --port 8000
```

Khi khởi động, ứng dụng tự tạo bảng, chạy migration idempotent và nạp catalog cùng mạng lưới địa điểm nếu bảng đang rỗng; ngoài production còn tạo tài khoản demo cho từng vai trò. Khách hàng mới tự đăng ký bằng `POST /api/v1/auth/register` rồi đăng nhập bằng `POST /api/v1/auth/login`.

## 9. Kiểm thử, CI và kiểm thử tải

```powershell
Set-Location backend; ruff check src tests scripts; pytest -q
```

- 120 test, mỗi test dùng database riêng: unit test nghiệp vụ với fake in-memory và integration test cho mọi nhóm endpoint, WebSocket, migration, transaction, kiến trúc, hợp đồng OpenAPI.
- [GitHub Actions](.github/workflows/ci.yml): Ruff → pytest → kiến trúc → OpenAPI contract → Docker build → smoke test container (non-root, dữ liệu còn sau restart, `healthy`).
- [Kaggle CPU](docs/KAGGLE_LOAD_TEST.md): notebook clone đúng commit, warm-up 30 giây rồi chạy 3 lần × 120 giây ở concurrency 20 với một Uvicorn worker; kết quả lưu tại `loadtest/results/phase1-baseline/`.

## 10. Giới hạn có chủ đích của Pha 1

Pha 1 ưu tiên tính đúng và khả năng kiểm thử, **chưa tối ưu** để có baseline đo được: SQLite và một Uvicorn worker, catalog trả toàn bộ danh sách, WebSocket quản lý trong bộ nhớ một process, JWT 7 ngày chưa có thu hồi hay rate limit, migration tự viết thay vì Alembic, ảnh lưu trên đĩa cục bộ.

## 11. Tài liệu

- [Thuyết trình Pha 1](docs/PHASE1_PRESENTATION.md) — bài toán, nghiệp vụ, vấn đề dễ thấy, tổ chức mã nguồn, yêu cầu kỹ thuật
- [Đặc tả API](docs/API.md) · [OpenAPI](docs/openapi.json) · [Kiến trúc](docs/ARCHITECTURE.md) · [Nghiệm thu Pha 1](docs/PHASE1_ACCEPTANCE.md)
- [Load test Kaggle](docs/KAGGLE_LOAD_TEST.md) · [Phân công](docs/PHASE1_BACKEND_ASSIGNMENT.md) · [Kế hoạch](docs/PHASE_PLAN.md)

## 12. Nhóm phát triển

| Thành viên | Phụ trách |
|---|---|
| Lê Hoàng Việt (Lead) | Kiến trúc, xác thực/RBAC, danh mục xe, OpenAPI, tích hợp |
| Hoàng Lê Minh | Báo giá, lịch lái thử, CRM, migration, kiểm thử tải Kaggle |
| Nguyễn Văn Toán | Chat thời gian thực, media, địa điểm, TCO, Docker và kiểm thử backend |
