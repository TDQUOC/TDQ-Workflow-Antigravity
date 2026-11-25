#!/usr/bin/env python3
"""PreToolUse on `mcp__lsp__start_lsp` — DENY a start that picks no language or the wrong root.

Why (request 2026-10-07-2225): without `language_id`, agent-lsp does not detect the language — it
starts EVERY configured server and makes the first one (`typescript`) current. On a Python repo
that crashed tsserver (`0xc0000409`) or answered "No Project" (bench 2026-10-07, runs 1–2). And
`find_symbol` only ever asks the current server, so a start on the wrong (root, language) makes it
answer empty with no error at all (upstream issue #55).

Rules, in order:
1. `language_id` missing → deny.
2. The root is inside this project AND the module table `docs/tdq/.tdq-lsp-module.json` exists AND
   no row has that (root, language) pair → deny, listing the valid calls. JavaScript and TypeScript
   are one family (one server), so either id is accepted for a module of that family.
3. Anything else → silent: a root outside the project, or no table yet, is not ours to judge.

It blocks for a WRONG CALL, never for a missing approval — `docs/kien-truc.md` 2026-07-29 stands.
The table is read as plain JSON; `lsp_module` (the tree scan) is never imported, so the hook stays
cheap (82–85 ms measured 2026-10-08, `_common` included).

Env: TDQ_PROJECT_DIR anchors the project; TDQ_LOG=0 silences the log.
"""
import os as _tdq_os, sys as _tdq_sys
_tdq_here = _tdq_os.path.dirname(_tdq_os.path.abspath(__file__))
_tdq_scripts = _tdq_os.path.normpath(_tdq_os.path.join(_tdq_here, '..', '..', 'scripts'))
for _p in (_tdq_scripts, _tdq_here):
    if _tdq_os.path.isdir(_p) and _p not in _tdq_sys.path:
        _tdq_sys.path.insert(0, _p)
import utf8_io  # noqa: E402,F401
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402
from search_rules import ten_lenh_tdq_lsp, trang_thai_lsp  # noqa: E402
from search_observe import doc_so, khoa_hien_tai  # noqa: E402

MA = "TDQ:LSP"
FILE_BANG = os.path.join("docs", "tdq", ".tdq-lsp-module.json")
HO_TS = ("typescript", "javascript")
TRAN_FILE_BLAST_RADIUS = 3


def _log(message):
    """Log service: ISO timestamp on stderr, on by default, muted by TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] lsp_gate: {message}", file=sys.stderr)


def _chuan(duong):
    return os.path.normcase(os.path.normpath(os.path.abspath(duong)))


def _cung_ho(a, b):
    return a == b or (a in HO_TS and b in HO_TS)


def doc_cap_hop_le(cwd):
    """-> [(absolute root, language)] from the module table, or None when there is no table."""
    try:
        with open(os.path.join(cwd, FILE_BANG), encoding="utf-8") as fh:
            module = (json.load(fh) or {}).get("module") or {}
    except (OSError, ValueError, AttributeError):
        return None
    return [(os.path.normpath(os.path.join(cwd, m.get("goc", "."))), m.get("lang", ""))
            for m in module.values() if isinstance(m, dict)]


def phan_xu(cwd, tool_input):
    """-> [] to allow, or the deny lines. Pure, for the tests."""
    lang = str(tool_input.get("language_id") or "").strip()
    goc = str(tool_input.get("root_dir") or "").strip()
    cap = doc_cap_hop_le(cwd) or []
    goi_y = [f'start_lsp {{"root_dir": {json.dumps(g)}, "language_id": "{l}"}}' for g, l in cap]
    if not lang:
        return ["start_lsp without language_id: agent-lsp starts every server and makes "
                "TypeScript current (crash 0xc0000409 / No Project on 2026-10-07).",
                *(["Use one of: " + " · ".join(goi_y)] if goi_y else
                  ["Pass the language of the code you work on, e.g. \"language_id\": \"python\"."])]
    if not goc or not cap:
        return []
    goc_c, cwd_c = _chuan(goc), _chuan(cwd)
    if not (goc_c == cwd_c or goc_c.startswith(cwd_c + os.sep)):
        return []
    if any(_chuan(g) == goc_c and _cung_ho(l, lang) for g, l in cap):
        return []
    return [f"No LSP module of this project is ({goc}, {lang}) — find_symbol would answer empty.",
            "Use one of: " + " · ".join(goi_y),
            "New module? python3 scripts/tdq_lsp.py kich-ban refreshes the table."]


def phan_xu_blast_radius(cwd, tool_input, rows=None):
    """-> [] to allow, or deny lines for mcp__lsp__blast_radius (O3/spec §3c Bước 2)."""
    changed_files = tool_input.get("changed_files")
    if not isinstance(changed_files, list) or len(changed_files) == 0:
        return [
            "blast_radius requires a non-empty list of changed_files.",
            "Use find_references for single symbols, or pass 1-3 files to blast_radius."
        ]
    if len(changed_files) > TRAN_FILE_BLAST_RADIUS:
        return [
            f"blast_radius requested on {len(changed_files)} files > {TRAN_FILE_BLAST_RADIUS}.",
            "Calling blast_radius across >3 files causes severe upstream timeouts (measured 1800s aborts).",
            "Narrow to <=3 changed files, use find_references per symbol, or use graphify affected."
        ]
    scope = tool_input.get("scope", "exported")
    if scope != "exported":
        return [
            f"blast_radius with scope='{scope}' is denied (only scope='exported' is permitted).",
            "scope='all' scans entire workspace private symbols and exhausts semaphore worker pools.",
            "Use scope='exported' (default), or find_references for targeted lookups."
        ]
    if bool(tool_input.get("include_transitive")) is True:
        return [
            "blast_radius with include_transitive=true is denied.",
            "Transitive symbol exploration causes combinatorial graph traversal and timeouts.",
            "Use graphify affected \"<symbol>\" --depth 2 for instant static graph traversal."
        ]

    # Circuit breaker check
    if rows is not None:
        tt = trang_thai_lsp(rows)
        if tt.get("mach_ngat_mo"):
            ly_do = tt.get("ly_do_ngat")
            return [
                f"Circuit breaker is OPEN for blast_radius ({ly_do}).",
                "Recent LSP call(s) failed or timed out in this workspace.",
                "blast_radius is temporarily halted. Use find_references or Grep + Graphify instead."
            ]

    return []


_ROOT_LANG_MARKERS = {
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "setup.py": "python",
    "tsconfig.json": "typescript",
    "package.json": "typescript",
    "jsconfig.json": "javascript",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "java",
}


def _lang_family(lang):
    return "typescript" if lang in HO_TS else lang


def _pick_from_module_table(cap, goc):
    if not cap:
        return None, None
    if goc:
        goc_c = _chuan(goc)
        matched = [(g, l) for g, l in cap if _chuan(g) == goc_c and l]
        families = {_lang_family(l) for _, l in matched}
        if len(families) == 1:
            return matched[0][1], matched[0][0]
        return None, None
    families = {_lang_family(l) for _, l in cap if l}
    if len(families) == 1:
        return cap[0][1], cap[0][0]
    return None, None


def _detect_unique_lang_o1(cwd, goc=""):
    """Detect unique project language in O(1) without calling lsp_module.do_module."""
    cap = doc_cap_hop_le(cwd)
    if cap:
        return _pick_from_module_table(cap, goc)
    if not cwd or not os.path.isdir(cwd):
        return None, None
    found = []
    try:
        entries = list(os.scandir(cwd))
    except OSError:
        return None, None
    for entry in entries:
        if not entry.is_file():
            continue
        if entry.name in _ROOT_LANG_MARKERS:
            found.append(_ROOT_LANG_MARKERS[entry.name])
        elif entry.name.lower().endswith((".csproj", ".sln")):
            found.append("csharp")
    families = {_lang_family(l) for l in found}
    if len(families) != 1:
        return None, None
    chosen = "typescript" if "typescript" in found else found[0]
    return chosen, cwd


def _agy_blast_radius(cwd, phien, tool_input):
    khoa = khoa_hien_tai(cwd, phien)
    rows = doc_so(cwd, khoa, phien)
    scope = tool_input.get("scope", "exported")
    transitive = bool(tool_input.get("include_transitive")) is True
    if _common.is_agy() and (scope != "exported" or transitive):
        patched = dict(tool_input, scope="exported", include_transitive=False)
        dong = phan_xu_blast_radius(cwd, patched, rows)
        if not dong:
            _common.set_overwrite({"scope": "exported", "include_transitive": False})
            _log("blast_radius auto-overwrite scope=exported · allow")
            return []
        return dong
    dong = phan_xu_blast_radius(cwd, tool_input, rows)
    _log(f"blast_radius files={len(tool_input.get('changed_files') or [])} - {'deny' if dong else 'allow'}")
    return dong


def _agy_start_lsp(cwd, tool_input):
    lang = str(tool_input.get("language_id") or "").strip()
    goc = str(tool_input.get("root_dir") or "").strip()
    if _common.is_agy() and not lang:
        det_lang, det_root = _detect_unique_lang_o1(cwd, goc)
        if det_lang:
            ov = {"language_id": det_lang}
            if not goc and det_root:
                ov["root_dir"] = det_root
            _common.set_overwrite(ov)
            _log(f"start_lsp auto-overwrite language_id={det_lang!r} - allow")
            return []
    dong = phan_xu(cwd, tool_input)
    _log(f"language_id={tool_input.get('language_id')!r} root={tool_input.get('root_dir')!r} - "
         f"{'deny' if dong else 'allow'}")
    return dong


def _phan_xu_lenh(cwd, phien, op, tool_input):
    """Route a TDQ LSP call to blast_radius, start_lsp, or allow."""
    if op == "blast_radius":
        return _agy_blast_radius(cwd, phien, tool_input)
    if op == "start_lsp":
        return _agy_start_lsp(cwd, tool_input)
    _log(f"tdq-lsp op={op} - allow")
    return []


def _tach_mcp_server_tool(tool_name, tool_input, policy=None):
    """Extract (server, tool) from Antigravity/Claude MCP tool names or inputs."""
    if tool_name == "call_mcp_tool" and isinstance(tool_input, dict):
        srv = str(tool_input.get("ServerName") or tool_input.get("server") or "").strip()
        tn = str(
            tool_input.get("ToolName")
            or tool_input.get("tool")
            or tool_input.get("Name")
            or tool_input.get("name")
            or ""
        ).strip()
        return (srv, tn) if (srv and tn) else (None, None)
    from mcp_policy import split_eager_mcp_name

    return split_eager_mcp_name(tool_name, policy=policy)


def _kiem_mcp_ngoai_lsp(cwd, payload, tool_name, tool_input):
    """Enforce P0 MCP quarantine on non-tdq-lsp MCP tool calls; return True if blocked."""
    if not (tool_name == "call_mcp_tool" or tool_name.startswith("mcp_")):
        return False
    from tdq_config import load_config

    cfg = load_config(cwd)
    if not (cfg.get("p0") or {}).get("mcp_quarantine_enabled", True):
        return False
    from mcp_policy import evaluate_tool_call, is_denied, load_policy

    policy, _corrupt = load_policy(cwd)
    server, tname = _tach_mcp_server_tool(tool_name, tool_input, policy=policy)
    if not server or not tname:
        return False
    schema_obj = tool_input.get("_mcp_schema") if isinstance(tool_input, dict) else None
    if not isinstance(schema_obj, dict):
        schema_obj = None
    ket_qua = evaluate_tool_call(cwd, server, tname, schema_obj=schema_obj)
    if is_denied(ket_qua):
        reason = str(ket_qua.get("reason") or f"MCP tool {server}/{tname} quarantined pending approval")
        hint = str(ket_qua.get("hint") or f"py -3 scripts/mcp_policy.py approve {server} {tname}")
        _log(f"non-tdq-lsp mcp deny server={server} tool={tname} reason={reason}")
        _common.block(cwd, payload, "TDQ:READONLY", [reason, f"Approve: {hint}"], day_du=True)
        return True
    return False


def main():
    try:
        payload = _common.read_payload()
        cwd = _common.payload_cwd(payload)
        phien = _common.session_id(payload)
        tool_name = str(payload.get("tool_name") or "")
        tool_input = payload.get("tool_input")
    except Exception as loi:  # noqa: BLE001 — a broken payload must never block the tool
        _log(f"cannot read payload ({loi}) — silent")
        sys.exit(0)
    op = ten_lenh_tdq_lsp(tool_name)
    if op is None:
        if _kiem_mcp_ngoai_lsp(cwd, payload, tool_name, tool_input):
            return
        _log(f"non-tdq-lsp tool={tool_name!r} — allow")
        sys.exit(0)
    if not isinstance(tool_input, dict):
        tool_input = {}
    if not (_common.has_tool_args() or tool_input):
        # Empty/broken payload: fail-open (measured 2026-10-08 on mangled JSON).
        _log("payload without tool_input — silent")
        sys.exit(0)
    dong = _phan_xu_lenh(cwd, phien, op, tool_input)
    if dong:
        _common.block(cwd, payload, MA, dong, day_du=True)
    sys.exit(0)



if __name__ == "__main__":
    main()
