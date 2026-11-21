//! StopStreak / Stop Hybrid Router in pure Rust.
//! Closes turns and allows immediately when idle/terminal/no-request;
//! delegates active open-request stops to Python `stop_gate.py`.

use crate::protocol::{GuidanceRepo, HookDecision, HookPayload};
use crate::storage::{
    effective_phase, mark_turn_closed, read_plan_tick_state, read_tdq_state, record_stop_streak,
};
use crate::RouteOutcome;
use std::path::Path;

const TERMINAL_STOP_REASONS: &[&str] = &[
    "USER_CANCELED",
    "CANCELLED",
    "CANCELED",
    "ABORTED",
    "TIMEOUT",
    "ERROR",
    "INTERRUPTED",
];

fn is_terminal_stop(payload: &HookPayload) -> bool {
    let reason = payload.termination_reason.as_deref().unwrap_or("");
    TERMINAL_STOP_REASONS
        .iter()
        .any(|r| r.eq_ignore_ascii_case(reason))
}

/// Evaluate pure-Rust Stop plan streak (also used by unit checks).
pub fn evaluate_open_plan_stop(workspace_root: &Path) -> HookDecision {
    let Some(state) = read_tdq_state(workspace_root) else {
        return HookDecision::allow();
    };
    let paused = state
        .implement_pause
        .as_ref()
        .map(|v| !v.is_null() && v.as_str() != Some(""))
        .unwrap_or(false);
    if effective_phase(&state) != "implement" || paused {
        return HookDecision::allow();
    }
    let tick = read_plan_tick_state(workspace_root, &state);
    let open_count = tick.total.saturating_sub(tick.done_count);
    if !tick.exists || open_count == 0 || tick.dispatched_count > 0 {
        return HookDecision::allow();
    }
    let dem = record_stop_streak(workspace_root, &tick.sha);
    if dem > 2 {
        return HookDecision::allow();
    }
    let card = GuidanceRepo::format_4part_card(
        "UNFINISHED",
        &format!(
            "{} open task(s) remain in active implement plan.",
            open_count
        ),
    );
    HookDecision::continue_run(card)
}

/// Hybrid Stop entrypoint: routes subagents to Python SubagentStop; allows terminal/idle leader.
pub fn handle_stop_streak(payload: &HookPayload, workspace_root: &Path) -> RouteOutcome {
    let sid = payload.canonical_session_id();
    if is_terminal_stop(payload) {
        mark_turn_closed(workspace_root, &sid);
        return RouteOutcome::Decided(HookDecision::allow());
    }
    if crate::events::pre_tool_use::detect_subagent_role(payload, workspace_root, &sid).is_some()
        || workspace_root.to_string_lossy().contains(".tdq-worktrees")
    {
        return RouteOutcome::DelegatePython;
    }
    let state = read_tdq_state(workspace_root);
    let active_req = state
        .as_ref()
        .and_then(|s| s.active_request.as_deref())
        .map(str::trim)
        .unwrap_or("");
    let phase = state.as_ref().map(effective_phase).unwrap_or("idle");
    if active_req.is_empty() || phase == "idle" {
        mark_turn_closed(workspace_root, &sid);
        return RouteOutcome::Decided(HookDecision::allow());
    }
    RouteOutcome::DelegatePython
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::events::post_tool_use::handle_post_tool_use;
    use crate::protocol::DecisionKind;
    use serde_json::json;
    use std::fs;

    #[test]
    fn test_post_tool_and_stop_hybrid_routes() {
        let tmp = std::env::temp_dir().join(format!("tdq_post_stop_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq").join("plan"));

        let post_payload = HookPayload {
            conversation_id: Some("sid-002".to_string()),
            tool_name: Some("read_file".to_string()),
            arguments: Some(json!({ "Path": "C:/demo/file.txt" })),
            ..Default::default()
        };
        let p_res = handle_post_tool_use(&post_payload, &tmp);
        assert_eq!(p_res.to_json_string(), "{}");
        assert!(
            !tmp.join("docs").join("tdq").join(".tdq-read.jsonl").is_file(),
            "PostToolUse(read_file) must not write obsolete .tdq-read.jsonl schema"
        );
        let lsp_post = HookPayload {
            conversation_id: Some("sid-002".to_string()),
            tool_name: Some("mcp__lsp__find_symbol".to_string()),
            arguments: Some(json!({ "query": "handle_pre_tool_use" })),
            ..Default::default()
        };
        assert_eq!(handle_post_tool_use(&lsp_post, &tmp).to_json_string(), "{}");
        assert!(tmp
            .join("docs")
            .join("tdq")
            .join(".tdq-search.jsonl")
            .is_file());

        let stop_idle = HookPayload {
            conversation_id: Some("sid-002".to_string()),
            ..Default::default()
        };
        assert!(
            matches!(handle_stop_streak(&stop_idle, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Allow)
        );

        fs::write(
            tmp.join("docs").join("tdq").join("state.json"),
            r#"{"active_request":"req1","phase":"implement","lane":"full","plan_file":"docs/tdq/plan/req1.md"}"#,
        )
        .unwrap();
        fs::write(
            tmp.join("docs").join("tdq").join("plan").join("req1.md"),
            "- [>] **T1.1** delegated — Test: `x`\n- [ ] **T1.2** todo — Test: `x`\n",
        )
        .unwrap();
        assert!(matches!(
            handle_stop_streak(&stop_idle, &tmp),
            RouteOutcome::DelegatePython
        ));
        // Dispatched `[>]` task counts as active progress and does not UNFINISHED-block
        assert_eq!(evaluate_open_plan_stop(&tmp).decision, DecisionKind::Allow);

        // Active without `[>]`: streak 1, 2 -> Continue ("UNFINISHED"), streak 3 -> Allow
        fs::write(
            tmp.join("docs").join("tdq").join("plan").join("req1.md"),
            "- [~] **T1.1** active — Test: `x`\n- [ ] **T1.2** todo — Test: `x`\n",
        )
        .unwrap();
        let d1 = evaluate_open_plan_stop(&tmp);
        assert_eq!(d1.decision, DecisionKind::Continue);
        assert!(d1.reason.unwrap_or_default().contains("UNFINISHED"));
        assert_eq!(
            evaluate_open_plan_stop(&tmp).decision,
            DecisionKind::Continue
        );
        assert_eq!(evaluate_open_plan_stop(&tmp).decision, DecisionKind::Allow);

        let sub_stop = HookPayload {
            conversation_id: Some("sub-001".to_string()),
            agent_type: Some("tdq-implementer".to_string()),
            ..Default::default()
        };
        assert!(matches!(
            handle_stop_streak(&sub_stop, &tmp),
            RouteOutcome::DelegatePython
        ));

        let _ = fs::remove_dir_all(&tmp);
    }
}
