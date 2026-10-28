# Thuyết trình Pha 1 — VinFast Digital Showroom Backend

Nội dung trình bày 5–7 phút: bài toán, nghiệp vụ, các vấn đề dễ thấy, tổ chức mã nguồn, framework và cách hệ thống đáp ứng yêu cầu kỹ thuật Pha 1. Mọi con số và tên test trong tài liệu này lấy từ mã nguồn và kết quả đo trên nhánh `main`.

| # | Phần | Thời lượng |
|---|---|---|
| 1 | Bài toán | ~1 phút |
| 2 | Nghiệp vụ | ~1,5 phút |
| 3 | Các vấn đề dễ thấy và cách xử lý | ~1,5 phút |
| 4 | Tổ chức mã nguồn và framework | ~1,5 phút |
| 5 | Yêu cầu kỹ thuật Pha 1 | ~1 phút |
| 6 | Demo trên Swagger (nếu còn thời gian) | ≤1 phút |

---

## 1. Bài toán

**Bối cảnh.** Khách hàng tìm hiểu ô tô và xe máy điện VinFast trên mạng, nhưng để thành giao dịch họ phải qua nhiều kênh rời rạc: gọi hotline hỏi giá, nhắn tin đặt lịch lái thử, trao đổi với nhân viên qua điện thoại cá nhân. Showroom ghi lại bằng bảng tính hoặc ghi chú.

**Hệ quả.**

- Lead thất lạc giữa các kênh; không biết khách đang ở bước nào.
- Mỗi nhân viên báo một giá, không có lịch sử ai đã duyệt chiết khấu nào.
- Lịch lái thử bị hẹn trùng hoặc hẹn vào ngày đã qua, không có bước xác nhận.
- Nhân viên nghỉ việc là mất lịch sử trao đổi với khách.
- Không có ranh giới quyền: ai cũng có thể xem thông tin của khách khác.

**Mục tiêu.** Một dịch vụ backend dùng chung, số hóa hành trình *xem xe → báo giá / lái thử → tư vấn → chốt* thành quy trình có dữ liệu, trạng thái, phân quyền và lịch sử.

> **Câu hỏi trung tâm:** làm thế nào để biến sự quan tâm trực tuyến thành quy trình bán hàng theo dõi được, mà mỗi người chỉ truy cập đúng dữ liệu thuộc quyền của mình?

**Phạm vi Pha 1:** REST API + WebSocket, xác thực, phân quyền, lưu trữ, Docker, kiểm thử. Không gồm frontend hoàn chỉnh, chatbot AI hay hệ thống bán hàng production.

## 2. Nghiệp vụ

### Tác nhân

| Vai trò | Nhu cầu | Quyền chính |
|---|---|---|
| Khách hàng (`customer`) | Tìm xe, biết giá, đặt lái thử, hỏi nhân viên | Xem danh mục, tính chi phí sở hữu, tạo báo giá/lịch lái thử/hội thoại **cho chính mình** |
| Nhân viên tư vấn (`consultant`) | Không bỏ sót lead, xử lý nhanh | Xem hàng đợi, cập nhật báo giá/lịch, ghi chú CRM, nhận và trả lời hội thoại, quản trị danh mục |
| Quản trị (`admin`) | Kiểm soát hệ thống | Toàn quyền nhân viên, tạo/khóa tài khoản, xóa xe |

### Luồng chính

```text
1. Khách tra cứu xe (public)           GET  /api/v1/cars, /motorbikes, /locations, POST /tco/calculate
2. Khách đăng ký / đăng nhập            POST /api/v1/auth/register → hồ sơ CRM được tạo cùng transaction
3. Khách yêu cầu báo giá / lái thử      POST /api/v1/quotes, /bookings → CRM tự cập nhật (QUOTED, TEST_DRIVEN)
4. Nhân viên xử lý trong hàng đợi       PUT  /api/v1/quotes/{id}, /bookings/{id} theo bảng trạng thái
5. Hai bên trao đổi                     /api/v1/conversations (REST lưu lịch sử) + WebSocket (đẩy realtime)
6. Nhân viên cập nhật lead và đóng      PUT /customer-profiles/{id}, POST /conversations/{id}/close
```

### Quy tắc nghiệp vụ quan trọng

- **Báo giá:** khách chỉ gửi `vehicle_id` và ghi chú. Tên xe và giá niêm yết do backend lấy từ catalog. Nhân viên áp chiết khấu với `0 ≤ discount ≤ base_price`; `final_price = base_price − discount` hoặc giá lăn bánh nhân viên chốt.
- **Lịch lái thử:** ngày tính theo giờ Việt Nam, không ở quá khứ, tối đa 180 ngày tới; giờ dạng `HH:MM`; xe phải tồn tại và đang kinh doanh.
- **Hội thoại:** chỉ khách hàng mở hội thoại (chủ đề 3–160 ký tự). Nhân viên phải **nhận** hội thoại trước khi trả lời và không giành hội thoại đã có người nhận; tin nhắn tối đa 2.000 ký tự, chỉ gửi khi hội thoại đang mở. Tin nhắn được lưu vào database rồi mới phát qua WebSocket.
- **CRM:** mỗi khách có một hồ sơ, tạo cùng transaction với tài khoản. Trạng thái lead (`NEW`, `CONTACTED`, `TEST_DRIVEN`, `QUOTED`, `WON`, `LOST`) tự chuyển sang `QUOTED`/`TEST_DRIVEN` khi khách tạo báo giá/lịch; nhân viên chỉnh tay trạng thái, điểm `HOT/WARM/COLD` và ghi chú.

| Đối tượng | Chuyển trạng thái hợp lệ (sai → `409 Conflict`) |
|---|---|
| Báo giá | `pending → contacted/approved/rejected/cancelled`; `contacted → approved/rejected/cancelled`; `approved → completed/cancelled` |
| Lịch lái thử | `pending → confirmed/cancelled`; `confirmed → completed/cancelled` |
| Hội thoại | `open → closed` |

## 3. Các vấn đề dễ thấy và cách xử lý

### 3.1. Trong nghiệp vụ showroom

| Vấn đề | Hệ thống xử lý bằng |
|---|---|
| Lead nằm rải rác, trùng lặp | Một hồ sơ CRM cho mỗi tài khoản, tự cập nhật khi khách tạo báo giá hoặc đặt lịch |
| Báo giá tùy người, không kiểm soát | Giá lấy từ catalog; chiết khấu có giới hạn; báo giá có trạng thái và người xử lý |
| Lịch hẹn sai ngày, không ai xác nhận | Kiểm tra ngày/giờ khi tạo; nhân viên chuyển `pending → confirmed → completed` |
| Lịch sử trao đổi phụ thuộc cá nhân | Hội thoại lưu trong database, gán nhân viên phụ trách, đọc lại được qua REST |
| Lộ dữ liệu khách hàng | JWT + vai trò; khách chỉ nhận dữ liệu gắn với UUID tài khoản trong token |

### 3.2. Trong mã nguồn — lỗi đã phát hiện khi rà soát và đã sửa

| Vấn đề dễ thấy | Rủi ro | Cách sửa | Kiểm chứng |
|---|---|---|---|
| Lịch lái thử lọc theo số điện thoại | Khách xem được lịch của người khác (IDOR) | Sở hữu theo `user_id` trong token | `test_reused_phone_number_does_not_leak_bookings` |
| Client gửi tên xe và giá khi tạo báo giá | Khách tự sửa giá | Backend lấy tên/giá từ catalog | `test_quote_name_and_price_come_from_catalog_not_client` |
| Trạng thái là chuỗi tự do | Dữ liệu đi sai quy trình | Enum + bảng chuyển trạng thái trong `domain/` | `test_booking_status_transitions`, `tests/unit/test_domain_rules.py` |
| Ghi nửa vời: báo giá lưu nhưng CRM lỗi | Dữ liệu lệch nhau | Unit of Work, một commit cho mỗi use case | `tests/test_transactions.py` |
| Upload chỉ kiểm tra đuôi file | Tệp giả mạo được lưu | Kiểm tra kích thước, MIME, chữ ký tệp; xóa file nếu ghi DB lỗi | `test_car_image_upload_validates_signature_and_stores_file`, `test_stored_files_are_removed_when_the_database_write_fails` |
| `/health` trả 200 khi database hỏng | Container báo khỏe giả | Trả `503` khi không truy cập được DB | `test_health_returns_503_when_database_is_down` |
| Nghiệp vụ trộn với ORM và HTTP | Khó test, khó thay đổi | Tách 4 tầng, kiểm tra tự động | `test_business_layers_are_framework_and_database_free` |

### 3.3. Giới hạn còn lại, chấp nhận có chủ đích ở Pha 1

Pha 1 chưa tối ưu để có baseline đo được trên Kaggle CPU:

- SQLite và một Uvicorn worker; `GET /cars` trả toàn bộ danh sách, chưa phân trang.
- WebSocket quản lý trong bộ nhớ của một process, nên chưa chạy được nhiều worker.
- JWT sống 7 ngày, chưa có thu hồi token hay rate limit.
- Migration tự viết (`create_all` + bước nâng cấp idempotent), chưa dùng Alembic; ảnh lưu trên đĩa cục bộ.

## 4. Tổ chức mã nguồn và framework

### Phân tầng

```text
api/             →  application/        →  domain/              ←  infrastructure/
Router, schema,     Use case: quyền,        Entity, trạng thái,     SQLAlchemy repository,
dependency auth,    điều phối, commit       lỗi, protocol           Unit of Work, JWT, file,
map lỗi → HTTP      một lần                 (Python thuần)          migration, seed
```

| Tầng | Số file / dòng mã | Thành phần |
|---|---|---|
| `api/` | 24 / ~1.430 | 11 nhóm router, schema Pydantic, `dependencies.py` (cổng xác thực + composition root), `errors.py` |
| `application/` | 12 / ~1.210 | `AuthService`, `CarCatalogService`, `MotorbikeCatalogService`, `QuoteService`, `BookingService`, `CustomerProfileService`, `LocationService`, `SupportChatService`, `VehicleMediaService`, TCO |
| `domain/` | 15 / ~910 | Entity dataclass, enum trạng thái, lỗi nghiệp vụ, protocol Repository/UnitOfWork/TokenService |
| `infrastructure/` | 21 / ~1.560 | ORM, 9 repository, Unit of Work, PBKDF2/JWT, lưu file, migration, seed |

**Quy tắc phụ thuộc** — được `tests/test_architecture.py` kiểm tra bằng AST trên mọi file:

- `domain/` và `application/` không import FastAPI, Pydantic, SQLAlchemy, JWT, passlib.
- `api/` không truy vấn database; chỉ `api/dependencies.py` được import `infrastructure/`.
- `infrastructure/` không import tầng web.

**Ví dụ một request — tạo báo giá:**

```text
POST /api/v1/quotes {vehicle_id, request_note}
 api/quotes.py           validate bằng Pydantic → get_current_user (JWT) → QuoteService.request_quote
 application/quotes.py   lấy giá + tên từ catalog → tạo Quote → cập nhật hồ sơ CRM → uow.commit()
 infrastructure/...      repository chỉ flush; lỗi bất kỳ bước nào → rollback toàn bộ
 api/errors.py           NotFoundError → 404, ValidationError → 422, ...
```

### Framework và công cụ

| Thành phần | Lựa chọn | Lý do |
|---|---|---|
| Web framework | FastAPI 0.141 (Python 3.11) | Async, WebSocket sẵn có, **tự sinh OpenAPI/Swagger**, dependency injection dùng làm cổng xác thực |
| Validation | Pydantic 2.13 | Schema request/response, sinh JSON Schema cho OpenAPI |
| ORM | SQLAlchemy 2.0 async | Repository/Unit of Work; chạy cả SQLite (aiosqlite) và PostgreSQL (asyncpg) |
| Bảo mật | PyJWT (HS256), passlib PBKDF2-SHA256 | Chuẩn phổ biến, không cần dịch vụ ngoài |
| Kiểm thử | pytest, pytest-asyncio, HTTPX, Starlette TestClient | 120 test, mỗi test một database riêng |
| Chất lượng | Ruff, GitHub Actions | Lint + test + kiến trúc + contract + Docker chạy ở mỗi lần push |
| Đóng gói | Docker multi-stage, Docker Compose | Image non-root, healthcheck, volume dữ liệu |

## 5. Yêu cầu kỹ thuật Pha 1

| Yêu cầu | Cách đáp ứng | Bằng chứng |
|---|---|---|
| REST, JSON | Mọi body là JSON trừ 3 endpoint tải ảnh `multipart/form-data` | `test_request_bodies_are_json_except_documented_uploads` |
| Có POST, GET, DELETE | 17 POST, 16 GET, 8 PUT, 5 DELETE | `test_required_rest_methods_are_published` |
| Tài liệu OpenAPI/Swagger | [openapi.json](openapi.json) (OpenAPI 3.1, hợp lệ), `/docs`, `/redoc` | `test_committed_openapi_matches_runtime` |
| API → Nghiệp vụ → Truy cập dữ liệu | 4 tầng như mục 4 | `tests/test_architecture.py` |
| Repository/DAL dùng ORM | 9 repository SQLAlchemy + Unit of Work | `tests/test_transactions.py` |
| Đăng nhập | `POST /api/v1/auth/login` trả JWT | `tests/test_api/test_auth.py` |
| ≥1 GET và ≥1 POST cần xác thực | 9 GET và 14 POST được bảo vệ | `test_every_protected_get_and_post_rejects_missing_token` |
| Xác thực qua cơ chế của framework | Dependency `get_current_user` + `require_roles` dùng chung | `test_security_declarations_match_the_access_policy` |
| Đóng gói Docker | Non-root, healthcheck, dữ liệu còn sau restart | CI job `Docker build and container smoke test` |
| GitHub công khai, README | Repository public, CI xanh trên `main`, README 1–4 trang | [README](../README.md) |
| Kiểm thử tải Kaggle CPU | Warm-up 30 s, 3 lần × 120 s, concurrency 20, 1 worker: median **53.5 RPS**, p95 **900 ms**, **0 %** lỗi | [Kết quả](../loadtest/results/phase1-baseline/README.md), [notebook Kaggle](https://www.kaggle.com/code/hoangviethehe/phase-1-baseline-kaggle-cpu-load-test?scriptVersionId=363226232), [quy trình](KAGGLE_LOAD_TEST.md) |

Trạng thái chi tiết: [PHASE1_ACCEPTANCE.md](PHASE1_ACCEPTANCE.md).

### Kết quả kiểm thử tải trên Kaggle CPU

Đo tại commit `545e229`, chạy Batch trên Kaggle (Intel Xeon 2.20 GHz, 4 vCPU), SQLite, 1 Uvicorn worker, concurrency 20, 3 lần × 120 s sau 30 s warm-up:

| RPS (median) | p50 | p95 | p99 | Max | Lỗi | Dao động RPS |
|---:|---:|---:|---:|---:|---:|---:|
| 53.5 | 268 ms | 900 ms | 968 ms | 1248 ms | 0 / 19 350 | 1.3 % |

- Ba lần đo chỉ lệch nhau 1.3 % và không có request lỗi, nên đây là mốc tin cậy để so trước/sau ở Pha 2.
- p95 gấp ~3.4 lần p50: một phần nhỏ request chậm hẳn. Pha 2 đo riêng từng endpoint rồi tối ưu catalog, mục tiêu giảm p95 ít nhất 30 % ([PHASE_PLAN.md](PHASE_PLAN.md)).
- Bằng chứng: [số liệu thô và giải thích](../loadtest/results/phase1-baseline/README.md), [notebook Kaggle](https://www.kaggle.com/code/hoangviethehe/phase-1-baseline-kaggle-cpu-load-test?scriptVersionId=363226232), tag [`phase1-baseline-v1`](https://github.com/vietsosad/Vinfast_Digital_Showroom/tree/phase1-baseline-v1).

## 6. Kịch bản demo (≤1 phút)

1. `docker compose up --build`, mở `http://localhost:8000/docs`.
2. `GET /api/v1/cars` không cần token → danh sách xe.
3. `POST /api/v1/bookings` không có token → **401**.
4. Đăng nhập bằng tài khoản khách demo, bấm **Authorize**, gọi lại `POST /api/v1/bookings` → **201**; `user_id` lấy từ token.
5. Đăng nhập nhân viên, `PUT /api/v1/bookings/{id}` sang `confirmed` → 200; thử chuyển ngược về `pending` → **409**.
6. Mở tab Actions trên GitHub: hai job CI xanh.

## Câu hỏi có thể gặp

- **Vì sao dùng dependency thay vì middleware toàn cục?** Dependency injection là cơ chế interceptor chính thức của FastAPI. Logic xác thực chỉ viết một lần trong `get_current_user`, route chỉ khai báo dùng nó. Nhờ vậy OpenAPI hiển thị đúng endpoint nào cần token, và các endpoint public (catalog, TCO) không phải đi qua danh sách ngoại lệ.
- **Làm sao chứng minh tầng nghiệp vụ không phụ thuộc framework?** `tests/test_architecture.py` phân tích AST từng file trong `domain/` và `application/`; chỉ cần một import FastAPI/SQLAlchemy là CI đỏ.
- **Tải ảnh dùng multipart có vi phạm yêu cầu JSON không?** Ba endpoint upload nhận dữ liệu nhị phân là ngoại lệ duy nhất, được ghi trong tài liệu và khóa bằng contract test; mọi dữ liệu nghiệp vụ khác đều là JSON.
- **Vì sao dùng SQLite?** Để setup nhanh và có baseline ổn định trên Kaggle CPU. PostgreSQL được hỗ trợ qua `DATABASE_URL` mà không đổi code nghiệp vụ.
- **Vì sao chỉ ~53 RPS?** Pha 1 cố ý chưa tối ưu: 1 worker, SQLite, catalog trả toàn bộ danh sách, mỗi request mở kết nối mới, client và server chạy chung một máy 4 vCPU. Với 20 client gửi liên tục, RPS ≈ 20 / latency trung bình (0.374 s) ≈ 53.5, nên muốn tăng RPS phải giảm thời gian xử lý mỗi request. Con số này là mốc để so sánh, không phải năng lực production.
