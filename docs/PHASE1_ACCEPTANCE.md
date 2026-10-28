# Nghiệm thu Pha 1

Bảng này đối chiếu từng yêu cầu của đề bài với bằng chứng kiểm chứng được. Cột **Trạng thái**: ✅ đã có trong mã và được kiểm tra tự động; ⏳ cần nhóm thực hiện ngoài mã nguồn (không thể tự động hóa hoặc cần tài khoản của nhóm).

## Yêu cầu đề bài

| Nhóm | Yêu cầu | Bằng chứng | Trạng thái |
|---|---|---|---|
| API | REST, giao tiếp JSON | Mọi request body là JSON trừ 3 endpoint upload ảnh — `test_request_bodies_are_json_except_documented_uploads` | ✅ |
| API | Có POST, GET, DELETE | `test_required_rest_methods_are_published`; 16 GET, 17 POST, 8 PUT, 5 DELETE | ✅ |
| API | Tài liệu OpenAPI/Swagger | `/docs`, `/openapi.json`, [openapi.json](openapi.json) khớp runtime — `test_committed_openapi_matches_runtime` | ✅ |
| Cấu trúc | API → Nghiệp vụ → Truy cập dữ liệu | `backend/src/{api,application,domain,infrastructure}` — [ARCHITECTURE.md](ARCHITECTURE.md) | ✅ |
| Cấu trúc | Nghiệp vụ không import framework web hay thư viện DB | `test_business_layers_are_framework_and_database_free` quét toàn bộ `domain/` và `application/` | ✅ |
| Cấu trúc | Repository/DAL dùng ORM | 9 repository SQLAlchemy + Unit of Work; `test_api_layer_never_touches_the_database`, `test_only_the_composition_root_imports_infrastructure` | ✅ |
| Bảo mật | Hỗ trợ đăng nhập | `POST /auth/login` (JWT); `tests/test_api/test_auth.py` | ✅ |
| Bảo mật | ≥1 GET và ≥1 POST cần xác thực | `test_every_protected_get_and_post_rejects_missing_token` lặp qua **mọi** GET/POST có security | ✅ |
| Bảo mật | Xác thực qua middleware/dependency, không lặp trong endpoint | `api/dependencies.py::get_current_user`, `require_roles`; `test_security_declarations_match_the_access_policy` | ✅ |
| Triển khai | Đóng gói Docker | CI job `docker`: build → smoke → non-root → restart giữ dữ liệu → `healthy` | ✅ (đã chạy local; ⏳ CI xanh trên GitHub) |
| Chung | GitHub công khai, commit cẩn thận | Repository `origin` đã ở chế độ Public; thay đổi đi qua Pull Request — xem mục “Việc nhóm cần làm” | ✅ Public; ⏳ CI xanh trên `main` |
| Chung | README mô tả kiến trúc và đặc tả | [README.md](../README.md), [API.md](API.md), [ARCHITECTURE.md](ARCHITECTURE.md) | ✅ |
| Chung | Chỉ chức năng cơ bản, chưa tối ưu | Không cache/pagination/multi-worker; ghi rõ trong ARCHITECTURE | ✅ |
| Chung | Kiểm thử tải trên Kaggle CPU | Notebook + script sẵn sàng; **chưa có số đo Kaggle** | ⏳ |

## Các lỗi đã sửa so với bản audit

| Vấn đề | Cách sửa | Kiểm chứng |
|---|---|---|
| Docker tính root bằng `Path(__file__).parents[2]` → `/static`, `PermissionError` với non-root | Mọi đường dẫn runtime là cấu hình (`STATIC_DIR`, `SEED_DATA_DIR`, `DATABASE_URL`), Dockerfile đặt rõ | Container chạy uid 10001, smoke test pass |
| `/health` trả 200 khi DB hỏng | Trả 503 + `database: unavailable` | `test_health_returns_503_when_database_is_down`; thử thật: dừng PostgreSQL → 503, bật lại → 200 |
| Image không có dữ liệu catalog | `data/catalog/vehicles.json` được copy vào image và seed khi bảng rỗng | Smoke test: 21 ô tô, 129 địa điểm |
| Production chấp nhận CORS `*` và `SECRET_KEY` yếu | `APP_ENV=production` từ chối khởi động khi secret ngắn/mặc định hoặc CORS chứa `*` | `Settings.validate_for_runtime` |
| Phân tầng chỉ đúng ở chat/media | Toàn bộ auth, catalog, quote, booking, CRM, location, chat, media qua use case + repository | `tests/test_architecture.py` |
| IDOR booking qua số điện thoại | Booking có `user_id` FK, lọc theo UUID trong token; migration backfill an toàn; số điện thoại duy nhất | `test_reused_phone_number_does_not_leak_bookings`, `test_booking_owner_is_backfilled_only_when_unambiguous` |
| Client gửi giá/tên xe khi tạo quote | Backend lấy tên/giá từ catalog; chiết khấu có giới hạn; `final_price` do backend tính | `test_quote_name_and_price_come_from_catalog_not_client` |
| Trạng thái/role là chuỗi tự do | Enum + bảng chuyển trạng thái cho quote, booking, conversation, role, lead | `tests/unit/test_domain_rules.py`, `test_booking_status_transitions` |
| Lỗi CRM để dữ liệu nửa vời | Unit of Work, một commit/use case | `tests/test_transactions.py` |
| Upload chỉ kiểm tra phần mở rộng | Kiểm tra kích thước, MIME, chữ ký tệp; xóa file khi ghi DB lỗi | `test_car_image_upload_validates_signature_and_stores_file`, `test_stored_files_are_removed_when_the_database_write_fails` |
| CRUD catalog dùng multipart | JSON; ảnh qua endpoint multipart riêng | contract test |
| Tài liệu ghi bcrypt | Ghi đúng PBKDF2-SHA256 | README, ARCHITECTURE |
| `catalog_service.py` Supabase cũ, dependency chưa khai báo | Đã xóa cùng test của nó; dependency khóa bằng `requirements.txt` + `constraints.txt` | — |
| Test CRM `pytest.skip` che lỗi; DB không reset | Không còn `skip`; mỗi test có database mới | `tests/conftest.py` |
| Test kiến trúc chỉ kiểm tra 1 file | Quét mọi file của mọi tầng | `tests/test_architecture.py` |
| Chưa test WebSocket authorization | Token giả → 4401, hội thoại người khác → 4403, broadcast thật | `test_websocket_*` |

## Việc nhóm cần làm để đóng Pha 1

1. **GitHub công khai đúng phiên bản**
   - Repository `origin` đã ở chế độ *Public*; giữ nguyên chế độ này đến khi chấm xong.
   - Push nhánh này, mở Pull Request vào `main`, để thành viên khác review rồi merge.
   - Xác minh ẩn danh: `git ls-remote https://github.com/<owner>/<repo>.git` (từ máy chưa đăng nhập) phải liệt kê `main` đúng commit hash.
   - Không push một snapshot khác tree; không viết lại lịch sử hay sửa tác giả commit cũ.
2. **CI xanh** trên repository public (tab Actions) — chụp màn hình cả job `quality` và `docker`.
3. **Kaggle baseline** theo [KAGGLE_LOAD_TEST.md](KAGGLE_LOAD_TEST.md): chạy notebook trên commit đã merge, commit `loadtest/results/phase1-baseline/`, gắn tag `phase1-baseline-v1`.
4. **Ảnh minh chứng** lưu tại `docs/evidence/`: Swagger UI, CI xanh, `docker compose ps` trạng thái `healthy`, báo cáo pytest.

## Definition of Done

Pha 1 chỉ được tuyên bố hoàn thành khi đồng thời có:

- [x] 100% endpoint công khai đi qua API → use case → repository.
- [x] Mọi GET/POST được bảo vệ trả 401 khi thiếu token.
- [x] Docker build/chạy non-root, healthcheck thực sự kiểm tra DB.
- [x] Swagger khớp runtime.
- [x] Test không skip lỗi; mỗi test có database độc lập.
- [x] README khớp với mã nguồn.
- [ ] CI xanh trên repository public hiện tại.
- [ ] Ba lần đo Kaggle có raw evidence và tag `phase1-baseline-v1`.
