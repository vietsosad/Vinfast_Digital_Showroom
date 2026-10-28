# Baseline load test summary

## Environment

| Key | Value |
|---|---|
| label | baseline |
| measured_at_utc | 2026-10-28T16:08:05+00:00 |
| repository | https://github.com/vietsosad/Vinfast_Digital_Showroom.git |
| git_ref | 545e2293d61c201e73ca2016a0968f0481cabd6c |
| commit | 545e2293d61c201e73ca2016a0968f0481cabd6c |
| platform | Linux-6.18.55+-x86_64-with-glibc2.39 |
| python | 3.13.15 |
| cpu_model | Intel(R) Xeon(R) CPU @ 2.20GHz |
| logical_cpus | 4 |
| physical_cpus | 2 |
| ram_gb | 31.35 |
| kaggle_kernel_run_type | Batch |
| database | sqlite (aiosqlite), file on local disk |
| dataset | data/catalog/vehicles.json + built-in locations dataset |
| server_command | -m uvicorn src.main:app --host 127.0.0.1 --port 8000 |
| workers | 1 |
| concurrency | 20 |
| warmup_seconds | 30 |
| run_seconds | 120 |
| runs | 3 |

## Result (median of runs)

| Version | Runs | RPS median | p50 ms | p95 ms | p99 ms | Max ms | Error % | RPS spread % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 3 | 53.473 | 268.425 | 899.556 | 967.535 | 1247.838 | 0.0 | 1.3 |

## Individual runs

| File | Requests | RPS | p50 ms | p95 ms | p99 ms | Max ms | Failed | Server CPU % (mean/max) | Server RSS MB (max) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline-run-1.json | 6430 | 53.473 | 268.425 | 899.556 | 963.788 | 1184.704 | 0 | 182.6/190.9 | 106.9 |
| baseline-run-2.json | 6414 | 53.323 | 269.221 | 911.271 | 993.96 | 1247.838 | 0 | 182.0/193.9 | 107.4 |
| baseline-run-3.json | 6506 | 54.017 | 266.462 | 896.757 | 967.535 | 1247.16 | 0 | 182.4/194.9 | 107.9 |

## Outcomes (all runs)

| Status | Count |
|---|---:|
| 200 | 19350 |
