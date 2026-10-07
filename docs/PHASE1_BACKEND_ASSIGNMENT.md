# PHÂN CÔNG PHA 1 — VINFAST DIGITAL SHOWROOM BACKEND

**Thành viên:** Lê Hoàng Việt (Lead), Hoàng Lê Minh, Nguyễn Văn Toán  
**Base URL:** `/api/v1`  
**Phạm vi:** REST API giao tiếp JSON, JWT, PostgreSQL, Swagger/OpenAPI, Docker và kiểm thử.  
**Không thuộc Pha 1:** giao diện người dùng, tư vấn AI/agent, RAG, sinh ảnh và các chức năng MVP phía frontend.

## Authentication & Vehicle Catalog (Lê Hoàng Việt — Lead)

- `POST /auth/register` — Đăng ký tài khoản khách hàng.
- `POST /auth/login` — Đăng nhập và trả về JWT access token.
- `GET /auth/me` — Lấy thông tin tài khoản hiện tại; yêu cầu xác thực.
- `PUT /auth/me` — Cập nhật hồ sơ cá nhân; yêu cầu xác thực.
- `GET /cars` — Danh sách ô tô, hỗ trợ tìm kiếm và lọc.
- `GET /cars/{id}` — Chi tiết một mẫu ô tô.
- `POST /cars` — Thêm mẫu ô tô; chỉ dành cho `staff/admin`.
- `DELETE /cars/{id}` — Xóa mẫu ô tô; chỉ dành cho `admin`.
- `GET /motorbikes` — Danh sách xe máy điện, hỗ trợ tìm kiếm và lọc.
- `GET /motorbikes/{id}` — Chi tiết một mẫu xe máy điện.
- `POST /motorbikes` — Thêm mẫu xe máy điện; chỉ dành cho `staff/admin`.
- `DELETE /motorbikes/{id}` — Xóa mẫu xe máy điện; chỉ dành cho `admin`.

**Trách nhiệm chính:** JWT và phân quyền tập trung qua middleware/dependency; hoàn thiện luồng API → Service → Repository cho danh mục xe; tích hợp OpenAPI; review kiến trúc và merge code của nhóm.

## Sales Workflow & Customer CRM (Hoàng Lê Minh)

- `GET /quotes` — Khách xem yêu cầu của mình; `staff/admin` xem toàn bộ.
- `POST /quotes` — Tạo yêu cầu báo giá; yêu cầu xác thực.
- `PUT /quotes/{id}` — Nhân viên cập nhật trạng thái và giá chốt.
- `GET /bookings` — Danh sách lịch lái thử theo quyền người dùng.
- `POST /bookings` — Đặt lịch lái thử; yêu cầu xác thực.
- `PUT /bookings/{id}` — Nhân viên xác nhận, hoàn thành hoặc hủy lịch.
- `GET /customer-profiles/me` — Khách xem hồ sơ CRM của chính mình.
- `GET /customer-profiles` — Nhân viên xem danh sách khách hàng.
- `GET /customer-profiles/{id}` — Nhân viên xem chi tiết một khách hàng.
- `PUT /customer-profiles/{id}` — Nhân viên cập nhật trạng thái lead và ghi chú thủ công.

**Trách nhiệm chính:** thiết kế dữ liệu và repository cho báo giá, lịch lái thử, CRM; kiểm soát quyền sở hữu dữ liệu; xử lý trạng thái nghiệp vụ; viết seed data và integration test cho các luồng bán hàng.

## Human Support & Supporting APIs (Nguyễn Văn Toán)

- `POST /conversations` — Khách hàng mở cuộc trò chuyện với nhân viên.
- `GET /conversations` — Khách xem hội thoại của mình; nhân viên xem hàng đợi hỗ trợ.
- `GET /conversations/{id}/messages` — Lấy lịch sử tin nhắn theo quyền truy cập.
- `POST /conversations/{id}/messages` — Khách hàng hoặc nhân viên gửi tin nhắn.
- `POST /conversations/{id}/assign` — Nhân viên nhận xử lý cuộc trò chuyện.
- `POST /conversations/{id}/close` — Đóng cuộc trò chuyện đã hoàn thành.
- `DELETE /conversations/{id}` — Xóa cuộc trò chuyện theo quy tắc phân quyền.
- `WS /conversations/{id}/ws` — Cập nhật tin nhắn thời gian thực; phần mở rộng sau khi REST API ổn định.
- `GET /locations` — Danh sách showroom/trạm dịch vụ/trạm sạc.
- `POST /tco/calculate` — Tính toán chi phí sở hữu xe từ dữ liệu đầu vào.
- `GET /health` — Kiểm tra trạng thái hoạt động của dịch vụ.

**Trách nhiệm chính:** xây dựng chat người-thật theo API → Service → Repository; kiểm tra quyền tham gia và vòng đời hội thoại; bổ sung WebSocket sau REST; viết unit test, kịch bản kiểm thử tải và hướng dẫn chạy trên Kaggle CPU.

## Quy ước kiến trúc chung

```text
HTTP request
    ↓
API/Controller: nhận request, xác thực, chuyển đổi DTO
    ↓
Business Service: xử lý quy tắc nghiệp vụ thuần
    ↓
Repository Interface: hợp đồng truy cập dữ liệu
    ↓
SQLAlchemy Repository → PostgreSQL
```

- Tầng nghiệp vụ không import FastAPI hoặc SQLAlchemy.
- Endpoint chỉ điều phối request/response, không chứa truy vấn cơ sở dữ liệu.
- Xác thực và phân quyền dùng dependency/middleware chung, không lặp lại trong từng endpoint.
- Response và lỗi đều dùng JSON; trạng thái lỗi tối thiểu gồm `400`, `401`, `403`, `404`, `409`, `422`.
- Swagger tại `/docs`; đặc tả OpenAPI tại `/openapi.json`.

## Tiêu chí hoàn thành cho mỗi thành viên

- Hoàn thành đầy đủ vertical slice do mình phụ trách: schema/DTO, service, repository và endpoint.
- Có mô tả endpoint, quyền truy cập, request mẫu và response mẫu trên Swagger.
- Có unit test cho nghiệp vụ và integration test cho endpoint quan trọng.
- Có tối thiểu một endpoint `GET` và một endpoint `POST` được bảo vệ bằng JWT trong toàn hệ thống.
- Code được một thành viên khác review trước khi Lead merge; commit nhỏ, rõ mục đích.
- Chạy được bằng Docker và kết nối PostgreSQL qua biến môi trường, không hard-code thông tin bí mật.

## Phân công công việc chung

| Hạng mục | Người phụ trách chính | Người kiểm tra |
|---|---|---|
| Kiến trúc, JWT/RBAC, OpenAPI, tích hợp cuối | Lê Hoàng Việt | Hoàng Lê Minh |
| Database schema, migration, seed data | Hoàng Lê Minh | Nguyễn Văn Toán |
| Test suite, Docker, Kaggle load test | Nguyễn Văn Toán | Lê Hoàng Việt |
| Review pull request và chuẩn hóa tài liệu | Cả nhóm | Lê Hoàng Việt duyệt cuối |

**API:** Hệ thống hỗ trợ xác thực người dùng, quản lý danh mục ô tô và xe máy điện, yêu cầu báo giá, đặt lịch lái thử, quản lý khách hàng, trò chuyện thời gian thực giữa khách hàng và nhân viên, tra cứu địa điểm và tính chi phí sở hữu. Pha 1 tập trung chứng minh kiến trúc phân tầng, bảo mật, tài liệu API, Docker và khả năng kiểm thử; chưa triển khai giao diện hay chức năng AI.
