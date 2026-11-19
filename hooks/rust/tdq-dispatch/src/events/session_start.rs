//! SessionStart hook event handler in pure Rust (0 Python subprocesses).

use crate::protocol::{cap_markdown, GuidanceRepo, HookDecision, HookPayload};
use crate::storage::{clean_old_runtime_files, read_tdq_state};
use std::fs;
use std::path::Path;
use std::time::Duration;

/// Handle Antigravity SessionStart event with UTF-8 boundary safety.
pub fn handle_session_start(_payload: &HookPayload, workspace_root: &Path) -> HookDecision {
    let _cleaned = clean_old_runtime_files(workspace_root, Duration::from_secs(7 * 86400));
    let mut context_blocks = Vec::new();
    let san_sang_path = workspace_root.join("docs").join("tdq").join(".tdq-san-sang.json");
    if !san_sang_path.exists() {
        context_blocks.push(GuidanceRepo::format_4part_card("SETUP", "Project setup incomplete"));
    }
    if let Some(state) = read_tdq_state(workspace_root) {
        if let Some(ref req) = state.active_request {
            let phase = state.phase.as_deref().unwrap_or("idle");
            let lane = state.lane.as_deref().unwrap_or("full");
            let muc_gat = state.muc_gat.as_deref().unwrap_or("full");
            context_blocks.push(format!(
                "[TDQ:SESSION] Request: {} · Lane: {} · Phase: {} · Level: {}",
                req, lane, phase, muc_gat
            ));
            let chung_md_path = workspace_root
                .join("skills")
                .join("tdq-build")
                .join("references")
                .join("rules")
                .join("chung.md");
            if let Ok(rules_content) = fs::read_to_string(&chung_md_path) {
                let slice = cap_markdown(&rules_content, 1500);
                context_blocks.push(format!("[TDQ:GON]\n{}", slice.trim()));
            }
        }
    } else {
        context_blocks.push(GuidanceRepo::format_4part_card("INTAKE", "No active TDQ request"));
    }

    if context_blocks.is_empty() {
        HookDecision::empty_json()
    } else {
        HookDecision::inject(context_blocks.join("\n\n"), None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_start_clean_and_context() {
        let tmp = std::env::temp_dir().join(format!("tdq_session_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq"));

        let payload = HookPayload::default();
        let decision = handle_session_start(&payload, &tmp);
        let json_out = decision.to_json_string();
        assert!(json_out.contains("\"injectSteps\""));
        assert!(json_out.contains("[TDQ:SETUP]"));

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_session_start_multibyte_utf8_no_panic() {
        let tmp = std::env::temp_dir().join(format!("tdq_utf8_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let rules_dir = tmp.join("skills").join("tdq-build").join("references").join("rules");
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq"));
        let _ = fs::create_dir_all(&rules_dir);
        fs::write(
            tmp.join("docs").join("tdq").join("state.json"),
            r#"{"active_request":"req-utf8","phase":"implement","lane":"full"}"#,
        )
        .unwrap();
        // Prefixing 1 ASCII byte shifts byte 1500 inside 3-byte 'ệ'.
        let repeated = format!("x{}", "ệ".repeat(600));
        fs::write(rules_dir.join("chung.md"), &repeated).unwrap();

        let payload = HookPayload::default();
        let decision = handle_session_start(&payload, &tmp);
        let json_out = decision.to_json_string();
        assert!(json_out.contains("[TDQ:GON]"));

        let _ = fs::remove_dir_all(&tmp);
    }
}
