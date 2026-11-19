//! Notification hook event handler in pure Rust.

use crate::protocol::{HookDecision, HookPayload};
use crate::storage::{append_jsonl_record, get_runtime_dir};
use std::path::Path;
use std::time::SystemTime;

/// Handle Antigravity Notification event.
pub fn handle_notification(payload: &HookPayload, workspace_root: &Path) -> HookDecision {
    if let Some(ref msg) = payload.notification_message {
        let log_file = get_runtime_dir(workspace_root).join("notifications.jsonl");
        let entry = serde_json::json!({
            "timestamp": format!("{:?}", SystemTime::now()),
            "session_id": payload.session_id.as_deref().unwrap_or(""),
            "message": msg
        });
        let _ = append_jsonl_record(&log_file, &entry);
    }
    HookDecision::allow()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::events::user_prompt_submit::handle_user_prompt_submit;
    use std::fs;

    #[test]
    fn test_prompt_and_notification() {
        let tmp =
            std::env::temp_dir().join(format!("tdq_prompt_notif_test_{}", std::process::id()));
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq"));

        // Prompt submit test
        let prompt_payload = HookPayload {
            session_id: Some("sid-001".to_string()),
            user_prompt: Some("tiếp tục".to_string()),
            ..Default::default()
        };
        let p_decision = handle_user_prompt_submit(&prompt_payload, &tmp);
        assert_eq!(p_decision.decision, crate::protocol::DecisionKind::Allow);

        // Notification test
        let notif_payload = HookPayload {
            session_id: Some("sid-001".to_string()),
            notification_message: Some("Task finished".to_string()),
            ..Default::default()
        };
        let n_decision = handle_notification(&notif_payload, &tmp);
        assert_eq!(n_decision.decision, crate::protocol::DecisionKind::Allow);

        let _ = fs::remove_dir_all(&tmp);
    }
}
