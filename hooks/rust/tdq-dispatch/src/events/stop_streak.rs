//! StopStreak hook event handler in pure Rust.
//! Detects and prevents infinite model stop loops.

use crate::protocol::{GuidanceRepo, HookDecision, HookPayload};
use crate::storage::record_stop_streak;
use sha2::{Digest, Sha256};
use std::path::Path;

fn get_plan_info(workspace_root: &Path) -> Option<(String, usize)> {
    let state_path = workspace_root.join("docs").join("tdq").join("state.json");
    let content = std::fs::read_to_string(&state_path).ok()?;
    let val: serde_json::Value = serde_json::from_str(&content).ok()?;
    let phase = val.get("phase").and_then(|v| v.as_str()).unwrap_or("");
    let paused = val.get("implement_pause").map(|v| !v.is_null() && v.as_str() != Some("")).unwrap_or(false);
    if phase == "implement" && !paused {
        if let Some(req) = val.get("active_request").and_then(|v| v.as_str()) {
            let plan_path = workspace_root
                .join("docs")
                .join("tdq")
                .join("plan")
                .join(format!("{}.md", req));
            if let Ok(plan_content) = std::fs::read_to_string(&plan_path) {
                let mut hasher = Sha256::new();
                hasher.update(plan_content.as_bytes());
                let sha = format!("{:x}", hasher.finalize());
                let mut open_count = 0;
                for line in plan_content.lines() {
                    let trimmed = line.trim_start();
                    if trimmed.starts_with("- [ ]") || trimmed.starts_with("- [~]") {
                        open_count += 1;
                    }
                }
                return Some((sha, open_count));
            }
        }
    }
    None
}

/// Handle Antigravity StopStreak / Stop event.
pub fn handle_stop_streak(_payload: &HookPayload, workspace_root: &Path) -> HookDecision {
    if let Some((sha, open_count)) = get_plan_info(workspace_root) {
        if open_count > 0 {
            let dem = record_stop_streak(workspace_root, &sha);
            if dem > 3 {
                let card = GuidanceRepo::format_4part_card(
                    "INTAKE",
                    &format!("Phát hiện vòng lặp dừng liên tiếp {} lần khi chưa xong việc", dem),
                );
                return HookDecision::allow()
                    .with_user_markdown(card)
                    .with_additional_context(format!(
                        "[TDQ:STUCK] {} open task(s). Finish plan or declare a genuine blocker.",
                        open_count
                    ));
            }
            return HookDecision::continue_run(format!(
                "[TDQ:UNFINISHED] {} open task(s). Keep working to the approved spec: mark [~], test, mark [x].",
                open_count
            ));
        }
    }

    HookDecision::allow()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::events::post_tool_use::handle_post_tool_use;
    use serde_json::json;
    use std::fs;

    #[test]
    fn test_post_tool_and_stop_streak() {
        let tmp = std::env::temp_dir().join(format!("tdq_post_stop_test_{}", std::process::id()));
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq"));

        // PostToolUse test
        let post_payload = HookPayload {
            session_id: Some("sid-002".to_string()),
            tool_name: Some("read_file".to_string()),
            arguments: Some(json!({ "Path": "C:/demo/file.txt" })),
            ..Default::default()
        };
        let p_res = handle_post_tool_use(&post_payload, &tmp);
        assert_eq!(p_res.decision, crate::protocol::DecisionKind::Allow);

        // StopStreak test without plan -> allow
        let stop_payload = HookPayload::default();
        let s_res = handle_stop_streak(&stop_payload, &tmp);
        assert_eq!(s_res.decision, crate::protocol::DecisionKind::Allow);

        let _ = fs::remove_dir_all(&tmp);
    }
}
