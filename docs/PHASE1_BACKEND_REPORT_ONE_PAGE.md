# PHÂN CÔNG BACKEND PHA 1 — VINFAST DIGITAL SHOWROOM

## Authentication & Vehicle Catalog (Lê Hoàng Việt — Lead)

- `POST /auth/register` — Đăng ký tài khoản.
- `POST /auth/login` — Đăng nhập, trả về JWT.
- `GET /auth/me` — Thông tin người dùng hiện tại.
- `PUT /auth/me` — Cập nhật hồ sơ người dùng.
- `GET /cars` — Danh sách ô tô.
- `GET /cars/{id}` — Chi tiết ô tô.
- `POST /cars` — Thêm ô tô.
- `DELETE /cars/{id}` — Xóa ô tô.
- `GET /motorbikes` — Danh sách xe máy điện.
- `GET /motorbikes/{id}` — Chi tiết xe máy điện.
- `POST /motorbikes` — Thêm xe máy điện.
- `DELETE /motorbikes/{id}` — Xóa xe máy điện.

## Sales Workflow & Customer CRM (Hoàng Lê Minh)

- `GET /quotes` — Danh sách yêu cầu báo giá.
- `POST /quotes` — Tạo yêu cầu báo giá.
- `PUT /quotes/{id}` — Cập nhật trạng thái và giá chốt.
- `GET /bookings` — Danh sách lịch lái thử.
- `POST /bookings` — Đặt lịch lái thử.
- `PUT /bookings/{id}` — Cập nhật trạng thái lịch lái thử.
- `GET /customer-profiles/me` — Hồ sơ khách hàng hiện tại.
- `GET /customer-profiles` — Danh sách khách hàng cho nhân viên.
- `GET /customer-profiles/{id}` — Chi tiết một khách hàng.
- `PUT /customer-profiles/{id}` — Cập nhật trạng thái lead và ghi chú.

## Human Support & Supporting APIs (Nguyễn Văn Toán)

- `POST /conversations` — Mở cuộc trò chuyện với nhân viên.
- `GET /conversations` — Danh sách cuộc trò chuyện theo quyền.
- `GET /conversations/{id}/messages` — Lịch sử tin nhắn.
- `POST /conversations/{id}/messages` — Gửi tin nhắn.
- `POST /conversations/{id}/assign` — Nhân viên nhận xử lý hội thoại.
- `POST /conversations/{id}/close` — Đóng hội thoại.
- `DELETE /conversations/{id}` — Xóa hội thoại.
- `WS /conversations/{id}/ws` — Nhận tin nhắn thời gian thực.
- `GET /locations` — Danh sách showroom, trạm dịch vụ và trạm sạc.
- `POST /tco/calculate` — Tính chi phí sở hữu xe.
- `GET /health` — Kiểm tra trạng thái dịch vụ.

**API:** Hệ thống backend cung cấp xác thực JWT, phân quyền khách hàng/nhân viên/quản trị viên, quản lý danh mục ô tô và xe máy điện, yêu cầu báo giá, lịch lái thử, hồ sơ khách hàng, trò chuyện trực tiếp giữa khách hàng và nhân viên, tra cứu địa điểm và tính chi phí sở hữu. API sử dụng JSON, có Swagger/OpenAPI, kiến trúc phân tầng API → Business → Repository, đóng gói Docker và kiểm thử trên Kaggle CPU. Pha 1 không triển khai frontend hoặc tư vấn AI/agent.

> Khi đưa vào báo cáo, thêm tiền tố `/api/v1` trước các REST endpoint. Swagger: `/docs`; OpenAPI: `/openapi.json`.
