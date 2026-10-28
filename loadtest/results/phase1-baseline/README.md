# Baseline Pha 1 — Kaggle CPU

Bằng chứng load test Pha 1 của backend tại commit [`545e229`](https://github.com/vietsosad/Vinfast_Digital_Showroom/commit/545e2293d61c201e73ca2016a0968f0481cabd6c), đo ngày 2026-10-28 lúc 16:08 UTC trên Kaggle CPU. Lần đo chạy dạng Batch (*Save & Run All*) bằng notebook [`kaggle_phase1_baseline.ipynb`](../../kaggle_phase1_baseline.ipynb); Kaggle lưu lại [version 363226232](https://www.kaggle.com/code/hoangviethehe/phase-1-baseline-kaggle-cpu-load-test?scriptVersionId=363226232) (notebook để private). Quy trình và tham số cố định xem [KAGGLE_LOAD_TEST.md](../../../docs/KAGGLE_LOAD_TEST.md).

## Kết quả chính

Median của 3 lần × 120 s, concurrency 20, 1 worker uvicorn, SQLite:

| Chỉ số | Giá trị |
|---|---|
| Throughput | **53.47 RPS** |
| Latency p50 / p95 / p99 | **268 / 900 / 968 ms** |
| Latency max | 1248 ms |
| Tỉ lệ lỗi | **0 %** (0 / 19 350 request) |
| Dao động RPS giữa 3 lần | 1.3 % |
| CPU tiến trình server | trung bình ~182 % (≈ 1.8 trên 4 vCPU), đỉnh 195 % |
| RAM (RSS) tiến trình server | ~107 MB |

## Các file trong thư mục

| File | Nội dung | Dùng để |
|---|---|---|
| `metadata.json` | Môi trường và cấu hình lúc đo: commit, Python 3.13.15, CPU Intel Xeon 2.20 GHz (4 logical / 2 physical), RAM 31 GB, SQLite, 1 worker, concurrency 20, số bản ghi (21 ô tô, 18 xe máy, 129 địa điểm), `kaggle_kernel_run_type = Batch` | Chứng minh đo đúng commit và đúng cấu hình. Lần đo Pha 2 chỉ được so sánh khi metadata giống hệt, trừ commit |
| `baseline-warmup.json` | 30 s chạy làm nóng (1 595 request) | Không tính vào kết quả; chỉ để server ổn định trước khi đo |
| `baseline-run-1.json` … `baseline-run-3.json` | Số liệu thô của từng lần đo 120 s: số request, thành công/lỗi, RPS, latency mean/p50/p95/p99/max, mã trạng thái, CPU %/RSS của server | Raw evidence; tính lại được bảng tổng hợp từ đây |
| `baseline-summary.md`, `baseline-summary.json` | Bảng tổng hợp do `summarize_load_tests.py` sinh: median của 3 lần, từng lần và metadata | Con số chính thức, dùng để so sánh ở Pha 2 |
| `server.log` | Access log của uvicorn trong suốt phiên đo (20 957 dòng) | Đối chiếu độc lập từ phía server: request thật sự tới backend và đều trả 200 |

## Đọc kết quả

1. **Ổn định, lặp lại được.** Ba lần đo đạt 53.32–54.02 RPS, p50 266–269 ms; warm-up cũng đạt 52.6 RPS nên không có hiệu ứng khởi động lạnh. Baseline đủ tin cậy để so trước/sau.
2. **Không có lỗi.** 19 350 / 19 350 request trả 200. `server.log` khớp với phía client: 20 949 dòng `200 OK` = 1 595 (warm-up) + 19 350 (3 lần đo) + 4 request notebook dùng để chờ `/health` và đếm bản ghi; không có dòng nào khác 200. Bốn endpoint được gọi đều nhau, mỗi endpoint ~5 200 request.
3. **RPS do latency quyết định.** Client là vòng kín: 20 luồng, mỗi luồng gửi request mới ngay khi nhận xong request trước. Theo định luật Little, RPS ≈ 20 / latency trung bình = 20 / 0.374 s ≈ 53.5, khớp số đo. Muốn tăng RPS ở cùng concurrency thì phải giảm thời gian xử lý mỗi request.
4. **Đuôi latency dài.** p95 (900 ms) gấp ~3.4 lần p50 (268 ms). Latency chỉ được đo gộp cho cả 4 endpoint nên chưa biết chắc endpoint nào gây đuôi. `/api/v1/locations` (nhiều bản ghi nhất, 129) là nghi vấn đầu tiên: thứ tự dòng trong `server.log` cho thấy request tới endpoint này thường hoàn thành muộn hơn các request mở cùng lúc. Cần đo riêng từng endpoint trước khi kết luận.
5. **Server dùng ~1.8 vCPU.** Chỉ có 1 worker nhưng CPU vượt 100 % vì psutil cộng CPU của mọi thread trong tiến trình, gồm cả thread của aiosqlite.
6. **Bộ nhớ ổn định.** RSS ~107 MB, chỉ tăng ~1 MB trong khoảng 6 phút (106.8 → 107.9 MB); chưa có dấu hiệu rò rỉ bộ nhớ.

## Giới hạn của phép đo

- Client và server chạy chung một VM Kaggle 4 vCPU và CPU của client không được đo, nên hai bên tranh tài nguyên với nhau.
- 1 worker, SQLite, dữ liệu nhỏ (21 / 18 / 129 bản ghi), chỉ các endpoint GET đọc dữ liệu; không đo ghi, đăng nhập hay WebSocket.
- Client mở kết nối TCP mới cho mỗi request (không keep-alive) và access log của uvicorn đang bật; cả hai đều cộng thêm chi phí vào latency.
- Đây là mốc để so sánh trước/sau, **không phải** năng lực của hệ thống production.

## Dùng cho Pha 2

- Chạy lại đúng notebook, chỉ đổi `GIT_REF`; đối chiếu `metadata.json` (CPU, số worker, database, concurrency, số bản ghi phải giống).
- Chỉ kết luận cải thiện khi tỉ lệ lỗi vẫn 0 % và chênh lệch RPS lớn hơn hẳn mức dao động 1.3 %.
- Thí nghiệm A trong [PHASE_PLAN.md](../../../docs/PHASE_PLAN.md) (giảm p95 ít nhất 30 %) cần p95 ≤ ~630 ms.

## Kiểm tra lại bảng tổng hợp

Từ thư mục gốc repository:

```bash
python backend/scripts/summarize_load_tests.py loadtest/results/phase1-baseline/baseline-run-*.json \
  --label Baseline --metadata loadtest/results/phase1-baseline/metadata.json --output /tmp/check
diff /tmp/check.md loadtest/results/phase1-baseline/baseline-summary.md
```

`diff` không in gì nghĩa là bảng tổng hợp đúng với số liệu thô.
