# Load test

- [`kaggle_phase1_baseline.ipynb`](kaggle_phase1_baseline.ipynb) — notebook chạy trên Kaggle CPU: clone commit, ghi metadata, warm-up 30 s, 3 × 120 s ở concurrency 20, tổng hợp median.
- [`results/phase1-baseline/`](results/phase1-baseline/README.md) — baseline Pha 1 đo trên Kaggle ([version 363226232](https://www.kaggle.com/code/hoangviethehe/phase-1-baseline-kaggle-cpu-load-test?scriptVersionId=363226232), tag `phase1-baseline-v1`): `metadata.json`, `baseline-run-{1,2,3}.json`, `baseline-warmup.json`, `baseline-summary.{md,json}`, `server.log` và README giải thích kết quả.

Script dùng chung nằm trong `backend/scripts/`: `load_test.py` (đo) và `summarize_load_tests.py` (tổng hợp).

Quy trình đầy đủ: [docs/KAGGLE_LOAD_TEST.md](../docs/KAGGLE_LOAD_TEST.md).

> Thư mục `results/phase1-baseline/` chỉ chứa số liệu đo trên Kaggle. Không commit số đo từ máy cá nhân vào đây.
