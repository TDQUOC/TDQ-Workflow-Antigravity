"""Find abnormally long user turns in recent Antigravity transcripts."""
import argparse
from datetime import datetime
import glob
import json
import os
from pathlib import Path
import re
import time

DEFAULT_BRAIN_DIR = Path(r"~\.gemini\antigravity\brain").expanduser()
NON_TOOL_TYPES = ("PLANNER_RESPONSE", "SYSTEM_MESSAGE", "USER_INPUT", "CHECKPOINT", "ERROR_MESSAGE")
USER_REQ_RE = re.compile(r"<USER_REQUEST>(.*?)</USER_REQUEST>", re.S)


def parse_ts(step: dict) -> float | None:
    """Parse ISO-8601 created_at timestamp to epoch seconds."""
    val = step.get("created_at")
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def step_text(step: dict) -> str:
    """Extract string content from a transcript step."""
    content = step.get("content") or ""
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)


def split_turns(steps: list[dict]) -> list[dict]:
    """Group transcript steps into turns starting at each USER_INPUT."""
    turns = []
    current = None
    for step in steps:
        if step.get("type") == "USER_INPUT":
            if current is not None:
                turns.append(current)
            current = {"user": step_text(step), "steps": [step]}
        elif current is not None:
            current["steps"].append(step)
    if current is not None:
        turns.append(current)
    return turns


def scan_long_turns(brain_dir: Path, days: float, min_min: float,
                    pattern: str | None = None) -> dict:
    """Return summary rows for turns lasting at least min_min minutes."""
    cutoff = time.time() - days * 86400.0
    pat = re.compile(pattern, re.I) if pattern else None
    files = sorted(
        f for f in glob.glob(str(brain_dir / "*" / ".system_generated" / "logs" / "transcript_full.jsonl"))
        if os.path.getmtime(f) > cutoff
    )
    rows = []
    for path in files:
        conv = Path(path).parts[-4]
        steps = []
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    steps.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        for turn in split_turns(steps):
            timed = [s for s in turn["steps"] if parse_ts(s) is not None]
            if len(timed) < 2:
                continue
            dur_min = (parse_ts(timed[-1]) - parse_ts(timed[0])) / 60.0
            raw_user = turn["user"]
            match = USER_REQ_RE.search(raw_user)
            prompt = (match.group(1) if match else raw_user).strip().replace("\n", " ")
            if dur_min < min_min or (pat and not pat.search(prompt)):
                continue
            err_wait_s = sum(
                parse_ts(b) - parse_ts(a) for a, b in zip(timed, timed[1:])
                if b.get("type") == "ERROR_MESSAGE"
            )
            model_after_s = sum(
                parse_ts(b) - parse_ts(a) for a, b in zip(timed, timed[1:])
                if a.get("type") == "PLANNER_RESPONSE" and b.get("type") != "ERROR_MESSAGE"
            )
            planner = [s for s in timed if s.get("type") == "PLANNER_RESPONSE" and s.get("input_tokens") is not None]
            max_ctx = max(((s.get("input_tokens") or 0) + (s.get("cache_read_tokens") or 0) for s in planner), default=0)
            cache_miss = sum(1 for s in planner if (s.get("cache_read_tokens") or 0) == 0 and (s.get("input_tokens") or 0) > 50000)
            rows.append({
                "conv": conv,
                "dur_min": round(dur_min, 2),
                "model_calls": sum(1 for s in timed if s.get("type") == "PLANNER_RESPONSE"),
                "tool_calls": sum(1 for s in timed if s.get("type") not in NON_TOOL_TYPES),
                "deny": sum(1 for s in timed if s.get("type") not in NON_TOOL_TYPES and "denied by pre-tool hook" in step_text(s)),
                "stop_block": sum(1 for s in timed if "Stop hook blocked termination" in step_text(s)),
                "api_err": sum(1 for s in timed if s.get("type") == "ERROR_MESSAGE"),
                "err_wait_min": round(err_wait_s / 60.0, 2),
                "model_after_min": round(model_after_s / 60.0, 2),
                "max_ctx_tokens": max_ctx,
                "cache_miss_gt50k": cache_miss,
                "prompt": prompt[:120],
            })
    rows.sort(key=lambda r: r["dur_min"], reverse=True)
    return {"schema": "tdq-long-turns-summary/v1", "days": days, "min_min": min_min, "turns": rows}


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Find long turns in Antigravity transcripts.")
    parser.add_argument("--days", type=float, default=2.0)
    parser.add_argument("--min-min", type=float, default=10.0)
    parser.add_argument("--pattern", default=None)
    parser.add_argument("--brain-dir", default=str(DEFAULT_BRAIN_DIR))
    parser.add_argument("--json", dest="json_out", help="Write JSON output to file.")
    args = parser.parse_args(argv)

    report = scan_long_turns(Path(args.brain_dir), args.days, args.min_min, args.pattern)
    for row in report["turns"][:25]:
        print(f"{row['dur_min']:6.1f}m err={row['err_wait_min']:5.1f}m model={row['model_after_min']:5.1f}m "
              f"deny={row['deny']:2d} stop={row['stop_block']:2d} maxctx={row['max_ctx_tokens']//1000:4d}k "
              f"{row['conv'][:8]} | {row['prompt'][:60]}")
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
