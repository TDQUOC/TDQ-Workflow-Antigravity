#!/usr/bin/env python3
"""Static AST/spec scaffolder, card emitter, plan verifier, and wave checker (stdlib only).

Sub-modes (CLI):
    --files <path...> [--refs <path...>] [--from-spec <spec.md>]
    --emit-cards [<plan.md>] [--files ...] [--refs ...] [--from-spec <spec.md>]
    --verify-plan <plan.md> [--from-spec <spec.md>] [--root <dir>]
    --check-wave <plan.md> [--root <dir>]

Env: TDQ_LOG=0 disables ISO-timestamped stderr logs (enabled by default).
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import utf8_io  # noqa: E402,F401 — imported for UTF-8 stdout/stderr setup
import tdq_team  # noqa: E402
import tdq_ten_lenh  # noqa: E402

_NON_PY_EXTS = frozenset({".rs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"})
_CODE_EXTS = frozenset({".py"}) | _NON_PY_EXTS
_TOOL_TOKENS = frozenset({"Edit", "Write", "Read", "MultiEdit", "Bash", "Grep", "Glob"})
_BUILTIN_TYPES = frozenset({
    "str", "int", "float", "bool", "dict", "list", "set", "tuple", "bytes",
    "None", "Any", "Optional", "List", "Dict", "Set", "Tuple", "Sequence",
})
_NONE_VALUES = frozenset({"", "none", "n/a", "na", "-", "empty", "không"})  # i18n-allow
_DOC_EXTS = frozenset({".md", ".json", ".yaml", ".yml", ".toml", ".html", ".txt"})

_PATH_RE = re.compile(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)")
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_SIG_CALL_RE = re.compile(
    r"^(?:(?:async\s+)?def\s+|(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+|"
    r"(?:export\s+(?:default\s+)?)?(?:async\s+)?function\*?\s+)?([A-Za-z_$][A-Za-z0-9_.$]*)\s*\(([^)]*)\)"
)
_TYPE_DECL_RE = re.compile(r"^(?:class|struct|enum|trait|interface|type)\s+([A-Za-z_$][A-Za-z0-9_$]*)")
_IDENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_.$]*$")
_LINE_ONLY_RE = re.compile(r"^L?\d+(?:-L?\d+)?$")
_RS_DECL_RE = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?"
    r"(?:extern\s+\"[^\"]*\"\s+)?(fn|struct|enum|trait|type|mod)\s+([A-Za-z_][A-Za-z0-9_]*)"
)
_RS_IMPL_RE = re.compile(
    r"^\s*(?:unsafe\s+)?impl(?:<[^>]+>)?\s+(?:[A-Za-z_][A-Za-z0-9_:<>]*\s+for\s+)?([A-Za-z_][A-Za-z0-9_]*)"
)
_JS_DECL_RE = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:declare\s+)?(?:abstract\s+)?(?:async\s+)?"
    r"(function\*?|class|interface|type|enum)\s+([A-Za-z_$][A-Za-z0-9_$]*)"
)
_JS_ARROW_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*(?::[^=]+)?=\s*"
    r"(?:async\s+)?(?:\([^)]*\)\s*(?::[^=]+)?=>|[A-Za-z_$][A-Za-z0-9_$]*\s*=>|function\b)"
)
_NON_PY_METHOD_RE = re.compile(
    r"^\s+(?:public|private|protected|static|async|readonly|\*|\s)*"
    r"([A-Za-z_$][A-Za-z0-9_$]*)\s*\([^)]*\)\s*(?::\s*[^\{;]+)?\{"
)
_CTRL_KEYWORDS = frozenset({"if", "for", "while", "switch", "catch", "match", "return", "else"})


class ScaffoldError(Exception):
    """Raised when scaffolding or verification fails closed."""


def _log_enabled() -> bool:
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message: str) -> None:
    """Emit one ISO-timestamped debug line on stderr unless TDQ_LOG=0."""
    if _log_enabled():
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{stamp}] tdq_plan_scaffold: {message}", file=sys.stderr)


def _err(message: str) -> None:
    """Always emit fatal/validation errors on stderr regardless of TDQ_LOG."""
    print(message, file=sys.stderr)


def _norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _is_file_like(token: str) -> bool:
    clean = token.split(":", 1)[0]
    if clean in tdq_team.ROOT_FILES:
        return True
    if "/" in clean:
        return "." in clean.rsplit("/", 1)[-1]
    ext = os.path.splitext(clean)[1].lower()
    return ext in _CODE_EXTS or ext in _DOC_EXTS


def _is_test_path(path: str) -> bool:
    norm = "/" + _norm(path).lower()
    base = os.path.basename(norm)
    suffixes = ("_test.py", ".test.ts", ".spec.ts", ".test.js", ".spec.js", "_test.rs")
    return "/tests/" in norm or "/test/" in norm or base.startswith("test_") or base.endswith(suffixes)


def _find_root_from_anchor(anchor: str) -> Optional[str]:
    abs_a = os.path.abspath(anchor)
    norm_a = abs_a.replace("\\", "/")
    idx = norm_a.find("/docs/tdq/")
    if idx > 0:
        return os.path.abspath(norm_a[:idx])
    cur = os.path.dirname(abs_a)
    while True:
        has_git = os.path.exists(os.path.join(cur, ".git"))
        has_tdq = os.path.isdir(os.path.join(cur, "docs", "tdq"))
        if has_git or has_tdq:
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _resolve_root_dir(
    plan_path: Optional[str], spec_path: Optional[str], root_dir: Optional[str]
) -> str:
    if root_dir:
        return os.path.abspath(root_dir)
    for anchor in (plan_path, spec_path):
        found = _find_root_from_anchor(anchor) if anchor else None
        if found:
            return found
    env_dir = os.environ.get("TDQ_PROJECT_DIR")
    return os.path.abspath(env_dir) if env_dir else os.getcwd()


def _resolve_path(path_str: str, root_dir: str) -> str:
    if os.path.isabs(path_str):
        return path_str
    candidate = os.path.join(root_dir, path_str)
    if os.path.exists(candidate):
        return candidate
    cwd_candidate = os.path.abspath(path_str)
    return cwd_candidate if os.path.exists(cwd_candidate) else candidate


# ------------------------------------------------------------------ symbol extraction

def _strip_line_for_braces(line: str) -> str:
    in_quote: Optional[str] = None
    out: List[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if in_quote:
            step = 2 if ch == "\\" and i + 1 < len(line) else 1
            if step == 1 and ch == in_quote:
                in_quote = None
            i += step
            continue
        if line[i : i + 2] == "//":
            break
        if ch in ("'", '"', "`"):
            in_quote = ch
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _find_block_end(lines: Sequence[str], start_idx: int) -> int:
    depth = 0
    opened = False
    for idx in range(start_idx, len(lines)):
        clean = _strip_line_for_braces(lines[idx])
        opens, closes = clean.count("{"), clean.count("}")
        opened = opened or bool(opens)
        depth += opens - closes
        if opened and depth <= 0:
            return idx + 1
        if not opened and ";" in clean:
            return idx + 1
    return start_idx + 1


def _clean_sig(raw: str) -> str:
    text = " ".join(raw.strip().split())
    return text[:-1].rstrip() if text.endswith("{") else text


def _match_non_py_decl(
    line: str, ext: str, inside_container: bool
) -> Optional[Tuple[str, str, bool]]:
    if ext == ".rs":
        m_impl = _RS_IMPL_RE.match(line)
        if m_impl:
            return m_impl.group(1), _clean_sig(line), True
        m_rs = _RS_DECL_RE.match(line)
        if m_rs:
            return m_rs.group(2), _clean_sig(line), m_rs.group(1) in ("struct", "enum", "trait")
        return None
    m_js = _JS_DECL_RE.match(line)
    if m_js:
        return m_js.group(2), _clean_sig(line), m_js.group(1) in ("class", "interface")
    m_arr = _JS_ARROW_RE.match(line)
    if m_arr:
        return m_arr.group(1), _clean_sig(line), False
    m_meth = _NON_PY_METHOD_RE.match(line) if inside_container else None
    if m_meth and m_meth.group(1) not in _CTRL_KEYWORDS:
        return m_meth.group(1), _clean_sig(line), False
    return None


def _extract_non_py_symbols(lines: Sequence[str], ext: str) -> List[Dict[str, Any]]:
    symbols: List[Dict[str, Any]] = []
    container_name = ""
    container_end = 0
    for idx, line in enumerate(lines):
        lineno = idx + 1
        if container_name and lineno > container_end:
            container_name, container_end = "", 0
        matched = _match_non_py_decl(line, ext, bool(container_name))
        if not matched:
            continue
        name, sig, is_container = matched
        end_line = _find_block_end(lines, idx)
        qual = f"{container_name}.{name}" if (container_name and not is_container) else name
        symbols.append({
            "name": name, "qual": qual, "start": lineno,
            "end": end_line, "sig": sig, "anchor_confidence": "LOW",
        })
        if is_container and end_line > lineno:
            container_name, container_end = name, end_line
    return symbols


def extract_symbols(path: str, root_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Extract symbols and line spans from Python (HIGH) or .rs/.ts/.tsx/.js/.jsx (LOW)."""
    target = _resolve_path(path, root_dir) if root_dir else path
    if not os.path.isfile(target):
        _log(f"extract_symbols skipped missing file: {target}")
        return []
    ext = os.path.splitext(target)[1].lower()
    with open(target, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    if ext == ".py":
        nodes = tdq_team._parse_py_nodes(target, lines)
        return [
            {
                "name": n["name"], "qual": n["qual"], "start": n["start"],
                "end": n["end"], "sig": n["sig"], "anchor_confidence": "HIGH",
            }
            for n in nodes
        ]
    return _extract_non_py_symbols(lines, ext) if ext in _NON_PY_EXTS else []


def _assign_names_from_stmt(node: ast.AST) -> List[str]:
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def _py_top_level_assigns(target: str) -> Set[str]:
    if not os.path.isfile(target) or not target.endswith(".py"):
        return set()
    try:
        with open(target, encoding="utf-8", errors="replace") as fh:
            tree = ast.parse(fh.read(), filename=target)
    except SyntaxError:
        return set()
    names: Set[str] = set()
    for node in tree.body:
        names.update(_assign_names_from_stmt(node))
    return names


# ------------------------------------------------------------------ spec §3c parser

def _extract_3c_lines(lines: Sequence[str]) -> List[Tuple[int, str]]:
    collecting = False
    section: List[Tuple[int, str]] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if re.match(r"^##\s+3c\b", stripped, re.I):
            collecting = True
            continue
        if collecting and re.match(r"^##\s+", stripped):
            break
        if collecting:
            section.append((idx, line))
    return section


def _skip_sig_token(clean: str) -> bool:
    return not clean or clean[0] in ("-", "§") or _is_file_like(clean)


def _parse_sig_token(token: str, has_file_ctx: bool) -> Optional[Tuple[str, str]]:
    clean = token.strip()
    if _skip_sig_token(clean):
        return None
    m_call = _SIG_CALL_RE.match(clean)
    if m_call:
        sym = m_call.group(1)
        return None if sym == "O" else (sym.split(".")[-1], clean)
    m_type = _TYPE_DECL_RE.match(clean)
    if m_type:
        return m_type.group(1), clean
    if "=" in clean:
        lhs = clean.split("=", 1)[0].strip()
        if _IDENT_RE.match(lhs):
            return lhs, clean
    if has_file_ctx and clean not in _TOOL_TOKENS and _IDENT_RE.match(clean):
        return clean.split(".")[-1], clean
    return None


def _parse_fence_contracts(
    fence_lines: Sequence[str], start_line: int, current_file: str
) -> List[Dict[str, Any]]:
    ext = os.path.splitext(current_file)[1].lower() if current_file else ".py"
    norm_f = _norm(current_file)
    if ext == ".py":
        nodes = tdq_team._parse_py_nodes(current_file or "<spec>", list(fence_lines))
        return [{"file": norm_f, "symbol": n["name"], "sig": n["sig"], "line": start_line + n["start"] - 1} for n in nodes]
    if ext in _NON_PY_EXTS:
        syms = _extract_non_py_symbols(fence_lines, ext)
        return [{"file": norm_f, "symbol": s["name"], "sig": s["sig"], "line": start_line + s["start"] - 1} for s in syms]
    return []


def _extract_row_file(first_cell: str) -> str:
    m_path = _PATH_RE.search(first_cell)
    if m_path and _is_file_like(m_path.group(1)):
        return _norm(m_path.group(1))
    return ""


def _parse_table_row(line: str, lineno: int) -> List[Dict[str, Any]]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 2 or all(set(c) <= {"-", ":"} for c in cells if c):
        return []
    row_file = _extract_row_file(cells[0])
    found: List[Dict[str, Any]] = []
    for cell in cells:
        for bt in _BACKTICK_RE.findall(cell):
            if _is_file_like(bt):
                row_file = row_file or _norm(bt)
                continue
            parsed = _parse_sig_token(bt, bool(row_file))
            if parsed:
                found.append({"file": row_file, "symbol": parsed[0], "sig": parsed[1], "line": lineno})
    return found


def _process_3c_line(
    line: str, lineno: int, state: Dict[str, Any], out: List[Dict[str, Any]]
) -> None:
    stripped = line.strip()
    if stripped.startswith("|"):
        out.extend(_parse_table_row(line, lineno))
        return
    indent = tdq_team._line_indent(line)
    if stripped.startswith("#"):
        state["file_indent"] = -1
    elif indent <= state["file_indent"]:
        state["file"], state["file_indent"] = "", -1
    for bt in _BACKTICK_RE.findall(line):
        if _is_file_like(bt):
            state["file"] = _norm(bt)
            state["file_indent"] = -1 if stripped.startswith("#") else indent
            continue
        parsed = _parse_sig_token(bt, bool(state["file"]))
        if parsed:
            out.append({"file": state["file"], "symbol": parsed[0], "sig": parsed[1], "line": lineno})


def _scan_3c_bullets_and_fences(section: Sequence[Tuple[int, str]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    state: Dict[str, Any] = {"file": "", "file_indent": -1, "fence": None, "buf": [], "start": 0}
    for lineno, line in section:
        fence, toggled = tdq_team._update_fence(state["fence"], line)
        state["fence"] = fence
        if toggled and fence is not None:
            state["buf"], state["start"] = [], lineno + 1
            continue
        if toggled and fence is None:
            out.extend(_parse_fence_contracts(state["buf"], state["start"], state["file"]))
            continue
        if fence is not None:
            state["buf"].append(line)
            continue
        _process_3c_line(line, lineno, state, out)
    return out


def parse_spec_contracts(spec_path: str) -> List[Dict[str, Any]]:
    """Parse section 3c contracts (file, symbol, sig, line) from a spec markdown file."""
    if not os.path.isfile(spec_path):
        raise FileNotFoundError(f"Spec file not found: {spec_path}")
    with open(spec_path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    raw = _scan_3c_bullets_and_fences(_extract_3c_lines(lines))
    dedup: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str, str]] = set()
    for item in raw:
        key = (item["file"], item["symbol"], item["sig"])
        if key not in seen:
            seen.add(key)
            dedup.append(item)
    return dedup


# ------------------------------------------------------------------ card emission

def _match_contracts_for_file(rel_path: str, contracts: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    norm_rel = _norm(rel_path)
    base = os.path.basename(norm_rel)
    exact = [c for c in contracts if _norm(c["file"]) == norm_rel]
    if exact:
        return exact
    by_base = [c for c in contracts if c["file"] and os.path.basename(_norm(c["file"])) == base]
    return by_base or [c for c in contracts if not c["file"]]


def _load_contracts_or_fail(spec_path: Optional[str], root: str) -> List[Dict[str, Any]]:
    if not spec_path:
        return []
    abs_spec = _resolve_path(spec_path, root)
    if not os.path.isfile(abs_spec):
        raise ScaffoldError(f"Spec file not found for --from-spec (§3c): {spec_path}")
    contracts = parse_spec_contracts(abs_spec)
    if not contracts:
        raise ScaffoldError(f"Spec §3c has no interface/signature contracts in --from-spec: {spec_path}")
    return contracts


def _inspect_target_file(
    rel: str, root: str, spec_path: Optional[str], contracts: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    abs_p = _resolve_path(rel, root)
    ext = os.path.splitext(rel)[1].lower()
    if os.path.isfile(abs_p):
        syms = extract_symbols(abs_p, root)
        low_conf = ext in _NON_PY_EXTS or any(s["anchor_confidence"] == "LOW" for s in syms)
        return {"path": _norm(rel), "mode": "Edit", "confidence": "LOW" if low_conf else "HIGH", "symbols": syms, "contracts": []}
    if not spec_path:
        if _is_test_path(rel):
            return {"path": _norm(rel), "mode": "Write", "confidence": "HIGH", "symbols": [], "contracts": []}
        raise ScaffoldError(f"Greenfield file `{rel}` not found on disk; pass --from-spec with §3c contracts.")
    matched = _match_contracts_for_file(rel, contracts)
    return {"path": _norm(rel), "mode": "Write", "confidence": "LOW" if ext in _NON_PY_EXTS else "HIGH", "symbols": [], "contracts": matched}


def _inspect_ref_file(rel: str, root: str, contracts: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    abs_r = _resolve_path(rel, root)
    ext = os.path.splitext(rel)[1].lower()
    if os.path.isfile(abs_r):
        syms = extract_symbols(abs_r, root)
        return {"path": _norm(rel), "confidence": "LOW" if ext in _NON_PY_EXTS else "HIGH", "sigs": [s["sig"] for s in syms[:3]]}
    matched = _match_contracts_for_file(rel, contracts)
    return {"path": _norm(rel), "confidence": "HIGH", "sigs": [c["sig"] for c in matched[:3]]}


def _extract_dep_text(task: tdq_team.Task) -> str:
    for line in task.text[1:]:
        if line.strip().startswith(tdq_team.NHAN_CAN):
            return line.split(":", 1)[1].strip() or "Không"  # i18n-allow
    return "Không"  # i18n-allow


def _format_anchor_summary(inspected: Sequence[Dict[str, Any]]) -> Tuple[str, str]:
    parts: List[str] = []
    details: List[str] = []
    for item in inspected:
        if item["symbols"]:
            top_syms = ", ".join(f"`{s['name']}` (L{s['start']}-{s['end']})" for s in item["symbols"][:3])
            parts.append(f"`{item['mode']}` on `{item['path']}` ({top_syms})")
            details.append(f"`{item['path']}`: `{item['symbols'][0]['sig']}`")
        elif item["contracts"]:
            sigs = ", ".join(f"`{c['sig']}`" for c in item["contracts"][:3])
            parts.append(f"`{item['mode']}` new `{item['path']}` (§3c: {sigs})")
        else:
            parts.append(f"`{item['mode']}` `{item['path']}`")
    return "; ".join(parts) or "`Edit` <target>", "; ".join(details[:2])


def _render_task_card(
    task: tdq_team.Task,
    ref_list: Sequence[str],
    root: str,
    spec_path: Optional[str],
    contracts: Sequence[Dict[str, Any]],
) -> str:
    targets = list(task.vung_file)
    if not targets:
        raise ScaffoldError(f"Task {task.ma} has no target files (Chạm:) and no --files provided.")  # i18n-allow
    inspected = [_inspect_target_file(p, root, spec_path, contracts) for p in targets]
    if not spec_path and all(item["mode"] == "Write" for item in inspected):
        raise ScaffoldError(f"Greenfield file `{targets[0]}` requires --from-spec with §3c contracts.")
    ref_info = [_inspect_ref_file(r, root, contracts) for r in ref_list]
    conf = "LOW" if any(x["confidence"] == "LOW" for x in inspected + ref_info) else "HIGH"
    anchor_line, detail_line = _format_anchor_summary(inspected)
    header_rest = task.text[0] if task.text else f"(e10m) Scaffold {task.ma} — Test: `{tdq_ten_lenh.ten_lenh_python()} -m unittest -v`"
    cham_str = ", ".join(f"`{_norm(p)}`" for p in targets)
    lines = [
        f"- [{task.trang_thai}] **{task.ma}** {header_rest}",
        "  - Req: <spec §req>",
        "  - Ngoài phạm vi: <keep existing behavior unchanged>",  # i18n-allow
        f"  - Chạm: {cham_str}",  # i18n-allow
    ]
    if ref_info:
        ref_str = ", ".join(f"`{r['path']}` (`{r['sigs'][0]}`)" if r["sigs"] else f"`{r['path']}`" for r in ref_info)
        lines.append(f"  - Tham chiếu: {ref_str}")  # i18n-allow
    lines.extend([
        f"  - Cần: {_extract_dep_text(task)}",  # i18n-allow
        "  - Giao tiếp: Consumes: <input type/contract> | Produces: <output signature>",  # i18n-allow
        f"  - Neo & Công cụ: {anchor_line} · ANCHOR_CONFIDENCE: {conf}",  # i18n-allow
    ])
    if detail_line:
        lines.append(f"    - {detail_line}")
    lines.extend([
        "  - Trước → Sau: <current behavior> -> <target behavior>",  # i18n-allow
        "  - Tiêu chí chấp nhận (EARS): WHEN <condition>, SYSTEM MUST <measurable outcome>",  # i18n-allow
        "  - Logic cốt lõi:",  # i18n-allow
        "    1. <step one>",
        "    2. <step two>",
        "  - Ca góc hiểm & Assert:",  # i18n-allow
        "    - Ca hiểm: <edge case and defensive guard>",  # i18n-allow
        "    - Tiêu chí: `<concrete assertion or command>`",  # i18n-allow
    ])
    return "\n".join(lines)


def _merge_unique(first: Sequence[str], second: Sequence[str]) -> List[str]:
    out: List[str] = []
    for item in list(first) + list(second):
        norm = _norm(item)
        if norm and norm not in out:
            out.append(norm)
    return out


def _apply_extra_files(tasks: List[tdq_team.Task], files: Sequence[str]) -> None:
    if not files:
        return
    if len(tasks) == 1:
        tasks[0].vung_file = _merge_unique(tasks[0].vung_file, files)
        return
    for t in tasks:
        if not t.vung_file:
            t.vung_file = list(files)


def _make_synthetic_task(files: Sequence[str]) -> tdq_team.Task:
    t = tdq_team.Task("T1.1", " ", "P1")
    t.vung_file = [_norm(f) for f in files]
    t.text = [f"(e10m) Implement {', '.join(t.vung_file)} — Test: `{tdq_ten_lenh.ten_lenh_python()} -m unittest -v`"]
    return t


def _collect_cards_tasks(plan_path: Optional[str], files: Sequence[str], root: str) -> List[tdq_team.Task]:
    if plan_path:
        abs_plan = _resolve_path(plan_path, root)
        if not os.path.isfile(abs_plan):
            raise ScaffoldError(f"Plan file not found: {plan_path}")
        tasks = tdq_team.doc_plan(abs_plan)
        if tasks:
            _apply_extra_files(tasks, files)
            return tasks
        if not files:
            raise ScaffoldError(f"Plan contains no tasks: {plan_path}")
    if files:
        return [_make_synthetic_task(files)]
    raise ScaffoldError("Provide a plan path or --files to emit cards.")


def emit_cards(
    plan_path: Optional[str] = None,
    refs: Sequence[str] = (),
    spec_path: Optional[str] = None,
    files: Sequence[str] = (),
    root_dir: Optional[str] = None,
) -> str:
    """Emit Per-Task Mini-Spec cards with verified anchors and §3c Greenfield contracts."""
    root = _resolve_root_dir(plan_path, spec_path, root_dir)
    contracts = _load_contracts_or_fail(spec_path, root)
    tasks = _collect_cards_tasks(plan_path, files, root)
    cards = [_render_task_card(t, _merge_unique(t.tham_chieu, refs), root, spec_path, contracts) for t in tasks]
    _log(f"emit_cards -> {len(cards)} card(s), contracts={len(contracts)}")
    return "\n\n".join(cards) + "\n"


def _format_file_anchors(
    files: Sequence[str], refs: Sequence[str], spec_path: Optional[str], root: str
) -> str:
    contracts = _load_contracts_or_fail(spec_path, root)
    if not files and not refs:
        raise ScaffoldError("Pass --files or --refs when not using --emit-cards.")
    out: List[str] = []
    for rel in files:
        info = _inspect_target_file(rel, root, spec_path, contracts)
        out.append(f"## `{info['path']}` (ANCHOR_CONFIDENCE: {info['confidence']})")
        out.extend(f"- `{s['qual']}` L{s['start']}-{s['end']}: `{s['sig']}`" for s in info["symbols"])
        out.extend(f"- [§3c] `{c['symbol']}`: `{c['sig']}`" for c in info["contracts"])
    for rel in refs:
        r_info = _inspect_ref_file(rel, root, contracts)
        out.append(f"## REF `{r_info['path']}` (ANCHOR_CONFIDENCE: {r_info['confidence']})")
        out.extend(f"- `{sig}`" for sig in r_info["sigs"])
    _log(f"files_anchors -> files={len(files)} refs={len(refs)}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ plan verification

def _step_task_map(lineno: int, line: str, state: Dict[str, Any], task_lines: Dict[str, List[Tuple[int, str, str]]]) -> None:
    if tdq_team._PHASE.match(line):
        state["id"] = None
        return
    m_task = tdq_team._TASK.match(line)
    if m_task:
        state["id"] = m_task.group(3)
        state["indent"] = tdq_team._line_indent(line)
        state["sec"] = "header"
        task_lines[state["id"]] = [(lineno, line, "header")]
        return
    cur_id = state["id"]
    if cur_id is None or not line.strip():
        return
    if tdq_team._line_indent(line) <= state["indent"]:
        state["id"] = None
        return
    stripped = line.strip()
    if stripped.startswith("- "):
        state["sec"] = tdq_team._classify_section(stripped[2:])
    task_lines[cur_id].append((lineno, line, state["sec"]))


def _map_task_lines(plan_lines: Sequence[str]) -> Dict[str, List[Tuple[int, str, str]]]:
    task_lines: Dict[str, List[Tuple[int, str, str]]] = {}
    state: Dict[str, Any] = {"fence": None, "id": None, "indent": 0, "sec": "header"}
    for lineno, line in enumerate(plan_lines, start=1):
        fence, toggled = tdq_team._update_fence(state["fence"], line)
        state["fence"] = fence
        if not toggled and fence is None:
            _step_task_map(lineno, line, state, task_lines)
    return task_lines


def _is_new_file_in_task(task_lines: Sequence[Tuple[int, str, str]], rel_path: str) -> bool:
    norm = _norm(rel_path)
    base = os.path.basename(norm)
    write_kw = re.compile(r"(`Write`|\bWrite\b|tạo mới|new file|\[NEW\]|sinh mới)", re.I)  # i18n-allow
    edit_kw = re.compile(r"(`Edit`|\bEdit\b)", re.I)
    has_unscoped_write = False
    for _ln, line, sec in task_lines:
        if sec == "sinh_ra" and any(_norm(p) == norm for p in tdq_team._extract_paths(line, allow_bare=True)):
            return True
        for clause in line.split(";"):
            if not write_kw.search(clause):
                continue
            if norm in clause or base in clause:
                return True
            if not tdq_team._extract_paths(clause, allow_bare=True):
                has_unscoped_write = True
    joined = "\n".join(line for _ln, line, _sec in task_lines)
    return bool(has_unscoped_write and not edit_kw.search(joined))


def _known_symbols_for_file(rel_path: str, root: str, spec_syms: Dict[str, Set[str]]) -> Optional[Set[str]]:
    norm = _norm(rel_path)
    abs_p = _resolve_path(rel_path, root)
    if os.path.isfile(abs_p):
        syms = extract_symbols(abs_p, root)
        known = {s["name"] for s in syms} | {s["qual"] for s in syms}
        return known | _py_top_level_assigns(abs_p) | spec_syms.get(norm, set())
    return set(spec_syms[norm]) if norm in spec_syms else None


def _is_non_symbol_token(clean: str) -> bool:
    return (
        not clean or clean in _TOOL_TOKENS or clean.startswith("-")
        or bool(_LINE_ONLY_RE.match(clean)) or _is_file_like(clean) or not _IDENT_RE.match(clean)
    )


def _strip_anchor_sym(token: str) -> Optional[str]:
    clean = token.strip().strip("`")
    clean = clean[:-2] if clean.endswith("()") else clean
    if ":" in clean and not clean.startswith("http"):
        head, tail = clean.split(":", 1)
        clean = head if _LINE_ONLY_RE.match(tail) else clean
    return None if _is_non_symbol_token(clean) else clean


def _check_anchor_line_bounds(
    token: str, active_file: Optional[str], root: str, lineno: int, task_id: str, errs: List[str]
) -> None:
    if not active_file:
        return
    abs_p = _resolve_path(active_file, root)
    m_line = re.match(r"^L?(\d+)(?:-L?(\d+))?$", token.strip())
    if not os.path.isfile(abs_p) or not m_line:
        return
    start_ln = int(m_line.group(1))
    with open(abs_p, encoding="utf-8", errors="replace") as fh:
        total = sum(1 for _ in fh)
    if total and start_ln > total:
        errs.append(f"L{lineno} [{task_id}]: anchor line L{start_ln} exceeds {active_file} ({total} lines)")


def _check_neo_symbol(
    sym: str, active_file: Optional[str], task: tdq_team.Task, lineno: int,
    root: str, spec_syms: Dict[str, Set[str]], errs: List[str]
) -> None:
    candidates = [active_file] if active_file else list(task.vung_file)
    code_files = [f for f in candidates if os.path.splitext(f)[1].lower() in _CODE_EXTS]
    if not code_files:
        return
    available = [ks for ks in (_known_symbols_for_file(f, root, spec_syms) for f in code_files) if ks is not None]
    if not available:
        return
    tail = sym.split(".")[-1]
    if not any(sym in ks or tail in ks for ks in available):
        errs.append(f"L{lineno} [{task.ma}]: missing symbol `{sym}` in `{', '.join(code_files)}`")


def _scan_neo_line(
    lineno: int, line: str, task: tdq_team.Task,
    root: str, spec_syms: Dict[str, Set[str]], errs: List[str]
) -> None:
    active_file: Optional[str] = None
    for bt in _BACKTICK_RE.findall(line):
        base_bt = bt.split(":", 1)[0]
        if _is_file_like(base_bt):
            active_file = _norm(base_bt)
            if ":" in bt:
                _check_anchor_line_bounds(bt.split(":", 1)[1], active_file, root, lineno, task.ma, errs)
            continue
        if _LINE_ONLY_RE.match(bt.strip()):
            _check_anchor_line_bounds(bt, active_file, root, lineno, task.ma, errs)
            continue
        sym = _strip_anchor_sym(bt)
        if sym:
            _check_neo_symbol(sym, active_file, task, lineno, root, spec_syms, errs)


def _verify_neo_lines(
    task: tdq_team.Task, t_lines: Sequence[Tuple[int, str, str]],
    root: str, spec_syms: Dict[str, Set[str]], errs: List[str]
) -> None:
    for lineno, line, sec in t_lines:
        if sec == "neo":
            _scan_neo_line(lineno, line, task, root, spec_syms, errs)


def _is_const_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_is_const_expr(el) for el in node.elts)
    if isinstance(node, ast.Dict):
        return all(_is_const_expr(k) and _is_const_expr(v) for k, v in zip(node.keys, node.values) if k is not None)
    return False


def _is_len_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len"


def _const_val(node: ast.AST) -> Any:
    return node.value if isinstance(node, ast.Constant) else None


def _is_len_nonneg(test: ast.Compare) -> bool:
    if len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    left, op, right = test.left, test.ops[0], test.comparators[0]
    if _is_len_call(left):
        return (type(op), _const_val(right)) in ((ast.GtE, 0), (ast.Gt, -1))
    return _is_len_call(right) and (type(op), _const_val(left)) == (ast.LtE, 0)


def _compare_anti2_reason(test: ast.Compare) -> Optional[str]:
    if _is_const_expr(test.left) and all(_is_const_expr(c) for c in test.comparators):
        return "constant-only comparison"
    if _is_len_nonneg(test):
        return "len(...) >= 0 always true"
    if len(test.ops) == 1 and isinstance(test.ops[0], (ast.Eq, ast.Is, ast.GtE, ast.LtE)):
        if ast.dump(test.left) == ast.dump(test.comparators[0]):
            return "reflexive self-comparison"
    return None


def _boolop_anti2_reason(test: ast.BoolOp) -> Optional[str]:
    if isinstance(test.op, ast.Or) and any(_anti2_reason(v) for v in test.values):
        return "boolean OR tautology"
    if isinstance(test.op, ast.And) and all(_anti2_reason(v) for v in test.values):
        return "boolean AND tautology"
    return None


def _anti2_reason(test: ast.AST) -> Optional[str]:
    if isinstance(test, ast.Constant) and bool(test.value):
        return "constant truthy literal"
    if isinstance(test, (ast.List, ast.Tuple, ast.Set)) and test.elts and _is_const_expr(test):
        return "constant non-empty container"
    if isinstance(test, ast.Compare):
        return _compare_anti2_reason(test)
    if isinstance(test, ast.BoolOp):
        return _boolop_anti2_reason(test)
    return None


def _extract_assert_snippets(line: str) -> List[str]:
    snippets = [bt.strip() for bt in _BACKTICK_RE.findall(line) if bt.strip().startswith("assert ")]
    if snippets:
        return snippets
    stripped = line.strip().lstrip("-").strip()
    if stripped.startswith("assert "):
        return [stripped]
    after = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
    return [after] if after.startswith("assert ") else []


def _is_assert_check_line(line: str, in_assert_block: bool) -> bool:
    low = line.strip().lower()
    if low.startswith(("- tiêu chí:", "tiêu chí:", "- assert:", "assert:", "- assert ", "assert ")):  # i18n-allow
        return True
    return in_assert_block and low.startswith("- `assert ")


def _check_assert_snippet(snip: str, lineno: int, task_id: str, errs: List[str]) -> None:
    try:
        tree = ast.parse(snip)
    except SyntaxError as exc:
        errs.append(f"L{lineno} [{task_id}]: invalid Python assert syntax ({exc.msg}): {snip}")
        return
    for stmt in tree.body:
        if isinstance(stmt, ast.Assert):
            reason = _anti2_reason(stmt.test)
            if reason:
                errs.append(f"L{lineno} [{task_id}]: ANTI-2 blind assertion ({reason}): {snip}")


def _verify_task_asserts(task_id: str, t_lines: Sequence[Tuple[int, str, str]], errs: List[str]) -> None:
    in_assert_block = False
    for lineno, line, _sec in t_lines:
        low = line.strip().lower()
        if low.startswith(("- ca góc hiểm", "ca góc hiểm")):  # i18n-allow
            in_assert_block = True
        elif line.strip().startswith("- ") and not low.startswith(("- ca hiểm", "- tiêu chí", "- assert", "- `assert ")):  # i18n-allow
            in_assert_block = False
        if not _is_assert_check_line(line, in_assert_block):
            continue
        for snip in _extract_assert_snippets(line):
            _check_assert_snippet(snip, lineno, task_id, errs)


def _load_plan_spec_syms(
    plan_lines: Sequence[str], abs_plan: str, root: str, spec_path: Optional[str]
) -> Tuple[Optional[str], Dict[str, Set[str]]]:
    target_spec = spec_path
    if not target_spec:
        for line in plan_lines[:15]:
            m_spec = re.search(r"Spec:\s*([^\s·]+)", line)
            if m_spec:
                cand = os.path.normpath(os.path.join(os.path.dirname(abs_plan), m_spec.group(1)))
                if os.path.isfile(cand):
                    target_spec = cand
                    break
    if not target_spec:
        return None, {}
    abs_spec = _resolve_path(target_spec, root)
    if not os.path.isfile(abs_spec):
        return f"Spec file not found: {target_spec}", {}
    by_file: Dict[str, Set[str]] = {}
    for c in parse_spec_contracts(abs_spec):
        if c["file"]:
            by_file.setdefault(_norm(c["file"]), set()).add(c["symbol"])
    return None, by_file


def _build_created_files_by_task(
    tasks: Sequence[tdq_team.Task], line_map: Dict[str, List[Tuple[int, str, str]]]
) -> Dict[str, Set[str]]:
    created: Dict[str, Set[str]] = {}
    for t in tasks:
        t_lines = line_map.get(t.ma, [])
        files = {_norm(f) for f in t.vung_file if _is_new_file_in_task(t_lines, f)}
        files |= {_norm(f) for f in t.sinh_ra}
        created[t.ma] = files
    return created


def _verify_task_refs(
    task: tdq_team.Task, head_ln: int, upstream_created: Set[str],
    root: str, spec_syms: Dict[str, Set[str]], errs: List[str]
) -> None:
    for ref_rel in task.tham_chieu:
        known = _known_symbols_for_file(ref_rel, root, spec_syms)
        if known is None and _norm(ref_rel) in upstream_created:
            continue
        if known is None:
            errs.append(f"L{head_ln} [{task.ma}]: reference file not found: {ref_rel}")
            continue
        for sym in task._tham_chieu_syms.get(ref_rel, []):
            if sym not in known and sym.split(".")[-1] not in known:
                errs.append(f"L{head_ln} [{task.ma}]: missing symbol `{sym}` in reference `{ref_rel}`")


def _verify_single_task(
    task: tdq_team.Task, t_lines: Sequence[Tuple[int, str, str]], upstream_created: Set[str],
    root: str, spec_syms: Dict[str, Set[str]], errs: List[str]
) -> None:
    head_ln = t_lines[0][0]
    created_paths = set(upstream_created) | {_norm(f) for f in task.sinh_ra}
    for rel in task.vung_file:
        is_created = _norm(rel) in created_paths or _is_new_file_in_task(t_lines, rel)
        if not is_created and not os.path.isfile(_resolve_path(rel, root)):
            errs.append(f"L{head_ln} [{task.ma}]: Chạm file not found on disk: {rel}")  # i18n-allow
    _verify_task_refs(task, head_ln, upstream_created, root, spec_syms, errs)
    _verify_neo_lines(task, t_lines, root, spec_syms, errs)
    _verify_task_asserts(task.ma, t_lines, errs)


def verify_plan(
    plan_path: str, root_dir: Optional[str] = None, spec_path: Optional[str] = None
) -> Tuple[int, List[str]]:
    """Verify Chạm: files, Neo/Tham chiếu: symbols, and Python assert AST/ANTI-2."""  # i18n-allow
    root = _resolve_root_dir(plan_path, spec_path, root_dir)
    abs_plan = _resolve_path(plan_path, root)
    if not os.path.isfile(abs_plan):
        return 1, [f"Plan file not found: {plan_path}"]
    with open(abs_plan, encoding="utf-8") as fh:
        plan_lines = fh.read().splitlines()
    spec_err, spec_syms = _load_plan_spec_syms(plan_lines, abs_plan, root, spec_path)
    if spec_err:
        return 1, [spec_err]
    tasks = tdq_team.doc_plan(abs_plan)
    if not tasks:
        return 1, [f"Plan contains no tasks: {plan_path}"]
    line_map = _map_task_lines(plan_lines)
    created_map = _build_created_files_by_task(tasks, line_map)
    ancestors = _ancestor_map(tdq_team.doc_phu_thuoc(tasks))
    errs: List[str] = []
    for task in tasks:
        up_files = {f for anc in ancestors.get(task.ma, set()) for f in created_map.get(anc, set())}
        _verify_single_task(task, line_map.get(task.ma, [(1, "", "header")]), up_files, root, spec_syms, errs)
    _log(f"verify_plan -> tasks={len(tasks)} errors={len(errs)}")
    return (0 if not errs else 1), errs


# ------------------------------------------------------------------ wave checker

def _split_params(raw_args: str) -> List[str]:
    parts = [p.strip() for p in raw_args.split(",") if p.strip()]
    return [p for p in parts if p not in ("self", "cls")]


def _extract_sigs_from_text(text: str) -> Dict[str, Tuple[int, str]]:
    sigs: Dict[str, Tuple[int, str]] = {}
    for bt in _BACKTICK_RE.findall(text):
        m = _SIG_CALL_RE.match(bt.strip())
        if m and m.group(1) not in _BUILTIN_TYPES:
            sigs[m.group(1).split(".")[-1]] = (len(_split_params(m.group(2))), bt.strip())
    if not sigs:
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", text):
            if m.group(1) not in _BUILTIN_TYPES:
                sigs[m.group(1)] = (len(_split_params(m.group(2))), m.group(0))
    return sigs


def _parse_delta_line(val: str) -> Optional[Dict[str, Any]]:
    if val.lower() in _NONE_VALUES:
        return None
    action = "remove" if re.search(r"\b(removes?|drops?|deletes?|deprecates?|renames?)\b", val, re.I) else "change"
    sigs = _extract_sigs_from_text(val)
    names = set(sigs) | {bt.strip() for bt in _BACKTICK_RE.findall(val) if _IDENT_RE.match(bt.strip())}
    return {"action": action, "sigs": sigs, "paths": tdq_team._extract_paths(val), "names": names, "raw": val}


def _parse_giao_tiep(body: str, produces: Dict[str, Tuple[int, str]], csigs: Dict[str, Tuple[int, str]], csyms: Set[str]) -> None:
    if "Produces:" in body:
        produces.update(_extract_sigs_from_text(body.split("Produces:", 1)[1]))
    if "Consumes:" not in body:
        return
    cons_part = body.split("Consumes:", 1)[1].split("|", 1)[0]
    extracted = _extract_sigs_from_text(cons_part)
    csigs.update(extracted)
    csyms.update(extracted)
    for bt in _BACKTICK_RE.findall(cons_part):
        clean = bt.strip().rstrip("()")
        if _IDENT_RE.match(clean) and clean not in _BUILTIN_TYPES:
            csyms.add(clean)


def _parse_task_wave_contracts(task: tdq_team.Task) -> Dict[str, Any]:
    deltas: List[Dict[str, Any]] = []
    produces: Dict[str, Tuple[int, str]] = {}
    csigs: Dict[str, Tuple[int, str]] = {}
    csyms: Set[str] = set()
    for line in task.text[1:]:
        low = line.strip().lower()
        if low.startswith("contract-delta:"):
            parsed = _parse_delta_line(line.split(":", 1)[1].strip())
            if parsed:
                deltas.append(parsed)
                if parsed["action"] == "change":
                    produces.update(parsed["sigs"])
        elif low.startswith("giao tiếp:"):  # i18n-allow
            _parse_giao_tiep(line.split(":", 1)[1], produces, csigs, csyms)
    for syms in task._tham_chieu_syms.values():
        csyms.update(s.split(".")[-1] for s in syms)
    return {"deltas": deltas, "produces": produces, "consumes_sigs": csigs, "consumes_syms": csyms}


def _ancestor_map(deps: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    anc: Dict[str, Set[str]] = {}
    for ma in deps:
        seen: Set[str] = set()
        stack = list(deps.get(ma, ()))
        while stack:
            cur = stack.pop()
            if cur not in seen:
                seen.add(cur)
                stack.extend(deps.get(cur, ()))
        anc[ma] = seen
    return anc


def _check_parallel_deltas(
    t1: tdq_team.Task, c1: Dict[str, Any], w1: int,
    tasks: Sequence[tdq_team.Task], info: Dict[str, Dict[str, Any]], waves: Dict[str, int], errs: List[str]
) -> None:
    if not c1["deltas"]:
        return
    n1 = {n for d in c1["deltas"] for n in d["names"]}
    p1 = {p for d in c1["deltas"] for p in d["paths"]}
    for t2 in tasks:
        if waves.get(t2.ma, 1) != w1 or not info[t2.ma]["deltas"]:
            continue
        n2 = {n for d in info[t2.ma]["deltas"] for n in d["names"]}
        p2 = {p for d in info[t2.ma]["deltas"] for p in d["paths"]}
        overlap = sorted((n1 & n2) | (p1 & p2))
        if overlap:
            errs.append(f"Wave {w1}: parallel CONTRACT-DELTA conflict between {t1.ma} and {t2.ma} on {', '.join(overlap)}")


def _check_producer_consumer_pair(
    cons: tdq_team.Task, cc: Dict[str, Any], wc: int,
    prod_id: str, cp: Dict[str, Any], wp: int, anc: Set[str], errs: List[str]
) -> None:
    for d in cp["deltas"]:
        dead = sorted(d["names"] & cc["consumes_syms"]) if d["action"] == "remove" else []
        if dead and wc >= wp:
            errs.append(f"Wave {wc}: {cons.ma} uses {', '.join(dead)} removed by {prod_id} CONTRACT-DELTA")
    for sym in sorted(set(cp["produces"]) & cc["consumes_syms"]):
        if wc <= wp or prod_id not in anc:
            errs.append(f"Wave {wc}: {cons.ma} consumes `{sym}` produced by {prod_id} (wave {wp}) without upstream Cần: {prod_id}")  # i18n-allow
    for sym in sorted(set(cp["produces"]) & set(cc["consumes_sigs"])):
        p_arity, p_sig = cp["produces"][sym]
        c_arity, c_sig = cc["consumes_sigs"][sym]
        if p_arity != c_arity:
            errs.append(f"Signature mismatch for `{sym}`: {prod_id} produces `{p_sig}` while {cons.ma} consumes `{c_sig}`")


def check_wave(plan_path: str, root_dir: Optional[str] = None) -> Tuple[int, List[str]]:
    """Verify CONTRACT-DELTA and producer/consumer symbol consistency across waves."""
    root = _resolve_root_dir(plan_path, None, root_dir)
    abs_plan = _resolve_path(plan_path, root)
    if not os.path.isfile(abs_plan):
        return 1, [f"Plan file not found: {plan_path}"]
    tasks = tdq_team.doc_plan(abs_plan)
    if not tasks:
        return 1, [f"Plan contains no tasks: {plan_path}"]
    waves = tdq_team.chia_dot(tasks, {t.ma: ("giao", "") for t in tasks}, project_root=root)
    ancestors = _ancestor_map(tdq_team.doc_phu_thuoc(tasks))
    info = {t.ma: _parse_task_wave_contracts(t) for t in tasks}
    errs: List[str] = []
    for idx, t1 in enumerate(tasks):
        c1, w1 = info[t1.ma], waves.get(t1.ma, 1)
        _check_parallel_deltas(t1, c1, w1, tasks[idx + 1:], info, waves, errs)
        for prod_id, cp in info.items():
            if prod_id != t1.ma:
                _check_producer_consumer_pair(t1, c1, w1, prod_id, cp, waves.get(prod_id, 1), ancestors.get(t1.ma, set()), errs)
    _log(f"check_wave -> tasks={len(tasks)} errors={len(errs)}")
    return (0 if not errs else 1), errs


# ------------------------------------------------------------------ CLI

def _flatten_list_args(groups: Optional[Sequence[Sequence[str]]]) -> List[str]:
    out: List[str] = []
    for grp in groups or ():
        for item in grp:
            for part in item.split(","):
                clean = part.strip()
                if clean and clean not in out:
                    out.append(clean)
    return out


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tdq_plan_scaffold.py",
        description="Static AST/spec scaffolder, card emitter, plan verifier, and wave checker.",
    )
    parser.add_argument("plan_pos", nargs="?", default=None, help="optional path to plan markdown")
    parser.add_argument("--plan", default=None, help="path to plan markdown")
    parser.add_argument("--files", action="append", nargs="+", help="target source files")
    parser.add_argument("--refs", action="append", nargs="+", help="reference source files")
    parser.add_argument("--from-spec", default=None, help="path to approved spec markdown (§3c)")
    parser.add_argument("--root", "--root-dir", dest="root_dir", default=None, help="project root dir")
    parser.add_argument("--emit-cards", nargs="?", const="__FLAG__", default=None, help="emit Per-Task Mini-Spec cards")
    parser.add_argument("--verify-plan", nargs="?", const="__FLAG__", default=None, help="verify symbols and asserts in plan")
    parser.add_argument("--check-wave", nargs="?", const="__FLAG__", default=None, help="verify CONTRACT-DELTA across waves")
    return parser


def _pick_plan(flag_val: Optional[str], args: argparse.Namespace) -> Optional[str]:
    return flag_val if (flag_val and flag_val != "__FLAG__") else (args.plan or args.plan_pos)


def _run_verify_or_wave(is_verify: bool, plan: Optional[str], args: argparse.Namespace) -> int:
    if not plan:
        flag = "--verify-plan" if is_verify else "--check-wave"
        _err(f"Usage error: {flag} requires a plan file path.")
        return 2
    rc, errs = (verify_plan(plan, root_dir=args.root_dir, spec_path=args.from_spec)
                if is_verify else check_wave(plan, root_dir=args.root_dir))
    for msg in errs:
        _err(msg)
    if rc == 0:
        msg = f"OK: verified `{plan}` with 0 errors." if is_verify else f"OK: wave check passed for `{plan}`."
        print(msg)
    return rc


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint."""
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    files, refs = _flatten_list_args(args.files), _flatten_list_args(args.refs)
    try:
        if args.verify_plan is not None:
            return _run_verify_or_wave(True, _pick_plan(args.verify_plan, args), args)
        if args.check_wave is not None:
            return _run_verify_or_wave(False, _pick_plan(args.check_wave, args), args)
        if args.emit_cards is not None:
            plan = _pick_plan(args.emit_cards, args)
            print(emit_cards(plan, refs=refs, spec_path=args.from_spec, files=files, root_dir=args.root_dir), end="")
            return 0
        if files or refs:
            root = _resolve_root_dir(args.plan or args.plan_pos, args.from_spec, args.root_dir)
            print(_format_file_anchors(files, refs, args.from_spec, root), end="")
            return 0
        parser.print_usage(sys.stderr)
        return 2
    except (ScaffoldError, FileNotFoundError) as exc:
        _err(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
