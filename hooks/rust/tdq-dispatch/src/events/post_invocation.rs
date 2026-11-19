//! PostInvocation hook event handler in pure Rust (0 Python subprocesses).
//! Pops queued PreToolUse/Stop reminders and flushes compact dual-channel output.

use crate::protocol::{GuidanceRepo, HookDecision, HookPayload};
use crate::storage::{pending_reminders_path, pop_pending_reminders};
use std::fs;
use std::path::Path;

/// Flush queued reminders for `conversationId`, returning `{}` when queue is absent/empty.
pub fn handle_post_invocation(payload: &HookPayload, workspace_root: &Path) -> HookDecision {
    let sid = payload.canonical_session_id();
    let qpath = pending_reminders_path(workspace_root, &sid);
    let is_non_empty = fs::metadata(&qpath).map(|m| m.len() > 0).unwrap_or(false);
    if !is_non_empty {
        return HookDecision::empty_json();
    }
    let items = pop_pending_reminders(workspace_root, &sid);
    if items.is_empty() {
        return HookDecision::empty_json();
    }
    let (model_text, user_md) = GuidanceRepo::merge_pending_channels(&items);
    let card_opt = if user_md.trim().is_empty() {
        None
    } else {
        Some(user_md)
    };
    HookDecision::inject(model_text, card_opt)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::storage::queue_pending_reminder;

    #[test]
    fn test_post_invocation_empty_and_flush() {
        let tmp = std::env::temp_dir().join(format!("tdq_post_inv_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq"));
        let payload = HookPayload {
            conversation_id: Some("conv-pi".to_string()),
            ..Default::default()
        };

        let empty = handle_post_invocation(&payload, &tmp);
        assert_eq!(empty.to_json_string(), "{}");

        assert!(queue_pending_reminder(&tmp, "conv-pi", "TICK", "5 edits"));
        let flushed = handle_post_invocation(&payload, &tmp);
        let out = flushed.to_json_string();
        assert!(out.contains("\"injectSteps\""));
        assert!(out.contains("\"user_markdown\""));
        assert!(out.contains("TDQ:TICK"));
        assert_eq!(
            handle_post_invocation(&payload, &tmp).to_json_string(),
            "{}"
        );

        let _ = fs::remove_dir_all(&tmp);
    }
}
