//! UserPromptSubmit hook event handler in pure Rust.

use crate::protocol::{HookDecision, HookPayload};
use crate::storage::{atomic_write_file, get_runtime_dir, read_tdq_state, reset_stop_streak};
use std::path::Path;
use std::time::SystemTime;

/// Handle Antigravity UserPromptSubmit event.
pub fn handle_user_prompt_submit(payload: &HookPayload, workspace_root: &Path) -> HookDecision {
    // 1. Reset consecutive stop streak on new user prompt
    reset_stop_streak(workspace_root);

    // 2. Track prompt turn timestamp
    if let Some(ref sid) = payload.session_id {
        let meta_file = get_runtime_dir(workspace_root).join(format!("turn-meta-{}.json", sid));
        let meta_data = serde_json::json!({
            "last_prompt_at": format!("{:?}", SystemTime::now()),
            "user_prompt": payload.user_prompt.as_deref().unwrap_or("")
        });
        if let Ok(bytes) = serde_json::to_vec(&meta_data) {
            let _ = atomic_write_file(&meta_file, &bytes);
        }
    }

    // 3. Inject concise guidance if in implement phase
    let mut decision = HookDecision::allow();
    if let Some(state) = read_tdq_state(workspace_root) {
        if state.phase.as_deref() == Some("implement") && state.muc_gat.as_deref() != Some("off") {
            decision = decision.with_additional_context(
                "[TDQ:GON] Phase implement: bám sát plan, TDD đỏ-xanh, không code ngoài task."
            );
        }
    }

    decision
}
