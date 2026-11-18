"""Reproduce three false-positive TDQ hook block groups against the installed plugin."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

DEFAULT_PLUGIN_DIR = Path(r"~\.gemini\config\plugins\tdq-workflow-agy").expanduser()
SCHEMA_VERSION = "tdq-false-positive-repro/v1"


def _log(message: str) -> None:
    """Emit ISO-timestamped stderr diagnostic unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"[{stamp}] false_positive_repro: {message}", file=sys.stderr)


def _read_plugin_version(plugin_dir: Path) -> str:
    """Return installed plugin version from manifest.json or 'unknown'."""
    manifest = plugin_dir / "manifest.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return str(data.get("version") or "unknown")
    except (OSError, ValueError):
        return "unknown"


def _parse_hook_output(raw_stdout: str) -> tuple[str, str]:
    """Extract (decision, reason) from Antigravity or Claude/Codex hook JSON stdout."""
    text = raw_stdout.strip()
    if not text:
        return "allow", ""
    last_line = text.splitlines()[-1]
    try:
        data = json.loads(last_line)
    except ValueError:
        return "unknown", text[:400]
    if not isinstance(data, dict):
        return "unknown", text[:400]
    if "decision" in data:
        return str(data.get("decision") or "allow"), str(data.get("reason") or "")
    specific = data.get("hookSpecificOutput")
    if isinstance(specific, dict):
        dec = str(specific.get("permissionDecision") or "allow")
        reason = str(specific.get("permissionDecisionReason") or "")
        return dec, reason
    return "allow", ""


def _invoke_hook(
    plugin_dir: Path,
    script_name: str,
    payload: dict,
    project_dir: Path,
    event: str | None = "PreToolUse",
) -> dict:
    """Spawn one installed hook script with JSON stdin and return decision details."""
    argv = ["py", "-3", "-X", "utf8", str(Path("hooks") / "scripts" / script_name)]
    if event:
        argv.extend(["--event", event])
    env = dict(os.environ, TDQ_LOG="0", TDQ_PROJECT_DIR=str(project_dir))
    proc = subprocess.run(
        argv,
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        cwd=str(plugin_dir),
        capture_output=True,
        env=env,
    )
    stdout_text = proc.stdout.decode("utf-8", errors="replace")
    stderr_text = proc.stderr.decode("utf-8", errors="replace")
    decision, reason = _parse_hook_output(stdout_text)
    return {
        "rc": proc.returncode,
        "decision": decision,
        "reason": reason,
        "stdout": stdout_text.strip(),
        "stderr": stderr_text.strip(),
    }


def _build_agy_payload(
    project_dir: Path,
    session_id: str,
    tool_name: str,
    tool_input: dict,
    tool_call: dict | None = None,
) -> dict:
    """Build an Antigravity PreToolUse payload."""
    payload = {
        "hookEventName": "PreToolUse",
        "workingDirectory": str(project_dir),
        "cwd": str(project_dir),
        "session_id": session_id,
        "conversationId": session_id,
        "toolName": tool_name,
        "toolInput": tool_input,
    }
    if tool_call is not None:
        payload["toolCall"] = tool_call
    return payload


def _build_claude_payload(
    project_dir: Path,
    session_id: str,
    tool_name: str,
    tool_input: dict,
) -> dict:
    """Build a Claude/Codex PreToolUse payload."""
    return {
        "hook_event_name": "PreToolUse",
        "cwd": str(project_dir),
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }


def _run_search_malformed_cases(plugin_dir: Path, tmp_dir: Path) -> list[dict]:
    """Reproduce [TDQ:SEARCH] malformed false positives on safe non-search shell commands."""
    py_c_cmd = (
        'py -3 -X utf8 -c "import pathlib; '
        "lines=pathlib.Path('docs/srs/03-functional-requirements.md')"
        ".read_text(encoding='utf-8').splitlines(); "
        "print(sum(1 for l in lines if '```mermaid' in l))\""
    )
    ps_herestring_cmd = (
        "@'\n"
        "from pathlib import Path\n"
        "html = Path('docs/srs/portal.html').read_text(encoding='utf-8')\n"
        "for i, line in enumerate(html.splitlines(), 1):\n"
        "    if '`' in line:\n"
        "        print(i, line[:80])\n"
        "'@ | py -3 -X utf8 -"
    )
    curl_split_cmd = (
        '(curl.exe -s "https://raw.githubusercontent.com/dashdogy/MFG-Unlocker/HEAD/README.md") '
        '-split "`n" | Select-Object -First 75'
    )

    specs = [
        (
            "search_py_c_backtick_agy_command_gate",
            "command_gate.py",
            "antigravity",
            "PreToolUse",
            "run_command",
            {"CommandLine": py_c_cmd},
            "f9e21752 L3361 / 011adcdf L80",
            "search_rules._tach_script checks backtick before double-quote state (L291 < L302); "
            "odd backticks inside Python -c double-quoted string set la_malformed=True.",
        ),
        (
            "search_py_c_backtick_agy_search_gate",
            "search_gate.py",
            "antigravity",
            "PreToolUse",
            "run_command",
            {"CommandLine": py_c_cmd},
            "f9e21752 L3361",
            "Standalone search_gate.py accepts run_command via CONG_CU_SHELL; in AGY hooks.json "
            "run_command is routed via command_gate.py which calls search_gate.eval_search.",
        ),
        (
            "search_py_c_backtick_claude_bash",
            "search_gate.py",
            "claude_codex",
            None,
            "Bash",
            {"command": py_c_cmd},
            "hooks/hooks.json Bash|Grep|PowerShell",
            "Claude/Codex hooks.json routes Bash directly to search_gate.py -> same malformed deny.",
        ),
        (
            "search_ps_herestring_agy_command_gate",
            "command_gate.py",
            "antigravity",
            "PreToolUse",
            "run_command",
            {"CommandLine": ps_herestring_cmd},
            "011adcdf L59 / 051cc9e9 L36",
            "search_rules._bo_heredoc only strips POSIX <<EOF heredocs, not PowerShell @'...'@; "
            "single quotes inside Python code close the quote at @' and expose backticks/parens.",
        ),
        (
            "search_ps_herestring_claude_powershell",
            "search_gate.py",
            "claude_codex",
            None,
            "PowerShell",
            {"command": ps_herestring_cmd},
            "hooks/hooks.json Bash|Grep|PowerShell",
            "PowerShell matcher in hooks/hooks.json routes PowerShell to search_gate.py -> malformed deny.",
        ),
        (
            "search_curl_split_agy_command_gate",
            "command_gate.py",
            "antigravity",
            "PreToolUse",
            "run_command",
            {"CommandLine": curl_split_cmd},
            "f7955f1c L683",
            "PowerShell newline escape \"`n\" has one backtick inside double quotes; "
            "_tach_script treats it as an unclosed POSIX backtick command substitution.",
        ),
        (
            "search_curl_split_claude_powershell",
            "search_gate.py",
            "claude_codex",
            None,
            "PowerShell",
            {"command": curl_split_cmd},
            "hooks/hooks.json Bash|Grep|PowerShell",
            "Claude/Codex PowerShell payload through search_gate.py hits the same \"`n\" parser bug.",
        ),
        (
            "search_grep_search_agy_control",
            "search_gate.py",
            "antigravity",
            "PreToolUse",
            "grep_search",
            {"Query": "def main", "SearchPath": str(tmp_dir)},
            "hooks.json L55-60",
            "AGY hooks.json binds standalone search_gate.py to grep_search|...; eval_search (L178) "
            "only checks 'Grep' or CONG_CU_SHELL, so grep_search exits allow.",
        ),
    ]

    cases = []
    for idx, (cid, hook, proto, ev, tname, tinput, tref, cause) in enumerate(specs, 1):
        sid = f"bench-fp-search-{idx}"
        if proto == "antigravity":
            payload = _build_agy_payload(tmp_dir, sid, tname, tinput)
        else:
            payload = _build_claude_payload(tmp_dir, sid, tname, tinput)
        res = _invoke_hook(plugin_dir, hook, payload, tmp_dir, event=ev)
        is_malformed = "[TDQ:SEARCH]" in res["reason"] and "malformed" in res["reason"]
        raw_summary = str(tinput.get("CommandLine") or tinput.get("command") or tinput)
        cases.append({
            "id": cid,
            "group": "search_malformed",
            "hook": hook,
            "protocol": proto,
            "tool_name": tname,
            "payload_summary": raw_summary.replace(str(tmp_dir), "<tmp_dir>")[:160],
            "decision": res["decision"],
            "reason": res["reason"],
            "reproduced": res["decision"] == "deny" and is_malformed,
            "rc": res["rc"],
            "technical_cause": cause,
            "transcript_ref": tref,
        })
    return cases


def _run_lsp_non_lsp_cases(plugin_dir: Path, tmp_dir: Path) -> tuple[list[dict], list[dict]]:
    """Test call_mcp_tool -> chrome-devtools (and one LSP control) through installed lsp_gate.py."""
    specs = [
        (
            "lsp_chrome_devtools_navigate_page",
            "antigravity",
            "PreToolUse",
            _build_agy_payload(
                tmp_dir,
                "bench-fp-lsp-1",
                "call_mcp_tool",
                {
                    "ServerName": "chrome-devtools",
                    "ToolName": "navigate_page",
                    "Arguments": {"url": "https://example.com"},
                },
            ),
            "chrome-devtools navigate_page",
            "Installed lsp_gate.py (synced 2026-11-18, commit 4c5d5fd5) unwraps call_mcp_tool via "
            "chuan_hoa_cong_cu_mcp -> 'mcp__chrome-devtools__navigate_page', then ten_lenh_tdq_lsp "
            "(lsp_gate.py:163-166, search_rules.py:975-1040) returns None -> exits 0 (allow). "
            "Pre-fix (4c5d5fd5~1) lacked ten_lenh_tdq_lsp and ran phan_xu on every call_mcp_tool.",
            "hooks/scripts/lsp_gate.py:163-166",
            False,
        ),
        (
            "lsp_chrome_devtools_new_page_0c6604ba",
            "antigravity",
            "PreToolUse",
            _build_agy_payload(
                tmp_dir,
                "bench-fp-lsp-2",
                "call_mcp_tool",
                {
                    "ServerName": "chrome-devtools",
                    "ToolName": "new_page",
                    "Arguments": {"url": "https://sheets.google.com"},
                },
            ),
            "chrome-devtools new_page (0c6604ba L105)",
            "Not reproduced on 2026-11-18 installed lsp_gate.py: op=ten_lenh_tdq_lsp('mcp__chrome-devtools__new_page') "
            "is None, so lsp_gate exits allow. In 0c6604ba (2026-11-16), pre-fix lsp_gate saw non-empty tool_input "
            "without language_id and denied with [TDQ:LSP].",
            "0c6604ba L105-106",
            False,
        ),
        (
            "lsp_chrome_devtools_select_page_batch_0c6604ba",
            "antigravity",
            "PreToolUse",
            _build_agy_payload(
                tmp_dir,
                "bench-fp-lsp-3",
                "call_mcp_tool",
                {},
                tool_call={
                    "name": "call_mcp_tool",
                    "args": {
                        "ServerName": "chrome-devtools",
                        "ToolName": "select_page",
                        "Arguments": {"bringToFront": True, "pageId": 1},
                    },
                },
            ),
            "toolCall batch step select_page (0c6604ba L59)",
            "normalize_payload extracts toolCall.args, unwraps to mcp__chrome-devtools__select_page, "
            "and ten_lenh_tdq_lsp returns None -> allow on installed lsp_gate.py.",
            "0c6604ba L59-60",
            False,
        ),
        (
            "lsp_chrome_devtools_new_page_no_event_fallback",
            "antigravity",
            None,
            _build_agy_payload(
                tmp_dir,
                "bench-fp-lsp-4",
                "call_mcp_tool",
                {
                    "ServerName": "chrome-devtools",
                    "ToolName": "new_page",
                    "Arguments": {"url": "https://sheets.google.com"},
                },
            ),
            "chrome-devtools new_page without --event",
            "Even without --event, _is_antigravity_payload detects toolName/toolInput and "
            "ten_lenh_tdq_lsp returns None -> allow.",
            "hooks/scripts/_common.py:149-160",
            False,
        ),
        (
            "lsp_tdq_start_lsp_missing_lang_control",
            "antigravity",
            "PreToolUse",
            _build_agy_payload(
                tmp_dir,
                "bench-fp-lsp-5",
                "call_mcp_tool",
                {
                    "ServerName": "tdq-workflow-agy_lsp",
                    "ToolName": "start_lsp",
                    "Arguments": {"root_dir": str(tmp_dir)},
                },
            ),
            "positive control: tdq-workflow-agy_lsp start_lsp without language_id",
            "Control case proving TDQ_LSP_SERVER_RE still matches tdq-workflow-agy_lsp and denies "
            "[TDQ:LSP] when language_id is omitted, while non-LSP servers like chrome-devtools pass.",
            "scripts/search_rules.py:975-985",
            True,
        ),
    ]

    cases, controls = [], []
    for cid, proto, ev, payload, summary, cause, tref, is_control in specs:
        res = _invoke_hook(plugin_dir, "lsp_gate.py", payload, tmp_dir, event=ev)
        row = {
            "id": cid,
            "group": "lsp_non_lsp",
            "hook": "lsp_gate.py",
            "protocol": proto,
            "tool_name": "call_mcp_tool",
            "payload_summary": summary,
            "decision": res["decision"],
            "reason": res["reason"],
            "reproduced": res["decision"] == "deny" and "[TDQ:LSP]" in res["reason"],
            "rc": res["rc"],
            "technical_cause": cause,
            "transcript_ref": tref,
        }
        (controls if is_control else cases).append(row)
    return cases, controls


def _prepare_tick_workspace(base_dir: Path, plan_body: str) -> Path:
    """Create a clean temporary TDQ project directory in phase=implement."""
    docs_tdq = base_dir / "docs" / "tdq"
    plan_dir = docs_tdq / "plan"
    log_dir = base_dir / "docs" / "workinglog"
    src_dir = base_dir / "src"
    plan_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)

    plan_rel = "docs/tdq/plan/repro-plan.md"
    (base_dir / plan_rel).write_text(plan_body, encoding="utf-8")
    today_log = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    today_log.write_text("# Working Log\n", encoding="utf-8")
    (src_dir / "app.py").write_text("def hello():\n    return 1\n", encoding="utf-8")

    state_data = {
        "schema_version": 6,
        "active_request": "repro-tick-loop",
        "lane": "full",
        "phase": "implement",
        "spec_approved": True,
        "plan_approved": True,
        "plan_file": plan_rel,
        "implement_mode": "main",
    }
    (docs_tdq / "state.json").write_text(json.dumps(state_data, indent=2), encoding="utf-8")
    (docs_tdq / "STATE.md").write_text(
        "# TDQ State\n- request: repro-tick-loop\n- phase: implement\n",
        encoding="utf-8",
    )
    return src_dir / "app.py"


def _run_tick_sequence(
    plugin_dir: Path,
    proj_dir: Path,
    target_file: Path,
    session_id: str,
    steps: int,
) -> list[dict]:
    """Invoke edit_gate.py sequentially without modifying the plan file."""
    results = []
    for idx in range(1, steps + 1):
        payload = _build_agy_payload(
            proj_dir,
            session_id,
            "edit_file",
            {"Path": str(target_file), "Target": "return 1", "Replacement": f"return {idx}"},
        )
        res = _invoke_hook(plugin_dir, "edit_gate.py", payload, proj_dir, event="PreToolUse")
        results.append({"step": idx, **res})
    return results


def _run_tick_loop_cases(plugin_dir: Path) -> list[dict]:
    """Reproduce [TDQ:TICK] loops in isolated temporary TDQ_PROJECT_DIR workspaces."""
    cases = []

    # Case 1: plan has only [ ] tasks (no [~]) -> immediate [TDQ:TICK] across 3 edits
    tmp1 = Path(tempfile.mkdtemp(prefix="tdq_tick_notask_"))
    try:
        target1 = _prepare_tick_workspace(
            tmp1,
            "# Plan\n\n- [ ] **T1** Implement feature A\n- [ ] **T2** Implement feature B\n",
        )
        seq1 = _run_tick_sequence(plugin_dir, tmp1, target1, "bench-fp-tick-1", steps=3)
        denied1 = [r for r in seq1 if r["decision"] == "deny" and "[TDQ:TICK]" in r["reason"]]
        cases.append({
            "id": "tick_loop_no_doing_task",
            "group": "tick_loop",
            "hook": "edit_gate.py",
            "protocol": "antigravity",
            "tool_name": "edit_file",
            "payload_summary": "3 consecutive edit_file calls with plan having only [ ] tasks (no [~])",
            "decision": seq1[-1]["decision"],
            "reason": seq1[-1]["reason"],
            "reproduced": len(denied1) == 3,
            "rc": seq1[-1]["rc"],
            "steps": [{"step": r["step"], "decision": r["decision"], "reason": r["reason"]} for r in seq1],
            "technical_cause": "edit_gate.py:266-272 blocks immediately when tick['has_doing'] is False "
            "and plan has uncompleted [ ] tasks; repeated edits hit the same block with '(lặp)'.",
            "transcript_ref": "hooks/scripts/edit_gate.py:266-272",
        })
    finally:
        shutil.rmtree(tmp1, ignore_errors=True)

    # Case 2: plan has 1 [~] task -> 3 edits allowed, 4th & 5th blocked by STREAK_NGUONG=3
    tmp2 = Path(tempfile.mkdtemp(prefix="tdq_tick_streak_"))
    try:
        target2 = _prepare_tick_workspace(
            tmp2,
            "# Plan\n\n- [~] **T1** Implement feature A\n- [ ] **T2** Implement feature B\n",
        )
        seq2 = _run_tick_sequence(plugin_dir, tmp2, target2, "bench-fp-tick-2", steps=5)
        denied2 = [r for r in seq2 if r["decision"] == "deny" and "[TDQ:TICK]" in r["reason"]]
        cases.append({
            "id": "tick_loop_streak_3_edits",
            "group": "tick_loop",
            "hook": "edit_gate.py",
            "protocol": "antigravity",
            "tool_name": "edit_file",
            "payload_summary": "5 consecutive edit_file calls on src/app.py with [~] task and unchanged plan_sha",
            "decision": seq2[3]["decision"],
            "reason": seq2[3]["reason"],
            "reproduced": (
                [r["decision"] for r in seq2[:3]] == ["allow", "allow", "allow"]
                and len(denied2) == 2
            ),
            "rc": seq2[3]["rc"],
            "steps": [{"step": r["step"], "decision": r["decision"], "reason": r["reason"]} for r in seq2],
            "technical_cause": "edit_gate.py:285-299 counts code_edit rows matching tick['sha']; "
            "once streak >= STREAK_NGUONG (3), edit #4+ is blocked until plan.md sha256 changes.",
            "transcript_ref": "15919377 L3115-3123",
        })
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    return cases


def run_repro(plugin_dir: Path) -> dict:
    """Execute all 3 false-positive reproduction groups and return structured report."""
    tmp_shared = Path(tempfile.mkdtemp(prefix="tdq_fp_shared_"))
    try:
        _log(f"Running false-positive reproduction against {plugin_dir}")
        cases = []
        cases.extend(_run_search_malformed_cases(plugin_dir, tmp_shared))
        lsp_cases, controls = _run_lsp_non_lsp_cases(plugin_dir, tmp_shared)
        cases.extend(lsp_cases)
        cases.extend(_run_tick_loop_cases(plugin_dir))
    finally:
        shutil.rmtree(tmp_shared, ignore_errors=True)

    by_group = {}
    for row in cases:
        grp = by_group.setdefault(row["group"], {"total": 0, "reproduced": 0})
        grp["total"] += 1
        if row["reproduced"]:
            grp["reproduced"] += 1

    return {
        "schema": SCHEMA_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "plugin_dir": str(plugin_dir),
        "plugin_version": _read_plugin_version(plugin_dir),
        "cases": cases,
        "controls": controls,
        "summary": {
            "total_cases": len(cases),
            "reproduced_count": sum(1 for c in cases if c["reproduced"]),
            "by_group": by_group,
        },
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Reproduce TDQ hook false positives against installed tdq-workflow-agy."
    )
    parser.add_argument("--plugin-dir", default=str(DEFAULT_PLUGIN_DIR))
    parser.add_argument("--json", dest="json_out", help="Write JSON output to file.")
    args = parser.parse_args(argv)

    report = run_repro(Path(args.plugin_dir))
    for row in report["cases"]:
        mark = "REPRO" if row["reproduced"] else "CLEAR"
        print(f"[{mark}] {row['group']:16s} {row['id']:45s} -> {row['decision']}")
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
