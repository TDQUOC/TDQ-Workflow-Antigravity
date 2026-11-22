#!/usr/bin/env python3
"""Lossless Context Compression & Restore (CCR) store for large files and DOM snapshots.

Stores exact raw bytes with SHA-256 verification under `.tdq-runtime/ccr/` when payloads exceed
32 KB or 200 lines, produces compact format-aware summaries (JSON, JSONL, CSV, Log, YAML, DOM),
rotates oldest records when exceeding the 128 MB cap, and restores 100% byte-identical content.

Usage:
    py -3 scripts/tdq_ccr.py summarize <path>
    py -3 scripts/tdq_ccr.py ingest [path]
    py -3 scripts/tdq_ccr.py retrieve <record_id> [--out <path>]
    py -3 scripts/tdq_ccr.py gc [--cap-bytes <bytes>]

Env:
    TDQ_LOG=0      Disable ISO-timestamped diagnostics on stderr.
    TDQ_CCR_DIR    Override default `.tdq-runtime/ccr` storage directory.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime
import hashlib
import hmac
import io
import json
import os
import re
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
import utf8_io  # noqa: F401

CCR_MIN_BYTES = 32 * 1024
CCR_MIN_LINES = 200
DEFAULT_CAP_BYTES = 128 * 1024 * 1024
DEFAULT_STORE_REL = Path(".tdq-runtime/ccr")

_ID_RE = re.compile(r"^[0-9a-fA-F]{6,64}$")
_ERR_RE = re.compile(r"\b(?:ERROR|FATAL|CRITICAL)\b", re.IGNORECASE)
_WARN_RE = re.compile(r"\bWARN(?:ING)?\b", re.IGNORECASE)
_LOG_LINE_RE = re.compile(r"^(?:\d{4}-\d{2}-\d{2}|\[?\d{2}:\d{2}:\d{2}|ERROR|WARN|INFO|DEBUG)\b")
_YAML_KEY_RE = re.compile(r"^( *)([A-Za-z0-9_.-]+):\s*(.*)$")

_EXT_TO_KIND = {
    ".json": "json",
    ".jsonl": "jsonl",
    ".ndjson": "jsonl",
    ".csv": "csv",
    ".tsv": "csv",
    ".log": "log",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".html": "dom",
    ".htm": "dom",
    ".xhtml": "dom",
    ".xml": "dom",
    ".svg": "dom",
    ".dom": "dom",
}


def _log(message: str) -> None:
    """Write one ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"[{stamp}] tdq_ccr: {message}", file=sys.stderr)


def default_store_dir() -> Path:
    """Return the configured CCR directory path."""
    override = os.environ.get("TDQ_CCR_DIR", "").strip()
    return Path(override) if override else DEFAULT_STORE_REL


def should_ccr(raw: bytes) -> bool:
    """Return True when payload exceeds 32 KB or has at least 200 lines."""
    return len(raw) > CCR_MIN_BYTES or len(raw.splitlines()) >= CCR_MIN_LINES


def _sniff_text_kind(raw: bytes) -> str:
    """Infer text format when the filename lacks a known data extension."""
    sample = raw[:4096].decode("utf-8", errors="replace").lstrip()
    if not sample:
        return "text"
    if sample.startswith("<") and ("</" in sample or "<html" in sample.lower()):
        return "dom"
    if sample[0] in "{[":
        try:
            json.loads(raw.decode("utf-8", errors="strict"))
            return "json"
        except (UnicodeDecodeError, ValueError):
            lines = [ln for ln in sample.splitlines()[:5] if ln.strip().startswith("{")]
            return "jsonl" if len(lines) >= 2 else "text"
    if any(_LOG_LINE_RE.match(ln) for ln in sample.splitlines()[:10]):
        return "log"
    return "text"


def detect_kind(source_path: str, raw: bytes) -> str:
    """Detect payload kind from binary markers, file extension, or content."""
    if b"\x00" in raw[:8192]:
        return "binary"
    ext = Path(source_path).suffix.lower() if source_path else ""
    if ext in _EXT_TO_KIND:
        return _EXT_TO_KIND[ext]
    return _sniff_text_kind(raw)


def _atomic_write_bytes(dest: Path, data: bytes) -> None:
    """Atomically write bytes into `dest` via a same-directory temp file."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
        os.replace(tmp_path, dest)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _collect_records(store_dir: Path) -> list[tuple[int, str, list[Path], int]]:
    """Group `.raw` and `.meta.json` files by record ID with mtime and total bytes."""
    grouped: dict[str, list[Path]] = {}
    for entry in store_dir.iterdir():
        if not entry.is_file() or entry.name.endswith(".tmp"):
            continue
        name = entry.name
        if name.endswith(".meta.json"):
            rid = name[:-10]
        elif name.endswith(".raw"):
            rid = name[:-4]
        else:
            continue
        grouped.setdefault(rid, []).append(entry)

    records: list[tuple[int, str, list[Path], int]] = []
    for rid, paths in grouped.items():
        total_size = 0
        mtime_ns = 0
        for path in paths:
            stat = path.stat()
            total_size += stat.st_size
            if path.name.endswith(".raw") or mtime_ns == 0:
                mtime_ns = stat.st_mtime_ns
        records.append((mtime_ns, rid, paths, total_size))
    return records


def enforce_cap(store_dir: Path, cap_bytes: int) -> list[str]:
    """Delete oldest records by mtime until total store size <= `cap_bytes`."""
    store = Path(store_dir)
    if not store.exists():
        return []
    limit = max(0, int(cap_bytes))
    records = _collect_records(store)
    total = sum(item[3] for item in records)
    if total <= limit:
        return []

    evicted: list[str] = []
    for _mtime, rid, paths, size in sorted(records, key=lambda item: (item[0], item[1])):
        if total <= limit:
            break
        for path in paths:
            path.unlink(missing_ok=True)
        total -= size
        evicted.append(rid)

    if evicted:
        _log(f"evicted {len(evicted)} record(s) to enforce cap={limit} remaining={total}")
    return evicted


def ingest_bytes(
    raw: bytes,
    source_path: str = "",
    store_dir: Path | None = None,
    cap_bytes: int = DEFAULT_CAP_BYTES,
) -> dict:
    """Persist raw bytes with SHA-256 metadata and enforce the store byte cap."""
    if isinstance(raw, (bytearray, memoryview)):
        raw = bytes(raw)
    if not isinstance(raw, bytes):
        raise TypeError("raw must be bytes-like")

    target_dir = Path(store_dir) if store_dir is not None else default_store_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    sha256 = hashlib.sha256(raw).hexdigest()
    record_id = sha256[:12]
    kind = detect_kind(source_path, raw)
    line_count = len(raw.splitlines())
    created_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    raw_path = target_dir / f"{record_id}.raw"
    meta_path = target_dir / f"{record_id}.meta.json"
    meta = {
        "id": record_id,
        "sha256": sha256,
        "bytes": len(raw),
        "lines": line_count,
        "kind": kind,
        "source_path": source_path,
        "created_at": created_at,
    }
    _atomic_write_bytes(raw_path, raw)
    _atomic_write_bytes(meta_path, (json.dumps(meta, indent=2) + "\n").encode("utf-8"))
    evicted = enforce_cap(target_dir, cap_bytes)
    _log(f"ingest id={record_id} bytes={len(raw)} lines={line_count} kind={kind} evicted={len(evicted)}")
    return {
        **meta,
        "raw_path": str(raw_path),
        "meta_path": str(meta_path),
        "evicted": evicted,
    }


def _resolve_record_paths(record_id: str, target_dir: Path) -> tuple[str, Path, Path]:
    """Validate `record_id` and resolve `.raw` and `.meta.json` paths."""
    if not isinstance(record_id, str) or not _ID_RE.fullmatch(record_id.strip()):
        raise ValueError(f"Invalid record id: {record_id!r}")
    rid = record_id.strip().lower()
    raw_path = target_dir / f"{rid}.raw"
    meta_path = target_dir / f"{rid}.meta.json"
    if len(rid) == 64 and not raw_path.exists():
        rid = rid[:12]
        raw_path = target_dir / f"{rid}.raw"
        meta_path = target_dir / f"{rid}.meta.json"
    if not raw_path.is_file() or not meta_path.is_file():
        raise ValueError(f"Record not found: {record_id}")
    return rid, raw_path, meta_path


def retrieve_record(record_id: str, store_dir: Path | None = None) -> bytes:
    """Load exact raw bytes for `record_id` after verifying SHA-256 integrity."""
    target_dir = Path(store_dir) if store_dir is not None else default_store_dir()
    rid, raw_path, meta_path = _resolve_record_paths(record_id, target_dir)
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        expected = str(meta["sha256"]).lower()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"Corrupt metadata for record: {rid}") from exc

    raw = raw_path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest().lower()
    if not hmac.compare_digest(actual, expected):
        _log(f"hash mismatch id={rid} expected={expected[:12]} actual={actual[:12]}")
        raise ValueError(f"SHA-256 mismatch for record {rid}: expected {expected}, got {actual}")

    _log(f"retrieve id={rid} bytes={len(raw)} verified=sha256")
    return raw


def _clip(text: str, width: int = 160) -> str:
    """Truncate a single line cleanly for summary output."""
    one = text.replace("\r", "").strip()
    return one if len(one) <= width else one[: width - 3] + "..."


def _summarize_head_tail(text: str, limit: int = 5) -> list[str]:
    """Format head and tail preview lines without duplicating short inputs."""
    lines = text.splitlines()
    if not lines:
        return ["head: (empty)"]
    out = ["head:"] + [f"  {i + 1}: {_clip(ln, 200)}" for i, ln in enumerate(lines[:limit])]
    if len(lines) > limit:
        tail_start = max(limit, len(lines) - limit)
        out.append("tail:")
        for idx in range(tail_start, len(lines)):
            out.append(f"  {idx + 1}: {_clip(lines[idx], 200)}")
    return out


def _describe_schema(node: object, depth: int = 0, max_depth: int = 3) -> str:
    """Render a compact JSON type/key tree up to `max_depth`."""
    if isinstance(node, dict):
        if depth >= max_depth or not node:
            return f"object(keys={len(node)})"
        items = list(node.items())[:12]
        inner = ", ".join(f"{k}: {_describe_schema(v, depth + 1, max_depth)}" for k, v in items)
        extra = f", ...(+{len(node) - 12})" if len(node) > 12 else ""
        return "{" + inner + extra + "}"
    if isinstance(node, list):
        if not node or depth >= max_depth:
            return f"array[{len(node)}]"
        return f"array[{len(node)}]<{_describe_schema(node[0], depth + 1, max_depth)}>"
    if node is None:
        return "null"
    return type(node).__name__


def _summarize_json(text: str) -> list[str]:
    """Summarize JSON schema tree, element counts, and 3 sample entries."""
    try:
        data = json.loads(text)
    except ValueError:
        _log("invalid json; falling back to head+tail summary")
        return ["note: invalid JSON fallback"] + _summarize_head_tail(text)

    if isinstance(data, list):
        count_line = f"root=array items={len(data)}"
        samples = [json.dumps(item, ensure_ascii=False) for item in data[:3]]
    elif isinstance(data, dict):
        count_line = f"root=object keys={len(data)}"
        samples = [f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in list(data.items())[:3]]
    else:
        count_line = f"root={type(data).__name__}"
        samples = [json.dumps(data, ensure_ascii=False)]

    lines = [count_line, f"schema: {_describe_schema(data)}", "samples:"]
    lines.extend(f"  - {_clip(s)}" for s in samples)
    return lines


def _summarize_jsonl(text: str) -> list[str]:
    """Summarize JSONL record count, union keys, and 3 sample records."""
    valid: list[object] = []
    invalid = 0
    keys: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except ValueError:
            invalid += 1
            continue
        valid.append(obj)
        if isinstance(obj, dict):
            for k in obj:
                if k not in seen and len(keys) < 20:
                    seen.add(k)
                    keys.append(str(k))

    if not valid:
        return ["note: no valid JSONL records; fallback"] + _summarize_head_tail(text)
    lines = [f"records={len(valid)} invalid={invalid} keys={keys}"]
    lines.append("samples:")
    lines.extend(f"  - {_clip(json.dumps(item, ensure_ascii=False))}" for item in valid[:3])
    return lines


def _summarize_csv(text: str, source_path: str) -> list[str]:
    """Summarize CSV/TSV header, row count, and first 5 rows."""
    delim = "\t" if Path(source_path).suffix.lower() == ".tsv" else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    if not rows:
        return ["rows=0 header=[]"]
    header = rows[0]
    data_rows = rows[1:]
    lines = [f"rows={len(data_rows)} cols={len(header)} header={header[:15]}"]
    lines.append("samples:")
    lines.extend(f"  {idx + 1}: {_clip(', '.join(row))}" for idx, row in enumerate(data_rows[:5]))
    return lines


def _summarize_log(text: str) -> list[str]:
    """Summarize log error/warning counts, error samples, and head/tail."""
    lines = text.splitlines()
    errors = 0
    warns = 0
    err_samples: list[str] = []
    for line in lines:
        if _ERR_RE.search(line):
            errors += 1
            if len(err_samples) < 3:
                err_samples.append(_clip(line))
        elif _WARN_RE.search(line):
            warns += 1

    out = [f"lines={len(lines)} errors={errors} warns={warns}"]
    if err_samples:
        out.append("error_samples:")
        out.extend(f"  - {sample}" for sample in err_samples)
    out.extend(_summarize_head_tail(text))
    return out


def _summarize_yaml(text: str) -> list[str]:
    """Extract level 1-2 YAML keys/items plus head/tail lines."""
    outline: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _YAML_KEY_RE.match(line)
        if match and len(match.group(1)) <= 2 and len(outline) < 15:
            depth = "  " if match.group(1) else ""
            outline.append(f"  {depth}{match.group(2)}:")
    out = ["structure:"] + (outline or ["  (no top-level keys)"])
    out.extend(_summarize_head_tail(text))
    return out


class _DomOutlineParser(HTMLParser):
    """Lightweight stdlib HTML/XML parser collecting tag stats and shallow outline."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.counts: collections.Counter[str] = collections.Counter()
        self.outline: list[str] = []
        self.title = ""
        self._depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        self.counts[name] += 1
        if name == "title":
            self._in_title = True
        if self._depth <= 2 and len(self.outline) < 16:
            attr_map = {k: v for k, v in attrs if k in ("id", "class") and v}
            suffix = "".join(f" {k}={v!r}" for k, v in attr_map.items())
            self.outline.append(f"  {'  ' * self._depth}<{name}{suffix}>")
        self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        self._depth = max(0, self._depth - 1)

    def handle_data(self, data: str) -> None:
        if self._in_title and not self.title:
            self.title = _clip(data, 120)


def _summarize_dom(text: str) -> list[str]:
    """Summarize DOM/HTML/XML element counts, title, structure, and head/tail."""
    parser = _DomOutlineParser()
    try:
        parser.feed(text)
        parser.close()
    except (AssertionError, TypeError, ValueError):
        return ["note: malformed DOM fallback"] + _summarize_head_tail(text)

    total = sum(parser.counts.values())
    top_tags = ", ".join(f"{tag}:{cnt}" for tag, cnt in parser.counts.most_common(8))
    out = [f"nodes={total} title={parser.title or '(none)'} top_tags=[{top_tags}]"]
    if parser.outline:
        out.append("structure:")
        out.extend(parser.outline)
    out.extend(_summarize_head_tail(text))
    return out


def _summarize_binary(raw: bytes) -> list[str]:
    """Summarize binary payloads safely with byte count and hex prefix."""
    preview = raw[:32].hex(" ")
    return [f"binary bytes={len(raw)} hex_head={preview}"]


def _format_body(kind: str, raw: bytes, source_path: str) -> list[str]:
    """Dispatch payload to the matching format summarizer."""
    if kind == "binary":
        return _summarize_binary(raw)
    text = raw.decode("utf-8", errors="replace")
    if kind == "json":
        return _summarize_json(text)
    if kind == "jsonl":
        return _summarize_jsonl(text)
    if kind == "csv":
        return _summarize_csv(text, source_path)
    if kind == "log":
        return _summarize_log(text)
    if kind == "yaml":
        return _summarize_yaml(text)
    if kind == "dom":
        return _summarize_dom(text)
    return _summarize_head_tail(text)


def summarize_file(
    path: str,
    store_dir: Path | None = None,
    cap_bytes: int = DEFAULT_CAP_BYTES,
) -> str:
    """Ingest `path` into the CCR store and return a format-aware summary with restore anchor."""
    file_path = Path(path)
    raw = file_path.read_bytes()
    rec = ingest_bytes(raw, source_path=str(file_path), store_dir=store_dir, cap_bytes=cap_bytes)
    header = f"CCR Summary: source={file_path.name} kind={rec['kind']} bytes={rec['bytes']} lines={rec['lines']}"
    body = _format_body(rec["kind"], raw, str(file_path))
    anchor = (
        f"CCR_ID={rec['id']} sha256={rec['sha256'][:12]} — "
        f"retrieve: py -3 scripts/tdq_ccr.py retrieve {rec['id']}"
    )
    return "\n".join([header, *body, anchor])


def _build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for ingest, summarize, retrieve, and gc."""
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--store-dir", default=argparse.SUPPRESS, help="Override CCR store directory.")

    parser = argparse.ArgumentParser(description="Lossless Context Compression & Restore (CCR) CLI.")
    parser.add_argument("--store-dir", default=None, help="Override CCR store directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ing = sub.add_parser("ingest", parents=[shared], help="Ingest a file or stdin into the CCR store.")
    p_ing.add_argument("path", nargs="?", default="-", help="Input file path, or '-' for stdin.")
    p_ing.add_argument("--cap-bytes", type=int, default=DEFAULT_CAP_BYTES, help="Max store cap in bytes.")
    p_ing.add_argument("--if-large", action="store_true", help="Only store when >32 KB or >=200 lines.")

    p_sum = sub.add_parser("summarize", parents=[shared], help="Ingest a file and print its summary.")
    p_sum.add_argument("path", help="Input file path to summarize.")
    p_sum.add_argument("--cap-bytes", type=int, default=DEFAULT_CAP_BYTES, help="Max store cap in bytes.")

    p_ret = sub.add_parser("retrieve", parents=[shared], help="Verify SHA-256 and output exact raw bytes.")
    p_ret.add_argument("record_id", help="12-char CCR record ID (or full SHA-256).")
    p_ret.add_argument("-o", "--out", default=None, help="Optional output file path (defaults to stdout).")

    p_gc = sub.add_parser("gc", parents=[shared], help="Enforce store cap by evicting oldest records.")
    p_gc.add_argument("--cap-bytes", type=int, default=DEFAULT_CAP_BYTES, help="Target store cap in bytes.")
    return parser


def _cmd_ingest(args: argparse.Namespace, store_dir: Path) -> int:
    if args.path == "-":
        raw = sys.stdin.buffer.read()
        source = ""
    else:
        raw = Path(args.path).read_bytes()
        source = args.path
    if args.if_large and not should_ccr(raw):
        print(json.dumps({"skipped": True, "bytes": len(raw), "lines": len(raw.splitlines())}))
        return 0
    rec = ingest_bytes(raw, source_path=source, store_dir=store_dir, cap_bytes=args.cap_bytes)
    print(json.dumps(rec, indent=2))
    return 0


def _cmd_retrieve(args: argparse.Namespace, store_dir: Path) -> int:
    raw = retrieve_record(args.record_id, store_dir=store_dir)
    if args.out:
        _atomic_write_bytes(Path(args.out), raw)
    else:
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
    return 0


def _cmd_gc(args: argparse.Namespace, store_dir: Path) -> int:
    evicted = enforce_cap(store_dir, args.cap_bytes)
    remaining = sum(item[3] for item in _collect_records(store_dir)) if store_dir.exists() else 0
    print(json.dumps({"evicted": evicted, "remaining_bytes": remaining, "cap_bytes": args.cap_bytes}))
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point returning 0 on success, 1 on runtime/integrity error."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    store_dir = Path(args.store_dir) if args.store_dir else default_store_dir()

    try:
        if args.command == "ingest":
            return _cmd_ingest(args, store_dir)
        if args.command == "summarize":
            print(summarize_file(args.path, store_dir=store_dir, cap_bytes=args.cap_bytes))
            return 0
        if args.command == "retrieve":
            return _cmd_retrieve(args, store_dir)
        if args.command == "gc":
            return _cmd_gc(args, store_dir)
    except (OSError, ValueError, TypeError) as exc:
        print(f"tdq_ccr error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
