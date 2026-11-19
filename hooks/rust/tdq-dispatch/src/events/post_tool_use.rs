//! PostToolUse hook event handler in pure Rust.
//! Logs tool usage, records read/search history to `docs/tdq/`, and stores large output in CCR.

use crate::command_parser::is_graphify_shell_query;
use crate::protocol::{HookDecision, HookPayload, NormalizedToolCall};
use crate::storage::{
    append_jsonl_record, append_turn_row, check_and_store_ccr, khoa_hien_tai, now_iso_utc,
    read_ledger_path, read_tdq_state, reset_stop_streak, search_ledger_path, unix_timestamp_f64,
};
use std::path::Path;

fn is_lsp_concept_op(op: &str) -> bool {
    matches!(
        op,
        "find_symbol"
            | "find_references"
            | "find_callers"
            | "go_to_definition"
            | "go_to_declaration"
            | "go_to_implementation"
            | "go_to_type_definition"
            | "inspect_symbol"
            | "explore"
            | "explore_symbol"
            | "list_symbols"
            | "blast_radius"
            | "type_hierarchy"
            | "get_cross_repo_references"
            | "get_document_highlights"
            | "get_symbol_documentation"
            | "get_symbol_source"
            | "get_tests_for_file"
    )
}

pub(crate) fn extract_concept_label(
    norm: &NormalizedToolCall,
    raw_cmd: Option<&str>,
) -> Option<String> {
    let t = norm.tool_name.as_str();
    let srv = norm.server_name.as_deref().unwrap_or("");
    if srv.ends_with("lsp") || t.contains("lsp") {
        let op = t.rsplit_once("__").map(|(_, r)| r).unwrap_or(t);
        let op = op.rsplit_once('.').map(|(_, r)| r).unwrap_or(op);
        if is_lsp_concept_op(op) {
            return Some(format!("lsp:{}", op));
        }
    }
    if srv.contains("graphify")
        || srv.contains("txtai")
        || t.contains("graphify")
        || t.contains("txtai")
    {
        return Some(format!("graphify:{}", t));
    }
    if matches!(t, "run_command" | "Bash" | "PowerShell") {
        if let Some(cmd) = raw_cmd {
            return is_graphify_shell_query(cmd);
        }
    }
    None
}

/// Handle Antigravity PostToolUse event cleanly, returning `{}`.
pub fn handle_post_tool_use(payload: &HookPayload, workspace_root: &Path) -> HookDecision {
    reset_stop_streak(workspace_root);
    let sid = payload.canonical_session_id();
    let norm = payload.normalize_tool_call();
    let cmd_opt = payload.get_command();
    let state = read_tdq_state(workspace_root);
    let khoa = khoa_hien_tai(state.as_ref(), &sid);

    if matches!(norm.tool_name.as_str(), "read_file" | "view_file" | "Read") {
        if let Some(target) = norm.target_path() {
            let rec = serde_json::json!({
                "ts": unix_timestamp_f64(),
                "khoa": khoa,
                "path": target.replace('\\', "/"),
            });
            let _ = append_jsonl_record(&read_ledger_path(workspace_root), &rec);
        }
    }
    if let Some(label) = extract_concept_label(&norm, cmd_opt.as_deref()) {
        let rec = serde_json::json!({
            "ts": unix_timestamp_f64(),
            "khoa": khoa,
            "loai": "khai_niem",
            "cong_cu": label,
            "su_kien": "PostToolUse",
        });
        let _ = append_jsonl_record(&search_ledger_path(workspace_root), &rec);
        let reset_row = serde_json::json!({
            "ts": now_iso_utc(),
            "kind": "observe",
            "event": "search_grace",
            "type": "search_grace",
            "state": "reset",
            "session": sid,
            "tool": norm.tool_name,
        });
        append_turn_row(workspace_root, &sid, &reset_row);
    }
    if let Some(extra) = payload
        .extra
        .get("response")
        .or_else(|| payload.extra.get("output"))
    {
        if let Some(text) = extra.as_str() {
            let _ = check_and_store_ccr(text, workspace_root);
        }
    }
    HookDecision::empty_json()
}
