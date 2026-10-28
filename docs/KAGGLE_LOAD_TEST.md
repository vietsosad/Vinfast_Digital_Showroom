# Load test trên Kaggle CPU

Mục tiêu là có **baseline lặp lại được** cho Pha 1 để so sánh trước/sau ở Pha 2, không phải tạo con số lớn nhất.

## Cấu hình cố định

| Tham số | Giá trị |
|---|---|
| Môi trường | Kaggle Notebook, *Accelerator: None* (CPU), *Internet: On* |
| Server | `uvicorn src.main:app` — 1 worker, cùng lệnh với Docker image |
| Database | SQLite (aiosqlite) trên đĩa notebook, seed từ `data/catalog/vehicles.json` + dataset địa điểm |
| Endpoint đọc | `/health`, `/api/v1/cars`, `/api/v1/motorbikes`, `/api/v1/locations` (xoay vòng) |
| Tải | concurrency **20**, warm-up **30 s** (bỏ), **3 lần × 120 s** |
| Báo cáo | median RPS, median p50/p95/p99, max latency, error rate, độ dao động RPS giữa các lần |

Mọi lần đo trước/sau phải giữ nguyên các tham số trên và chỉ thay đổi commit.

## Chạy

Repository được đo: [vietsosad/Vinfast_Digital_Showroom](https://github.com/vietsosad/Vinfast_Digital_Showroom) (public). Notebook đã điền sẵn `REPO_URL = "https://github.com/vietsosad/Vinfast_Digital_Showroom.git"`; mỗi lần đo chỉ đổi `GIT_REF`.

1. Lấy commit hash đầy đủ của `main` cần đo (lệnh này không phụ thuộc remote trên máy):

   ```bash
   git ls-remote https://github.com/vietsosad/Vinfast_Digital_Showroom.git refs/heads/main
   ```

   Commit đó phải chứa `backend/constraints.txt`, `backend/scripts/load_test.py`, `backend/scripts/summarize_load_tests.py` và `data/catalog/vehicles.json`; nếu thiếu, ô clone của notebook dừng và liệt kê file thiếu.
2. Tài khoản Kaggle phải **xác minh số điện thoại** (*Settings → Phone verification*) thì mới bật được Internet.
3. Trên [kaggle.com](https://www.kaggle.com): *+ Create* → *New Notebook* → *File → Import Notebook* → kéo thả [`loadtest/kaggle_phase1_baseline.ipynb`](../loadtest/kaggle_phase1_baseline.ipynb) → *Import*.
4. Panel phải *Session options*: Accelerator `None`, Internet `On`.
5. Ô cấu hình đầu tiên: `GIT_REF = "<hash ở bước 1>"`. Chạy thử ô 1–2 (*Shift + Enter*): phải in `Testing commit <hash>` và không báo lỗi.
6. *Save Version* → *Save & Run All (Commit)* → *Save*, rồi tắt session tương tác (⏻). Bản commit chạy trong phiên sạch (~10 phút), Kaggle lưu lại version làm bằng chứng và `metadata.json` ghi `kaggle_kernel_run_type = Batch`; theo dõi ở *View Active Events*. Notebook sẽ:
   - clone đúng commit, kiểm tra file bắt buộc và cài dependency theo `constraints.txt`;
   - ghi `metadata.json`: commit, Python, CPU model, số CPU, RAM, database, dataset, số bản ghi, lệnh server;
   - khởi động backend, chờ `/health`, warm-up 30 s;
   - chạy 3 lần × 120 s, mỗi lần lưu raw JSON kèm CPU%/RSS của tiến trình server;
   - tạo `baseline-summary.md` và `baseline-summary.json`, nén thành `phase1-baseline-results.zip`.
7. Khi version báo *Successful*: mở version → tab *Output* → tải `phase1-baseline-results.zip`.
8. Giải nén vào `loadtest/results/phase1-baseline/`, chép dòng `Baseline` trong `baseline-summary.md` vào bảng [Định dạng kết quả](#định-dạng-kết-quả), đổi trạng thái Kaggle trong [PHASE1_ACCEPTANCE.md](PHASE1_ACCEPTANCE.md), rồi commit và gắn tag trong bản clone của repository trên:

```bash
git add loadtest/results/phase1-baseline docs/KAGGLE_LOAD_TEST.md docs/PHASE1_ACCEPTANCE.md
git commit -m "test(load): add Kaggle CPU phase 1 baseline"
git tag -a phase1-baseline-v1 -m "Phase 1 baseline measured on Kaggle CPU"
git push origin main phase1-baseline-v1
```

Chỉ sau tag này mới bắt đầu Pha 2. Không đưa cache, index, Redis hay nhiều worker vào trước khi có baseline.

## Chạy thủ công (ngoài notebook)

```bash
cd backend
pip install -r requirements.txt -c constraints.txt
APP_ENV=production SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))") \
CORS_ORIGINS=http://localhost uvicorn src.main:app --host 127.0.0.1 --port 8000 &

python scripts/load_test.py --duration 30 --concurrency 20 --output warmup.json
for i in 1 2 3; do
  python scripts/load_test.py --duration 120 --concurrency 20 --output baseline-run-$i.json
done
python scripts/summarize_load_tests.py baseline-run-*.json --label Baseline --output baseline-summary
```

## Định dạng kết quả

Mỗi `baseline-run-N.json` chứa: `started_at`, `commit`, `duration_seconds`, `concurrency`, `requests`, `successful`, `failed`, `error_rate_percent`, `requests_per_second`, `latency_ms.{mean,p50,p95,p99,max}`, `outcomes` (mã trạng thái/lỗi) và `server_resources.{cpu_percent_mean,cpu_percent_max,rss_mb_max}`.

Bảng báo cáo (sinh bởi `summarize_load_tests.py`):

| Version | Runs | RPS median | p50 ms | p95 ms | p99 ms | Max ms | Error % | RPS spread % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 3 | | | | | | | |
| Improved | 3 | | | | | | | |

## Nguyên tắc kết luận

- Không so hai cấu hình phần cứng/database khác nhau; đối chiếu `metadata.json` của hai phiên bản.
- Không bỏ run xấu nếu không chứng minh được lỗi môi trường.
- Chỉ kết luận cải thiện khi error rate không xấu đi và chênh lệch lớn hơn độ dao động giữa các lần (`RPS spread %`).
- Nêu trade-off: cache làm dữ liệu trễ, index tăng chi phí ghi, nhiều worker tăng RAM.
