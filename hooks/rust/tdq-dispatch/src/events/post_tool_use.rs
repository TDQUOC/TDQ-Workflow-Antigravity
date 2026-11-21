//! PostToolUse hook event handler in pure Rust.
//! Logs tool usage, records read/search history to `docs/tdq/`, and stores large output in CCR.

use crate::command_parser::is_graphify_shell_query;
use crate::protocol::{HookDecision, HookPayload, NormalizedToolCall};
use crate::storage::{
    append_jsonl_record, append_turn_row, check_and_store_ccr, khoa_hien_tai, now_iso_utc,
    read_tdq_state, register_sessions_role, reset_stop_streak, search_ledger_path,
    unix_timestamp_f64,
};
use crate::RouteOutcome;
use serde_json::Value;
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

fn extract_subagent_role_arg(norm: &NormalizedToolCall, payload: &HookPayload) -> Option<String> {
    for key in ["TypeName", "subagent_type", "name", "Role", "role"] {
        if let Some(val) = norm.args.get(key).and_then(|v| v.as_str()) {
            let trimmed = val.trim();
            if !trimmed.is_empty() {
                return Some(trimmed.to_string());
            }
        }
    }
    payload
        .agent_type
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string)
}

fn extract_spawned_conversation_id(payload: &HookPayload) -> Option<String> {
    for key in ["response", "output", "tool_response"] {
        let Some(val) = payload.extra.get(key) else {
            continue;
        };
        let parsed: Option<Value> = match val {
            Value::Object(_) => Some(val.clone()),
            Value::String(s) if s.trim().starts_with('{') => serde_json::from_str(s).ok(),
            _ => None,
        };
        if let Some(obj) = parsed {
            for cand in [
                obj.get("result").and_then(|r| r.get("conversationId")),
                obj.get("conversationId"),
                obj.get("agentId"),
            ] {
                if let Some(cid) = cand.and_then(|v| v.as_str()).map(str::trim) {
                    if !cid.is_empty() {
                        return Some(cid.to_string());
                    }
                }
            }
        }
    }
    None
}

/// Hybrid PostToolUse router: captures subagent role registration and delegates subagent telemetry.
pub fn route_post_tool_use(payload: &HookPayload, workspace_root: &Path) -> RouteOutcome {
    let norm = payload.normalize_tool_call();
    if matches!(
        norm.tool_name.as_str(),
        "invoke_subagent" | "swarm" | "define_subagent" | "Task" | "Agent"
    ) {
        if let (Some(conv_id), Some(role)) = (
            extract_spawned_conversation_id(payload),
            extract_subagent_role_arg(&norm, payload),
        ) {
            register_sessions_role(workspace_root, &conv_id, &role, "");
        }
        return RouteOutcome::DelegatePython;
    }
    RouteOutcome::Decided(handle_post_tool_use(payload, workspace_root))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::storage::read_sessions_role;
    use serde_json::json;
    use std::fs;

    #[test]
    fn test_route_post_tool_use_registers_subagent_role_and_delegates() {
        let tmp = std::env::temp_dir().join(format!("tdq_post_subagent_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(&tmp);

        let payload = HookPayload::from_json_str(
            &json!({
                "tool_name": "invoke_subagent",
                "tool_input": { "TypeName": "tdq-qc-tester", "Prompt": "Audit Q1" },
                "response": { "result": { "conversationId": "conv-qc-99" } }
            })
            .to_string(),
        );
        assert_eq!(
            route_post_tool_use(&payload, &tmp),
            RouteOutcome::DelegatePython
        );
        let rec = read_sessions_role(&tmp, "conv-qc-99").expect("role registered");
        assert_eq!(rec.role, "tdq-qc-tester");

        let _ = fs::remove_dir_all(&tmp);
    }
}
