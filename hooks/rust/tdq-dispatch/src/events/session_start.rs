//! SessionStart hook event handler in pure Rust (0 Python subprocesses).

use crate::protocol::{GuidanceRepo, HookDecision, HookPayload};
use crate::storage::{clean_old_runtime_files, read_tdq_state};
use std::fs;
use std::path::Path;
use std::time::Duration;

/// Handle Antigravity SessionStart event.
pub fn handle_session_start(_payload: &HookPayload, workspace_root: &Path) -> HookDecision {
    // 1. Clean stale runtime logs older than 7 days
    let _cleaned = clean_old_runtime_files(workspace_root, Duration::from_secs(7 * 86400));

    let mut context_blocks = Vec::new();

    // 2. Check setup readiness (.tdq-san-sang.json)
    let san_sang_path = workspace_root.join("docs").join("tdq").join(".tdq-san-sang.json");
    if !san_sang_path.exists() {
        let setup_card = GuidanceRepo::format_4part_card("SETUP", "Dự án chưa chạy khởi tạo TDQ ban đầu");
        let search_card = GuidanceRepo::format_4part_card("SEARCH", "Ưu tiên tra cứu LSP/Grep trước khi sửa đổi");
        context_blocks.push(format!("{}\n\n{}", setup_card, search_card));
    }

    // 3. Inspect TDQ state
    if let Some(state) = read_tdq_state(workspace_root) {
        if let Some(ref req) = state.active_request {
            let phase = state.phase.as_deref().unwrap_or("idle");
            let lane = state.lane.as_deref().unwrap_or("full");
            let muc_gat = state.muc_gat.as_deref().unwrap_or("full");

            let banner = format!(
                "[TDQ:SESSION] Request: {} · Lane: {} · Phase: {} · Mức gắt: {}",
                req, lane, phase, muc_gat
            );
            context_blocks.push(banner);

            // Read concise rules from chung.md if available
            let chung_md_path = workspace_root
                .join("skills")
                .join("tdq-build")
                .join("references")
                .join("rules")
                .join("chung.md");

            if let Ok(rules_content) = fs::read_to_string(&chung_md_path) {
                // Extract first 1500 chars of core rules
                let slice = if rules_content.len() > 1500 {
                    &rules_content[..1500]
                } else {
                    &rules_content
                };
                context_blocks.push(format!("[TDQ:GON]\n{}", slice.trim()));
            }
        }
    } else {
        // No request open
        let intake_hint = GuidanceRepo::format_4part_card("INTAKE", "Chưa có request TDQ nào đang mở");
        context_blocks.push(intake_hint);
    }

    let decision = HookDecision::allow();
    if !context_blocks.is_empty() {
        let full_context = context_blocks.join("\n\n");
        decision.with_additional_context(full_context)
    } else {
        decision
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_start_clean_and_context() {
        let tmp = std::env::temp_dir().join(format!("tdq_session_test_{}", std::process::id()));
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq"));

        let payload = HookPayload::default();
        let decision = handle_session_start(&payload, &tmp);

        assert_eq!(decision.decision, crate::protocol::DecisionKind::Allow);
        assert!(decision.additional_context.is_some());
        let ctx = decision.additional_context.unwrap();
        assert!(ctx.contains("[TDQ:SETUP]"));

        let _ = fs::remove_dir_all(&tmp);
    }
}
