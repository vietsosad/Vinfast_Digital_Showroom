"""Small, dependency-free HTTP load runner for the Kaggle CPU baseline."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

DEFAULT_PATHS = (
    "/health",
    "/api/v1/cars",
    "/api/v1/motorbikes",
    "/api/v1/locations",
)


def percentile(sorted_values: list[float], value: float) -> float:
    if not sorted_values:
        return 0.0
    index = round((len(sorted_values) - 1) * value)
    return sorted_values[index]


def run_worker(
    worker_id: int,
    base_url: str,
    paths: tuple[str, ...],
    deadline: float,
    timeout: float,
    samples: list[tuple[float, str]],
    lock: Lock,
) -> None:
    index = worker_id
    while time.perf_counter() < deadline:
        path = paths[index % len(paths)]
        index += 1
        started = time.perf_counter()
        outcome = "200"
        try:
            request = urllib.request.Request(
                f"{base_url}{path}",
                headers={"Accept": "application/json", "User-Agent": "p101-load-test/1.0"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response.read()
                outcome = str(response.status)
        except urllib.error.HTTPError as exc:
            outcome = str(exc.code)
        except Exception as exc:  # network errors are part of the measured result
            outcome = type(exc).__name__
        elapsed_ms = (time.perf_counter() - started) * 1_000
        with lock:
            samples.append((elapsed_ms, outcome))


def main() -> int:
    parser = argparse.ArgumentParser(description="Repeatable read-only API load test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.duration <= 0 or args.concurrency <= 0:
        parser.error("duration and concurrency must be positive")

    samples: list[tuple[float, str]] = []
    lock = Lock()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    started = time.perf_counter()
    deadline = started + args.duration
    base_url = args.base_url.rstrip("/")

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(
                run_worker,
                worker_id,
                base_url,
                DEFAULT_PATHS,
                deadline,
                args.timeout,
                samples,
                lock,
            )
            for worker_id in range(args.concurrency)
        ]
        for future in futures:
            future.result()

    elapsed = time.perf_counter() - started
    latencies = sorted(sample[0] for sample in samples)
    outcomes = Counter(sample[1] for sample in samples)
    successful = sum(count for status, count in outcomes.items() if status.startswith("2"))
    total = len(samples)
    result = {
        "started_at": started_at,
        "base_url": base_url,
        "paths": list(DEFAULT_PATHS),
        "duration_seconds": round(elapsed, 3),
        "concurrency": args.concurrency,
        "requests": total,
        "successful": successful,
        "failed": total - successful,
        "error_rate_percent": round(((total - successful) / total * 100) if total else 0, 3),
        "requests_per_second": round(total / elapsed if elapsed else 0, 3),
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 3) if latencies else 0,
            "p50": round(percentile(latencies, 0.50), 3),
            "p95": round(percentile(latencies, 0.95), 3),
            "p99": round(percentile(latencies, 0.99), 3),
            "max": round(max(latencies), 3) if latencies else 0,
        },
        "outcomes": dict(sorted(outcomes.items())),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if total and successful == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
