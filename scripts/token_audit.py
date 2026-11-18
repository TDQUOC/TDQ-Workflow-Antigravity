#!/usr/bin/env python3
"""token_audit.py — measure the real token cost of one Claude Code session.

Cost model: every tool call = 1 API call = the model re-reads the WHOLE context.
So a tool output `n` characters long does not cost `n/4` tokens, it costs
`n/4 × the number of API calls left after it`. That quantity is the **carry-cost**.

The script reads the jsonl transcript of Claude Code (changing nothing), sums carry-cost
per tool group and prints a table showing where the tokens burn.

Usage:
        python3 scripts/token_audit.py                     # current project, 3 newest sessions
    python3 scripts/token_audit.py --sessions 5
    python3 scripts/token_audit.py --transcript-dir <dir>
        python3 scripts/token_audit.py --top 20            # plus a table of the priciest tool outputs

Tokens are counted with a real tokenizer (`anthropic-tokenizer` in the `.venv-tokens/` venv,
the same counter `skill_tokens.py` uses). Missing library → the script ERRORS, it NEVER
falls back to characters/4: this table decides what gets cut, and the characters/4 estimate
is most wrong exactly in the priciest group — repeated strings and base64 compress very well,
accented text does the opposite.

Env: TDQ_AUDIT_LOG=0 turns the progress log off (log to stderr, table to stdout).
Exit: 0 even when no session is found (a warning only). 2 = bad syntax.
          3 = the token-counting library is missing.
"""

import argparse
import base64
import bisect
import collections
import datetime
import glob
import hashlib
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import skill_tokens  # noqa: E402 — share ONE token counter with the skill table
import utf8_io  # noqa: E402,F401 — imported for its side effect: stdout/stderr become UTF-8
from tdq_transcript import (  # noqa: E402
    claude_transcript_dir,
    detect_host_from_events,
    discover_host_sessions,
    extract_agy_audit_data,
    extract_codex_audit_data,
)

EXIT_THIEU_THU_VIEN = skill_tokens.EXIT_THIEU_THU_VIEN
SUBAGENT_TOOLS = frozenset({
    "Agent",
    "Task",
    "invoke_subagent",
    "define_subagent",
    "manage_subagents",
    "send_message",
    "browser_subagent",
    "spawn_agent",
    "send_input",
    "wait",
    "wait_agent",
    "close_agent",
})
READ_TOOLS = frozenset({"Read", "read_file", "view_file", "view_file_outline", "view_code_item"})
EDIT_TOOLS = frozenset({
    "Edit",
    "MultiEdit",
    "edit_file",
    "replace_file_content",
    "multi_replace_file_content",
})
SHELL_TOOLS = frozenset({"Bash", "run_command", "exec", "exec_command", "shell"})

# Normalisation factors to "equivalent input tokens" — taken from the multiplier table of the
# official pricing page (platform.claude.com/docs/en/about-claude/pricing, read 2026-08-05):
# cache hit 0.1x · cache write TTL 5 min 1.25x · cache write TTL 1 hour 2x · output 5x.
COST_WEIGHTS = {"cache_read": 0.1, "input": 1.0, "output": 5.0}
CACHE_WRITE_WEIGHT = {"5m": 1.25, "1h": 2.0}
DEFAULT_CACHE_TTL = "1h"        # Claude Code sessions currently run on a 1-hour TTL

Row = collections.namedtuple("Row", "group count tokens")
Item = collections.namedtuple("Item", "tokens chars group label size")
Phan = collections.namedtuple("Phan", "group count trung_vi p90 p99 lon_nhat tong")
HanhViRead = collections.namedtuple("HanhViRead", "tong co_pham_vi doc_lai")


# ----------------------------------------------------------------- token counting

# Cache by content: a transcript repeats a great many identical chunks (the same file read
# again, the same command re-run). Keyed by digest rather than by the string itself so the
# dict does not hold a second copy of the whole transcript in memory.
_CACHE = {}
_BO_DEM = None
_DA_THU_TRONG_TIEN_TRINH = False


def _khoa(text):
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()


def dem_nhieu(doan):
    """Count tokens for a batch of chunks, returning a list in the same order. Raises
    `ThieuThuVienDem` when a real count is impossible — guessing is banned."""
    global _BO_DEM, _DA_THU_TRONG_TIEN_TRINH
    khoa = [_khoa(t) if t else None for t in doan]
    can = {}
    for k, t in zip(khoa, doan):
        if k is not None and k not in _CACHE:
            can[k] = t
    if can:
        if not _DA_THU_TRONG_TIEN_TRINH:
            try:
                _BO_DEM = skill_tokens.nap_bo_dem()
            except skill_tokens.ThieuThuVienDem:
                _BO_DEM = None
            _DA_THU_TRONG_TIEN_TRINH = True
        if _BO_DEM is not None:
            so = [_BO_DEM(t) for t in can.values()]
        else:
            _log(f"counted {len(can)} chunk(s) through the python of .venv-tokens")
            so = skill_tokens.dem_qua_venv(list(can.values()))
        _CACHE.update(zip(can, so))
    return [_CACHE[k] if k is not None else 0 for k in khoa]


def dem_token(text):
    """The real token count of one chunk."""
    return dem_nhieu([text])[0]


# ----------------------------------------------------------------- log service

def _log_enabled():
    return (os.environ.get("TDQ_AUDIT_LOG", "1") != "0"
            and os.environ.get("TDQ_LOG", "1") != "0")


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _log(message):
    """Log progress to stderr with an ISO timestamp. Turn it off with TDQ_AUDIT_LOG=0 or TDQ_LOG=0."""
    if _log_enabled():
        print(f"[{_now()}] {message}", file=sys.stderr)


# ----------------------------------------------------------------- reading the transcript

def iter_events(path):
    """Yield the jsonl records one by one. A broken/empty line is skipped without spoiling the read."""
    try:
        fh = open(path, encoding="utf-8")
    except OSError as exc:
        _log(f"skipping {os.path.basename(str(path))}: {exc}")
        return
    bad = 0
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except (ValueError, TypeError):
                bad += 1
                continue
            if isinstance(record, dict):
                yield record
            else:
                bad += 1
    if bad:
        _log(f"{os.path.basename(str(path))}: skipped {bad} unreadable line(s)")


def default_transcript_dir(project_dir=None):
    """The Claude Code transcript folder for a project (~/.claude/projects/<slug>)."""
    return claude_transcript_dir(project_dir)


def find_sessions(transcript_dir, limit=3):
    """The list of newest jsonl files (by mtime), at most `limit` of them."""
    files = glob.glob(os.path.join(transcript_dir, "*.jsonl"))
    files.sort(key=os.path.getmtime)
    return files[-limit:] if limit and limit > 0 else files


# ----------------------------------------------------------------- grouping

def classify(tool_name, tool_input):
    """Group tool calls into readable buckets — the bucket is the unit for deciding what to cut."""
    if tool_name in SHELL_TOOLS:
        inp = tool_input or {}
        cmd = inp.get("command") or inp.get("CommandLine") or inp.get("cmd") or ""
        if "tdq_state.py" in cmd:
            return "tdq_state.py (dump JSON)"
        if "unittest" in cmd or "pytest" in cmd:
            return "test suite run"
        if "doc_lint" in cmd:
            return "doc_lint"
        if "graphify" in cmd:
            return "graphify"
        return "other Bash" if tool_name == "Bash" else tool_name
    if tool_name in READ_TOOLS:
        return "Read file"
    if tool_name in EDIT_TOOLS:
        return "Edit (echoes the diff back)"
    if tool_name and "tavily" in tool_name:
        return "tavily search"
    return tool_name or "?"


def _label(tool_name, tool_input):
    """A short label identifying one specific tool call in the top table."""
    inp = tool_input or {}
    keys = (
        "file_path", "command", "query", "description", "pattern",
        "Path", "path", "AbsolutePath", "CommandLine", "cmd",
        "Query", "Recipient", "AgentName", "Name", "Prompt", "raw",
    )
    for key in keys:
        if inp.get(key):
            return f"{tool_name}: {str(inp[key])[:70]}"
    return tool_name or "?"


# Images are counted by patch rather than by base64 string length: each 28×28 px patch is one
# vision token, so an image costs ⌈w/28⌉ × ⌈h/28⌉ tokens (Claude's Vision docs,
# platform.claude.com/docs/build-with-claude/vision, read 2026-08-19). When the size cannot be
# read, 1,600 is used — the level the docs give for a max-size image that is not downscaled.
PATCH_PX = 28
TOKEN_ANH_KHONG_RO = 1600


def _kich_thuoc_png(raw):
    if raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", raw[16:24])


def _kich_thuoc_jpeg(raw):
    if raw[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(raw):
        if raw[i] != 0xFF:
            i += 1
            continue
        marker = raw[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        do_dai = int.from_bytes(raw[i + 2:i + 4], "big")
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            cao, rong = struct.unpack(">HH", raw[i + 5:i + 9])
            return rong, cao
        i += 2 + do_dai
    return None


def dem_anh(media_type, data_base64):
    """The tokens of one image block. Reads the real size from the header, never decoding the image."""
    try:
        raw = base64.b64decode(data_base64[:512], validate=False)
    except Exception:
        return TOKEN_ANH_KHONG_RO
    kich_thuoc = _kich_thuoc_png(raw)
    if kich_thuoc is None and "jpeg" in (media_type or ""):
        kich_thuoc = _kich_thuoc_jpeg(base64.b64decode(data_base64, validate=False))
    if not kich_thuoc or not all(kich_thuoc):
        return TOKEN_ANH_KHONG_RO
    rong, cao = kich_thuoc
    return -(-rong // PATCH_PX) * -(-cao // PATCH_PX)


def _content_text(block):
    """The TEXT part of a tool_result, with the image payload lifted out (see `_tach_anh`)."""
    return _tach_anh(block)[0]


def _tach_anh(block):
    """Split a tool_result into (text part, total image tokens).

    The base64 payload of an image is replaced by a short label before counting: keeping it makes
    one screenshot swell to hundreds of thousands of tokens while the model spends a few thousand.
    """
    content = block.get("content")
    if isinstance(content, str):
        return content, 0
    if not isinstance(content, list):
        return json.dumps(content, ensure_ascii=False), 0
    anh = 0
    sach = []
    for khoi in content:
        if isinstance(khoi, dict) and khoi.get("type") == "image":
            src = khoi.get("source") or {}
            anh += dem_anh(src.get("media_type"), src.get("data") or "")
            sach.append({"type": "image", "media_type": src.get("media_type")})
        else:
            sach.append(khoi)
    return json.dumps(sach, ensure_ascii=False), anh


# ----------------------------------------------------------------- computation

def _message_key(ev, index):
    """The key that groups jsonl lines back into one message.

    Claude Code writes ONE message (thinking + text + tool_use) as SEVERAL jsonl lines sharing
    a `message.id`, each line repeating the whole `usage` block. Summing per line double-counts.
    A line with no `id` (old transcript) counts as a message of its own.
    """
    mid = (ev.get("message") or {}).get("id")
    return mid if mid else f"__line_{index}"


def _count_chunks(chunks, allow_inferred=False):
    """Count tokens using real tokenizer, or chars/4 fallback if `allow_inferred` is True."""
    if not chunks:
        return [], "measured"
    try:
        return dem_nhieu(chunks), "measured"
    except skill_tokens.ThieuThuVienDem:
        if not allow_inferred:
            raise
        counts = [max(1, len(text) // 4) if text else 0 for text in chunks]
        return counts, "inferred"


def _read_path_and_range(tool_name, args):
    if tool_name not in READ_TOOLS or not isinstance(args, dict):
        return None, False
    path = args.get("file_path") or args.get("Path") or args.get("path") or args.get("AbsolutePath")
    has_range = any(
        args.get(key) is not None
        for key in ("offset", "limit", "StartLine", "EndLine", "start_line", "end_line")
    )
    return path, has_range


def _collect_claude_tool_uses(events):
    names, reads = {}, []
    for ev in events:
        content = (ev.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name, inp = block.get("name"), block.get("input") or {}
            names[block.get("id")] = (name, inp)
            rpath, has_range = _read_path_and_range(name, inp)
            if rpath:
                reads.append((rpath, has_range))
    return names, reads


def _collect_claude_usage(events):
    usage_by_msg, call_idx = {}, []
    for i, ev in enumerate(events):
        usage = (ev.get("message") or {}).get("usage")
        if not usage:
            continue
        key = _message_key(ev, i)
        if key not in usage_by_msg:
            usage_by_msg[key] = usage
            call_idx.append(i)
    return usage_by_msg, call_idx


def _scan_claude(events, allow_inferred=False):
    names, reads = _collect_claude_tool_uses(events)
    usage_by_msg, call_idx = _collect_claude_usage(events)

    totals = collections.Counter()
    totals["api_calls"] = len(usage_by_msg)
    totals["tool_calls"] = len(names)        # already deduped by `tool_use.id`
    for field in ("output", "input", "cache_read", "cache_write"):
        totals[field] += 0
    for usage in usage_by_msg.values():
        totals["output"] += usage.get("output_tokens", 0)
        totals["input"] += usage.get("input_tokens", 0)
        totals["cache_read"] += usage.get("cache_read_input_tokens", 0)
        totals["cache_write"] += usage.get("cache_creation_input_tokens", 0)

    tho = []
    for i, ev in enumerate(events):
        content = (ev.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            name, inp = names.get(block.get("tool_use_id"), (None, {}))
            text, anh = _tach_anh(block)
            remaining = len(call_idx) - bisect.bisect_left(call_idx, i)
            tho.append((text, anh, remaining, classify(name, inp), _label(name, inp), name, inp))
    so, carry_basis = _count_chunks([t[0] for t in tho], allow_inferred=allow_inferred)
    items = [
        Item((n + anh) * con_lai, len(text), group, label, n + anh)
        for (text, anh, con_lai, group, label, _, _), n in zip(tho, so)
    ]
    subagents = [
        (name, label, item.tokens, item.size)
        for (_, _, _, _, label, name, _), item in zip(tho, items)
        if name in SUBAGENT_TOOLS
    ]
    read_items = [
        (rpath, item.tokens)
        for (_, _, _, _, _, name, inp), item in zip(tho, items)
        for rpath, _ in [_read_path_and_range(name, inp)]
        if rpath
    ]
    usage_basis = "measured" if usage_by_msg else "inferred"
    basis = "measured" if (usage_basis == "measured" and carry_basis == "measured") else "inferred"
    if not events:
        usage_basis = carry_basis = basis = "inferred"
    meta = {
        "host": "claude",
        "basis": basis,
        "usage_basis": usage_basis,
        "carry_basis": carry_basis,
        "reads": reads,
        "read_items": read_items,
        "subagents": subagents,
    }
    return items, totals, meta


def _scan_non_claude(events, host, allow_inferred=True):
    data = extract_agy_audit_data(events) if host == "agy" else extract_codex_audit_data(events)
    call_idx = data["call_idx"]
    reads = [
        res_pair for name, args in data["tool_calls"]
        for res_pair in [_read_path_and_range(name, args)]
        if res_pair[0]
    ]
    raw_rows = []
    for res in data["results"]:
        name, args, text = res["tool_name"], res["args"], res["text"]
        img_tok = res.get("media_count", 0) * TOKEN_ANH_KHONG_RO
        remaining = len(call_idx) - bisect.bisect_left(call_idx, res["index"])
        raw_rows.append((text, img_tok, remaining, classify(name, args), _label(name, args), name, args))

    counts, carry_basis = _count_chunks([row[0] for row in raw_rows], allow_inferred=allow_inferred)
    items = [
        Item((n + img_tok) * rem, len(text), group, label, n + img_tok)
        for (text, img_tok, rem, group, label, _, _), n in zip(raw_rows, counts)
    ]
    subagents = [
        (name, label, item.tokens, item.size)
        for (_, _, _, _, label, name, _), item in zip(raw_rows, items)
        if name in SUBAGENT_TOOLS
    ]
    read_items = [
        (rpath, item.tokens)
        for (_, _, _, _, _, name, args), item in zip(raw_rows, items)
        for rpath, _ in [_read_path_and_range(name, args)]
        if rpath
    ]
    usage_basis = "measured" if data["has_real_usage"] else "inferred"
    if not events:
        usage_basis = carry_basis = "inferred"
    basis = "measured" if (usage_basis == "measured" and carry_basis == "measured") else "inferred"
    meta = {
        "host": host,
        "basis": basis,
        "usage_basis": usage_basis,
        "carry_basis": carry_basis,
        "reads": reads,
        "read_items": read_items,
        "subagents": subagents,
    }
    return items, data["totals"], meta


def _scan_with_meta(path, host=None, allow_inferred=False):
    events = list(iter_events(path))
    resolved = host or detect_host_from_events(events)
    if resolved == "claude":
        return _scan_claude(events, allow_inferred=allow_inferred)
    return _scan_non_claude(events, resolved, allow_inferred=True)


def _scan(path, host=None, allow_inferred=False):
    """Returns (the list of Items of this file, the usage totals)."""
    items, totals, _ = _scan_with_meta(path, host=host, allow_inferred=allow_inferred)
    return items, totals


def _all_items(paths):
    items = []
    for path in paths:
        got, _ = _scan(path)
        _log(f"{os.path.basename(str(path))}: {len(got)} tool result")
        items.extend(got)
    return items


def carry_cost(paths):
    """The carry-cost table grouped by bucket, descending. `paths` empty → empty table."""
    agg_tokens = collections.Counter()
    agg_count = collections.Counter()
    for item in _all_items(paths):
        agg_tokens[item.group] += item.tokens
        agg_count[item.group] += 1
    rows = [Row(g, agg_count[g], t) for g, t in agg_tokens.items()]
    rows.sort(key=lambda r: r.tokens, reverse=True)
    return rows


def top_items(paths, limit=15):
    """The priciest tool outputs by carry-cost."""
    return sorted(_all_items(paths), key=lambda it: it.tokens, reverse=True)[:limit]


def _phan_vi(day_sap_xep, q):
    """Nearest-rank percentile: position `ceil(q×n)`, counting from 1.

    This kind, not interpolation, because every printed value must be a REAL output present in
    the transcript — an interpolated number matches no call and cannot be traced back.
    """
    if not day_sap_xep:
        return 0
    n = len(day_sap_xep)
    hang = max(1, min(n, -(-int(round(q * n * 1000)) // 1000)))
    return day_sap_xep[hang - 1]


def phan_ra(paths):
    """Output size broken down per tool group: n, median, p90, p99, largest.

    Different from `carry_cost`: here are the REAL tokens of each output, not yet multiplied by
    the calls remaining. A high total carry-cost has two very different causes — many small calls
    (behaviour must change) or a few huge ones (an output ceiling must be set) — and only this
    table tells them apart.
    """
    theo_nhom = collections.defaultdict(list)
    for item in _all_items(paths):
        theo_nhom[item.group].append(item.size)
    rows = []
    for group, sizes in theo_nhom.items():
        sizes.sort()
        rows.append(Phan(group, len(sizes), _phan_vi(sizes, 0.5), _phan_vi(sizes, 0.9),
                         _phan_vi(sizes, 0.99), sizes[-1], sum(sizes)))
    return sorted(rows, key=lambda r: r.tong, reverse=True)


def hanh_vi_read(paths):
    """Measure `Read` behaviour: how many calls, how many carry `offset`/`limit`, how many
    re-read a file already read in the SAME session.

    This table only MEASURES, it does not judge: TDQ rules demand a re-read in several cases
    (`đọc lại, cấm làm theo trí nhớ`), so a high re-read count does NOT mean waste.  # i18n-allow
    """
    tong = co_pham_vi = doc_lai = 0
    for path in paths:
        da_doc = set()
        for ev in iter_events(path):
            content = (ev.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if (not isinstance(block, dict) or block.get("type") != "tool_use"
                        or block.get("name") != "Read"):
                    continue
                inp = block.get("input") or {}
                tong += 1
                if inp.get("offset") is not None or inp.get("limit") is not None:
                    co_pham_vi += 1
                duong_dan = inp.get("file_path")
                if duong_dan in da_doc:
                    doc_lai += 1
                else:
                    da_doc.add(duong_dan)
    return HanhViRead(tong, co_pham_vi, doc_lai)


def usage_totals(paths):
    """Sum the real usage the API returned: API calls, output, cache read/write."""
    totals = collections.Counter()
    for path in paths:
        _, got = _scan(path)
        totals.update(got)
    return dict(totals)


def cost_equivalent(totals, cache_ttl=DEFAULT_CACHE_TTL):
    """Normalise the bill into equivalent input tokens.

    `cache_read×0,1 + cache_write×W + input×1 + output×5`, W theo TTL cache
    (1 hour = 2.0 · 5 minutes = 1.25). Returns (total, {part: equivalent tokens}).
    """
    weight = dict(COST_WEIGHTS)
    weight["cache_write"] = CACHE_WRITE_WEIGHT.get(cache_ttl, CACHE_WRITE_WEIGHT["1h"])
    parts = {k: totals.get(k, 0) * w for k, w in weight.items()}
    return sum(parts.values()), parts


def _merge_basis(values):
    return "measured" if values and all(v == "measured" for v in values) else "inferred"


def _aggregate_repeated_reads(session_reads, read_carry, top):
    agg = {}
    for file_path, counts in session_reads.items():
        agg[file_path] = {
            "file_path": file_path,
            "reads": counts["reads"],
            "re_reads": counts["re_reads"],
            "carry_tokens": read_carry.get(file_path, 0),
            "hosts": sorted(counts["hosts"]),
            "basis": _merge_basis(counts["bases"]),
        }
    rows = sorted(
        agg.values(),
        key=lambda row: (row["re_reads"], row["reads"], row["carry_tokens"]),
        reverse=True,
    )
    return rows[:top] if top and top > 0 else rows


def _aggregate_subagents(raw_subagents, top):
    agg = {}
    for host_name, tool_name, label, tokens, size, basis in raw_subagents:
        key = (host_name, tool_name, label)
        entry = agg.setdefault(key, {
            "host": host_name, "tool": tool_name, "label": label,
            "count": 0, "tokens": 0, "size": 0, "bases": [],
        })
        entry["count"] += 1
        entry["tokens"] += tokens
        entry["size"] += size
        entry["bases"].append(basis)
    rows = [
        {
            "host": e["host"], "tool": e["tool"], "label": e["label"],
            "count": e["count"], "tokens": e["tokens"], "size": e["size"],
            "basis": _merge_basis(e["bases"]),
        }
        for e in agg.values()
    ]
    rows.sort(key=lambda row: (row["tokens"], row["size"], row["count"]), reverse=True)
    return rows[:top] if top and top > 0 else rows


def _audit_session_pairs(pairs, host="all", limit=5, top=10, cache_ttl=DEFAULT_CACHE_TTL):
    allow_inferred = host != "claude"
    host_buckets = {}
    group_agg = {}
    all_top = []
    session_reads = {}
    read_carry = collections.Counter()
    raw_subagents = []

    for hname, path in pairs:
        items, totals, meta = _scan_with_meta(path, host=hname, allow_inferred=allow_inferred)
        _log(f"[{hname}] {os.path.basename(str(path))}: {len(items)} tool result(s) ({meta['basis']})")
        bucket = host_buckets.setdefault(hname, {
            "host": hname, "sessions": 0, "totals": collections.Counter(),
            "carry_cost": 0, "bases": [], "usage_bases": [], "carry_bases": [], "paths": [],
        })
        bucket["sessions"] += 1
        bucket["totals"].update(totals)
        bucket["carry_cost"] += sum(it.tokens for it in items)
        bucket["bases"].append(meta["basis"])
        bucket["usage_bases"].append(meta["usage_basis"])
        bucket["carry_bases"].append(meta["carry_basis"])
        bucket["paths"].append(str(path))

        for it in items:
            grp = group_agg.setdefault(it.group, {"count": 0, "tokens": 0, "bases": []})
            grp["count"] += 1
            grp["tokens"] += it.tokens
            grp["bases"].append(meta["carry_basis"])
            all_top.append({
                "host": hname, "group": it.group, "label": it.label,
                "tokens": it.tokens, "size": it.size, "chars": it.chars,
                "basis": meta["carry_basis"],
            })

        seen_in_session = set()
        for rpath, _ in meta["reads"]:
            entry = session_reads.setdefault(rpath, {"reads": 0, "re_reads": 0, "hosts": set(), "bases": []})
            entry["reads"] += 1
            entry["hosts"].add(hname)
            entry["bases"].append(meta["carry_basis"])
            if rpath in seen_in_session:
                entry["re_reads"] += 1
            else:
                seen_in_session.add(rpath)
        for rpath, tok in meta["read_items"]:
            read_carry[rpath] += tok
        for tool_name, label, tok, size in meta["subagents"]:
            raw_subagents.append((hname, tool_name, label, tok, size, meta["carry_basis"]))

    host_rows = []
    for b in host_buckets.values():
        t = b["totals"]
        equiv, _ = cost_equivalent(t, cache_ttl)
        host_rows.append({
            "host": b["host"],
            "sessions": b["sessions"],
            "api_calls": t.get("api_calls", 0),
            "tool_calls": t.get("tool_calls", 0),
            "input": t.get("input", 0),
            "output": t.get("output", 0),
            "cache_read": t.get("cache_read", 0),
            "cache_write": t.get("cache_write", 0),
            "carry_cost": b["carry_cost"],
            "equiv_cost": round(equiv, 2),
            "basis": _merge_basis(b["bases"]),
            "usage_basis": _merge_basis(b["usage_bases"]),
            "carry_basis": _merge_basis(b["carry_bases"]),
            "paths": b["paths"],
        })

    groups = sorted(
        ({"group": g, "count": d["count"], "tokens": d["tokens"], "basis": _merge_basis(d["bases"])}
         for g, d in group_agg.items()),
        key=lambda row: row["tokens"],
        reverse=True,
    )
    all_top.sort(key=lambda row: (row["tokens"], row["size"]), reverse=True)
    top_rows = all_top[:top] if top and top > 0 else all_top
    return {
        "host_filter": host,
        "limit": limit,
        "sessions_scanned": len(pairs),
        "hosts": host_rows,
        "groups": groups,
        "top_items": top_rows,
        "repeated_reads": _aggregate_repeated_reads(session_reads, read_carry, top),
        "subagent_calls": _aggregate_subagents(raw_subagents, top),
    }


def audit_multi_host(host="all", project_dir=None, limit=5, top=10, home=None, cache_ttl=DEFAULT_CACHE_TTL):
    """Audit up to `limit` newest sessions per host (`all`, `agy`, `codex`, `claude`)."""
    pairs = discover_host_sessions(host=host, project_dir=project_dir, limit=limit, home=home)
    return _audit_session_pairs(pairs, host=host, limit=limit, top=top, cache_ttl=cache_ttl)


# ----------------------------------------------------------------- CLI

def _fmt(n):
    return f"{n:,}"


def _print_multi_host_report(report, top):
    print(f"# Multi-host token audit — host={report['host_filter']} · "
          f"{report['sessions_scanned']} session(s)")
    print()
    print(f"{'host':<10}{'sess':>6}{'api':>7}{'tools':>7}"
          f"{'equiv_tok':>14}{'carry-cost':>15}  {'basis':<10}")
    print("-" * 71)
    for row in report["hosts"]:
        print(f"{row['host']:<10}{row['sessions']:>6}{row['api_calls']:>7}{row['tool_calls']:>7}"
              f"{_fmt(round(row['equiv_cost'])):>14}{_fmt(row['carry_cost']):>15}  {row['basis']:<10}")
    print()
    print(f"{'group':<28}{'calls':>7}{'carry-cost (tokens)':>22}  {'basis':<10}")
    print("-" * 69)
    for grp in report["groups"]:
        print(f"{grp['group']:<28}{grp['count']:>7}{_fmt(grp['tokens']):>22}  {grp['basis']:<10}")
    if top and report["top_items"]:
        print()
        print(f"# Top {len(report['top_items'])} priciest tool outputs")
        for item in report["top_items"]:
            print(f"  [{item['host']}|{item['basis']}] {_fmt(item['tokens']):>12} tok | "
                  f"{_fmt(item['chars']):>8} chars | {item['group']:<22} {item['label'][:60]}")
    if report["repeated_reads"]:
        print()
        print("# Repeated file reads")
        for rd in report["repeated_reads"]:
            print(f"  [{rd['basis']}] re-reads={rd['re_reads']} total={rd['reads']} | "
                  f"{_fmt(rd['carry_tokens']):>10} tok | {rd['file_path']}")
    if report["subagent_calls"]:
        print()
        print("# Subagent calls")
        for sub in report["subagent_calls"]:
            print(f"  [{sub['host']}|{sub['basis']}] calls={sub['count']} | "
                  f"{_fmt(sub['tokens']):>10} tok | {sub['label'][:70]}")


def _run_multi_host_cli(args, sessions, top_n):
    if args.transcript_dir:
        paths = find_sessions(args.transcript_dir, sessions)
        if not paths:
            _log(f"no session found in {args.transcript_dir} — nothing to measure")
            print("No session to measure.")
            return 0
        host_name = "claude" if args.host == "claude" else args.host
        pairs = [(host_name if host_name != "all" else detect_host_from_events(list(iter_events(p))), p)
                 for p in paths]
        report = _audit_session_pairs(pairs, host=args.host, limit=sessions, top=top_n, cache_ttl=args.cache_ttl)
    else:
        report = audit_multi_host(
            host=args.host, project_dir=args.project, limit=sessions, top=top_n, cache_ttl=args.cache_ttl
        )
    if not report["sessions_scanned"]:
        _log(f"no session found for host={args.host} — nothing to measure")
        print("No session to measure.")
        return 0
    _print_multi_host_report(report, top_n)
    total_carry = sum(row["carry_cost"] for row in report["hosts"])
    _log(f"done — multi-host total carry-cost {_fmt(total_carry)} tokens")
    return 0


def _run_legacy_cli(args, sessions, top_n):
    tdir = args.transcript_dir or default_transcript_dir(args.project)
    _log(f"reading transcripts from {tdir}")
    paths = find_sessions(tdir, sessions)
    if not paths:
        _log(f"no session found in {tdir} — nothing to measure")
        print("No session to measure.")
        return 0
    _log(f"measuring {len(paths)} session(s)")

    totals = usage_totals(paths)
    rows = carry_cost(paths)
    total_carry = sum(r.tokens for r in rows)

    print(f"# Token audit — {len(paths)} session · {tdir}")
    print()
    print(f"API call: {_fmt(totals.get('api_calls', 0))} · "
          f"tool call: {_fmt(totals.get('tool_calls', 0))} · "
          f"output: {_fmt(totals.get('output', 0))} · "
          f"input: {_fmt(totals.get('input', 0))} · "
          f"cache_read: {_fmt(totals.get('cache_read', 0))} · "
          f"cache_write: {_fmt(totals.get('cache_write', 0))}")
    equiv, parts = cost_equivalent(totals, args.cache_ttl)
    share = " · ".join(f"{k} {parts[k] / equiv * 100:.0f}%"
                       for k in ("cache_read", "cache_write", "input", "output")) if equiv else "—"
    print(f"Converted cost (TTL {args.cache_ttl}): {_fmt(round(equiv))} equivalent "
          f"input tokens — {share}")
    print()
    print(f"{'group':<28}{'calls':>7}{'carry-cost (tokens)':>22}")
    print("-" * 57)
    for row in rows:
        print(f"{row.group:<28}{row.count:>7}{_fmt(row.tokens):>22}")
    print("-" * 57)
    print(f"{'TOTAL':<28}{sum(r.count for r in rows):>7}{_fmt(total_carry):>22}")

    print()
    print("# Output size breakdown (real tokens of each call)")
    print(f"{'group':<28}{'calls':>7}{'median':>10}{'p90':>10}{'p99':>10}{'largest':>11}")
    print("-" * 76)
    for pr in phan_ra(paths):
        print(f"{pr.group:<28}{pr.count:>7}{_fmt(pr.trung_vi):>10}{_fmt(pr.p90):>10}"
              f"{_fmt(pr.p99):>10}{_fmt(pr.lon_nhat):>11}")
    hv = hanh_vi_read(paths)
    if hv.tong:
        print()
        print(f"Read: {_fmt(hv.tong)} call(s) · with offset/limit {hv.co_pham_vi} "
              f"({hv.co_pham_vi / hv.tong * 100:.1f}%) · re-read an already-read file "
              f"{hv.doc_lai} ({hv.doc_lai / hv.tong * 100:.1f}%)")
        print("  (re-reading is the RIGHT behaviour in the 5 cases the rules demand — this only measures)")

    if top_n:
        print()
        print(f"# Top {top_n} priciest tool outputs")
        for item in top_items(paths, top_n):
            print(f"  {_fmt(item.tokens):>12} tok | {_fmt(item.chars):>8} chars | "
                  f"{item.group:<26} {item.label[:70]}")

    _log(f"done — total carry-cost {_fmt(total_carry)} tokens")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Measure the token carry-cost of Antigravity, Codex, and Claude Code transcripts.")
    parser.add_argument("--host", choices=("all", "agy", "codex", "claude"),
                        help="host transcript source to audit (default: legacy Claude-only mode)")
    parser.add_argument("--project", help="project folder (default: the current folder)")
    parser.add_argument("--transcript-dir", help="point straight at the folder holding *.jsonl")
    parser.add_argument("--sessions", type=int, default=None,
                        help="how many newest sessions to measure (default 3 for legacy, 5 for --host; 0 = all)")
    parser.add_argument("--top", type=int, default=None,
                        help="also print the N priciest tool outputs (default 0 for legacy, 10 for --host)")
    parser.add_argument("--cache-ttl", choices=sorted(CACHE_WRITE_WEIGHT),
                        default=DEFAULT_CACHE_TTL,
                        help="cache TTL used to convert the cost (default 1h = factor 2.0)")
    args = parser.parse_args(argv)

    is_multi = args.host is not None
    sessions = (5 if is_multi else 3) if args.sessions is None else args.sessions
    top_n = (10 if is_multi else 0) if args.top is None else args.top
    try:
        if is_multi:
            return _run_multi_host_cli(args, sessions, top_n)
        return _run_legacy_cli(args, sessions, top_n)
    except skill_tokens.ThieuThuVienDem as exc:
        print("token_audit.py: the token-counting library `anthropic-tokenizer` is missing.\n"
              "This script is FORBIDDEN to estimate characters/4, so it stops here.\n"
              f"Install with: {exc}", file=sys.stderr)
        return EXIT_THIEU_THU_VIEN


if __name__ == "__main__":
    sys.exit(main())
