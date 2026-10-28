"""Aggregate repeated load-test runs into the Phase 1 baseline table.

    python scripts/summarize_load_tests.py results/baseline-run-*.json \
        --label Baseline --metadata results/metadata.json --output results/baseline-summary

Writes <output>.json and <output>.md. Medians are taken across runs so one noisy
run cannot dominate; every individual run is listed as well.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def load_runs(paths: list[Path]) -> list[dict]:
    runs = []
    for path in sorted(paths):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_file"] = path.name
        runs.append(data)
    if not runs:
        raise SystemExit("no run files given")
    return runs


def summarize(runs: list[dict]) -> dict:
    def median(getter):
        return round(statistics.median(getter(run) for run in runs), 3)

    total_requests = sum(run["requests"] for run in runs)
    total_failed = sum(run["failed"] for run in runs)
    return {
        "runs": len(runs),
        "concurrency": sorted({run["concurrency"] for run in runs}),
        "duration_seconds": sorted({round(run["duration_seconds"]) for run in runs}),
        "median_rps": median(lambda run: run["requests_per_second"]),
        "median_p50_ms": median(lambda run: run["latency_ms"]["p50"]),
        "median_p95_ms": median(lambda run: run["latency_ms"]["p95"]),
        "median_p99_ms": median(lambda run: run["latency_ms"]["p99"]),
        "max_latency_ms": round(max(run["latency_ms"]["max"] for run in runs), 3),
        "total_requests": total_requests,
        "total_failed": total_failed,
        "error_rate_percent": round(total_failed / total_requests * 100, 3) if total_requests else 0.0,
        "rps_spread_percent": round(
            (max(r["requests_per_second"] for r in runs) - min(r["requests_per_second"] for r in runs))
            / statistics.median(r["requests_per_second"] for r in runs)
            * 100,
            2,
        ),
    }


def render_markdown(label: str, summary: dict, runs: list[dict], metadata: dict | None) -> str:
    lines = [f"# {label} load test summary", ""]
    if metadata:
        lines += ["## Environment", "", "| Key | Value |", "|---|---|"]
        lines += [f"| {key} | {value} |" for key, value in metadata.items() if not isinstance(value, (dict, list))]
        lines.append("")
    lines += [
        "## Result (median of runs)",
        "",
        "| Version | Runs | RPS median | p50 ms | p95 ms | p99 ms | Max ms | Error % | RPS spread % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {label} | {summary['runs']} | {summary['median_rps']} | {summary['median_p50_ms']} | "
        f"{summary['median_p95_ms']} | {summary['median_p99_ms']} | {summary['max_latency_ms']} | "
        f"{summary['error_rate_percent']} | {summary['rps_spread_percent']} |",
        "",
        "## Individual runs",
        "",
        "| File | Requests | RPS | p50 ms | p95 ms | p99 ms | Max ms | Failed | Server CPU % (mean/max) | Server RSS MB (max) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for run in runs:
        latency = run["latency_ms"]
        resources = run.get("server_resources") or {}
        cpu = f"{resources.get('cpu_percent_mean', '–')}/{resources.get('cpu_percent_max', '–')}"
        lines.append(
            f"| {run['_file']} | {run['requests']} | {run['requests_per_second']} | {latency['p50']} | "
            f"{latency['p95']} | {latency['p99']} | {latency['max']} | {run['failed']} | {cpu} | "
            f"{resources.get('rss_mb_max', '–')} |"
        )
    outcomes: dict[str, int] = {}
    for run in runs:
        for status, count in run.get("outcomes", {}).items():
            outcomes[status] = outcomes.get(status, 0) + count
    lines += ["", "## Outcomes (all runs)", "", "| Status | Count |", "|---|---:|"]
    lines += [f"| {status} | {count} |" for status, count in sorted(outcomes.items())]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--label", default="Baseline")
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Output path without extension")
    args = parser.parse_args()

    runs = load_runs(args.runs)
    summary = summarize(runs)
    metadata = json.loads(args.metadata.read_text(encoding="utf-8")) if args.metadata else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(
        json.dumps({"label": args.label, "summary": summary, "metadata": metadata}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = render_markdown(args.label, summary, runs, metadata)
    args.output.with_suffix(".md").write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    main()
