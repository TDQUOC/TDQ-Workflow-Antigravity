"""Decompose abnormally long user turns in recent Antigravity transcripts."""
import argparse
from datetime import datetime, timezone
import glob
import json
import os
from pathlib import Path
import re
import statistics
import sys
import time

DEFAULT_BRAIN_DIR = Path(r"~\.gemini\antigravity\brain").expanduser()
DEFAULT_BENCH_JSON = Path(__file__).with_name("bench_hooks.json")
NON_TOOL_TYPES = (
    "PLANNER_RESPONSE",
    "SYSTEM_MESSAGE",
    "USER_INPUT",
    "CHECKPOINT",
    "ERROR_MESSAGE",
)
USER_REQ_RE = re.compile(r"<USER_REQUEST>(.*?)</USER_REQUEST>", re.S)
TOOL_SPAN_RE = re.compile(r"Created At:\s*(\S+)\s*\nCompleted At:\s*(\S+)")

DEFAULT_HOOK_RATES = {
    "pre_inv_s": 0.4495,
    "pre_tool_s": 0.0973,
    "post_tool_s": 0.0854,
    "post_inv_s": 0.0841,
    "stop_s": 0.0883,
}


def _log(msg: str) -> None:
    """Write ISO-8601 timestamped message to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG") == "0":
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"{stamp} [long_turns] {msg}", file=sys.stderr)


def parse_ts(step: dict) -> float | None:
    """Parse ISO-8601 created_at timestamp to epoch seconds."""
    val = step.get("created_at")
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def parse_tool_span(step: dict) -> float | None:
    """Parse tool Created At / Completed At timestamps from step content."""
    match = TOOL_SPAN_RE.search(step_text(step))
    if not match:
        return None
    try:
        t0 = datetime.fromisoformat(match.group(1)).timestamp()
        t1 = datetime.fromisoformat(match.group(2)).timestamp()
        return max(0.0, t1 - t0)
    except ValueError:
        return None


def step_text(step: dict) -> str:
    """Extract string content from a transcript step."""
    content = step.get("content") or ""
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def load_hook_rates(bench_path: Path | None) -> dict[str, float]:
    """Load per-event median hook durations in seconds from bench_hooks.json."""
    rates = dict(DEFAULT_HOOK_RATES)
    target = bench_path or DEFAULT_BENCH_JSON
    if not target.is_file():
        return rates
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return rates
    by_name = {
        c["name"]: c["median_ms"] / 1000.0
        for c in data.get("cases", [])
        if "name" in c and "median_ms" in c
    }
    pre_inv = (
        by_name.get("PreInvocation prompt_context", 0.0)
        + by_name.get("PreInvocation search_observe", 0.0)
    )
    if pre_inv > 0:
        rates["pre_inv_s"] = round(pre_inv, 4)
    pre_tools = [v for k, v in by_name.items() if k.startswith("PreToolUse ")]
    if pre_tools:
        rates["pre_tool_s"] = round(statistics.mean(pre_tools), 4)
    post_tool_key = "PostToolUse search_observe (run_command)"
    if post_tool_key in by_name:
        rates["post_tool_s"] = round(by_name[post_tool_key], 4)
    post_inv_key = "PostInvocation post_invocation"
    if post_inv_key in by_name:
        rates["post_inv_s"] = round(by_name[post_inv_key], 4)
    if "Stop stop_gate" in by_name:
        rates["stop_s"] = round(by_name["Stop stop_gate"], 4)
    return rates


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


def _is_subagent_wait(timed: list[dict], idx: int) -> bool:
    """Return True when PLANNER_RESPONSE -> SYSTEM_MESSAGE awaits a wakeup."""
    cur, nxt = timed[idx], timed[idx + 1]
    if cur.get("type") != "PLANNER_RESPONSE" or nxt.get("type") != "SYSTEM_MESSAGE":
        return False
    if "[Message]" in step_text(nxt):
        return True
    if idx + 2 < len(timed) and timed[idx + 2].get("type") == "SYSTEM_MESSAGE":
        return "[Message]" in step_text(timed[idx + 2])
    return False


def _is_deny_or_stop(step_type: str | None, text: str) -> bool:
    """Return True if step represents a pre-tool denial or Stop hook block."""
    is_deny = step_type not in NON_TOOL_TYPES and "denied by pre-tool hook" in text
    return is_deny or "Stop hook blocked termination" in text


def _classify_intervals(timed: list[dict]) -> dict[str, float]:
    """Partition adjacent timed step intervals into non-overlapping buckets."""
    raw = {
        "api_err_s": 0.0,
        "deny_wait_s": 0.0,
        "subagent_wait_s": 0.0,
        "model_raw_s": 0.0,
        "tool_raw_s": 0.0,
        "compaction_s": 0.0,
        "other_s": 0.0,
    }
    for idx in range(len(timed) - 1):
        a, b = timed[idx], timed[idx + 1]
        dt = max(0.0, (parse_ts(b) or 0.0) - (parse_ts(a) or 0.0))
        at, bt = a.get("type"), b.get("type")
        ac = step_text(a)
        if bt == "ERROR_MESSAGE":
            raw["api_err_s"] += dt
        elif _is_deny_or_stop(at, ac):
            raw["deny_wait_s"] += dt
        elif _is_subagent_wait(timed, idx):
            raw["subagent_wait_s"] += dt
        elif at == "PLANNER_RESPONSE":
            raw["model_raw_s"] += dt
        elif at not in NON_TOOL_TYPES:
            raw["tool_raw_s"] += dt
        elif at == "CHECKPOINT":
            raw["compaction_s"] += dt
        else:
            raw["other_s"] += dt
    return raw


def _deduct_hooks(
    raw: dict[str, float], counts: dict[str, int], rates: dict[str, float]
) -> dict[str, float]:
    """Extract non-overlapping hook_est_s from active execution intervals."""
    n_plan = counts["model_calls"]
    n_tool = counts["tool_calls"]
    n_stop = counts["stop_block"]
    hook_raw = (
        n_plan * (rates["pre_inv_s"] + rates["post_inv_s"])
        + n_tool * (rates["pre_tool_s"] + rates["post_tool_s"])
        + n_stop * rates["stop_s"]
    )
    active_budget = raw["model_raw_s"] + raw["tool_raw_s"] + raw["other_s"]
    hook_est = min(hook_raw, active_budget)

    pre_tool_d = min(raw["model_raw_s"], n_tool * rates["pre_tool_s"])
    model_net = raw["model_raw_s"] - pre_tool_d
    post_d = min(
        raw["tool_raw_s"],
        n_tool * rates["post_tool_s"] + n_plan * rates["post_inv_s"],
    )
    tool_net = raw["tool_raw_s"] - post_d

    rem_hook = max(0.0, hook_est - pre_tool_d - post_d)
    from_other = min(raw["other_s"], rem_hook)
    other_rem = raw["other_s"] - from_other
    rem_hook -= from_other

    from_model = min(model_net, rem_hook)
    model_net -= from_model
    rem_hook -= from_model

    from_tool = min(tool_net, rem_hook)
    tool_net -= from_tool

    return {
        "model_gen_s": model_net,
        "tool_exec_s": tool_net,
        "hook_est_s": hook_est,
        "other_s": other_rem,
    }


def _build_note(
    do_phu: float, subagent_s: float, compaction_s: float, other_s: float
) -> str:
    """Explain unattributed wall-clock time when 5-component coverage < 0.9."""
    if do_phu >= 0.9:
        return ""
    parts = []
    if subagent_s >= 5.0:
        parts.append(f"subagent_wait={subagent_s / 60.0:.1f}m")
    if compaction_s >= 5.0:
        parts.append(f"compaction={compaction_s / 60.0:.1f}m")
    if other_s >= 5.0:
        parts.append(f"queued_or_other={other_s / 60.0:.1f}m")
    return "; ".join(parts) if parts else "timestamp_rounding_gap"


def _step_counts(timed: list[dict], tool_steps: list[dict]) -> dict[str, int]:
    """Count planner calls, tool steps, denials, stop blocks, and API errors."""
    return {
        "model_calls": sum(1 for s in timed if s.get("type") == "PLANNER_RESPONSE"),
        "tool_calls": len(tool_steps),
        "deny": sum(
            1 for s in tool_steps if "denied by pre-tool hook" in step_text(s)
        ),
        "stop_block": sum(
            1 for s in timed if "Stop hook blocked termination" in step_text(s)
        ),
        "api_err": sum(1 for s in timed if s.get("type") == "ERROR_MESSAGE"),
    }


def _analyze_turn(
    conv: str,
    turn: dict,
    rates: dict[str, float],
    min_min: float,
    pat: re.Pattern[str] | None,
) -> dict | None:
    """Compute 5-component non-overlapping breakdown for one qualifying turn."""
    timed = [s for s in turn["steps"] if parse_ts(s) is not None]
    if len(timed) < 2:
        return None
    dur_s = max(0.0, (parse_ts(timed[-1]) or 0.0) - (parse_ts(timed[0]) or 0.0))
    dur_min = dur_s / 60.0
    raw_user = turn["user"]
    match = USER_REQ_RE.search(raw_user)
    prompt = (match.group(1) if match else raw_user).strip().replace("\n", " ")
    if dur_min < min_min or (pat and not pat.search(prompt)):
        return None

    tool_steps = [s for s in timed if s.get("type") not in NON_TOOL_TYPES]
    planner = [
        s
        for s in timed
        if s.get("type") == "PLANNER_RESPONSE" and s.get("input_tokens") is not None
    ]
    counts = _step_counts(timed, tool_steps)
    raw = _classify_intervals(timed)
    adj = _deduct_hooks(raw, counts, rates)
    comp5 = {
        "api_err_s": round(raw["api_err_s"], 2),
        "model_gen_s": round(adj["model_gen_s"], 2),
        "tool_exec_s": round(adj["tool_exec_s"], 2),
        "hook_est_s": round(adj["hook_est_s"], 2),
        "deny_wait_s": round(raw["deny_wait_s"], 2),
    }
    do_phu = round(min(1.0, sum(comp5.values()) / dur_s), 4) if dur_s > 0 else 0.0
    parsed = [sp for sp in (parse_tool_span(s) for s in tool_steps) if sp is not None]
    max_ctx = max(
        (
            (s.get("input_tokens") or 0) + (s.get("cache_read_tokens") or 0)
            for s in planner
        ),
        default=0,
    )
    cache_miss = sum(
        1
        for s in planner
        if (s.get("cache_read_tokens") or 0) == 0
        and (s.get("input_tokens") or 0) > 50000
    )
    note = _build_note(
        do_phu, raw["subagent_wait_s"], raw["compaction_s"], adj["other_s"]
    )
    return {
        "conv": conv,
        "dur_min": round(dur_min, 2),
        "dur_s": round(dur_s, 2),
        **counts,
        **comp5,
        "tool_exec_parsed_s": round(sum(parsed), 2),
        "subagent_wait_s": round(raw["subagent_wait_s"], 2),
        "compaction_s": round(raw["compaction_s"], 2),
        "other_s": round(adj["other_s"], 2),
        "do_phu": do_phu,
        "top_cause": max(comp5, key=comp5.get),
        "ghi_chu": note,
        "err_wait_min": round(comp5["api_err_s"] / 60.0, 2),
        "model_after_min": round(comp5["model_gen_s"] / 60.0, 2),
        "max_ctx_tokens": max_ctx,
        "cache_miss_gt50k": cache_miss,
        "prompt": prompt[:120],
    }


def _read_steps(path: str) -> list[dict]:
    """Read JSONL transcript file, ignoring malformed lines."""
    steps = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                steps.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return steps


def scan_long_turns(
    brain_dir: Path,
    days: float,
    min_min: float,
    pattern: str | None = None,
    bench_json: Path | None = None,
) -> dict:
    """Return 5-component breakdown for turns lasting at least min_min minutes."""
    cutoff = time.time() - days * 86400.0
    pat = re.compile(pattern, re.I) if pattern else None
    rates = load_hook_rates(bench_json)
    glob_pat = str(
        brain_dir / "*" / ".system_generated" / "logs" / "transcript_full.jsonl"
    )
    files = sorted(f for f in glob.glob(glob_pat) if os.path.getmtime(f) > cutoff)
    _log(f"scanning {len(files)} recent transcript(s) days={days} min_min={min_min}")
    rows = []
    for path in files:
        conv = Path(path).parts[-4]
        for turn in split_turns(_read_steps(path)):
            row = _analyze_turn(conv, turn, rates, min_min, pat)
            if row is not None:
                rows.append(row)
    rows.sort(key=lambda r: r["dur_s"], reverse=True)
    return {
        "schema": "tdq-long-turns/v2",
        "days": days,
        "min_min": min_min,
        "hook_rates_s": rates,
        "summary": {
            "total_turns": len(rows),
            "cov_ge_90": sum(1 for r in rows if r["do_phu"] >= 0.9),
            "f9e21752_turns": sum(
                1 for r in rows if r["conv"].startswith("f9e21752")
            ),
        },
        "turns": rows,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Decompose long turns in Antigravity transcripts."
    )
    parser.add_argument("--days", type=float, default=2.0)
    parser.add_argument("--min-min", type=float, default=10.0)
    parser.add_argument("--pattern", default=None)
    parser.add_argument("--brain-dir", default=str(DEFAULT_BRAIN_DIR))
    parser.add_argument("--bench-json", default=str(DEFAULT_BENCH_JSON))
    parser.add_argument("--json", dest="json_out", help="Write JSON output to file.")
    args = parser.parse_args(argv)

    report = scan_long_turns(
        Path(args.brain_dir),
        args.days,
        args.min_min,
        args.pattern,
        Path(args.bench_json),
    )
    for row in report["turns"][:25]:
        print(
            f"{row['dur_min']:6.1f}m cov={row['do_phu']:4.2f} "
            f"err={row['api_err_s'] / 60:5.1f}m "
            f"mod={row['model_gen_s'] / 60:5.1f}m "
            f"tool={row['tool_exec_s'] / 60:4.1f}m "
            f"hook={row['hook_est_s'] / 60:4.1f}m "
            f"deny={row['deny_wait_s']:4.0f}s "
            f"{row['conv'][:8]} | {row['prompt'][:48]}"
        )
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(report, indent=2, ensure_ascii=False)
        out.write_text(payload, encoding="utf-8")
        _log(f"wrote {len(report['turns'])} turns to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
