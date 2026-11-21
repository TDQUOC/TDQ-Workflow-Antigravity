//! UserPromptSubmit hook event handler in pure Rust.

use crate::command_parser::extract_git_grants;
use crate::protocol::{HookDecision, HookPayload};
use crate::storage::{
    append_turn_row, now_iso_utc, read_sessions_role, read_tdq_state, read_turn_meta,
    reset_stop_streak, write_turn_meta,
};
use std::path::Path;

fn is_subagent_prompt(payload: &HookPayload, workspace_root: &Path, sid: &str) -> bool {
    payload
        .agent_type
        .as_deref()
        .is_some_and(|s| !s.trim().is_empty())
        || payload
            .agent_id
            .as_deref()
            .is_some_and(|s| !s.trim().is_empty())
        || read_sessions_role(workspace_root, sid).is_some()
}

fn record_turn_git_grants(payload: &HookPayload, workspace_root: &Path) {
    let has_sid = payload.session_id.is_some()
        || payload.conversation_id.is_some()
        || payload.trajectory_id.is_some();
    if !has_sid {
        return;
    }
    let sid = payload.canonical_session_id();
    if is_subagent_prompt(payload, workspace_root, &sid) {
        return;
    }
    let mut meta = read_turn_meta(workspace_root, &sid).unwrap_or_default();
    meta.turn_closed = false;
    let grants = extract_git_grants(payload.effective_prompt().unwrap_or(""));
    meta.git_grants = grants.clone();
    let _ = write_turn_meta(workspace_root, &sid, &meta);
    if !grants.is_empty() {
        append_turn_row(
            workspace_root,
            &sid,
            &serde_json::json!({
                "ts": now_iso_utc(),
                "kind": "signal",
                "event": "git_grant",
                "target": "git_grant",
                "session": sid,
                "grants": grants
            }),
        );
        if std::env::var("TDQ_LOG").as_deref() != Ok("0") {
            eprintln!(
                "[{}] tdq-dispatch: git_grant minted sid={} grants={:?}",
                now_iso_utc(),
                sid,
                grants
            );
        }
    }
}

/// Handle Antigravity UserPromptSubmit event.
pub fn handle_user_prompt_submit(payload: &HookPayload, workspace_root: &Path) -> HookDecision {
    // 1. Reset consecutive stop streak on new user prompt
    reset_stop_streak(workspace_root);

    // 2. Preserve TurnMeta schema, open turn, and extract per-turn git grants for main session
    record_turn_git_grants(payload, workspace_root);

    // 3. Inject concise guidance if in implement phase
    if let Some(state) = read_tdq_state(workspace_root) {
        if state.phase.as_deref() == Some("implement") && state.muc_gat.as_deref() != Some("off") {
            let gon = if state.work_kind.as_deref() == Some("investigate") {
                "[TDQ:GON] investigate mode: cite file:line or URL+ts per claim; write ONLY inside assigned artifact shard."
            } else {
                "[TDQ:GON] Phase implement: follow plan, TDD red-green, no out-of-scope edits."
            };
            return HookDecision::inject(gon, None);
        }
    }

    HookDecision::allow()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::storage::{
        get_runtime_dir, read_turn_meta, read_turn_rows, write_turn_meta, TurnMeta,
    };
    use std::fs;

    #[test]
    fn test_user_prompt_submit_mints_clears_and_isolates_git_grants() {
        let tmp = std::env::temp_dir().join(format!("tdq_ups_grants_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(get_runtime_dir(&tmp));

        let seed = TurnMeta {
            last_user_sig: "ui:9:t".to_string(),
            turn_closed: true,
            prompt_sha: "sha9".to_string(),
            phase_anchor: "implement".to_string(),
            mode: "subagent".to_string(),
            git_grants: vec!["clean_f".to_string()],
        };
        write_turn_meta(&tmp, "ups1", &seed).unwrap();

        let p_allow = HookPayload {
            session_id: Some("ups1".to_string()),
            user_prompt: Some("ok push lên origin đi".to_string()),
            ..Default::default()
        };
        let _ = handle_user_prompt_submit(&p_allow, &tmp);
        let m1 = read_turn_meta(&tmp, "ups1").unwrap();
        assert_eq!(m1.last_user_sig, "ui:9:t");
        assert_eq!(m1.prompt_sha, "sha9");
        assert_eq!(m1.phase_anchor, "implement");
        assert_eq!(m1.mode, "subagent");
        assert!(!m1.turn_closed);
        assert_eq!(m1.git_grants, vec!["push".to_string()]);
        let rows = read_turn_rows(&tmp, "ups1");
        assert!(rows.iter().any(|r| {
            r.get("kind").and_then(|v| v.as_str()) == Some("signal")
                && r.get("event").and_then(|v| v.as_str()) == Some("git_grant")
                && r.get("target").and_then(|v| v.as_str()) == Some("git_grant")
        }));

        let p_neg = HookPayload {
            session_id: Some("ups1".to_string()),
            user_prompt: Some("không push nhé".to_string()),
            ..Default::default()
        };
        let _ = handle_user_prompt_submit(&p_neg, &tmp);
        let m2 = read_turn_meta(&tmp, "ups1").unwrap();
        assert!(!m2.turn_closed);
        assert!(m2.git_grants.is_empty());

        let p_meta = HookPayload {
            session_id: Some("ups1".to_string()),
            user_prompt: Some("mở request update hook cho phép git push".to_string()),
            ..Default::default()
        };
        let _ = handle_user_prompt_submit(&p_meta, &tmp);
        let m3 = read_turn_meta(&tmp, "ups1").unwrap();
        assert!(m3.git_grants.is_empty());

        let p_sub = HookPayload {
            session_id: Some("sub-ups".to_string()),
            agent_type: Some("tdq-implementer".to_string()),
            user_prompt: Some("ok push lên origin đi".to_string()),
            ..Default::default()
        };
        let _ = handle_user_prompt_submit(&p_sub, &tmp);
        let sub_grants = read_turn_meta(&tmp, "sub-ups")
            .map(|m| m.git_grants)
            .unwrap_or_default();
        assert!(sub_grants.is_empty());

        let _ = fs::remove_dir_all(&tmp);
    }
}
