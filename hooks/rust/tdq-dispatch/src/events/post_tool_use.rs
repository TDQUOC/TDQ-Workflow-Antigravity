//! PostToolUse hook event handler in pure Rust.
//! Logs tool usage, records read/search history, and stores large output in CCR store.

use crate::protocol::{HookDecision, HookPayload};
use crate::storage::{
    append_jsonl_record, check_and_store_ccr, get_runtime_dir, reset_stop_streak,
};
use std::path::Path;
use std::time::SystemTime;

/// Handle Antigravity PostToolUse event.
pub fn handle_post_tool_use(payload: &HookPayload, workspace_root: &Path) -> HookDecision {
    // 1. Reset stop streak on tool use
    reset_stop_streak(workspace_root);

    let tool_name = payload.tool_name.as_deref().unwrap_or("");
    let runtime_dir = get_runtime_dir(workspace_root);

    // 2. Track tool turn history in turns-<sid>.jsonl
    if let Some(ref sid) = payload.session_id {
        let turn_log = runtime_dir.join(format!("turns-{}.jsonl", sid));
        let record = serde_json::json!({
            "timestamp": format!("{:?}", SystemTime::now()),
            "tool": tool_name,
            "session_id": sid,
        });
        let _ = append_jsonl_record(&turn_log, &record);
    }

    // 3. Track search / read logs
    if tool_name == "read_file" {
        if let Some(ref args) = payload.arguments {
            if let Some(path_str) = args.get("Path").and_then(|v| v.as_str()) {
                let read_log = runtime_dir.join(".tdq-read.jsonl");
                let rec = serde_json::json!({
                    "timestamp": format!("{:?}", SystemTime::now()),
                    "path": path_str,
                });
                let _ = append_jsonl_record(&read_log, &rec);
            }
        }
    } else if tool_name == "search_web"
        || tool_name.contains("grep")
        || tool_name.contains("find")
        || tool_name.contains("lsp")
    {
        let search_log = runtime_dir.join(".tdq-search.jsonl");
        let rec = serde_json::json!({
            "timestamp": format!("{:?}", SystemTime::now()),
            "tool": tool_name,
        });
        let _ = append_jsonl_record(&search_log, &rec);
    }

    // 4. Check for massive tool outputs to store in CCR cache (>32KB or >=200 lines)
    let mut decision = HookDecision::allow();
    if let Some(ref extra) = payload.extra.get("response").or_else(|| payload.extra.get("output")) {
        if let Some(text) = extra.as_str() {
            if let Some(marker) = check_and_store_ccr(text, workspace_root) {
                decision = decision.with_additional_context(format!(
                    "Large tool output preserved in CCR store: {}",
                    marker
                ));
            }
        }
    }

    decision
}
