"""Measure model step latency by uncached input token bucket and API error waits."""
import argparse
import collections
from datetime import datetime
import glob
import json
import os
from pathlib import Path
import statistics
import time

DEFAULT_BRAIN_DIR = Path(r"~\.gemini\antigravity\brain").expanduser()
BUCKETS = [
    ("0k-50k", 0, 50_000),
    ("50k-100k", 50_000, 100_000),
    ("100k-200k", 100_000, 200_000),
    ("200k-300k", 200_000, 300_000),
    ("300k-400k", 300_000, 400_000),
    ("400k+", 400_000, 10_000_000),
]


def parse_ts(step: dict) -> float | None:
    """Parse ISO-8601 created_at timestamp to epoch seconds."""
    val = step.get("created_at")
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def analyze_model_latency(brain_dir: Path, days: float) -> dict:
    """Compute API errors, waits before errors, and latency per context-size bucket."""
    cutoff = time.time() - days * 86400.0
    files = sorted(
        f for f in glob.glob(str(brain_dir / "*" / ".system_generated" / "logs" / "transcript_full.jsonl"))
        if os.path.getmtime(f) > cutoff
    )
    errs = collections.Counter()
    err_wait_s = 0.0
    rows = []
    idle_err_tokens = []
    total_planner = 0
    cache_hits = 0

    for path in files:
        steps = []
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    steps.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        last_input_tokens = None
        for idx, step in enumerate(steps):
            t_cur = parse_ts(step)
            t_prev = parse_ts(steps[idx - 1]) if idx > 0 else None
            if step.get("type") == "ERROR_MESSAGE":
                msg = str(step.get("error") or "")
                errs[":".join(msg.split(":")[:3])[:110]] += 1
                if t_prev is not None and t_cur is not None and t_cur >= t_prev:
                    err_wait_s += t_cur - t_prev
                if "idle timeout" in msg and last_input_tokens is not None:
                    idle_err_tokens.append(last_input_tokens)
            elif step.get("type") == "PLANNER_RESPONSE" and step.get("input_tokens") is not None:
                total_planner += 1
                itok = step.get("input_tokens") or 0
                last_input_tokens = itok
                if (step.get("cache_read_tokens") or 0) > 0:
                    cache_hits += 1
                if idx + 1 < len(steps):
                    t_next = parse_ts(steps[idx + 1])
                    if t_cur is not None and t_next is not None:
                        gap = t_next - t_cur
                        if 0 <= gap < 900:
                            rows.append((itok, gap))

    bucket_stats = []
    for label, lo, hi in BUCKETS:
        gaps = sorted(g for itok, g in rows if lo <= itok < hi)
        if gaps:
            bucket_stats.append({
                "bucket": label,
                "n": len(gaps),
                "median_s": round(statistics.median(gaps), 2),
                "p90_s": round(gaps[int(len(gaps) * 0.9)], 2),
            })

    return {
        "schema": "tdq-model-latency/v1",
        "days": days,
        "files": len(files),
        "planner_with_tokens": total_planner,
        "cache_read_pos": cache_hits,
        "api_errors_total": sum(errs.values()),
        "api_error_wait_minutes": round(err_wait_s / 60.0, 2),
        "api_errors_top": [{"error": k, "count": v} for k, v in errs.most_common(10)],
        "latency_by_uncached_tokens": bucket_stats,
        "idle_timeout_last_tokens": {
            "n": len(idle_err_tokens),
            "median": statistics.median(idle_err_tokens) if idle_err_tokens else 0,
            "ge_200k": sum(1 for x in idle_err_tokens if x >= 200_000),
        },
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Analyze model latency vs context size and API errors.")
    parser.add_argument("--days", type=float, default=4.0)
    parser.add_argument("--brain-dir", default=str(DEFAULT_BRAIN_DIR))
    parser.add_argument("--json", dest="json_out", help="Write JSON output to file.")
    args = parser.parse_args(argv)

    report = analyze_model_latency(Path(args.brain_dir), args.days)
    print(f"planner={report['planner_with_tokens']} cache_pos={report['cache_read_pos']} "
          f"api_errors={report['api_errors_total']} wait={report['api_error_wait_minutes']}min")
    for row in report["latency_by_uncached_tokens"]:
        print(f"  {row['bucket']:10s} n={row['n']:5d} median={row['median_s']:6.1f}s p90={row['p90_s']:6.1f}s")
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
