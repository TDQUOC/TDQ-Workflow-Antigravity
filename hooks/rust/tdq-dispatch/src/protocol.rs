//! Hook protocol data structures and Antigravity 2.0 JSON response builders.

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;

/// Maximum characters allowed for single-line model hints and user cards.
pub const MAX_MODEL_HINT_CHARS: usize = 160;
pub const MAX_MODEL_SUMMARY_CHARS: usize = 200;
pub const MAX_USER_MARKDOWN_CHARS: usize = 1200;
pub const MAX_DETAIL_CHARS: usize = 320;

/// Truncate UTF-8 text safely on char/word boundaries without panicking on multibyte sequences.
pub fn cap_chars(text: &str, limit: usize) -> String {
    let cleaned: String = text.split_whitespace().collect::<Vec<_>>().join(" ");
    let char_count = cleaned.chars().count();
    if char_count <= limit {
        return cleaned;
    }
    if limit <= 1 {
        return cleaned.chars().take(limit).collect();
    }
    let keep = limit - 1;
    let byte_end = cleaned
        .char_indices()
        .nth(keep)
        .map(|(idx, _)| idx)
        .unwrap_or(cleaned.len());
    let mut cut = cleaned[..byte_end].trim_end();
    if let Some(space_idx) = cut.rfind(' ') {
        if cut[..space_idx].chars().count() > limit / 2 {
            cut = cut[..space_idx].trim_end();
        }
    }
    format!("{}…", cut)
}

/// Truncate multiline markdown text safely without collapsing newlines.
pub fn cap_markdown(text: &str, limit: usize) -> String {
    if text.chars().count() <= limit {
        return text.to_string();
    }
    if limit <= 1 {
        return text.chars().take(limit).collect();
    }
    let byte_end = text
        .char_indices()
        .nth(limit - 1)
        .map(|(idx, _)| idx)
        .unwrap_or(text.len());
    let cut = text[..byte_end].trim_end();
    format!("{}…", cut)
}

/// Standard Antigravity 2.0 hook decisions (`Empty` is skipped when serializing).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum DecisionKind {
    Allow,
    Deny,
    Continue,
    #[serde(other)]
    Empty,
}

impl DecisionKind {
    /// True when response omits top-level `decision` (e.g. `PostToolUse` `{}` or `injectSteps`).
    pub fn is_empty(&self) -> bool {
        matches!(self, DecisionKind::Empty)
    }
}

/// Metadata attached inside `injectSteps[0].systemMessage`.
#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct HookMetadata {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user_markdown: Option<String>,
}

/// Inner `systemMessage` object inside Antigravity `injectSteps`.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct InjectSystemMessage {
    #[serde(rename = "systemMessage")]
    pub system_message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<HookMetadata>,
}

/// Wrapper item inside Antigravity `injectSteps` array.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct InjectStep {
    #[serde(rename = "systemMessage")]
    pub system_message: InjectSystemMessage,
}

/// Hook execution result payload serialized to stdout per Antigravity 2.0 contract.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct HookDecision {
    #[serde(skip_serializing_if = "DecisionKind::is_empty")]
    pub decision: DecisionKind,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub overwrite: Option<Value>,
    #[serde(rename = "injectSteps", skip_serializing_if = "Option::is_none")]
    pub inject_steps: Option<Vec<InjectStep>>,
}

impl HookDecision {
    /// Build an empty `{}` JSON response (PostToolUse or no-op SessionStart/PreInv/PostInv).
    pub fn empty_json() -> Self {
        Self {
            decision: DecisionKind::Empty,
            reason: None,
            overwrite: None,
            inject_steps: None,
        }
    }

    /// Build `{"decision":"allow"}` response.
    pub fn allow() -> Self {
        Self {
            decision: DecisionKind::Allow,
            ..Self::empty_json()
        }
    }

    /// Build `{"decision":"deny","reason":...}` response.
    pub fn deny(reason: impl Into<String>) -> Self {
        let msg = cap_markdown(reason.into().trim(), MAX_USER_MARKDOWN_CHARS);
        Self {
            decision: DecisionKind::Deny,
            reason: Some(msg),
            ..Self::empty_json()
        }
    }

    /// Build `{"decision":"continue","reason":...}` Stop block response.
    pub fn continue_run(reason: impl Into<String>) -> Self {
        let msg = cap_markdown(reason.into().trim(), MAX_USER_MARKDOWN_CHARS);
        Self {
            decision: DecisionKind::Continue,
            reason: Some(msg),
            ..Self::empty_json()
        }
    }

    /// Build `injectSteps` response (returns `{}` when both channels are empty).
    pub fn inject(model_text: impl Into<String>, user_md: Option<String>) -> Self {
        let text = model_text.into();
        let clean_md = user_md.and_then(|s| {
            let trimmed = s.trim();
            if trimmed.is_empty() {
                None
            } else {
                Some(cap_markdown(trimmed, MAX_USER_MARKDOWN_CHARS))
            }
        });
        if text.trim().is_empty() && clean_md.is_none() {
            return Self::empty_json();
        }
        let metadata = clean_md.map(|md| HookMetadata {
            user_markdown: Some(md),
        });
        let step = InjectStep {
            system_message: InjectSystemMessage {
                system_message: text,
                metadata,
            },
        };
        Self {
            decision: DecisionKind::Empty,
            reason: None,
            overwrite: None,
            inject_steps: Some(vec![step]),
        }
    }

    /// Attach shallow `overwrite` fields onto PreToolUse allow response.
    pub fn with_overwrite(mut self, overwrite_val: Value) -> Self {
        self.overwrite = Some(overwrite_val);
        self
    }

    /// Serialize response to compact single-line JSON for stdout.
    pub fn to_json_string(&self) -> String {
        serde_json::to_string(self).unwrap_or_else(|_| "{\"decision\":\"allow\"}".to_string())
    }
}

/// Decode `file:///` workspace URIs into local filesystem paths cleanly.
pub fn decode_file_uri(raw: &str) -> String {
    let trimmed = raw.trim();
    if !trimmed.to_ascii_lowercase().starts_with("file://") {
        return trimmed.to_string();
    }
    let after_scheme = &trimmed["file://".len()..];
    let path_part = after_scheme
        .strip_prefix("localhost/")
        .map(|rest| format!("/{}", rest))
        .unwrap_or_else(|| after_scheme.to_string());
    let decoded = percent_decode(&path_part);
    let bytes = decoded.as_bytes();
    if cfg!(windows) && bytes.len() >= 3 && bytes[0] == b'/' && bytes[2] == b':' {
        decoded[1..].to_string()
    } else if !decoded.is_empty() {
        decoded
    } else {
        trimmed.to_string()
    }
}

fn percent_decode(input: &str) -> String {
    let bytes = input.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' && i + 2 < bytes.len() {
            if let Ok(hex) = std::str::from_utf8(&bytes[i + 1..i + 3]) {
                if let Ok(val) = u8::from_str_radix(hex, 16) {
                    out.push(val);
                    i += 3;
                    continue;
                }
            }
        }
        out.push(bytes[i]);
        i += 1;
    }
    String::from_utf8(out).unwrap_or_else(|_| input.to_string())
}

fn decode_json_object_val(val: &Value) -> Option<(Map<String, Value>, bool)> {
    match val {
        Value::Object(map) => Some((map.clone(), false)),
        Value::String(s) => {
            let mut cur: Value = serde_json::from_str(s).ok()?;
            for _ in 0..3 {
                match cur {
                    Value::Object(map) => return Some((map, true)),
                    Value::String(inner) => cur = serde_json::from_str(&inner).ok()?,
                    _ => return None,
                }
            }
            None
        }
        _ => None,
    }
}

/// Nested `toolCall` object sent by Antigravity 2.0 `PreToolUse`/`PostToolUse`.
#[derive(Debug, Clone, Deserialize, Default)]
pub struct ToolCallPayload {
    #[serde(default)]
    pub id: Option<String>,
    #[serde(default)]
    pub name: Option<String>,
    #[serde(default)]
    pub args: Option<Value>,
    #[serde(default)]
    pub arguments: Option<Value>,
}

/// Unwrapped AGY tool invocation preserving `call_mcp_tool` wrapping shape.
#[derive(Debug, Clone, Default)]
pub struct NormalizedToolCall {
    pub raw_tool_name: String,
    pub tool_name: String,
    pub server_name: Option<String>,
    pub args: Map<String, Value>,
    pub is_mcp_wrapper: bool,
    pub raw_args_is_str: bool,
    pub raw_arguments: Map<String, Value>,
}

impl NormalizedToolCall {
    /// Extract canonical target file/path across Antigravity & Claude aliases.
    pub fn target_path(&self) -> Option<&str> {
        for key in [
            "Path",
            "TargetFile",
            "file_path",
            "AbsolutePath",
            "notebook_path",
            "TargetDir",
            "SearchPath",
            "DirectoryPath",
        ] {
            if let Some(s) = self.args.get(key).and_then(|v| v.as_str()) {
                if !s.trim().is_empty() {
                    return Some(s);
                }
            }
        }
        None
    }

    /// Wrap shallow overwrite fields inside `Arguments` when tool came via `call_mcp_tool`.
    pub fn wrap_overwrite(&self, fields: Value) -> Value {
        if !self.is_mcp_wrapper {
            return fields;
        }
        let mut merged = self.raw_arguments.clone();
        if let Some(obj) = fields.as_object() {
            for (k, v) in obj {
                if !v.is_null() {
                    merged.insert(k.clone(), v.clone());
                }
            }
        }
        let encoded = if self.raw_args_is_str {
            Value::String(Value::Object(merged).to_string())
        } else {
            Value::Object(merged)
        };
        serde_json::json!({ "Arguments": encoded })
    }
}

/// Incoming Antigravity 2.0 / Claude Code hook event payload read from stdin.
#[derive(Debug, Clone, Deserialize, Default)]
pub struct HookPayload {
    #[serde(rename = "conversationId", alias = "conversation_id", default)]
    pub conversation_id: Option<String>,
    #[serde(rename = "sessionId", alias = "session_id", default)]
    pub session_id: Option<String>,
    #[serde(default)]
    pub trajectory_id: Option<String>,
    #[serde(rename = "transcriptPath", alias = "transcript_path", default)]
    pub transcript_path: Option<String>,
    #[serde(default)]
    pub cwd: Option<String>,
    #[serde(rename = "workingDirectory", alias = "working_directory", default)]
    pub working_directory: Option<String>,
    #[serde(rename = "workspacePaths", default)]
    pub workspace_paths: Vec<String>,
    #[serde(rename = "toolName", alias = "tool_name", default)]
    pub tool_name: Option<String>,
    #[serde(rename = "toolCall", default)]
    pub tool_call: Option<ToolCallPayload>,
    #[serde(default)]
    pub arguments: Option<Value>,
    #[serde(rename = "toolInput", alias = "tool_input", alias = "input", default)]
    pub tool_input: Option<Value>,
    #[serde(
        rename = "userPrompt",
        alias = "prompt",
        alias = "user_message",
        default
    )]
    pub user_prompt: Option<String>,
    #[serde(rename = "lastUserInput", default)]
    pub last_user_input: Option<String>,
    #[serde(
        rename = "continuationActive",
        alias = "continuation_active",
        alias = "stop_hook_active",
        default
    )]
    pub continuation_active: Option<bool>,
    #[serde(rename = "terminationReason", default)]
    pub termination_reason: Option<String>,
    #[serde(rename = "message", default)]
    pub notification_message: Option<String>,
    #[serde(default)]
    pub agent_type: Option<String>,
    #[serde(default)]
    pub agent_id: Option<String>,
    #[serde(rename = "hookEventName", alias = "hook_event_name", default)]
    pub hook_event_name: Option<String>,
    #[serde(flatten)]
    pub extra: HashMap<String, Value>,
}

fn unwrap_mcp_tool_call(raw_name: String, outer: Map<String, Value>) -> NormalizedToolCall {
    let server_name = outer
        .get("ServerName")
        .or_else(|| outer.get("server"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let inner_name = outer
        .get("ToolName")
        .or_else(|| outer.get("tool"))
        .or_else(|| outer.get("Name"))
        .or_else(|| outer.get("name"))
        .and_then(|v| v.as_str())
        .unwrap_or("call_mcp_tool")
        .to_string();
    let raw_args_val = outer.get("Arguments").or_else(|| outer.get("arguments"));
    let (inner_args, is_str) = raw_args_val
        .and_then(decode_json_object_val)
        .unwrap_or_default();
    NormalizedToolCall {
        raw_tool_name: raw_name,
        tool_name: inner_name,
        server_name,
        args: inner_args.clone(),
        is_mcp_wrapper: true,
        raw_args_is_str: is_str,
        raw_arguments: inner_args,
    }
}

impl HookPayload {
    /// Parse raw JSON stdin fail-open.
    pub fn from_json_str(s: &str) -> Self {
        serde_json::from_str(s).unwrap_or_default()
    }

    /// Return sanitized session/conversation identifier matching Python `session_id()`.
    pub fn canonical_session_id(&self) -> String {
        let candidates = [
            self.conversation_id.as_deref(),
            self.session_id.as_deref(),
            self.trajectory_id.as_deref(),
        ];
        for cand in candidates.into_iter().flatten() {
            let trimmed = cand.trim();
            if !trimmed.is_empty() {
                let sanitized: String = trimmed
                    .chars()
                    .map(|c| {
                        if c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-') {
                            c
                        } else {
                            '_'
                        }
                    })
                    .take(64)
                    .collect();
                return sanitized;
            }
        }
        "default".to_string()
    }

    /// Return decoded local path from first valid `workspacePaths` entry.
    pub fn first_workspace_path(&self) -> Option<String> {
        self.workspace_paths
            .iter()
            .map(|p| decode_file_uri(p))
            .find(|p| !p.trim().is_empty())
    }

    /// Extract normalized tool name and unwrapped argument map across AGY/Claude formats.
    pub fn normalize_tool_call(&self) -> NormalizedToolCall {
        let tc = self.tool_call.as_ref();
        let mut raw_name = self
            .tool_name
            .as_deref()
            .or_else(|| tc.and_then(|c| c.name.as_deref()))
            .unwrap_or("")
            .to_string();
        if let Some(stripped) = raw_name.strip_prefix("CORTEX_STEP_TYPE_") {
            raw_name = stripped.to_ascii_lowercase();
        }
        let container = self
            .tool_input
            .as_ref()
            .or_else(|| tc.and_then(|c| c.args.as_ref()))
            .or_else(|| tc.and_then(|c| c.arguments.as_ref()))
            .or(self.arguments.as_ref());
        let outer = container
            .and_then(decode_json_object_val)
            .map(|(m, _)| m)
            .unwrap_or_default();
        if raw_name != "call_mcp_tool" {
            return NormalizedToolCall {
                raw_tool_name: raw_name.clone(),
                tool_name: raw_name,
                server_name: None,
                args: outer,
                is_mcp_wrapper: false,
                raw_args_is_str: false,
                raw_arguments: Map::new(),
            };
        }
        unwrap_mcp_tool_call(raw_name, outer)
    }

    /// Extract shell command across `CommandLine` / `command` / `cmd` / `script`.
    pub fn get_command(&self) -> Option<String> {
        let norm = self.normalize_tool_call();
        for key in ["CommandLine", "command", "cmd", "script"] {
            if let Some(val) = norm.args.get(key).and_then(|v| v.as_str()) {
                return Some(val.to_string());
            }
        }
        None
    }

    /// Return effective prompt string (`userPrompt` / `prompt` / `lastUserInput`).
    pub fn effective_prompt(&self) -> Option<&str> {
        self.user_prompt
            .as_deref()
            .filter(|s| !s.trim().is_empty())
            .or_else(|| {
                self.last_user_input
                    .as_deref()
                    .filter(|s| !s.trim().is_empty())
            })
    }
}

/// Guidance table embedded at compile time and parsed once via `OnceLock`.
pub struct GuidanceRepo;

static EMBEDDED_GUIDANCE_JSON: &str = include_str!("../../../../tools/patches/gate_guidance.json");
static GUIDANCE_CACHE: OnceLock<Option<GuidanceData>> = OnceLock::new();

#[derive(Deserialize)]
struct GuidanceData {
    guidance_codes: HashMap<String, GuidanceEntry>,
    hard_deny_codes: Vec<String>,
    #[allow(dead_code)]
    overwrite_codes: Vec<String>,
}

/// Single code definition inside `gate_guidance.json`.
#[derive(Deserialize, Clone)]
pub struct GuidanceEntry {
    pub chuyen_gi: String,
    pub vi_sao: String,
    pub lam_gi: String,
    pub bo_qua: String,
    pub model_hint: String,
}

/// Queued dual-channel reminder item matching `pending-reminders-<sid>.jsonl`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReminderEntry {
    pub code: String,
    pub model_line: String,
    pub user_card: String,
    pub text: String,
}

fn clean_code(code: &str) -> String {
    let raw = code.trim().trim_start_matches('[').trim_end_matches(']');
    let upper = raw.trim().to_ascii_uppercase();
    upper
        .strip_prefix("TDQ:")
        .unwrap_or(&upper)
        .trim()
        .to_string()
}

fn load_guidance() -> Option<&'static GuidanceData> {
    GUIDANCE_CACHE
        .get_or_init(|| serde_json::from_str(EMBEDDED_GUIDANCE_JSON).ok())
        .as_ref()
}

impl GuidanceRepo {
    /// Look up one canonical gate code from `gate_guidance.json`.
    pub fn get_entry(code: &str) -> Option<GuidanceEntry> {
        let key = clean_code(code);
        load_guidance()?.guidance_codes.get(&key).cloned()
    }

    /// Format a 4-part Vietnamese Markdown guidance block (colon inside bold, <= 1,200 chars).
    pub fn format_4part_card(code: &str, detail: &str) -> String {
        let key = clean_code(code);
        let clean_detail = cap_chars(detail, MAX_DETAIL_CHARS);
        if let Some(entry) = Self::get_entry(&key) {
            let what = if clean_detail.is_empty() {
                entry.chuyen_gi
            } else {
                format!("{} ({})", entry.chuyen_gi, clean_detail)
            };
            let card = format!(
                "**[TDQ:{}]**\n- **Chuyện gì:** {}\n- **Vì sao:** {}\n- **Làm gì:** {}\n- **Bỏ qua:** {}",
                key, what, entry.vi_sao, entry.lam_gi, entry.bo_qua
            );
            cap_markdown(&card, MAX_USER_MARKDOWN_CHARS)
        } else if clean_detail.is_empty() {
            format!("**[TDQ:{}]**", key)
        } else {
            cap_markdown(
                &format!("**[TDQ:{}]**: {}", key, clean_detail),
                MAX_USER_MARKDOWN_CHARS,
            )
        }
    }

    /// Build dual-channel reminder payload (`model_line <= 160`, `user_card <= 1,200`).
    pub fn build_reminder_entry(code: &str, detail: &str) -> ReminderEntry {
        let key = clean_code(code);
        let prefix = format!("[TDQ:{}] ", key);
        let clean_detail = detail.split_whitespace().collect::<Vec<_>>().join(" ");
        let model_hint = Self::get_entry(&key)
            .map(|e| e.model_hint)
            .unwrap_or_else(|| format!("Gate {} triggered; check policy before retrying.", key));
        let base_line = format!("{}{}", prefix, model_hint);
        let model_line =
            if !clean_detail.is_empty() && base_line.chars().count() < MAX_MODEL_HINT_CHARS - 8 {
                cap_chars(
                    &format!("{} ({})", base_line, clean_detail),
                    MAX_MODEL_HINT_CHARS,
                )
            } else {
                cap_chars(&base_line, MAX_MODEL_HINT_CHARS)
            };
        ReminderEntry {
            code: key.clone(),
            model_line: model_line.clone(),
            user_card: Self::format_4part_card(&key, detail),
            text: model_line,
        }
    }

    /// Merge queued reminder items into compact dual-channel output (`<= 200` model, `<= 1,200` user).
    pub fn merge_pending_channels(items: &[ReminderEntry]) -> (String, String) {
        let mut seen = HashSet::new();
        let mut unique = Vec::new();
        for item in items {
            let key = clean_code(&item.code);
            if key.is_empty() || !seen.insert(key) {
                continue;
            }
            unique.push(item);
        }
        if unique.is_empty() {
            return (String::new(), String::new());
        }
        let model_lines: Vec<String> = unique
            .iter()
            .map(|r| r.model_line.trim())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_string())
            .collect();
        let model_text = if model_lines.len() == 1 {
            cap_chars(&model_lines[0], MAX_MODEL_SUMMARY_CHARS)
        } else {
            cap_markdown(&model_lines.join("\n"), MAX_MODEL_SUMMARY_CHARS)
        };
        let cards: Vec<&str> = unique
            .iter()
            .map(|r| r.user_card.trim())
            .filter(|s| !s.is_empty())
            .collect();
        let user_md = cap_markdown(&cards.join("\n\n"), MAX_USER_MARKDOWN_CHARS);
        (model_text, user_md)
    }

    /// Return true when canonical code is a hard-deny gate.
    pub fn is_hard_deny(code: &str) -> bool {
        let key = clean_code(code);
        load_guidance()
            .map(|data| data.hard_deny_codes.iter().any(|c| c == &key))
            .unwrap_or(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_decision_builders() {
        let empty = HookDecision::empty_json();
        assert_eq!(empty.to_json_string(), "{}");

        let allow = HookDecision::allow();
        assert_eq!(allow.decision, DecisionKind::Allow);
        assert!(allow.to_json_string().contains("\"decision\":\"allow\""));

        let deny = HookDecision::deny("Forbidden operation");
        let deny_json = deny.to_json_string();
        assert_eq!(deny.decision, DecisionKind::Deny);
        assert!(deny_json.contains("\"reason\""));
        assert!(!deny_json.contains("\"explanation\""));
        assert!(deny_json.contains("Forbidden operation"));

        let inject = HookDecision::inject("Reminder text", Some("**[TDQ:TICK]** card".to_string()));
        let inject_json = inject.to_json_string();
        assert!(inject_json.contains("\"injectSteps\""));
        assert!(inject_json.contains("\"user_markdown\""));
        assert!(!inject_json.contains("\"additional_context\""));
    }

    #[test]
    fn test_payload_parsing() {
        let raw = r#"{
            "conversationId": "conv/abc:1",
            "workspacePaths": ["file:///C:/repo/my%20app"],
            "toolCall": {
                "name": "call_mcp_tool",
                "args": {
                    "Name": "start_lsp",
                    "Arguments": "{\"root_dir\":\"C:/repo\"}"
                }
            }
        }"#;
        let payload = HookPayload::from_json_str(raw);
        assert_eq!(payload.canonical_session_id(), "conv_abc_1");
        assert!(payload
            .first_workspace_path()
            .unwrap_or_default()
            .contains("C:/repo/my app"));
        let norm = payload.normalize_tool_call();
        assert_eq!(norm.tool_name, "start_lsp");
        assert!(norm.is_mcp_wrapper);
        assert!(norm.raw_args_is_str);
        let wrapped = norm.wrap_overwrite(serde_json::json!({ "language_id": "rust" }));
        assert!(wrapped["Arguments"].as_str().unwrap_or("").contains("rust"));
    }

    #[test]
    fn test_guidance_and_utf8_cap() {
        assert!(GuidanceRepo::is_hard_deny("GIT"));
        assert!(!GuidanceRepo::is_hard_deny("SEARCH"));
        let card = GuidanceRepo::format_4part_card("GIT", "Phát hiện trailer tiếng Việt có dấu");
        assert!(card.contains("**[TDQ:GIT]**"));
        assert!(card.contains("- **Chuyện gì:**"));
        let clipped = cap_chars("Tiếng Việt có dấu rất dài vượt ngưỡng cắt ký tự", 15);
        assert!(clipped.chars().count() <= 15);
    }
}
