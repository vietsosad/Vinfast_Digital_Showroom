# Load test

- [`kaggle_phase1_baseline.ipynb`](kaggle_phase1_baseline.ipynb) — notebook chạy trên Kaggle CPU: clone commit, ghi metadata, warm-up 30 s, 3 × 120 s ở concurrency 20, tổng hợp median.
- `results/phase1-baseline/` — nơi commit kết quả thật từ Kaggle (`metadata.json`, `baseline-run-{1,2,3}.json`, `baseline-warmup.json`, `baseline-summary.{md,json}`, `server.log`).

Script dùng chung nằm trong `backend/scripts/`: `load_test.py` (đo) và `summarize_load_tests.py` (tổng hợp).

Quy trình đầy đủ: [docs/KAGGLE_LOAD_TEST.md](../docs/KAGGLE_LOAD_TEST.md).

> Thư mục `results/phase1-baseline/` chỉ chứa số liệu đo trên Kaggle. Không commit số đo từ máy cá nhân vào đây.
