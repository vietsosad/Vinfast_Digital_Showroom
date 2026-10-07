# Load test trên Kaggle CPU

Mục tiêu là so sánh phiên bản trước/sau trên cùng môi trường, không phải tạo con số lớn nhất.

## Cấu hình cố định

- Kaggle Notebook: CPU only, accelerator `None`.
- Cùng dataset và cùng commit seed.
- `concurrency=20`, warm-up 30 giây, mỗi lần đo 120 giây.
- Ba lần chạy cho mỗi phiên bản; báo median của RPS và p95.
- Endpoint đọc: `/health`, `/api/v1/cars`, `/api/v1/motorbikes`, `/api/v1/locations`.

Ghi lại Python version, số CPU, RAM, commit hash và `DATABASE_URL` loại SQLite/PostgreSQL; không ghi password.

## Chạy

Khởi động backend trong một cell/terminal:

```bash
cd backend
pip install -r requirements.txt
python scripts/seed_catalog_from_frontend.py
uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Warm-up:

```bash
python scripts/load_test.py --base-url http://127.0.0.1:8000 --duration 30 --concurrency 20
```

Đo chính thức và lưu raw JSON:

```bash
python scripts/load_test.py \
  --base-url http://127.0.0.1:8000 \
  --duration 120 \
  --concurrency 20 \
  --output baseline-run-1.json
```

Lặp `run-2`, `run-3`. Sau cải tiến chạy lại đúng câu lệnh với prefix `improved`.

## Chỉ số bắt buộc

- Tổng request thành công/thất bại.
- Throughput requests/second.
- Latency p50, p95, p99 và maximum.
- Error rate và status code/error phổ biến.
- CPU/RAM quan sát trong notebook nếu có.

Mẫu bảng báo cáo:

| Version | RPS median | p50 ms | p95 ms | p99 ms | Error % | Ghi chú |
|---|---:|---:|---:|---:|---:|---|
| Baseline | | | | | | |
| Improved | | | | | | |
| Chênh lệch | | | | | | |

## Nguyên tắc kết luận

- Không so hai cấu hình phần cứng/database khác nhau.
- Không bỏ run xấu nếu không chứng minh được lỗi môi trường.
- Nêu cả trade-off: cache tăng độ trễ dữ liệu, index tăng chi phí ghi, nhiều worker tăng RAM.
- Chỉ kết luận cải thiện khi error rate không xấu đi và mức thay đổi vượt nhiễu giữa ba lần chạy.
