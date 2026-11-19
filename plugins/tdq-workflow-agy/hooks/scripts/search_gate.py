#!/usr/bin/env python3
"""PreToolUse on `Bash` and `Grep` — DENY a code search that skips the concept layer.

Why this gate blocks while every other TDQ hook only reminds (`docs/kien-truc.md` 2026-10-03):
measured on a real session (2026-10-02, excalidraw), an agent made ~20 code searches across four
requests — almost all through Bash `grep`, not the `Grep` tool — with 0 lumen and 0 LSP calls,
until the user asked about the search rule. The rule lived in text only; nothing held it at the
moment the agent picked a tool. The user asked for it to be FORCED, and Codex's `PreToolUse`
accepts nothing but `deny` — a reminder is not available there at all.

What is decided here is decided by `scripts/search_rules.py` (pure, no I/O), so the replay tool
(`scripts/search_replay.py`) runs the very same rules on recorded sessions. This hook only:
  1. reads the command or the Grep pattern, and lets everything that is not a search through;
  2. reads the request's state from the search ledger (`search_observe.py` owns the format);
  3. asks `search_rules.quyet_dinh`, records the search, and prints `deny` + reason when refused.

It never breaks a tool call because of its own fault: any exception lets the call through. It is
cheap — no subprocess, and it never opens the files the agent is searching.

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
import re as _re
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402 — also puts `scripts/` on sys.path for search_rules
import search_observe  # noqa: E402
import search_rules  # noqa: E402

MA = "TDQ:SEARCH"
# The readiness stamp `tdq_setup.py --nen` writes, and how long a "still building" claim is
# believed: the builder's own overall cap (`tdq_setup.TRAN_GIAY`, 1800 s — sized from an 11-minute
# lumen index of excalidraw). Past that the build is dead, not slow.
HAN_DUNG_NEN_GIAY = 1800
# The concept layers of the readiness stamp. A stamp written before 0.58.0 may still carry a
# `lumen` key; it is never read, so a removed layer can neither unlock the rule nor be suggested.
TANG_KHAI_NIEM = ("lsp", "graphify")
# Denials in one scope, with no concept query ever recorded, after which a machine with NO
# readiness stamp is treated as having no concept layer (see `ly_do_dung_xuong`).
BREAKER_CHAN = 3


def _log(message):
    """Log service: ISO timestamp on stderr, on by default, muted by TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        print(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] search_gate: {message}",
              file=sys.stderr)


def _lenh(ten_tool, vao):
    """-> what to classify: the shell command (str or argv list) or the whole Grep input.

    Grep's `glob`/`path`/`type` decide whether it searches code or documents, so they travel too.
    """
    if ten_tool in ("Grep", "grep_search", "search_directory"):
        return vao
    return vao.get("command") or vao.get("cmd") or ""


def _doc_moc(cwd):
    """-> the readiness stamp `tdq_setup.py --nen` writes, or None. Read directly: importing
    `tdq_setup` would drag the whole setup module in before every Bash call."""
    try:
        with open(os.path.join(cwd or ".", search_rules.MOC_SAN_SANG), "r", encoding="utf-8") as fh:
            moc = json.load(fh)
    except (OSError, ValueError):
        return None
    return moc if isinstance(moc, dict) else None


FILE_MOC_NGON_NGU = (
    ("tsconfig.json", "typescript"),
    ("package.json", "typescript"),
    ("jsconfig.json", "javascript"),
    ("pyproject.toml", "python"),
    ("requirements.txt", "python"),
    ("Pipfile", "python"),
    ("setup.py", "python"),
    ("go.mod", "go"),
    ("Cargo.toml", "rust"),
)


def do_ngon_ngu_du_an(cwd):
    """Detect the project's primary language_id from marker files."""
    if not cwd or not os.path.isdir(cwd):
        return None
    for ten_file, lang in FILE_MOC_NGON_NGU:
        if os.path.isfile(os.path.join(cwd, ten_file)):
            return lang
    return None


def tang_song(moc):
    """-> the concept layers the stamp marks ready, in rule order; None when there is no stamp."""
    if moc is None:
        return None
    tang = moc.get("tang") or {}
    return tuple(t for t in TANG_KHAI_NIEM if (tang.get(t) or {}).get("san_sang"))


def ly_do_dung_xuong(moc, tt):
    """-> why the gate must stand down (the agent has no right way to go), else None.

    1. The stamp says NEITHER LSP nor graphify can answer — whether it is still building or
       finished that way (ollama off, no language server). Denying then sends the agent to tools
       that cannot answer; the first version did exactly that once a build had finished (review
       2026-10-03).
    2. No stamp at all (never built here: Codex, a host without SessionStart, auto-init off) AND
       the gate has already denied BREAKER_CHAN times in this scope with no concept query ever
       recorded. That is a machine without a concept layer, or a host whose tool names the ledger
       cannot see. It is deliberately NOT applied when a stamp says a layer is alive: there,
       "retry three times" must not become a way around the rule.
    """
    if moc is not None:
        tang = moc.get("tang") or {}
        song = [t for t in TANG_KHAI_NIEM if (tang.get(t) or {}).get("san_sang")]
        if not song:
            trang = "being built" if moc.get("dang_dung") else "not available here"
            return (f"no concept layer can answer yet (LSP, graphify: {trang}) — "
                    "searching freely until one does; run tdq-setup to fix it")
        return None
    if not tt.get("da_goi_khai_niem") and tt.get("so_lan_bi_chan", 0) >= BREAKER_CHAN:
        return (f"{BREAKER_CHAN} searches denied and no concept query was ever recorded here — "
                "the concept layer looks unavailable; searching freely. Run tdq-setup to install it")
    return None


_RTK_BYPASS_RE = _re.compile(
    r"(?:^|[;&|])\s*rtk(?:\.exe)?(?:\s+-[^\s]+)*\s+bypass\b",
    _re.IGNORECASE,
)


def _is_rtk_bypass(ten_tool, vao):
    if ten_tool == "Grep" or not isinstance(vao, dict):
        return False
    cmd = vao.get("command") or vao.get("cmd") or ""
    if isinstance(cmd, list):
        cmd = " ".join(str(x) for x in cmd)
    return bool(_RTK_BYPASS_RE.search(str(cmd)))


def _search_grace_state(cwd, phien):
    """Return latest consecutive search_grace state from turns-<sid>.jsonl."""
    rows = _common._read_jsonl(_common._shard_turn_path(cwd, phien))
    state_val = "clean"
    for row in rows:
        if row.get("type") == "search_grace" or row.get("event") == "search_grace":
            val = row.get("state")
            if val in ("warned", "reset", "clean"):
                state_val = val
    return state_val


_SEARCH_CMD_LEAK_RE = _re.compile(r"(?:\b(?:rg|grep|findstr)\b|Select-String)", _re.IGNORECASE)
_PS_HERESTRING_RE = _re.compile(r"(?s)@'\r?\n.*?\r?\n'@|@\"\r?\n.*?\r?\n\"@")


def _has_search_leak(ten_tool, vao):
    """Detect raw search CLI invocations inside malformed shell strings outside PS here-strings."""
    if ten_tool in ("Grep", "grep_search", "search_directory") or not isinstance(vao, dict):
        return False
    cmd = vao.get("command") or vao.get("cmd") or ""
    if isinstance(cmd, list):
        cmd = " ".join(str(x) for x in cmd)
    stripped = _PS_HERESTRING_RE.sub(" ", str(cmd))
    return bool(_SEARCH_CMD_LEAK_RE.search(stripped))


def _mark_search_grace(cwd, phien, state_val, tool_name):
    row = {
        "ts": _common.tdq_state.now_iso(),
        "kind": "observe",
        "event": "search_grace",
        "type": "search_grace",
        "state": state_val,
        "session": phien,
        "tool": tool_name,
    }
    _common._lock_and_append_jsonl(_common._shard_turn_path(cwd, phien), row)


def quyet(cwd, phien, ten_tool, vao):
    """-> (allowed, reason, classification, stand_down). Testable without a subprocess."""
    cong_cu = "Grep" if ten_tool in ("Grep", "grep_search", "search_directory") else "Bash"
    pl = search_rules.phan_loai(cong_cu, _lenh(ten_tool, vao))
    if pl.get("status") != "unknown" and pl.get("loai") not in (search_rules.TIM_CODE, search_rules.LOC_FILE):
        return True, "not a search", pl, False
    khoa = search_observe.khoa_hien_tai(cwd, phien)
    tt = search_rules.trang_thai(search_observe.doc_so(cwd, khoa, phien))
    tt["cua_so"] = search_rules.CUA_SO
    moc = _doc_moc(cwd)
    tt["tang_song"] = tang_song(moc)
    tt["ngon_ngu"] = do_ngon_ngu_du_an(cwd)
    pha = None
    try:
        from tdq_state import effective_phase, load
        st = load(cwd, heal=False)
        pha = effective_phase(st, warn=False)
    except Exception:
        pass
    tt["phase"] = pha
    if _common.is_agy() and pl.get("status") == "unknown":
        if _has_search_leak(ten_tool, vao):
            pl = dict(pl, loai=search_rules.TIM_CODE, status="leak_search")
        else:
            if pl.get("loai") == search_rules.TIM_CODE:
                search_observe.ghi_so(cwd, {"ts": time.time(), "khoa": khoa, "loai": "tim",
                                            "cho_phep": True, "tinh_cua_so": False, "doan_mo": False})
                if pha in ("implement", "qc"):
                    return True, "agy_malformed_remind", pl, False
            return True, "agy_malformed_allow", pl, False
    if _common.is_agy() and pl.get("loai") == search_rules.TIM_CODE and _is_rtk_bypass(ten_tool, vao):
        search_observe.ghi_so(cwd, {"ts": time.time(), "khoa": khoa, "loai": "tim",
                                    "cho_phep": False, "tinh_cua_so": False, "doan_mo": bool(pl.get("doan_mo"))})
        return False, "[TDQ:SEARCH] rtk bypass grep/rg is denied; query LSP or Graphify first.", pl, False
    ok, ly_do = search_rules.quyet_dinh(pl, tt)
    dung_xuong = None
    if not ok:
        dung_xuong = ly_do_dung_xuong(moc, tt)
        if dung_xuong:
            ok, ly_do = True, dung_xuong
    if _common.is_agy() and not ok and not dung_xuong:
        if _search_grace_state(cwd, phien) != "warned":
            _mark_search_grace(cwd, phien, "warned", ten_tool)
            search_observe.ghi_so(cwd, {"ts": time.time(), "khoa": khoa, "loai": "tim",
                                        "cho_phep": True, "tinh_cua_so": False, "doan_mo": bool(pl.get("doan_mo"))})
            return True, "agy_search_grace", pl, False
    if pl.get("loai") == search_rules.TIM_CODE or pl.get("status") == "unknown":
        search_observe.ghi_so(cwd, {"ts": time.time(), "khoa": khoa, "loai": "tim",
                                    "cho_phep": ok, "tinh_cua_so": ok,
                                    "doan_mo": bool(pl.get("doan_mo"))})
    return ok, ly_do, pl, bool(dung_xuong)


def eval_search(payload):
    """Evaluate search gate rules for an already-read payload; return True to allow continuing."""
    try:
        ten_tool = (payload or {}).get("tool_name") or ""
        if ten_tool not in ("Grep", "grep_search", "search_directory") and ten_tool.lower() not in search_rules.CONG_CU_SHELL:
            return True
        cwd = _common.payload_cwd(payload)
        vao = (payload or {}).get("tool_input") or {}
        ok, ly_do, pl, dung_xuong = quyet(cwd, _common.session_id(payload), ten_tool, vao)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — a gate must never break the agent's tool call
        _log(f"error, letting the call through: {type(exc).__name__}: {exc}")
        return True

    _log(f"{ten_tool} · {pl.get('loai')} · doan_mo={pl.get('doan_mo')} · "
         f"{'cho' if ok else 'CHAN'} · {ly_do.splitlines()[0][:80]}")
    if ly_do == "agy_malformed_remind":
        _common.remind(cwd, payload, MA, [f"Malformed command suspected search ({ten_tool})"])
    elif ly_do == "agy_search_grace":
        _common.queue_remind(cwd, payload, MA, f"Use LSP or Graphify before consecutive {ten_tool}", check_turn=False)
    elif dung_xuong:
        _common.remind(cwd, payload, MA, [ly_do, "Concept layer: LSP find_symbol/find_references, graphify query."])
    if ok:
        return True
    # Every Claude Code deny goes through `_common.block()` (pinned by test_compliance_protocol).
    # `day_du=True`: the 200-character reminder cap would cut the one thing the agent needs here —
    # which query to run instead. The rules already start the reason with the code; drop it so
    # `block()` does not print it twice.
    dong = [str(x) for x in ly_do.splitlines()] or [str(ly_do)]
    dong[0] = dong[0].replace(f"[{MA}] ", "", 1)
    _common.block(cwd, payload, MA, dong, day_du=True)
    return False


def main():
    eval_search(_common.read_payload())
    sys.exit(0)


if __name__ == "__main__":
    main()
