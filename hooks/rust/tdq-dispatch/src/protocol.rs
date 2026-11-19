//! Hook protocol data structures and JSON response builders for Antigravity.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Standard Antigravity hook decisions.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum DecisionKind {
    Allow,
    Deny,
    Continue,
}

/// Metadata attached to hook responses (dual-channel cards).
#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct HookMetadata {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user_markdown: Option<String>,
}

/// Hook execution result payload printed to stdout.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct HookDecision {
    pub decision: DecisionKind,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub explanation: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<HookMetadata>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub overwrite: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub additional_context: Option<String>,
}

impl HookDecision {
    pub fn allow() -> Self {
        Self {
            decision: DecisionKind::Allow,
            explanation: None,
            metadata: None,
            overwrite: None,
            additional_context: None,
        }
    }

    pub fn deny(explanation: impl Into<String>) -> Self {
        Self {
            decision: DecisionKind::Deny,
            explanation: Some(explanation.into()),
            metadata: None,
            overwrite: None,
            additional_context: None,
        }
    }

    pub fn continue_run(reason: impl Into<String>) -> Self {
        Self {
            decision: DecisionKind::Continue,
            explanation: Some(reason.into()),
            metadata: None,
            overwrite: None,
            additional_context: None,
        }
    }

    pub fn with_user_markdown(mut self, md: impl Into<String>) -> Self {
        let meta = self.metadata.get_or_insert_with(Default::default);
        meta.user_markdown = Some(md.into());
        self
    }

    pub fn with_overwrite(mut self, overwrite_val: serde_json::Value) -> Self {
        self.overwrite = Some(overwrite_val);
        self
    }

    pub fn with_additional_context(mut self, ctx: impl Into<String>) -> Self {
        self.additional_context = Some(ctx.into());
        self
    }

    pub fn to_json_string(&self) -> String {
        serde_json::to_string(self).unwrap_or_else(|_| "{\"decision\":\"allow\"}".to_string())
    }
}

/// Incoming hook event payload read from stdin.
#[derive(Debug, Clone, Deserialize, Default)]
pub struct HookPayload {
    #[serde(rename = "sessionId", default)]
    pub session_id: Option<String>,
    #[serde(rename = "transcriptPath", default)]
    pub transcript_path: Option<String>,
    #[serde(default)]
    pub cwd: Option<String>,
    #[serde(rename = "toolName", default)]
    pub tool_name: Option<String>,
    #[serde(default)]
    pub arguments: Option<serde_json::Value>,
    #[serde(rename = "userPrompt", default)]
    pub user_prompt: Option<String>,
    #[serde(rename = "message", default)]
    pub notification_message: Option<String>,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

impl HookPayload {
    pub fn from_json_str(s: &str) -> Self {
        serde_json::from_str(s).unwrap_or_default()
    }

    pub fn get_command(&self) -> Option<String> {
        if let Some(ref args) = self.arguments {
            if let Some(cmd) = args.get("CommandLine").and_then(|v| v.as_str()) {
                return Some(cmd.to_string());
            }
            if let Some(cmd) = args.get("command").and_then(|v| v.as_str()) {
                return Some(cmd.to_string());
            }
            if let Some(cmd) = args.get("script").and_then(|v| v.as_str()) {
                return Some(cmd.to_string());
            }
        }
        None
    }
}

/// Guidance table embedded at compile time for zero runtime file-IO.
pub struct GuidanceRepo;

static EMBEDDED_GUIDANCE_JSON: &str = include_str!("../../../../tools/patches/gate_guidance.json");

#[derive(Deserialize)]
struct GuidanceData {
    guidance_codes: HashMap<String, GuidanceEntry>,
    hard_deny_codes: Vec<String>,
    #[allow(dead_code)]
    overwrite_codes: Vec<String>,
}

#[derive(Deserialize, Clone)]
pub struct GuidanceEntry {
    pub chuyen_gi: String,
    pub vi_sao: String,
    pub lam_gi: String,
    pub bo_qua: String,
    pub model_hint: String,
}

impl GuidanceRepo {
    pub fn get_entry(code: &str) -> Option<GuidanceEntry> {
        let clean = code.trim().trim_start_matches("[TDQ:").trim_end_matches(']');
        let data: GuidanceData = serde_json::from_str(EMBEDDED_GUIDANCE_JSON).ok()?;
        data.guidance_codes.get(clean).cloned()
    }

    pub fn format_4part_card(code: &str, detail: &str) -> String {
        let clean = code.trim().trim_start_matches("[TDQ:").trim_end_matches(']');
        if let Some(entry) = Self::get_entry(clean) {
            let what = if detail.is_empty() {
                entry.chuyen_gi
            } else {
                format!("{} ({})", entry.chuyen_gi, detail)
            };
            format!(
                "**[TDQ:{}]**\n- **Chuyện gì**: {}\n- **Vì sao**: {}\n- **Làm gì**: {}\n- **Bỏ qua**: {}",
                clean, what, entry.vi_sao, entry.lam_gi, entry.bo_qua
            )
        } else {
            format!("**[TDQ:{}]**: {}", clean, detail)
        }
    }

    pub fn is_hard_deny(code: &str) -> bool {
        let clean = code.trim().trim_start_matches("[TDQ:").trim_end_matches(']');
        if let Ok(data) = serde_json::from_str::<GuidanceData>(EMBEDDED_GUIDANCE_JSON) {
            data.hard_deny_codes.iter().any(|c| c == clean)
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_decision_builders() {
        let allow = HookDecision::allow();
        assert_eq!(allow.decision, DecisionKind::Allow);
        assert!(allow.to_json_string().contains("\"decision\":\"allow\""));

        let deny = HookDecision::deny("Forbidden operation")
            .with_user_markdown("**[TDQ:GIT]** Do not push");
        assert_eq!(deny.decision, DecisionKind::Deny);
        assert_eq!(deny.explanation, Some("Forbidden operation".to_string()));
        assert!(deny.to_json_string().contains("Do not push"));
    }

    #[test]
    fn test_payload_parsing() {
        let raw = r#"{
            "sessionId": "test-sid-123",
            "toolName": "run_command",
            "arguments": { "CommandLine": "git status" }
        }"#;
        let payload = HookPayload::from_json_str(raw);
        assert_eq!(payload.session_id.as_deref(), Some("test-sid-123"));
        assert_eq!(payload.tool_name.as_deref(), Some("run_command"));
        assert_eq!(payload.get_command().as_deref(), Some("git status"));
    }

    #[test]
    fn test_guidance_embedded() {
        let entry = GuidanceRepo::get_entry("APPROVE");
        assert!(entry.is_some());
        let e = entry.unwrap();
        assert!(!e.chuyen_gi.is_empty());
        assert!(!e.model_hint.is_empty());

        assert!(GuidanceRepo::is_hard_deny("GIT"));
        assert!(!GuidanceRepo::is_hard_deny("SEARCH"));

        let card = GuidanceRepo::format_4part_card("GIT", "Co-Authored trailer detected");
        assert!(card.contains("**[TDQ:GIT]**"));
        assert!(card.contains("Co-Authored trailer detected"));
    }
}
