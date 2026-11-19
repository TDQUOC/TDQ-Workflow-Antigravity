//! PreToolUse Hybrid Hot-path handler in pure Rust.
//! Enforces hard gates (`READONLY`, `STATE`, `GIT`, `VUNG`, `ZERO-POPUP`, `APPROVE`, `TICK`),
//! handles `start_lsp` overwrite and concept ledger writes, and delegates Cold-path edge cases.

use crate::command_parser::{
    has_banned_ai_branch, inspect_command_safety, is_shell_mutator, mutates_outside_docs,
    mutates_outside_docs_any, mutates_tdq_state, needs_python_command_gate, CommandSafetyViolation,
};
use crate::events::post_tool_use::extract_concept_label;
use crate::protocol::{GuidanceRepo, HookDecision, HookPayload, NormalizedToolCall};
use crate::storage::{
    already_reminded, append_jsonl_record, append_turn_row, cong_dang_cho,
    count_code_edits_for_sha, effective_phase, khoa_hien_tai, now_iso_utc, queue_pending_reminder,
    read_plan_tick_state, read_sessions_role, read_tdq_state, search_ledger_path,
    today_log_rel_for_state, unix_timestamp_f64, TdqState,
};
use crate::RouteOutcome;
use std::fs::{self, File};
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};

const SUBAGENT_ROLES: &[&str] = &[
    "tdq-security-reviewer",
    "tdq-reviewer",
    "tdq-qc-tester",
    "tdq-implementer",
    "tdq-build-resolver",
    "tdq-refactor-cleaner",
];

fn detect_subagent_role(payload: &HookPayload, workspace_root: &Path, sid: &str) -> Option<String> {
    if let Some(rec) = read_sessions_role(workspace_root, sid) {
        if !rec.role.trim().is_empty() {
            return Some(rec.role);
        }
    }
    if let Some(ref atype) = payload.agent_type {
        if !atype.trim().is_empty() {
            return Some(atype.trim().to_string());
        }
    }
    if let Some(ref tpath) = payload.transcript_path {
        if let Ok(file) = File::open(tpath) {
            let mut first = String::new();
            if BufReader::new(file).read_line(&mut first).is_ok() {
                if let Some(found) = SUBAGENT_ROLES.iter().find(|r| first.contains(**r)) {
                    return Some((*found).to_string());
                }
            }
        }
    }
    payload
        .agent_id
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .map(|_| "subagent".to_string())
}

fn is_readonly_role(role: &str) -> bool {
    let low = role.to_ascii_lowercase();
    low.contains("reviewer") || low.contains("qc-tester") || low.contains("browser")
}

fn deny_with_block(workspace_root: &Path, sid: &str, code: &str, detail: &str) -> RouteOutcome {
    let card = GuidanceRepo::format_4part_card(code, detail);
    let clean_code = code
        .strip_prefix("TDQ:")
        .unwrap_or(code)
        .to_ascii_uppercase();
    let row = serde_json::json!({
        "ts": now_iso_utc(),
        "kind": "block",
        "event": "block",
        "session": sid,
        "code": clean_code,
        "reason_key": detail,
        "source_event": "PreToolUse",
    });
    append_turn_row(workspace_root, sid, &row);
    RouteOutcome::Decided(HookDecision::deny(card))
}

fn queue_remind_once(workspace_root: &Path, sid: &str, code: &str, detail: &str) {
    if already_reminded(workspace_root, sid, code) {
        return;
    }
    if queue_pending_reminder(workspace_root, sid, code, detail) {
        let row = serde_json::json!({
            "ts": now_iso_utc(),
            "kind": "remind",
            "event": "remind",
            "session": sid,
            "code": code.strip_prefix("TDQ:").unwrap_or(code),
            "source_event": "PreToolUse",
        });
        append_turn_row(workspace_root, sid, &row);
    }
}

fn canonical_or_ancestor(path: &Path) -> String {
    let resolved = if let Ok(c) = fs::canonicalize(path) {
        c
    } else if let (Some(parent), Some(name)) = (path.parent(), path.file_name()) {
        fs::canonicalize(parent)
            .map(|p| p.join(name))
            .unwrap_or_else(|_| path.to_path_buf())
    } else {
        path.to_path_buf()
    };
    let s = resolved.to_string_lossy().into_owned();
    s.strip_prefix(r"\\?\").unwrap_or(&s).replace('\\', "/")
}

fn resolve_rel_in_project(raw_target: &str, workspace_root: &Path) -> Option<String> {
    let abs = if Path::new(raw_target).is_absolute() {
        PathBuf::from(raw_target)
    } else {
        workspace_root.join(raw_target)
    };
    let norm_root = canonical_or_ancestor(workspace_root);
    let trim_root = norm_root.trim_end_matches('/');
    let norm_abs = canonical_or_ancestor(&abs);
    if cfg!(windows) {
        let low_a = norm_abs.to_ascii_lowercase();
        let low_r = format!("{}/", trim_root.to_ascii_lowercase());
        if low_a.starts_with(&low_r) {
            return Some(norm_abs[low_r.len()..].to_string());
        }
    } else if let Some(rest) = norm_abs.strip_prefix(&format!("{}/", trim_root)) {
        return Some(rest.to_string());
    }
    None
}

fn is_state_target(raw_target: &str) -> bool {
    let norm = raw_target.replace('\\', "/");
    norm.ends_with("docs/tdq/state.json") || norm.ends_with("docs/tdq/STATE.md")
}

fn check_tick_gates(
    workspace_root: &Path,
    sid: &str,
    state: &TdqState,
    rel_target: &str,
    in_docs: bool,
) -> Result<Option<String>, RouteOutcome> {
    let low = rel_target.to_ascii_lowercase();
    let in_tests = low == "tests" || low.starts_with("tests/");
    let in_wt = low.contains(".tdq-worktrees/");
    if in_docs || in_tests || in_wt || !matches!(effective_phase(state), "implement" | "qc") {
        return Ok(None);
    }
    let tick = read_plan_tick_state(workspace_root, state);
    if tick.exists && tick.total > 0 && !tick.has_doing() && !tick.all_done() {
        return Err(deny_with_block(
            workspace_root,
            sid,
            "TICK",
            "No active [~] task in plan before editing code.",
        ));
    }
    if tick.exists && tick.doing_count > 1 {
        return Err(deny_with_block(
            workspace_root,
            sid,
            "TICK",
            "Multiple [~] tasks open; close old task before editing.",
        ));
    }
    if tick.exists && tick.doing_count == 1 {
        let streak = count_code_edits_for_sha(workspace_root, sid, &tick.sha);
        if streak >= 8 {
            return Err(deny_with_block(
                workspace_root,
                sid,
                "TICK",
                &format!("{} consecutive edits without plan update.", streak),
            ));
        }
        if (4..8).contains(&streak) {
            queue_remind_once(
                workspace_root,
                sid,
                "TICK",
                &format!("{}/8 source edits without plan tick.", streak),
            );
        }
        return Ok(Some(tick.sha));
    }
    Ok(None)
}

fn record_edit_observations(
    workspace_root: &Path,
    sid: &str,
    state: &TdqState,
    rel_target: &str,
    in_docs: bool,
    code_edit_sha: Option<String>,
) {
    append_turn_row(
        workspace_root,
        sid,
        &serde_json::json!({
            "ts": now_iso_utc(), "kind": "observe", "event": "edit", "session": sid, "path": rel_target,
        }),
    );
    let today_log = today_log_rel_for_state(Some(state));
    if rel_target == today_log {
        append_turn_row(
            workspace_root,
            sid,
            &serde_json::json!({
                "ts": now_iso_utc(), "kind": "observe", "event": "log_written", "session": sid, "path": rel_target,
            }),
        );
    } else if !in_docs && !workspace_root.join(&today_log).is_file() {
        queue_remind_once(
            workspace_root,
            sid,
            "LOG",
            &format!("Changed {} without {}", rel_target, today_log),
        );
    }
    if let Some(sha) = code_edit_sha {
        append_turn_row(
            workspace_root,
            sid,
            &serde_json::json!({
                "ts": now_iso_utc(), "kind": "observe", "event": "code_edit", "session": sid, "path": rel_target, "plan_sha": sha,
            }),
        );
    }
}

fn handle_edit_tool(
    workspace_root: &Path,
    norm: &NormalizedToolCall,
    sid: &str,
    role_opt: Option<&str>,
) -> RouteOutcome {
    let Some(raw_target) = norm.target_path() else {
        return RouteOutcome::Decided(HookDecision::allow());
    };
    if let Some(role) = role_opt.filter(|r| is_readonly_role(r)) {
        return deny_with_block(
            workspace_root,
            sid,
            "READONLY",
            &format!("Read-only role `{}` cannot edit.", role),
        );
    }
    if is_state_target(raw_target) {
        return deny_with_block(
            workspace_root,
            sid,
            "STATE",
            "Direct edit of TDQ state is prohibited; use tdq_state.py.",
        );
    }
    let Some(rel_target) = resolve_rel_in_project(raw_target, workspace_root) else {
        return RouteOutcome::DelegatePython;
    };
    let Some(state) = read_tdq_state(workspace_root) else {
        append_turn_row(
            workspace_root,
            sid,
            &serde_json::json!({
                "ts": now_iso_utc(), "kind": "observe", "event": "edit", "session": sid, "path": rel_target,
            }),
        );
        return RouteOutcome::Decided(HookDecision::allow());
    };
    if state
        .active_request
        .as_deref()
        .unwrap_or("")
        .trim()
        .is_empty()
    {
        return RouteOutcome::Decided(HookDecision::allow());
    }
    if role_opt.is_some() || state.implement_mode.as_deref() == Some("subagent") {
        return RouteOutcome::DelegatePython;
    }
    let low_rel = rel_target.to_ascii_lowercase();
    let in_docs = low_rel == "docs" || low_rel.starts_with("docs/");
    if !in_docs {
        if let Some(gate) = cong_dang_cho(&state) {
            return deny_with_block(
                workspace_root,
                sid,
                "APPROVE",
                &format!("{} approval pending before editing source.", gate),
            );
        }
    }
    match check_tick_gates(workspace_root, sid, &state, &rel_target, in_docs) {
        Err(deny_outcome) => deny_outcome,
        Ok(code_sha) => {
            record_edit_observations(workspace_root, sid, &state, &rel_target, in_docs, code_sha);
            RouteOutcome::Decided(HookDecision::allow())
        }
    }
}

fn handle_command_tool(
    payload: &HookPayload,
    workspace_root: &Path,
    sid: &str,
    role_opt: Option<&str>,
) -> RouteOutcome {
    let Some(cmd) = payload.get_command() else {
        return RouteOutcome::Decided(HookDecision::allow());
    };
    if let Some(role) = role_opt.filter(|r| is_readonly_role(r)) {
        if is_shell_mutator(&cmd) {
            return deny_with_block(
                workspace_root,
                sid,
                "READONLY",
                &format!("Read-only subagent `{}` cannot mutate via shell.", role),
            );
        }
    }
    if mutates_tdq_state(&cmd) {
        return deny_with_block(
            workspace_root,
            sid,
            "STATE",
            "Do not mutate TDQ state via shell; use tdq_state.py.",
        );
    }
    if let Some(violation) = inspect_command_safety(&cmd) {
        let (code, msg) = match violation {
            CommandSafetyViolation::GitPushForbidden => {
                ("GIT", "git push is forbidden unless explicitly asked.")
            }
            CommandSafetyViolation::GitDestructiveReset => {
                ("GIT", "Destructive git reset/clean is prohibited.")
            }
            CommandSafetyViolation::CoAuthoredTrailer => {
                ("GIT", "AI co-author trailers are banned in commits.")
            }
            CommandSafetyViolation::RemoteScriptExecution => {
                ("VUNG", "Piping remote downloads to shell is forbidden.")
            }
            CommandSafetyViolation::ExecutionPolicyBypass => {
                ("VUNG", "PowerShell ExecutionPolicy bypass is blocked.")
            }
        };
        return deny_with_block(workspace_root, sid, code, msg);
    }
    if let Some(bad_branch) = has_banned_ai_branch(&cmd) {
        return deny_with_block(
            workspace_root,
            sid,
            "GIT",
            &format!("AI-prefixed branch `{}` is banned.", bad_branch),
        );
    }
    if let Some(state) = read_tdq_state(workspace_root) {
        if !state
            .active_request
            .as_deref()
            .unwrap_or("")
            .trim()
            .is_empty()
        {
            if role_opt.is_some()
                && !matches!(effective_phase(&state), "implement" | "qc")
                && mutates_outside_docs(&cmd)
            {
                return RouteOutcome::DelegatePython;
            }
            if role_opt.is_none() && mutates_outside_docs_any(&cmd) {
                if let Some(gate) = cong_dang_cho(&state) {
                    return deny_with_block(
                        workspace_root,
                        sid,
                        "APPROVE",
                        &format!("{} has no recorded approval for shell write.", gate),
                    );
                }
            }
        }
    }
    if needs_python_command_gate(&cmd) {
        return RouteOutcome::DelegatePython;
    }
    RouteOutcome::Decided(HookDecision::allow())
}

fn handle_read_tool(norm: &NormalizedToolCall, workspace_root: &Path) -> RouteOutcome {
    let has_range = ["StartLine", "EndLine", "offset", "limit", "ByteOffset"]
        .iter()
        .any(|k| norm.args.get(*k).is_some_and(|v| !v.is_null()));
    if has_range {
        return RouteOutcome::Decided(HookDecision::allow());
    }
    if let Some(raw_target) = norm.target_path() {
        let p = Path::new(raw_target);
        let full = if p.is_absolute() {
            p.to_path_buf()
        } else {
            workspace_root.join(p)
        };
        if fs::metadata(full).map(|m| m.len() <= 2048).unwrap_or(false) {
            return RouteOutcome::Decided(HookDecision::allow());
        }
    }
    RouteOutcome::DelegatePython
}

fn detect_unique_language_o1(dir: &Path) -> Option<&'static str> {
    let mut langs: Vec<&'static str> = Vec::new();
    if dir.join("Cargo.toml").is_file() {
        langs.push("rust");
    }
    if ["pyproject.toml", "requirements.txt", "Pipfile", "setup.py"]
        .iter()
        .any(|f| dir.join(f).is_file())
    {
        langs.push("python");
    }
    if ["tsconfig.json", "package.json", "jsconfig.json"]
        .iter()
        .any(|f| dir.join(f).is_file())
    {
        langs.push("typescript");
    }
    if dir.join("go.mod").is_file() {
        langs.push("go");
    }
    if langs.len() == 1 {
        Some(langs[0])
    } else {
        None
    }
}

fn handle_mcp_tool(workspace_root: &Path, norm: &NormalizedToolCall, sid: &str) -> RouteOutcome {
    let op = norm
        .tool_name
        .rsplit_once("__")
        .map(|(_, r)| r)
        .unwrap_or(&norm.tool_name);
    let op = op.rsplit_once('.').map(|(_, r)| r).unwrap_or(op);
    if op == "blast_radius" {
        return RouteOutcome::DelegatePython;
    }
    if op == "start_lsp" {
        let lang = norm
            .args
            .get("language_id")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim();
        let goc = norm
            .args
            .get("root_dir")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim();
        if lang.is_empty() {
            let root = if goc.is_empty() {
                workspace_root.to_path_buf()
            } else {
                PathBuf::from(goc)
            };
            if let Some(det) = detect_unique_language_o1(&root) {
                let mut patch = serde_json::json!({ "language_id": det });
                if goc.is_empty() {
                    patch["root_dir"] =
                        serde_json::Value::String(workspace_root.to_string_lossy().into_owned());
                }
                return RouteOutcome::Decided(
                    HookDecision::allow().with_overwrite(norm.wrap_overwrite(patch)),
                );
            }
            return RouteOutcome::DelegatePython;
        }
        return RouteOutcome::Decided(HookDecision::allow());
    }
    if let Some(label) = extract_concept_label(norm, None) {
        let state = read_tdq_state(workspace_root);
        let khoa = khoa_hien_tai(state.as_ref(), sid);
        let _ = append_jsonl_record(
            &search_ledger_path(workspace_root),
            &serde_json::json!({
                "ts": unix_timestamp_f64(), "khoa": khoa, "loai": "khai_niem", "cong_cu": label, "su_kien": "PreToolUse",
            }),
        );
        append_turn_row(
            workspace_root,
            sid,
            &serde_json::json!({
                "ts": now_iso_utc(), "kind": "observe", "event": "search_grace", "type": "search_grace", "state": "reset", "session": sid, "tool": norm.tool_name,
            }),
        );
    }
    RouteOutcome::Decided(HookDecision::allow())
}

/// Handle Antigravity PreToolUse event across Hot-path Rust and Cold-path Python.
pub fn handle_pre_tool_use(payload: &HookPayload, workspace_root: &Path) -> RouteOutcome {
    let sid = payload.canonical_session_id();
    let norm = payload.normalize_tool_call();
    let tname = norm.tool_name.as_str();
    let role_opt = detect_subagent_role(payload, workspace_root, &sid);

    if matches!(
        tname,
        "ask_question" | "ask_user_question" | "AskUserQuestion"
    ) {
        return deny_with_block(
            workspace_root,
            &sid,
            "ZERO-POPUP",
            "Ask numbered choices in chat; popup UI is blocked.",
        );
    }
    if matches!(
        tname,
        "edit_file"
            | "write_to_file"
            | "write_file"
            | "replace_file_content"
            | "multi_replace_file_content"
            | "notebook_edit"
            | "Edit"
            | "Write"
            | "MultiEdit"
            | "NotebookEdit"
    ) {
        return handle_edit_tool(workspace_root, &norm, &sid, role_opt.as_deref());
    }
    if matches!(tname, "run_command" | "Bash" | "PowerShell") {
        return handle_command_tool(payload, workspace_root, &sid, role_opt.as_deref());
    }
    if matches!(tname, "read_file" | "view_file" | "Read") {
        return handle_read_tool(&norm, workspace_root);
    }
    if matches!(tname, "grep_search" | "search_directory" | "Grep") {
        return RouteOutcome::DelegatePython;
    }
    if matches!(
        tname,
        "invoke_subagent" | "swarm" | "define_subagent" | "Task" | "Agent"
    ) {
        return RouteOutcome::DelegatePython;
    }
    if norm.is_mcp_wrapper || tname.starts_with("mcp_") || tname.starts_with("lsp.") {
        return handle_mcp_tool(workspace_root, &norm, &sid);
    }
    RouteOutcome::Decided(HookDecision::allow())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::protocol::DecisionKind;
    use serde_json::json;

    #[test]
    fn test_pre_tool_use_security_and_hardening_gates() {
        let tmp = std::env::temp_dir().join(format!("tdq_pre_tool_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq").join("plan"));
        fs::write(tmp.join("Cargo.toml"), "[package]\nname=\"demo\"").unwrap();

        let git_push = HookPayload {
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "git push origin dev" })),
            ..Default::default()
        };
        assert!(
            matches!(handle_pre_tool_use(&git_push, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:GIT]"))
        );

        let qc_write = HookPayload {
            agent_type: Some("tdq-qc-tester".to_string()),
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "Set-Content app.py bad" })),
            ..Default::default()
        };
        assert!(
            matches!(handle_pre_tool_use(&qc_write, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]"))
        );

        let state_edit = HookPayload {
            tool_name: Some("write_to_file".to_string()),
            tool_input: Some(
                json!({ "TargetFile": tmp.join("docs/tdq/state.json").to_string_lossy() }),
            ),
            ..Default::default()
        };
        assert!(
            matches!(handle_pre_tool_use(&state_edit, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:STATE]"))
        );

        // TICK 0 [~] hard deny on edit
        fs::write(tmp.join("docs/tdq/state.json"), r#"{"active_request":"r1","phase":"implement","lane":"full","spec_approved":true,"plan_approved":true,"plan_file":"docs/tdq/plan/r1.md"}"#).unwrap();
        fs::write(tmp.join("docs/tdq/plan/r1.md"), "- [ ] **T1** open\n").unwrap();
        let tick0 = HookPayload {
            tool_name: Some("edit_file".to_string()),
            tool_input: Some(json!({ "TargetFile": tmp.join("src.py").to_string_lossy() })),
            ..Default::default()
        };
        assert!(
            matches!(handle_pre_tool_use(&tick0, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:TICK]"))
        );

        // call_mcp_tool start_lsp overwrite preserving string Arguments
        let mcp_lsp = HookPayload {
            tool_name: Some("call_mcp_tool".to_string()),
            tool_input: Some(
                json!({ "ServerName": "lsp", "ToolName": "start_lsp", "Arguments": json!({"root_dir": tmp.to_string_lossy()}).to_string() }),
            ),
            ..Default::default()
        };
        match handle_pre_tool_use(&mcp_lsp, &tmp) {
            RouteOutcome::Decided(d) => {
                let ov = d.overwrite.unwrap();
                assert!(ov["Arguments"].as_str().unwrap_or("").contains("rust"));
            }
            RouteOutcome::DelegatePython => panic!("expected rust overwrite"),
        }

        let _ = fs::remove_dir_all(&tmp);
    }
}
