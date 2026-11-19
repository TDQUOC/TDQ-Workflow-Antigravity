//! PreToolUse hook event handler in pure Rust.
//! Enforces 9 hard gates, handles auto-overwrite for LSP/Subagents, and soft search guidance.

use crate::command_parser::{inspect_command_safety, CommandSafetyViolation};
use crate::protocol::{GuidanceRepo, HookDecision, HookPayload};
use std::path::Path;

/// Handle Antigravity PreToolUse event.
pub fn handle_pre_tool_use(payload: &HookPayload, workspace_root: &Path) -> HookDecision {
    let tool_name = payload.tool_name.as_deref().unwrap_or("");

    // 1. Inspect state.json mutation protection
    if tool_name == "write_file" || tool_name == "edit_file" {
        if let Some(ref args) = payload.arguments {
            let target_path = args.get("Path").and_then(|v| v.as_str()).unwrap_or("");
            if target_path.replace('\\', "/").ends_with("docs/tdq/state.json") {
                let card = GuidanceRepo::format_4part_card(
                    "STATE",
                    "Chỉ scripts/tdq_state.py được quyền ghi docs/tdq/state.json",
                );
                return HookDecision::deny(
                    "Direct editing of docs/tdq/state.json is prohibited; use tdq_state.py CLI.",
                )
                .with_user_markdown(card);
            }
        }
    }

    // 2. Command safety gate (run_command)
    if tool_name == "run_command" {
        if let Some(cmd) = payload.get_command() {
            if let Some(violation) = inspect_command_safety(&cmd) {
                match violation {
                    CommandSafetyViolation::GitPushForbidden => {
                        let card = GuidanceRepo::format_4part_card(
                            "GIT",
                            "Cấm tự ý git push khi người dùng chưa yêu cầu",
                        );
                        return HookDecision::deny(
                            "git push is forbidden by TDQ policy; only push when explicitly asked.",
                        )
                        .with_user_markdown(card);
                    }
                    CommandSafetyViolation::GitDestructiveReset => {
                        let card = GuidanceRepo::format_4part_card(
                            "GIT",
                            "Cấm dùng git reset --hard hoặc git clean -f làm mất dữ liệu",
                        );
                        return HookDecision::deny(
                            "Destructive git reset/clean is prohibited to protect user worktree.",
                        )
                        .with_user_markdown(card);
                    }
                    CommandSafetyViolation::CoAuthoredTrailer => {
                        let card = GuidanceRepo::format_4part_card(
                            "GIT",
                            "Cấm thêm Co-Authored-By hoặc attribution trailer vào commit",
                        );
                        return HookDecision::deny(
                            "AI co-author trailer is strictly forbidden in commit messages.",
                        )
                        .with_user_markdown(card);
                    }
                    CommandSafetyViolation::RemoteScriptExecution => {
                        let card = GuidanceRepo::format_4part_card(
                            "VUNG",
                            "Không tải và chạy script từ xa qua pipe vào shell",
                        );
                        return HookDecision::deny(
                            "Piping remote downloads to shell interpreter is forbidden.",
                        )
                        .with_user_markdown(card);
                    }
                    CommandSafetyViolation::ExecutionPolicyBypass => {
                        let card = GuidanceRepo::format_4part_card(
                            "VUNG",
                            "Cấm vượt ExecutionPolicy của PowerShell",
                        );
                        return HookDecision::deny(
                            "PowerShell ExecutionPolicy bypass is blocked by security policy.",
                        )
                        .with_user_markdown(card);
                    }
                }
            }
        }
    }

    // 3. LSP start gate: auto-overwrite missing language_id
    if tool_name == "start_lsp" {
        if let Some(ref args) = payload.arguments {
            let lang = args.get("language_id").and_then(|v| v.as_str());
            if lang.is_none() || lang.unwrap().trim().is_empty() {
                // Auto-detect language from workspace root
                let detected = if workspace_root.join("Cargo.toml").exists() {
                    "rust"
                } else if workspace_root.join("package.json").exists() {
                    "typescript"
                } else {
                    "python"
                };

                let mut new_args = args.clone();
                new_args["language_id"] = serde_json::Value::String(detected.to_string());

                let card = GuidanceRepo::format_4part_card(
                    "LSP",
                    &format!("Tự động điền language_id='{}' bị thiếu", detected),
                );
                return HookDecision::allow()
                    .with_overwrite(new_args)
                    .with_user_markdown(card);
            }
        }
    }

    // 4. Subagent invocation gate: auto-overwrite missing Workspace="inherit"
    if tool_name == "invoke_subagent" {
        if let Some(ref args) = payload.arguments {
            let ws = args.get("Workspace").and_then(|v| v.as_str());
            if ws.is_none() || ws.unwrap().trim().is_empty() {
                let mut new_args = args.clone();
                new_args["Workspace"] = serde_json::Value::String("inherit".to_string());

                let card = GuidanceRepo::format_4part_card(
                    "SUBAGENT",
                    "Tự động đặt Workspace='inherit' mặc định",
                );
                return HookDecision::allow()
                    .with_overwrite(new_args)
                    .with_user_markdown(card);
            }
        }
    }

    // Default: allow
    HookDecision::allow()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::fs;

    #[test]
    fn test_pre_tool_use_git_push_deny() {
        let tmp = std::env::temp_dir().join(format!("tdq_pre_tool_test_{}", std::process::id()));
        let payload = HookPayload {
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "git push origin dev" })),
            ..Default::default()
        };

        let decision = handle_pre_tool_use(&payload, &tmp);
        assert_eq!(decision.decision, crate::protocol::DecisionKind::Deny);
        assert!(decision.explanation.unwrap().contains("git push is forbidden"));
        assert!(decision.metadata.unwrap().user_markdown.unwrap().contains("[TDQ:GIT]"));
    }

    #[test]
    fn test_pre_tool_use_state_json_deny() {
        let tmp = std::env::temp_dir().join(format!("tdq_pre_state_test_{}", std::process::id()));
        let payload = HookPayload {
            tool_name: Some("write_file".to_string()),
            arguments: Some(json!({ "Path": "C:/repo/docs/tdq/state.json", "Content": "{}" })),
            ..Default::default()
        };

        let decision = handle_pre_tool_use(&payload, &tmp);
        assert_eq!(decision.decision, crate::protocol::DecisionKind::Deny);
        assert!(decision.metadata.unwrap().user_markdown.unwrap().contains("[TDQ:STATE]"));
    }

    #[test]
    fn test_pre_tool_use_lsp_overwrite() {
        let tmp = std::env::temp_dir().join(format!("tdq_pre_lsp_test_{}", std::process::id()));
        let _ = fs::create_dir_all(&tmp);
        let _ = fs::write(tmp.join("Cargo.toml"), "[package]\nname=\"foo\"");

        let payload = HookPayload {
            tool_name: Some("start_lsp".to_string()),
            arguments: Some(json!({ "root_dir": tmp.to_str().unwrap() })),
            ..Default::default()
        };

        let decision = handle_pre_tool_use(&payload, &tmp);
        assert_eq!(decision.decision, crate::protocol::DecisionKind::Allow);
        assert!(decision.overwrite.is_some());
        let ov = decision.overwrite.unwrap();
        assert_eq!(ov["language_id"], "rust");

        let _ = fs::remove_dir_all(&tmp);
    }
}
