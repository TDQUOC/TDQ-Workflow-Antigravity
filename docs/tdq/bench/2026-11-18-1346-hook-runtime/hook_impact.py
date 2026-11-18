"""Scan recent Antigravity transcripts for TDQ hook denials, stop blocks, and injections."""
import argparse
import collections
from datetime import datetime
import glob
import json
import os
from pathlib import Path
import re
import statistics
import time

DEFAULT_BRAIN_DIR = Path(r"~\.gemini\antigravity\brain").expanduser()
TAG_RE = re.compile(r"\[TDQ:([A-Z_\-]+)\]")
NON_TOOL_TYPES = ("USER_INPUT", "PLANNER_RESPONSE", "SYSTEM_MESSAGE", "CHECKPOINT")


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


def analyze_transcripts(brain_dir: Path, days: float) -> dict:
    """Aggregate hook denials, Stop blocks, context injections, and retry gaps."""
    cutoff = time.time() - days * 86400.0
    files = sorted(
        f for f in glob.glob(str(brain_dir / "*" / ".system_generated" / "logs" / "transcript_full.jsonl"))
        if os.path.getmtime(f) > cutoff
    )
    deny_counts = collections.Counter()
    deny_planner_mentions = collections.Counter()
    deny_streak = collections.Counter()
    deny_samples = {}
    stop_counts = collections.Counter()
    stop_samples = {}
    injections = collections.defaultdict(list)
    deny_waits = []
    conv_stats = []
    tool_steps_total = 0
    model_calls_total = 0

    for path in files:
        conv_id = Path(path).parts[-4]
        steps = []
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    steps.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        n_deny = n_stop = n_tool = 0
        last_deny_tag = None
        pending_deny_ts = None
        for step in steps:
            txt = step_text(step)
            typ = step.get("type")
            if typ == "PLANNER_RESPONSE":
                model_calls_total += 1
            elif typ not in NON_TOOL_TYPES:
                n_tool += 1
            if "denied by pre-tool hook" in txt:
                match = TAG_RE.search(txt)
                tag = match.group(1) if match else "?"
                if typ in NON_TOOL_TYPES:
                    deny_planner_mentions[tag] += 1
                else:
                    deny_counts[tag] += 1
                    n_deny += 1
                    deny_samples.setdefault(tag, txt[txt.find("denied by pre-tool hook"):][:260])
                    if tag == last_deny_tag:
                        deny_streak[tag] += 1
                    last_deny_tag = tag
                    if pending_deny_ts is None:
                        pending_deny_ts = parse_ts(step)
                continue
            if typ not in NON_TOOL_TYPES and step.get("status") == "DONE":
                step_t = parse_ts(step)
                if pending_deny_ts is not None and step_t is not None and step_t >= pending_deny_ts:
                    deny_waits.append(step_t - pending_deny_ts)
                pending_deny_ts = None
                last_deny_tag = None
            if "Stop hook blocked termination" in txt:
                idx = txt.find("Stop hook blocked")
                match = TAG_RE.search(txt[idx:])
                tag = match.group(1) if match else "?"
                stop_counts[tag] += 1
                n_stop += 1
                stop_samples.setdefault(tag, txt[idx:][:260])
            for ev in ("PreInvocation", "PostInvocation", "SessionStart", "SubagentStart"):
                marker = f"injected by a {ev} hook"
                if marker in txt:
                    body = txt[txt.find(marker):]
                    end = body.find("</SYSTEM_MESSAGE>")
                    injections[ev].append(len(body[:end if end > 0 else None]))
        tool_steps_total += n_tool
        conv_stats.append({"conv": conv_id, "deny": n_deny, "stop": n_stop, "tool_steps": n_tool})

    deny_waits.sort()
    p90_wait = deny_waits[int(len(deny_waits) * 0.9)] if deny_waits else 0.0
    inj_summary = {
        ev: {
            "n": len(vals),
            "avg_chars": round(statistics.mean(vals), 1),
            "max_chars": max(vals),
            "total_chars": sum(vals),
        }
        for ev, vals in injections.items() if vals
    }
    conv_stats.sort(key=lambda r: r["deny"] + r["stop"], reverse=True)
    return {
        "schema": "tdq-hook-impact/v1",
        "days": days,
        "files": len(files),
        "model_calls_total": model_calls_total,
        "tool_steps_total": tool_steps_total,
        "pretool_deny_total": sum(deny_counts.values()),
        "pretool_deny_by_tag": [
            {
                "tag": tag,
                "count": cnt,
                "streak_repeat": deny_streak[tag],
                "sample": deny_samples.get(tag, ""),
            }
            for tag, cnt in deny_counts.most_common()
        ],
        "planner_or_system_mentions": dict(deny_planner_mentions),
        "stop_block_total": sum(stop_counts.values()),
        "stop_block_by_tag": [
            {"tag": tag, "count": cnt, "sample": stop_samples.get(tag, "")}
            for tag, cnt in stop_counts.most_common()
        ],
        "injections": inj_summary,
        "deny_to_next_ok_tool": {
            "n": len(deny_waits),
            "median_s": round(statistics.median(deny_waits), 2) if deny_waits else 0.0,
            "p90_s": round(p90_wait, 2),
            "total_minutes": round(sum(deny_waits) / 60.0, 2),
        },
        "top_conversations": conv_stats[:15],
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Quantify TDQ hook impact in transcripts.")
    parser.add_argument("--days", type=float, default=4.0)
    parser.add_argument("--brain-dir", default=str(DEFAULT_BRAIN_DIR))
    parser.add_argument("--json", dest="json_out", help="Write JSON output to file.")
    args = parser.parse_args(argv)

    report = analyze_transcripts(Path(args.brain_dir), args.days)
    print(f"files={report['files']} days={report['days']} "
          f"model_calls={report['model_calls_total']} tool_steps={report['tool_steps_total']}")
    print(f"== PreToolUse DENY total={report['pretool_deny_total']} "
          f"(non-tool mentions={report['planner_or_system_mentions']})")
    for row in report["pretool_deny_by_tag"]:
        print(f"  {row['count']:5d} {row['tag']:14s} streak={row['streak_repeat']:4d}")
    print(f"== Stop BLOCK total={report['stop_block_total']}")
    for row in report["stop_block_by_tag"]:
        print(f"  {row['count']:5d} {row['tag']:14s}")
    dw = report["deny_to_next_ok_tool"]
    print(f"== deny->next ok: n={dw['n']} median={dw['median_s']}s "
          f"p90={dw['p90_s']}s sum={dw['total_minutes']}min")
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
