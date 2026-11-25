//! PreToolUse Hybrid Hot-path handler in pure Rust.
//! Enforces hard gates (`READONLY`, `STATE`, `GIT`, `VUNG`, `ZERO-POPUP`, `APPROVE`, `TICK`),
//! handles `start_lsp` overwrite and concept ledger writes, and delegates Cold-path edge cases.

use crate::command_parser::{
    collect_git_policy_violations, has_banned_ai_branch, inspect_command_safety,
    is_graphify_shell_query, is_pure_intake_branch_create, is_shell_mutator, mutates_outside_docs,
    mutates_outside_docs_any, mutates_tdq_state, needs_python_command_gate, CommandSafetyViolation,
    GitPolicyViolation,
};
use crate::events::post_tool_use::extract_concept_label;
use crate::protocol::{GuidanceRepo, HookDecision, HookPayload, NormalizedToolCall};
use crate::storage::{
    already_reminded, append_jsonl_record, append_turn_row, cong_dang_cho,
    count_code_edits_for_sha, effective_phase, khoa_hien_tai, maybe_bump_burden, now_iso_utc,
    queue_pending_reminder, read_plan_tick_state, read_sessions_role, read_tdq_state,
    read_turn_meta, reset_burden_checkpoint, search_ledger_path, today_log_rel_for_state,
    unix_timestamp_f64, TdqState,
};
use crate::RouteOutcome;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};

const SUBAGENT_ROLES: &[&str] = &[
    "tdq-security-reviewer",
    "tdq-reviewer",
    "tdq-qc-tester",
    "tdq-implementer",
    "tdq-build-resolver",
    "tdq-refactor-cleaner",
    "tdq-explorer",
    "tdq-debugger",
];

pub(crate) fn detect_subagent_role(
    payload: &HookPayload,
    workspace_root: &Path,
    sid: &str,
) -> Option<String> {
    if let Some(rec) = read_sessions_role(workspace_root, sid) {
        if !rec.role.trim().is_empty() {
            return Some(rec.role);
        }
    }
    if let Some(ref atype) = payload.agent_type {
        if !atype.trim().is_empty() {
            return Some(atype.trim().to_string());
        }
    }
    if let Some(ref tpath) = payload.transcript_path {
        if let Ok(file) = File::open(tpath) {
            let mut first = String::new();
            if BufReader::new(file).read_line(&mut first).is_ok() {
                if let Some(found) = SUBAGENT_ROLES.iter().find(|r| first.contains(**r)) {
                    return Some((*found).to_string());
                }
            }
        }
    }
    payload
        .agent_id
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .map(|_| "subagent".to_string())
}

fn is_readonly_role(role: &str) -> bool {
    let low = role.to_ascii_lowercase();
    low.contains("reviewer")
        || low.contains("qc-tester")
        || low.contains("browser")
        || low.contains("explorer")
        || low.contains("debugger")
}

fn deny_with_block(workspace_root: &Path, sid: &str, code: &str, detail: &str) -> RouteOutcome {
    let card = GuidanceRepo::format_4part_card(code, detail);
    let clean_code = code
        .strip_prefix("TDQ:")
        .unwrap_or(code)
        .to_ascii_uppercase();
    let row = serde_json::json!({
        "ts": now_iso_utc(),
        "kind": "block",
        "event": "block",
        "session": sid,
        "code": clean_code,
        "reason_key": detail,
        "source_event": "PreToolUse",
    });
    append_turn_row(workspace_root, sid, &row);
    RouteOutcome::Decided(HookDecision::deny(card))
}

fn queue_remind_once(workspace_root: &Path, sid: &str, code: &str, detail: &str) {
    if already_reminded(workspace_root, sid, code) {
        return;
    }
    if queue_pending_reminder(workspace_root, sid, code, detail) {
        let row = serde_json::json!({
            "ts": now_iso_utc(),
            "kind": "remind",
            "event": "remind",
            "session": sid,
            "code": code.strip_prefix("TDQ:").unwrap_or(code),
            "source_event": "PreToolUse",
        });
        append_turn_row(workspace_root, sid, &row);
    }
}

fn canonical_or_ancestor(path: &Path) -> Option<String> {
    let mut tail: Vec<std::ffi::OsString> = Vec::new();
    for anc in path.ancestors() {
        if anc.exists() {
            if let Ok(canon) = fs::canonicalize(anc) {
                let mut full = canon;
                for seg in tail.into_iter().rev() {
                    full.push(seg);
                }
                let s = full.to_string_lossy().into_owned();
                return Some(s.strip_prefix(r"\\?\").unwrap_or(&s).replace('\\', "/"));
            }
        }
        let name = anc.file_name()?;
        if name == ".." {
            return None;
        }
        tail.push(name.to_os_string());
    }
    None
}

fn resolve_rel_in_project(raw_target: &str, workspace_root: &Path) -> Option<String> {
    let abs = if Path::new(raw_target).is_absolute() {
        PathBuf::from(raw_target)
    } else {
        workspace_root.join(raw_target)
    };
    let norm_root = canonical_or_ancestor(workspace_root)?;
    let trim_root = norm_root.trim_end_matches('/');
    let norm_abs = canonical_or_ancestor(&abs)?;
    if cfg!(windows) {
        let low_a = norm_abs.to_ascii_lowercase();
        let low_r = format!("{}/", trim_root.to_ascii_lowercase());
        if low_a.starts_with(&low_r) {
            return Some(norm_abs[low_r.len()..].to_string());
        }
    } else if let Some(rest) = norm_abs.strip_prefix(&format!("{}/", trim_root)) {
        return Some(rest.to_string());
    }
    None
}

fn is_scoped_artifact_role(role: &str) -> bool {
    let low = role.trim().to_ascii_lowercase();
    if low.contains("security-reviewer")
        || low.contains("browser")
        || low.contains("qc-tester")
        || low.is_empty()
        || low == "subagent"
    {
        return false;
    }
    matches!(
        low.as_str(),
        "tdq-explorer" | "explorer" | "tdq-debugger" | "debugger" | "tdq-reviewer" | "reviewer"
    )
}

fn is_investigation_artifact_target(raw_target: &str, workspace_root: &Path, role: &str) -> bool {
    if !is_scoped_artifact_role(role) || raw_target.trim().is_empty() || raw_target.contains('\0') {
        return false;
    }
    let bytes = raw_target.as_bytes();
    let after_drive = if bytes.len() >= 2 && bytes[1] == b':' {
        &raw_target[2..]
    } else {
        raw_target
    };
    if after_drive.contains(':')
        || Path::new(raw_target)
            .components()
            .any(|c| matches!(c, std::path::Component::ParentDir))
    {
        return false;
    }
    let Some(state) = read_tdq_state(workspace_root) else {
        return false;
    };
    let slug = state.active_request.as_deref().unwrap_or("").trim();
    if slug.is_empty()
        || slug.contains("..")
        || !slug
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-'))
    {
        return false;
    }
    let Some(rel) = resolve_rel_in_project(raw_target, workspace_root) else {
        return false;
    };
    let fname = rel.rsplit('/').next().unwrap_or(&rel).to_ascii_lowercase();
    let ext_ok = fname.ends_with(".md") || fname.ends_with(".json") || fname.ends_with(".jsonl");
    if !ext_ok
        || fname.starts_with("evidence")
        || ((fname.starts_with("trial_") || fname.starts_with("rec_")) && fname.ends_with(".json"))
    {
        return false;
    }
    let rel_cmp = if cfg!(windows) { rel.to_ascii_lowercase() } else { rel };
    let slug_cmp = if cfg!(windows) { slug.to_ascii_lowercase() } else { slug.to_string() };
    let art_prefix = format!("docs/tdq/artifacts/{}/", slug_cmp);
    if rel_cmp.starts_with(&art_prefix) && rel_cmp.len() > art_prefix.len() {
        return true;
    }
    if let Some(tail) = rel_cmp.strip_prefix("docs/tdq/research/") {
        return !tail.contains('/')
            && (tail == format!("{}.md", slug_cmp)
                || (tail.starts_with(&format!("{}-", slug_cmp))
                    && tail.ends_with(".md")
                    && tail.len() > slug_cmp.len() + 4));
    }
    false
}

fn normalize_lexical(path: &Path) -> PathBuf {
    use std::path::Component;
    let mut out = PathBuf::new();
    for comp in path.components() {
        match comp {
            Component::CurDir => {}
            Component::ParentDir => {
                if !out.pop() {
                    out.push(Component::ParentDir);
                }
            }
            other => out.push(other),
        }
    }
    out
}

fn is_qc_report_target(raw_target: &str, workspace_root: &Path) -> bool {
    if raw_target.trim().is_empty() {
        return false;
    }
    let abs_raw = if Path::new(raw_target).is_absolute() {
        PathBuf::from(raw_target)
    } else {
        workspace_root.join(raw_target)
    };
    let lexical = normalize_lexical(&abs_raw);
    let lexical_str = lexical.to_string_lossy();
    let Some(rel) = resolve_rel_in_project(&lexical_str, workspace_root) else {
        return false;
    };
    let low = rel.replace('\\', "/").to_ascii_lowercase();
    low.starts_with("docs/tdq/qc/") && low.ends_with(".md")
}

fn is_protected_state_norm(norm_low: &str) -> bool {
    norm_low == "docs/tdq/state.json"
        || norm_low.ends_with("/docs/tdq/state.json")
        || norm_low == "docs/tdq/state.md"
        || norm_low.ends_with("/docs/tdq/state.md")
        || norm_low == "docs/tdq/.tdq-runtime"
        || norm_low.ends_with("/docs/tdq/.tdq-runtime")
        || norm_low.starts_with("docs/tdq/.tdq-runtime/")
        || norm_low.contains("/docs/tdq/.tdq-runtime/")
}

fn is_state_target(raw_target: &str, workspace_root: &Path) -> bool {
    let raw_low = raw_target.replace('\\', "/").to_ascii_lowercase();
    let abs_raw = if Path::new(raw_target).is_absolute() {
        PathBuf::from(raw_target)
    } else {
        workspace_root.join(raw_target)
    };
    let lex = normalize_lexical(&abs_raw);
    let lex_low = lex.to_string_lossy().replace('\\', "/").to_ascii_lowercase();
    if is_protected_state_norm(&lex_low) || (!raw_low.contains("..") && is_protected_state_norm(&raw_low)) {
        return true;
    }
    resolve_rel_in_project(&lex.to_string_lossy(), workspace_root)
        .is_some_and(|rel| is_protected_state_norm(&rel.to_ascii_lowercase()))
}

fn tdq_log_enabled() -> bool {
    std::env::var("TDQ_LOG").as_deref() != Ok("0")
}

static EMBEDDED_MCP_POLICY_JSON: &str =
    include_str!("../../../../../scripts/defaults/mcp-policy.default.json");

const DESTRUCTIVE_VERBS: &[&str] = &[
    "delete", "remove", "drop", "destroy", "exec", "execute", "run", "push", "deploy", "reset",
];

fn read_json_object(path: &Path) -> Result<Option<Value>, ()> {
    if !path.is_file() {
        return Ok(None);
    }
    let Ok(raw) = fs::read_to_string(path) else {
        return Err(());
    };
    let Ok(val) = serde_json::from_str::<Value>(&raw) else {
        return Err(());
    };
    if val.is_object() {
        Ok(Some(val))
    } else {
        Err(())
    }
}

fn read_p0_config_val(workspace_root: &Path) -> Option<Value> {
    let cfg_path = workspace_root.join("docs").join("tdq").join("config.json");
    let Ok(Some(val)) = read_json_object(&cfg_path) else {
        return None;
    };
    val.get("p0").cloned()
}

fn read_p0_bool(workspace_root: &Path, key: &str, default_val: bool) -> bool {
    read_p0_config_val(workspace_root)
        .and_then(|p| p.get(key).and_then(|v| v.as_bool()))
        .unwrap_or(default_val)
}

fn read_p0_mcp_mode(workspace_root: &Path) -> String {
    read_p0_config_val(workspace_root)
        .and_then(|p| p.get("mcp_mode").and_then(|v| v.as_str()).map(|s| s.trim().to_ascii_lowercase()))
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "balanced".to_string())
}

fn split_p0_unlock_tokens(seg: &str) -> Option<Vec<String>> {
    let mut tokens = Vec::new();
    let mut cur = String::new();
    let mut quote: Option<char> = None;
    let mut in_tok = false;
    for ch in seg.chars() {
        match quote {
            Some(q) if ch == q => quote = None,
            Some(_) => cur.push(ch),
            None if ch == '\'' || ch == '"' => {
                quote = Some(ch);
                in_tok = true;
            }
            None if ch.is_whitespace() => {
                if in_tok {
                    tokens.push(std::mem::take(&mut cur));
                    in_tok = false;
                }
            }
            None => {
                cur.push(ch);
                in_tok = true;
            }
        }
    }
    if quote.is_some() {
        return None;
    }
    if in_tok {
        tokens.push(cur);
    }
    if tokens.is_empty() { None } else { Some(tokens) }
}

fn has_valid_p0_subcmd(script_name: &str, args: &[String]) -> bool {
    let mut pos: Option<String> = None;
    let mut skip_next = false;
    for arg in args {
        if skip_next {
            skip_next = false;
            continue;
        }
        if arg == "--cwd" || arg == "--project" {
            skip_next = true;
            continue;
        }
        if arg.starts_with('-') {
            continue;
        }
        pos = Some(arg.to_ascii_lowercase());
        break;
    }
    matches!(
        (script_name, pos.as_deref()),
        ("tdq_state.py", Some("reset-breaker")) | ("mcp_policy.py", Some("approve" | "reset"))
    )
}

fn is_p0_python_unlock_target(tokens: &[String]) -> bool {
    let base = tokens[0].rsplit(['/', '\\']).next().unwrap_or("").to_ascii_lowercase();
    let runner = base.strip_suffix(".exe").unwrap_or(&base);
    if !matches!(runner, "py" | "python" | "python3") && !runner.starts_with("python3.") {
        return false;
    }
    let mut idx = 1usize;
    while idx < tokens.len() {
        let tok = tokens[idx].as_str();
        if matches!(tok, "-3" | "-2" | "-B" | "-E" | "-I" | "-O" | "-OO" | "-S" | "-s" | "-u" | "-v" | "-q")
            || (tok.starts_with("-X") && tok.len() > 2)
        {
            idx += 1;
        } else if tok == "-X" && idx + 1 < tokens.len() {
            idx += 2;
        } else {
            break;
        }
    }
    if idx >= tokens.len() {
        return false;
    }
    let script_name = tokens[idx].rsplit(['/', '\\']).next().unwrap_or("").to_ascii_lowercase();
    if script_name != "tdq_state.py" && script_name != "mcp_policy.py" {
        return false;
    }
    has_valid_p0_subcmd(&script_name, &tokens[idx + 1..])
}

fn is_p0_unlock_command(cmd: &str) -> bool {
    let trimmed = cmd.trim();
    if trimmed.is_empty()
        || trimmed.contains('|')
        || trimmed.contains('`')
        || trimmed.contains("$(")
        || trimmed.contains('\n')
        || trimmed.contains('\r')
        || trimmed.contains('<')
        || trimmed.contains('>')
        || trimmed.contains('#')
    {
        return false;
    }
    let mut has_unlock = false;
    for seg in trimmed
        .split("&&")
        .flat_map(|s| s.split(';'))
        .map(str::trim)
        .filter(|s| !s.is_empty())
    {
        if seg.contains('&') {
            return false;
        }
        let Some(tokens) = split_p0_unlock_tokens(seg) else {
            return false;
        };
        let head = tokens[0].rsplit(['/', '\\']).next().unwrap_or("").to_ascii_lowercase();
        if head == "cd" && (tokens.len() == 2 || (tokens.len() == 3 && tokens[1].eq_ignore_ascii_case("/d"))) {
            continue;
        }
        if !is_p0_python_unlock_target(&tokens) {
            return false;
        }
        has_unlock = true;
    }
    has_unlock
}

fn json_finite_nonneg(val: Option<&Value>) -> Option<f64> {
    let v = val?;
    if v.is_boolean() {
        return None;
    }
    v.as_f64().filter(|n| n.is_finite() && *n >= 0.0)
}

fn load_budget_caps_rust(workspace_root: &Path) -> (Option<f64>, Option<f64>) {
    let cfg_path = workspace_root.join("docs").join("tdq").join("config.json");
    let Ok(Some(cfg)) = read_json_object(&cfg_path) else {
        return (None, None);
    };
    let caps = if let Some(p0) = cfg.get("p0") {
        p0.get("budget_caps").and_then(|v| v.as_object())
    } else {
        cfg.get("budget_caps").and_then(|v| v.as_object())
    };
    let Some(caps_obj) = caps else {
        return (None, None);
    };
    let token_cap = json_finite_nonneg(caps_obj.get("hard_stop_tokens")).filter(|n| *n > 0.0);
    let usd_cap = json_finite_nonneg(caps_obj.get("hard_stop_usd")).filter(|n| *n > 0.0);
    (token_cap, usd_cap)
}

fn sum_telemetry_usage_rust(telemetry_path: &Path) -> (f64, f64) {
    let Ok(raw) = fs::read_to_string(telemetry_path) else {
        return (0.0, 0.0);
    };
    let (mut total_tokens, mut total_usd) = (0.0_f64, 0.0_f64);
    for line in raw.lines().map(str::trim).filter(|l| !l.is_empty()) {
        let Ok(Value::Object(row)) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        let row_toks = json_finite_nonneg(row.get("tokens"))
            .or_else(|| json_finite_nonneg(row.get("total_tokens")))
            .unwrap_or_else(|| {
                json_finite_nonneg(row.get("input_tokens")).unwrap_or(0.0)
                    + json_finite_nonneg(row.get("output_tokens")).unwrap_or(0.0)
            });
        let row_usd = json_finite_nonneg(row.get("cost_usd"))
            .or_else(|| json_finite_nonneg(row.get("usd")))
            .unwrap_or(0.0);
        total_tokens += row_toks;
        total_usd += row_usd;
    }
    (total_tokens, total_usd)
}

fn is_budget_hard_stop_reached(workspace_root: &Path) -> bool {
    let (token_cap, usd_cap) = load_budget_caps_rust(workspace_root);
    if token_cap.is_none() && usd_cap.is_none() {
        return false;
    }
    let tel_path = workspace_root.join("docs").join("tdq").join(".tdq-agent-telemetry.jsonl");
    let (total_tokens, raw_usd) = sum_telemetry_usage_rust(&tel_path);
    let total_usd = (raw_usd * 1_000_000_000.0).round() / 1_000_000_000.0;
    let mut max_ratio = 0.0_f64;
    if let Some(tc) = token_cap {
        max_ratio = max_ratio.max(total_tokens / tc);
    }
    if let Some(uc) = usd_cap {
        max_ratio = max_ratio.max(total_usd / uc);
    }
    ((max_ratio * 1_000_000_000.0).round() / 1_000_000_000.0) >= 1.0
}

/// Evaluate P0 Circuit Breaker & Budget hard_stop state from `docs/tdq/state.json` and telemetry.
pub(crate) fn check_p0_runtime_guard(workspace_root: &Path, sid: &str) -> Option<RouteOutcome> {
    let spath = workspace_root.join("docs").join("tdq").join("state.json");
    let state_val = read_json_object(&spath).ok().flatten();
    let p0_rt = state_val
        .as_ref()
        .and_then(|v| v.get("p0_runtime"))
        .and_then(|v| v.as_object());
    let breaker_open = p0_rt
        .and_then(|rt| rt.get("breaker"))
        .and_then(|b| b.get("open"))
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    if read_p0_bool(workspace_root, "breaker_enabled", true) && breaker_open {
        return Some(deny_with_block(
            workspace_root,
            sid,
            "READONLY",
            "P0 circuit breaker is OPEN after consecutive failures. Run: py -3 scripts/tdq_state.py reset-breaker",
        ));
    }
    let hard_stopped = p0_rt
        .and_then(|rt| rt.get("budget"))
        .and_then(|b| b.get("hard_stopped"))
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    if hard_stopped || is_budget_hard_stop_reached(workspace_root) {
        return Some(deny_with_block(
            workspace_root,
            sid,
            "READONLY",
            "P0 budget hard_stop reached. Raise cap in docs/tdq/config.json or run: py -3 scripts/tdq_state.py reset-breaker",
        ));
    }
    None
}

fn load_mcp_baseline(workspace_root: &Path) -> Value {
    let default_path = workspace_root
        .join("scripts")
        .join("defaults")
        .join("mcp-policy.default.json");
    if let Ok(Some(val)) = read_json_object(&default_path) {
        return val;
    }
    serde_json::from_str::<Value>(EMBEDDED_MCP_POLICY_JSON).unwrap_or_else(|_| Value::Object(Default::default()))
}

fn merge_policy_override(baseline: &Value, override_val: &Value) -> Result<Value, ()> {
    let mut merged = baseline.as_object().cloned().unwrap_or_default();
    let Some(ov) = override_val.as_object() else {
        return Err(());
    };
    if let Some(mode_v) = ov.get("mode") {
        let Some(mode_s) = mode_v.as_str().map(str::trim).filter(|s| !s.is_empty()) else {
            return Err(());
        };
        merged.insert("mode".to_string(), Value::String(mode_s.to_ascii_lowercase()));
    }
    for key in ["trusted_servers", "read_prefixes", "write_prefixes"] {
        if let Some(v) = ov.get(key) {
            if !v.is_array() {
                return Err(());
            }
            merged.insert(key.to_string(), v.clone());
        }
    }
    if let Some(app_v) = ov.get("approved_tools") {
        let Some(app_obj) = app_v.as_object() else {
            return Err(());
        };
        let mut base_app = merged
            .get("approved_tools")
            .and_then(|v| v.as_object())
            .cloned()
            .unwrap_or_default();
        for (k, v) in app_obj {
            base_app.insert(k.clone(), v.clone());
        }
        merged.insert("approved_tools".to_string(), Value::Object(base_app));
    }
    Ok(Value::Object(merged))
}

fn load_mcp_policy_merged(workspace_root: &Path) -> (Value, bool) {
    let baseline = load_mcp_baseline(workspace_root);
    let proj_path = workspace_root.join("docs").join("tdq").join("mcp-policy.json");
    match read_json_object(&proj_path) {
        Ok(None) => (baseline, false),
        Ok(Some(ov)) => match merge_policy_override(&baseline, &ov) {
            Ok(merged) => (merged, false),
            Err(()) => (baseline, true),
        },
        Err(()) => (baseline, true),
    }
}

fn extract_mcp_server_and_tool(norm: &NormalizedToolCall, policy: &Value) -> (String, String) {
    let srv_raw = norm
        .server_name
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty() && *s != "_");
    if let Some(srv) = srv_raw {
        return (srv.to_string(), norm.tool_name.clone());
    }
    if let Some(rest) = norm.tool_name.strip_prefix("mcp__") {
        if let Some((srv, tool)) = rest.split_once("__") {
            return (srv.to_string(), tool.to_string());
        }
    }
    if let Some(rest) = norm.tool_name.strip_prefix("mcp_") {
        if let Some((srv, tool)) = rest.split_once("__") {
            return (srv.to_string(), tool.to_string());
        }
        let mut trusted = json_lower_list(policy, "trusted_servers");
        trusted.sort_by_key(|s| std::cmp::Reverse(s.len()));
        let rest_low = rest.to_ascii_lowercase();
        for srv in trusted {
            let prefix_low = format!("{}_", srv);
            if rest_low.starts_with(&prefix_low)
                && rest.len() > prefix_low.len()
                && rest.is_char_boundary(srv.len())
                && rest.is_char_boundary(srv.len() + 1)
            {
                return (rest[..srv.len()].to_string(), rest[srv.len() + 1..].to_string());
            }
        }
        if let Some(idx) = rest_low.find("_lsp_") {
            if rest.is_char_boundary(idx)
                && rest.is_char_boundary(idx + 4)
                && rest.is_char_boundary(idx + 5)
                && !rest[..idx].contains('_')
                && idx + 5 < rest.len()
            {
                return (rest[..idx + 4].to_string(), rest[idx + 5..].to_string());
            }
        }
        if let Some((srv, tool)) = rest.split_once('_') {
            return (srv.to_string(), tool.to_string());
        }
    }
    (String::new(), norm.tool_name.clone())
}

fn json_lower_list(policy: &Value, key: &str) -> Vec<String> {
    policy
        .get(key)
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str())
                .map(|s| s.trim().to_ascii_lowercase())
                .filter(|s| !s.is_empty())
                .collect()
        })
        .unwrap_or_default()
}

fn strip_tool_prefix_lower(srv_lower: &str, tool_lower: &str) -> String {
    if !srv_lower.is_empty() {
        let exact_prefix = format!("mcp__{}__", srv_lower);
        if let Some(rest) = tool_lower.strip_prefix(&exact_prefix) {
            return rest.to_string();
        }
    }
    if let Some(rest) = tool_lower.strip_prefix("mcp__") {
        if let Some((_, tail)) = rest.split_once("__") {
            return tail.to_string();
        }
    }
    tool_lower.strip_prefix("lsp.").unwrap_or(tool_lower).to_string()
}

fn matches_any_prefix(short: &str, prefixes: &[String]) -> bool {
    prefixes
        .iter()
        .any(|p| short == p || short.starts_with(p.as_str()))
}

fn is_destructive_short(short: &str) -> bool {
    DESTRUCTIVE_VERBS
        .iter()
        .any(|v| short == *v || short.starts_with(v))
}

fn classify_mcp_tier_rust(server: &str, tool_name: &str, policy: &Value) -> &'static str {
    let srv = server.trim().to_ascii_lowercase();
    let short = strip_tool_prefix_lower(&srv, &tool_name.trim().to_ascii_lowercase());
    let write_prefixes = json_lower_list(policy, "write_prefixes");
    if matches_any_prefix(&short, &write_prefixes) {
        return if is_destructive_short(&short) {
            "destructive"
        } else {
            "write"
        };
    }
    let trusted = json_lower_list(policy, "trusted_servers");
    if trusted.iter().any(|t| t == &srv) || srv.contains("lsp") {
        return "read";
    }
    let read_prefixes = json_lower_list(policy, "read_prefixes");
    if matches_any_prefix(&short, &read_prefixes) {
        return "read";
    }
    if is_destructive_short(&short) {
        "destructive"
    } else {
        "write"
    }
}

fn escape_json_ascii(raw: &str) -> String {
    let mut out = String::with_capacity(raw.len());
    for ch in raw.chars() {
        let code = ch as u32;
        if code <= 0x7F {
            out.push(ch);
        } else if code <= 0xFFFF {
            out.push_str(&format!("\\u{:04x}", code));
        } else {
            let adj = code - 0x1_0000;
            out.push_str(&format!("\\u{:04x}\\u{:04x}", 0xD800 + (adj >> 10), 0xDC00 + (adj & 0x3FF)));
        }
    }
    out
}

fn canonical_schema_sha256(val: Option<&Value>) -> String {
    let empty = Value::Object(Default::default());
    let target = val.unwrap_or(&empty);
    let compact = serde_json::to_string(target).unwrap_or_else(|_| "{}".to_string());
    let ascii = escape_json_ascii(&compact);
    let mut hasher = Sha256::new();
    hasher.update(ascii.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn lookup_approved_sha<'a>(
    policy: &'a Value,
    server: &str,
    tool_name: &str,
    raw_tool_name: &str,
) -> Option<&'a str> {
    let approved = policy.get("approved_tools")?.as_object()?;
    let candidates = [
        if server.is_empty() {
            tool_name.to_string()
        } else {
            format!("{}::{}", server, tool_name)
        },
        tool_name.to_string(),
        if server.is_empty() {
            raw_tool_name.to_string()
        } else {
            format!("{}::{}", server, raw_tool_name)
        },
        raw_tool_name.to_string(),
    ];
    for k in candidates {
        if let Some(sha) = approved.get(&k).and_then(|e| e.get("sha256")).and_then(|v| v.as_str()) {
            return Some(sha);
        }
    }
    None
}

fn effective_mcp_mode(workspace_root: &Path, policy: &Value) -> String {
    let pol_mode = policy
        .get("mode")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_ascii_lowercase())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "balanced".to_string());
    if pol_mode != "balanced" {
        pol_mode
    } else {
        read_p0_mcp_mode(workspace_root)
    }
}

fn deny_quarantined_mcp(
    workspace_root: &Path,
    sid: &str,
    server: &str,
    tool_name: &str,
    tier: &str,
    corrupt: bool,
) -> RouteOutcome {
    if corrupt {
        if tdq_log_enabled() {
            eprintln!("[{}] tdq-dispatch: deny READONLY corrupt mcp-policy.json tool={}::{}", now_iso_utc(), server, tool_name);
        }
        return deny_with_block(
            workspace_root,
            sid,
            "READONLY",
            "Project mcp-policy.json is corrupt; write/destructive MCP tool blocked",
        );
    }
    let srv_arg = if server.is_empty() { "_" } else { server };
    let key = if server.is_empty() {
        tool_name.to_string()
    } else {
        format!("{}::{}", server, tool_name)
    };
    if tdq_log_enabled() {
        eprintln!("[{}] tdq-dispatch: deny READONLY quarantined tool={} tier={}", now_iso_utc(), key, tier);
    }
    deny_with_block(
        workspace_root,
        sid,
        "READONLY",
        &format!(
            "MCP tool '{}' requires policy approval or schema hash changed. Run: py -3 scripts/mcp_policy.py approve {} {}",
            key, srv_arg, tool_name
        ),
    )
}

/// Evaluate balanced MCP quarantine policy matching `scripts/mcp_policy.py`.
pub(crate) fn evaluate_non_lsp_mcp_rust(
    workspace_root: &Path,
    norm: &NormalizedToolCall,
    sid: &str,
) -> Option<RouteOutcome> {
    if !read_p0_bool(workspace_root, "mcp_quarantine_enabled", true) {
        return None;
    }
    let (policy, corrupt) = load_mcp_policy_merged(workspace_root);
    let (server, tool_name) = extract_mcp_server_and_tool(norm, &policy);
    let tier = classify_mcp_tier_rust(&server, &tool_name, &policy);
    let mode = effective_mcp_mode(workspace_root, &policy);
    let srv_low = server.trim().to_ascii_lowercase();
    let trusted = json_lower_list(&policy, "trusted_servers");
    if mode == "balanced" && (trusted.iter().any(|t| t == &srv_low) || srv_low.contains("lsp") || tier == "read") {
        return None;
    }
    if corrupt {
        return Some(deny_quarantined_mcp(workspace_root, sid, &server, &tool_name, tier, true));
    }
    let sha = canonical_schema_sha256(norm.args.get("_mcp_schema"));
    if lookup_approved_sha(&policy, &server, &tool_name, &norm.tool_name) == Some(sha.as_str()) {
        return None;
    }
    Some(deny_quarantined_mcp(workspace_root, sid, &server, &tool_name, tier, false))
}

fn collect_required_git_grants(violations: &[GitPolicyViolation]) -> Vec<&'static str> {
    let mut keys = Vec::new();
    for v in violations {
        if let Some(k) = v.required_grant() {
            if !keys.contains(&k) {
                keys.push(k);
            }
        }
    }
    keys
}

fn verify_turn_git_grants(workspace_root: &Path, sid: &str, needed: &[&str]) -> Option<RouteOutcome> {
    let Some(meta) = read_turn_meta(workspace_root, sid) else {
        return Some(deny_with_block(
            workspace_root,
            sid,
            "GIT",
            &format!("git `{}` requires explicit user approval in this turn before running.", needed[0]),
        ));
    };
    if meta.turn_closed {
        return Some(deny_with_block(
            workspace_root,
            sid,
            "GIT",
            &format!("Turn is closed; ask the user again in a new turn to approve git `{}`.", needed[0]),
        ));
    }
    if let Some(missing) = needed.iter().find(|k| !meta.git_grants.iter().any(|g| g == *k)) {
        return Some(deny_with_block(
            workspace_root,
            sid,
            "GIT",
            &format!("git `{}` requires explicit user approval in this turn before running.", missing),
        ));
    }
    if tdq_log_enabled() {
        eprintln!("[{}] tdq-dispatch: git_grant allowed sid={} grants={:?}", now_iso_utc(), sid, needed);
    }
    append_turn_row(
        workspace_root,
        sid,
        &serde_json::json!({ "ts": now_iso_utc(), "kind": "observe", "event": "git_grant_used", "session": sid, "grants": needed }),
    );
    None
}

fn check_git_command_gate(
    workspace_root: &Path,
    sid: &str,
    role_opt: Option<&str>,
    cmd: &str,
) -> Option<RouteOutcome> {
    let violations = collect_git_policy_violations(cmd);
    if violations.is_empty() {
        return None;
    }
    if violations.contains(&GitPolicyViolation::ForcePushForbidden) {
        return Some(deny_with_block(
            workspace_root,
            sid,
            "GIT",
            "Force-push (--force/-f/--force-with-lease/+refspec) is strictly forbidden.",
        ));
    }
    if violations.contains(&GitPolicyViolation::CoAuthoredTrailer) {
        return Some(deny_with_block(
            workspace_root,
            sid,
            "GIT",
            "AI co-author trailers are banned in commits.",
        ));
    }
    let needed = collect_required_git_grants(&violations);
    if needed.is_empty() {
        return None;
    }
    if role_opt.is_some() {
        return Some(deny_with_block(
            workspace_root,
            sid,
            "GIT",
            "Subagents cannot execute protected git commands even with user turn grant.",
        ));
    }
    verify_turn_git_grants(workspace_root, sid, &needed)
}

fn check_tick_gates(
    workspace_root: &Path,
    sid: &str,
    state: &TdqState,
    rel_target: &str,
    in_docs: bool,
) -> Result<Option<String>, RouteOutcome> {
    let low = rel_target.to_ascii_lowercase();
    let in_tests = low == "tests" || low.starts_with("tests/");
    let in_wt = low.contains(".tdq-worktrees/");
    if in_docs || in_tests || in_wt || !matches!(effective_phase(state), "implement" | "qc") {
        return Ok(None);
    }
    let tick = read_plan_tick_state(workspace_root, state);
    if tick.exists && tick.total > 0 && !tick.has_doing() && !tick.all_done() {
        return Err(deny_with_block(
            workspace_root,
            sid,
            "TICK",
            "No active [~] task in plan before editing code.",
        ));
    }
    if tick.exists && tick.doing_count > 1 {
        return Err(deny_with_block(
            workspace_root,
            sid,
            "TICK",
            "Multiple [~] tasks open; close old task before editing.",
        ));
    }
    if tick.exists && tick.doing_count == 1 {
        let streak = count_code_edits_for_sha(workspace_root, sid, &tick.sha);
        if streak >= 8 {
            return Err(deny_with_block(
                workspace_root,
                sid,
                "TICK",
                &format!("{} consecutive edits without plan update.", streak),
            ));
        }
        if (4..8).contains(&streak) {
            queue_remind_once(
                workspace_root,
                sid,
                "TICK",
                &format!("{}/8 source edits without plan tick.", streak),
            );
        }
        return Ok(Some(tick.sha));
    }
    Ok(None)
}

fn record_edit_observations(
    workspace_root: &Path,
    sid: &str,
    state: &TdqState,
    rel_target: &str,
    in_docs: bool,
    code_edit_sha: Option<String>,
) {
    append_turn_row(
        workspace_root,
        sid,
        &serde_json::json!({
            "ts": now_iso_utc(), "kind": "observe", "event": "edit", "session": sid, "path": rel_target,
        }),
    );
    let today_log = today_log_rel_for_state(Some(state));
    if rel_target == today_log {
        append_turn_row(
            workspace_root,
            sid,
            &serde_json::json!({
                "ts": now_iso_utc(), "kind": "observe", "event": "log_written", "session": sid, "path": rel_target,
            }),
        );
    } else if !in_docs && !workspace_root.join(&today_log).is_file() {
        queue_remind_once(
            workspace_root,
            sid,
            "LOG",
            &format!("Changed {} without {}", rel_target, today_log),
        );
    }
    if let Some(sha) = code_edit_sha {
        append_turn_row(
            workspace_root,
            sid,
            &serde_json::json!({
                "ts": now_iso_utc(), "kind": "observe", "event": "code_edit", "session": sid, "path": rel_target, "plan_sha": sha,
            }),
        );
    }
}

fn handle_edit_tool(
    workspace_root: &Path,
    norm: &NormalizedToolCall,
    sid: &str,
    role_opt: Option<&str>,
) -> RouteOutcome {
    let Some(raw_target) = norm.target_path() else {
        return RouteOutcome::Decided(HookDecision::allow());
    };
    if let Some(role) = role_opt {
        let qc_ok = role.to_ascii_lowercase().contains("qc-tester")
            && is_qc_report_target(raw_target, workspace_root);
        let scoped_ok = !qc_ok && is_investigation_artifact_target(raw_target, workspace_root, role);
        if qc_ok || scoped_ok {
            let obs_rel = resolve_rel_in_project(raw_target, workspace_root)
                .unwrap_or_else(|| raw_target.replace('\\', "/"));
            append_turn_row(
                workspace_root,
                sid,
                &serde_json::json!({
                    "ts": now_iso_utc(), "kind": "observe", "event": "edit", "session": sid, "path": obs_rel,
                }),
            );
            if scoped_ok {
                reset_burden_checkpoint(workspace_root, sid);
            }
            return RouteOutcome::Decided(HookDecision::allow());
        }
        if is_readonly_role(role) {
            return deny_with_block(
                workspace_root,
                sid,
                "READONLY",
                &format!(
                    "Read-only role `{}` cannot edit (artifacts/<slug>/ for explorer|debugger|reviewer; docs/tdq/qc/*.md for qc-tester).",
                    role
                ),
            );
        }
    }
    if is_state_target(raw_target, workspace_root) {
        return deny_with_block(
            workspace_root,
            sid,
            "STATE",
            "Direct edit of TDQ state is prohibited; use tdq_state.py.",
        );
    }
    let Some(rel_target) = resolve_rel_in_project(raw_target, workspace_root) else {
        return RouteOutcome::DelegatePython;
    };
    let low_rel = rel_target.to_ascii_lowercase();
    let in_docs = low_rel == "docs" || low_rel.starts_with("docs/");
    if !in_docs {
        if let Some(deny) = check_p0_runtime_guard(workspace_root, sid) {
            return deny;
        }
    }
    let Some(state) = read_tdq_state(workspace_root) else {
        append_turn_row(
            workspace_root,
            sid,
            &serde_json::json!({
                "ts": now_iso_utc(), "kind": "observe", "event": "edit", "session": sid, "path": rel_target,
            }),
        );
        return RouteOutcome::Decided(HookDecision::allow());
    };
    if state
        .active_request
        .as_deref()
        .unwrap_or("")
        .trim()
        .is_empty()
    {
        return RouteOutcome::Decided(HookDecision::allow());
    }
    if role_opt.is_some() || state.implement_mode.as_deref() == Some("subagent") {
        return RouteOutcome::DelegatePython;
    }
    if !in_docs {
        if let Some(gate) = cong_dang_cho(&state) {
            return deny_with_block(
                workspace_root,
                sid,
                "APPROVE",
                &format!("{} approval pending before editing source.", gate),
            );
        }
    }
    match check_tick_gates(workspace_root, sid, &state, &rel_target, in_docs) {
        Err(deny_outcome) => deny_outcome,
        Ok(code_sha) => {
            record_edit_observations(workspace_root, sid, &state, &rel_target, in_docs, code_sha);
            RouteOutcome::Decided(HookDecision::allow())
        }
    }
}

fn handle_command_tool(
    payload: &HookPayload,
    workspace_root: &Path,
    sid: &str,
    role_opt: Option<&str>,
) -> RouteOutcome {
    let Some(cmd) = payload.get_command() else {
        return RouteOutcome::Decided(HookDecision::allow());
    };
    if let Some(role) = role_opt.filter(|r| is_readonly_role(r)) {
        if is_shell_mutator(&cmd) {
            return deny_with_block(
                workspace_root,
                sid,
                "READONLY",
                &format!("Read-only subagent `{}` cannot mutate via shell.", role),
            );
        }
    }
    if mutates_tdq_state(&cmd) {
        return deny_with_block(
            workspace_root,
            sid,
            "STATE",
            "Do not mutate TDQ state via shell; use tdq_state.py.",
        );
    }
    if let Some(outcome) = check_git_command_gate(workspace_root, sid, role_opt, &cmd) {
        return outcome;
    }
    if let Some(violation) = inspect_command_safety(&cmd) {
        let outcome = match violation {
            CommandSafetyViolation::RemoteScriptExecution => Some(deny_with_block(
                workspace_root,
                sid,
                "VUNG",
                "Piping remote downloads to shell is forbidden.",
            )),
            CommandSafetyViolation::ExecutionPolicyBypass => Some(deny_with_block(
                workspace_root,
                sid,
                "VUNG",
                "PowerShell ExecutionPolicy bypass is blocked.",
            )),
            CommandSafetyViolation::GitPushForbidden
            | CommandSafetyViolation::GitDestructiveReset
            | CommandSafetyViolation::CoAuthoredTrailer => None,
        };
        if let Some(deny) = outcome {
            return deny;
        }
    }
    if let Some(bad_branch) = has_banned_ai_branch(&cmd) {
        return deny_with_block(
            workspace_root,
            sid,
            "GIT",
            &format!("AI-prefixed branch `{}` is banned.", bad_branch),
        );
    }
    if !is_p0_unlock_command(&cmd) {
        if let Some(deny) = check_p0_runtime_guard(workspace_root, sid) {
            return deny;
        }
    }
    if let Some(state) = read_tdq_state(workspace_root) {
        if !state
            .active_request
            .as_deref()
            .unwrap_or("")
            .trim()
            .is_empty()
        {
            if role_opt.is_some()
                && !matches!(effective_phase(&state), "implement" | "qc")
                && mutates_outside_docs(&cmd)
            {
                return RouteOutcome::DelegatePython;
            }
            let step3b_exempt = is_pure_intake_branch_create(&cmd)
                && matches!(effective_phase(&state), "analyze" | "idle");
            if role_opt.is_none() && mutates_outside_docs_any(&cmd) && !step3b_exempt {
                if let Some(gate) = cong_dang_cho(&state) {
                    return deny_with_block(
                        workspace_root,
                        sid,
                        "APPROVE",
                        &format!("{} has no recorded approval for shell write.", gate),
                    );
                }
            }
        }
    }
    if cmd.contains("tdq_team") && cmd.contains("evidence") && (cmd.contains(" add") || cmd.contains(" merge")) {
        reset_burden_checkpoint(workspace_root, sid);
    } else if is_graphify_shell_query(&cmd).is_some() {
        maybe_bump_burden(workspace_root, sid, 2);
    } else if !is_shell_mutator(&cmd) {
        maybe_bump_burden(workspace_root, sid, 1);
    }
    if needs_python_command_gate(&cmd) {
        return RouteOutcome::DelegatePython;
    }
    RouteOutcome::Decided(HookDecision::allow())
}

fn handle_read_tool(norm: &NormalizedToolCall, workspace_root: &Path, sid: &str) -> RouteOutcome {
    maybe_bump_burden(workspace_root, sid, 3);
    let has_range = ["StartLine", "EndLine", "offset", "limit", "ByteOffset"]
        .iter()
        .any(|k| norm.args.get(*k).is_some_and(|v| !v.is_null()));
    if has_range {
        return RouteOutcome::Decided(HookDecision::allow());
    }
    if let Some(raw_target) = norm.target_path() {
        let p = Path::new(raw_target);
        let full = if p.is_absolute() {
            p.to_path_buf()
        } else {
            workspace_root.join(p)
        };
        if fs::metadata(full).map(|m| m.len() <= 2048).unwrap_or(false) {
            return RouteOutcome::Decided(HookDecision::allow());
        }
    }
    RouteOutcome::DelegatePython
}

fn detect_unique_language_o1(dir: &Path) -> Option<&'static str> {
    let mut langs: Vec<&'static str> = Vec::new();
    if dir.join("Cargo.toml").is_file() {
        langs.push("rust");
    }
    if ["pyproject.toml", "requirements.txt", "Pipfile", "setup.py"]
        .iter()
        .any(|f| dir.join(f).is_file())
    {
        langs.push("python");
    }
    if ["tsconfig.json", "package.json", "jsconfig.json"]
        .iter()
        .any(|f| dir.join(f).is_file())
    {
        langs.push("typescript");
    }
    if dir.join("go.mod").is_file() {
        langs.push("go");
    }
    if langs.len() == 1 {
        Some(langs[0])
    } else {
        None
    }
}

fn handle_mcp_tool(workspace_root: &Path, norm: &NormalizedToolCall, sid: &str) -> RouteOutcome {
    let op = norm
        .tool_name
        .rsplit_once("__")
        .map(|(_, r)| r)
        .unwrap_or(&norm.tool_name);
    let op = op.rsplit_once('.').map(|(_, r)| r).unwrap_or(op);
    if op == "blast_radius" {
        return RouteOutcome::DelegatePython;
    }
    if op == "start_lsp" {
        let lang = norm
            .args
            .get("language_id")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim();
        let goc = norm
            .args
            .get("root_dir")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim();
        if lang.is_empty() {
            let root = if goc.is_empty() {
                workspace_root.to_path_buf()
            } else {
                PathBuf::from(goc)
            };
            if let Some(det) = detect_unique_language_o1(&root) {
                let mut patch = serde_json::json!({ "language_id": det });
                if goc.is_empty() {
                    patch["root_dir"] =
                        serde_json::Value::String(workspace_root.to_string_lossy().into_owned());
                }
                return RouteOutcome::Decided(
                    HookDecision::allow().with_overwrite(norm.wrap_overwrite(patch)),
                );
            }
            return RouteOutcome::DelegatePython;
        }
        return RouteOutcome::Decided(HookDecision::allow());
    }
    if let Some(deny) = evaluate_non_lsp_mcp_rust(workspace_root, norm, sid) {
        return deny;
    }
    if matches!(
        op,
        "tavily_extract" | "tavily_crawl" | "tavily_map" | "navigate_page" | "take_snapshot" | "click" | "fill" | "evaluate_script"
    ) || norm.server_name.as_deref().unwrap_or("").contains("chrome-devtools")
    {
        maybe_bump_burden(workspace_root, sid, 3);
    } else if matches!(op, "tavily_search" | "tavily_research") {
        maybe_bump_burden(workspace_root, sid, 2);
    }
    if let Some(label) = extract_concept_label(norm, None) {
        maybe_bump_burden(workspace_root, sid, 2);
        let state = read_tdq_state(workspace_root);
        let khoa = khoa_hien_tai(state.as_ref(), sid);
        let _ = append_jsonl_record(
            &search_ledger_path(workspace_root),
            &serde_json::json!({
                "ts": unix_timestamp_f64(), "khoa": khoa, "loai": "khai_niem", "cong_cu": label, "su_kien": "PreToolUse",
            }),
        );
        append_turn_row(
            workspace_root,
            sid,
            &serde_json::json!({
                "ts": now_iso_utc(), "kind": "observe", "event": "search_grace", "type": "search_grace", "state": "reset", "session": sid, "tool": norm.tool_name,
            }),
        );
    }
    RouteOutcome::Decided(HookDecision::allow())
}

/// Handle Antigravity PreToolUse event across Hot-path Rust and Cold-path Python.
pub fn handle_pre_tool_use(payload: &HookPayload, workspace_root: &Path) -> RouteOutcome {
    let sid = payload.canonical_session_id();
    let norm = payload.normalize_tool_call();
    let tname = norm.tool_name.as_str();
    let role_opt = detect_subagent_role(payload, workspace_root, &sid);

    if matches!(
        tname,
        "ask_question" | "ask_user_question" | "AskUserQuestion"
    ) {
        return deny_with_block(
            workspace_root,
            &sid,
            "ZERO-POPUP",
            "Ask numbered choices in chat; popup UI is blocked.",
        );
    }
    if matches!(
        tname,
        "edit_file"
            | "write_to_file"
            | "write_file"
            | "replace_file_content"
            | "multi_replace_file_content"
            | "notebook_edit"
            | "Edit"
            | "Write"
            | "MultiEdit"
            | "NotebookEdit"
    ) {
        return handle_edit_tool(workspace_root, &norm, &sid, role_opt.as_deref());
    }
    if matches!(tname, "run_command" | "Bash" | "PowerShell") {
        return handle_command_tool(payload, workspace_root, &sid, role_opt.as_deref());
    }
    if matches!(tname, "read_file" | "view_file" | "Read") {
        return handle_read_tool(&norm, workspace_root, &sid);
    }
    if matches!(tname, "grep_search" | "search_directory" | "Grep" | "find_by_name") {
        maybe_bump_burden(workspace_root, &sid, 2);
        return RouteOutcome::DelegatePython;
    }
    if tname == "search_web" {
        maybe_bump_burden(workspace_root, &sid, 2);
        return RouteOutcome::Decided(HookDecision::allow());
    }
    if matches!(tname, "read_url_content" | "view_content_chunk") || tname.starts_with("browser_") {
        maybe_bump_burden(workspace_root, &sid, 3);
        return RouteOutcome::Decided(HookDecision::allow());
    }
    if matches!(
        tname,
        "invoke_subagent" | "swarm" | "define_subagent" | "Task" | "Agent"
    ) {
        return RouteOutcome::DelegatePython;
    }
    if norm.is_mcp_wrapper || tname.starts_with("mcp_") || tname.starts_with("lsp.") {
        return handle_mcp_tool(workspace_root, &norm, &sid);
    }
    RouteOutcome::Decided(HookDecision::allow())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::protocol::DecisionKind;
    use serde_json::json;

    #[test]
    fn test_pre_tool_use_security_and_hardening_gates() {
        let tmp = std::env::temp_dir().join(format!("tdq_pre_tool_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq").join("plan"));
        fs::write(tmp.join("Cargo.toml"), "[package]\nname=\"demo\"").unwrap();

        let git_push = HookPayload {
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "git push origin dev" })),
            ..Default::default()
        };
        assert!(
            matches!(handle_pre_tool_use(&git_push, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:GIT]"))
        );

        let qc_write = HookPayload {
            agent_type: Some("tdq-qc-tester".to_string()),
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "Set-Content app.py bad" })),
            ..Default::default()
        };
        assert!(
            matches!(handle_pre_tool_use(&qc_write, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]"))
        );

        let qc_allow_md = HookPayload {
            agent_type: Some("tdq-qc-tester".to_string()),
            tool_name: Some("write_to_file".to_string()),
            tool_input: Some(json!({ "TargetFile": "docs/tdq/qc/2026-11-20-q1.md" })),
            ..Default::default()
        };
        assert!(
            matches!(handle_pre_tool_use(&qc_allow_md, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Allow)
        );

        let qc_block_trav = HookPayload {
            agent_type: Some("tdq-qc-tester".to_string()),
            tool_name: Some("write_to_file".to_string()),
            tool_input: Some(json!({ "TargetFile": "docs/tdq/qc/../../a.py" })),
            ..Default::default()
        };
        assert!(
            matches!(handle_pre_tool_use(&qc_block_trav, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]"))
        );

        for ro_role in &["tdq-explorer", "tdq-debugger"] {
            let deny_ro = HookPayload {
                agent_type: Some((*ro_role).to_string()),
                tool_name: Some("write_to_file".to_string()),
                tool_input: Some(json!({ "TargetFile": "docs/tdq/qc/2026-11-20-q1.md" })),
                ..Default::default()
            };
            assert!(
                matches!(handle_pre_tool_use(&deny_ro, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]"))
            );
        }

        let state_edit = HookPayload {
            tool_name: Some("write_to_file".to_string()),
            tool_input: Some(
                json!({ "TargetFile": tmp.join("docs/tdq/state.json").to_string_lossy() }),
            ),
            ..Default::default()
        };
        assert!(
            matches!(handle_pre_tool_use(&state_edit, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:STATE]"))
        );

        // TICK 0 [~] hard deny on edit
        fs::write(tmp.join("docs/tdq/state.json"), r#"{"active_request":"r1","phase":"implement","lane":"full","spec_approved":true,"plan_approved":true,"plan_file":"docs/tdq/plan/r1.md"}"#).unwrap();
        fs::write(tmp.join("docs/tdq/plan/r1.md"), "- [ ] **T1** open\n").unwrap();
        let tick0 = HookPayload {
            tool_name: Some("edit_file".to_string()),
            tool_input: Some(json!({ "TargetFile": tmp.join("src.py").to_string_lossy() })),
            ..Default::default()
        };
        assert!(
            matches!(handle_pre_tool_use(&tick0, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:TICK]"))
        );

        // call_mcp_tool start_lsp overwrite preserving string Arguments
        let mcp_lsp = HookPayload {
            tool_name: Some("call_mcp_tool".to_string()),
            tool_input: Some(
                json!({ "ServerName": "lsp", "ToolName": "start_lsp", "Arguments": json!({"root_dir": tmp.to_string_lossy()}).to_string() }),
            ),
            ..Default::default()
        };
        match handle_pre_tool_use(&mcp_lsp, &tmp) {
            RouteOutcome::Decided(d) => {
                let ov = d.overwrite.unwrap();
                assert!(ov["Arguments"].as_str().unwrap_or("").contains("rust"));
            }
            RouteOutcome::DelegatePython => panic!("expected rust overwrite"),
        }

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_scoped_write_5_layer_and_weighted_burden_sid_isolation() {
        let tmp = std::env::temp_dir().join(format!("tdq_v2_rust_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq").join("artifacts").join("inv1"));
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq").join("research"));
        fs::write(
            tmp.join("docs").join("tdq").join("state.json"),
            r#"{"active_request":"inv1","phase":"implement","lane":"full","spec_approved":true,"plan_approved":true,"work_kind":"investigate"}"#,
        )
        .unwrap();

        // 1. Valid scoped-write by tdq-explorer must Allow directly & log observe("edit")
        let allow_shard = HookPayload {
            conversation_id: Some("worker-a".to_string()),
            agent_type: Some("tdq-explorer".to_string()),
            tool_name: Some("write_to_file".to_string()),
            tool_input: Some(json!({ "TargetFile": "docs/tdq/artifacts/inv1/nested/deep/shard.md" })),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_tool_use(&allow_shard, &tmp),
            RouteOutcome::Decided(d) if d.decision == DecisionKind::Allow
        ));
        assert!(crate::storage::read_turn_rows(&tmp, "worker-a").iter().any(|r| r.get("event").and_then(|v| v.as_str()) == Some("edit")));

        // 2. Security-reviewer, browser, empty/subagent, denylist, wrong slug, traversal MUST Deny [TDQ:READONLY]
        let deny_cases = [
            ("tdq-security-reviewer", "docs/tdq/artifacts/inv1/shard.md"),
            ("tdq-browser", "docs/tdq/artifacts/inv1/shard.md"),
            ("tdq-explorer", "docs/tdq/artifacts/inv1/evidence.jsonl"),
            ("tdq-explorer", "docs/tdq/artifacts/inv1/trial_1.json"),
            ("tdq-explorer", "docs/tdq/artifacts/inv1/rec_01.json"),
            ("tdq-explorer", "docs/tdq/artifacts/inv1/bad.py"),
            ("tdq-explorer", "docs/tdq/artifacts/other/shard.md"),
            ("tdq-explorer", "docs/tdq/artifacts/inv1/sub/../../outside.md"),
            ("tdq-explorer", "docs/tdq/research/inv1/nested.md"),
        ];
        for (role, path) in deny_cases {
            let p = HookPayload {
                conversation_id: Some("sec-check".to_string()),
                agent_type: Some(role.to_string()),
                tool_name: Some("write_to_file".to_string()),
                tool_input: Some(json!({ "TargetFile": path })),
                ..Default::default()
            };
            assert!(
                matches!(handle_pre_tool_use(&p, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")),
                "Expected READONLY deny for role={} path={}",
                role,
                path
            );
        }

        // 3. Weighted Burden Counter per sid: 14 ranged reads -> >=40pts -> [TDQ:DOC] queued, worker-b isolated
        for i in 0..14 {
            let rp = HookPayload {
                conversation_id: Some("worker-a".to_string()),
                tool_name: Some("view_file".to_string()),
                tool_input: Some(json!({ "AbsolutePath": tmp.join(format!("f{}.py", i)).to_string_lossy(), "StartLine": 1, "EndLine": 10 })),
                ..Default::default()
            };
            assert!(matches!(handle_pre_tool_use(&rp, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Allow));
        }
        let rem_a = crate::storage::pending_reminders_path(&tmp, "worker-a");
        assert!(rem_a.is_file(), "Expected [TDQ:DOC] queued after 42 burden points");
        assert!(fs::read_to_string(&rem_a).unwrap_or_default().contains("DOC"));

        // worker-b shard write must NOT reset worker-a
        let wb = HookPayload {
            conversation_id: Some("worker-b".to_string()),
            agent_type: Some("tdq-debugger".to_string()),
            tool_name: Some("write_to_file".to_string()),
            tool_input: Some(json!({ "TargetFile": "docs/tdq/artifacts/inv1/wb.md" })),
            ..Default::default()
        };
        assert!(matches!(handle_pre_tool_use(&wb, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Allow));
        let cp_a = fs::read_to_string(crate::storage::get_runtime_dir(&tmp).join("checkpoint-worker-a.json")).unwrap_or_default();
        assert!(cp_a.contains("42"));

        // worker-a shard write resets worker-a checkpoint
        assert!(matches!(handle_pre_tool_use(&allow_shard, &tmp), RouteOutcome::Decided(d) if d.decision == DecisionKind::Allow));
        let cp_a_after = fs::read_to_string(crate::storage::get_runtime_dir(&tmp).join("checkpoint-worker-a.json")).unwrap_or_default();
        assert!(cp_a_after.contains(":0"));

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_git_turn_grants_runtime_lock_and_step3b_exemption() {
        let tmp = std::env::temp_dir().join(format!("tdq_git_grant_gate_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(crate::storage::get_runtime_dir(&tmp));
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq").join("spec"));

        let rt = crate::storage::get_runtime_dir(&tmp);
        fs::write(
            rt.join("turn-meta-g1.json"),
            r#"{"turn_closed":false,"git_grants":["push"]}"#,
        )
        .unwrap();

        let allow_push = HookPayload {
            conversation_id: Some("g1".to_string()),
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "git push origin dev" })),
            ..Default::default()
        };
        assert!(!matches!(
            handle_pre_tool_use(&allow_push, &tmp),
            RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Deny
        ));
        assert!(crate::storage::read_turn_rows(&tmp, "g1").iter().any(|r| {
            r.get("kind").and_then(|v| v.as_str()) == Some("observe")
                && r.get("event").and_then(|v| v.as_str()) == Some("git_grant_used")
        }));

        for (cmd, needle) in [
            ("git reset --hard HEAD~1", "reset_hard"),
            ("git push --force origin dev", "Force-push"),
            ("git push origin dev && git reset --hard HEAD~1", "[TDQ:GIT]"),
            (r#"git commit -m "feat: x" -m "Co-Authored-By: Claude""#, "[TDQ:GIT]"),
        ] {
            let p = HookPayload {
                conversation_id: Some("g1".to_string()),
                tool_name: Some("run_command".to_string()),
                arguments: Some(json!({ "CommandLine": cmd })),
                ..Default::default()
            };
            assert!(
                matches!(handle_pre_tool_use(&p, &tmp), RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:GIT]") && d.reason.as_deref().unwrap_or("").contains(needle)),
                "Expected deny containing [TDQ:GIT] and {} for cmd={}",
                needle,
                cmd
            );
        }

        let sub_push = HookPayload {
            conversation_id: Some("g1".to_string()),
            agent_type: Some("tdq-implementer".to_string()),
            ..allow_push.clone()
        };
        assert!(
            matches!(handle_pre_tool_use(&sub_push, &tmp), RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:GIT]"))
        );

        fs::write(rt.join("turn-meta-g_closed.json"), r#"{"turn_closed":true,"git_grants":["push"]}"#).unwrap();
        fs::write(rt.join("turn-meta-g_corrupt.json"), "{corrupt-json").unwrap();
        for sid in ["g_closed", "g_corrupt"] {
            let p = HookPayload {
                conversation_id: Some(sid.to_string()),
                ..allow_push.clone()
            };
            assert!(
                matches!(handle_pre_tool_use(&p, &tmp), RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:GIT]"))
            );
        }

        for (tool, key, target) in [
            ("write_to_file", "TargetFile", "docs/tdq/.tdq-runtime/turn-meta-1.json"),
            ("edit_file", "TargetFile", r"docs\tdq\.tdq-runtime\turn-meta-1.json"),
            ("write_to_file", "TargetFile", "docs/tdq/spec/../.tdq-runtime/turn-meta-1.json"),
        ] {
            let p = HookPayload {
                tool_name: Some(tool.to_string()),
                tool_input: Some(json!({ key: target })),
                ..Default::default()
            };
            assert!(
                matches!(handle_pre_tool_use(&p, &tmp), RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:STATE]")),
                "Expected [TDQ:STATE] deny for {}",
                target
            );
        }

        fs::write(
            tmp.join("docs/tdq/state.json"),
            r#"{"active_request":"req1","phase":"analyze","spec_approved":false,"plan_approved":false}"#,
        )
        .unwrap();
        let step3b_ok = HookPayload {
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "git switch -c feature/demo" })),
            ..Default::default()
        };
        assert!(!matches!(
            handle_pre_tool_use(&step3b_ok, &tmp),
            RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Deny
        ));

        for (cmd, code) in [
            ("git switch -c feature/demo; echo a > src/x.py", "[TDQ:APPROVE]"),
            ("git switch -c claude-bad", "[TDQ:GIT]"),
        ] {
            let p = HookPayload {
                tool_name: Some("run_command".to_string()),
                arguments: Some(json!({ "CommandLine": cmd })),
                ..Default::default()
            };
            assert!(
                matches!(handle_pre_tool_use(&p, &tmp), RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains(code)),
                "Expected {} for {}",
                code,
                cmd
            );
        }

        fs::write(
            tmp.join("docs/tdq/state.json"),
            r#"{"active_request":"req1","phase":"spec","spec_file":"docs/tdq/spec/x.md","spec_approved":false,"plan_approved":false}"#,
        )
        .unwrap();
        assert!(
            matches!(handle_pre_tool_use(&step3b_ok, &tmp), RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Deny && d.reason.as_deref().unwrap_or("").contains("[TDQ:APPROVE]"))
        );

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_p0_mcp_quarantine_and_breaker_guard() {
        let tmp = std::env::temp_dir().join(format!("tdq_p0_guard_rust_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        fs::create_dir_all(tmp.join("docs").join("tdq")).unwrap();

        // 1. Unknown non-LSP read tool -> Allow
        let read_mcp = HookPayload {
            tool_name: Some("call_mcp_tool".to_string()),
            tool_input: Some(json!({ "ServerName": "github", "ToolName": "get_issue", "Arguments": "{}" })),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_tool_use(&read_mcp, &tmp),
            RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Allow
        ));

        // 2. Unapproved non-LSP write tool -> Deny [TDQ:READONLY] with approve CLI hint
        let write_mcp = HookPayload {
            tool_name: Some("mcp__github__create_issue".to_string()),
            tool_input: Some(json!({ "title": "bug" })),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_tool_use(&write_mcp, &tmp),
            RouteOutcome::Decided(ref d)
                if d.decision == DecisionKind::Deny
                && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
                && d.reason.as_deref().unwrap_or("").contains("mcp_policy.py")
        ));
        let eager_lsp = HookPayload {
            tool_name: Some("mcp_other_lsp_start_lsp".to_string()),
            tool_input: Some(json!({ "root_dir": tmp.to_string_lossy() })),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_tool_use(&eager_lsp, &tmp),
            RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Allow
        ));
        let eager_tavily = HookPayload {
            tool_name: Some("mcp_tdq-workflow-agy_tavily-primary_tavily_search".to_string()),
            tool_input: Some(json!({ "query": "tdq" })),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_tool_use(&eager_tavily, &tmp),
            RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Allow
        ));
        let evil_lsp_bypass = HookPayload {
            tool_name: Some("mcp_evil_delete_lsp_entry".to_string()),
            tool_input: Some(json!({})),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_tool_use(&evil_lsp_bypass, &tmp),
            RouteOutcome::Decided(ref d)
                if d.decision == DecisionKind::Deny
                && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
        ));

        // 3. Approved baseline matching SHA-256 -> Allow
        let norm_write = write_mcp.normalize_tool_call();
        let mut hasher = Sha256::new();
        hasher.update(b"{}");
        let empty_sha = format!("{:x}", hasher.finalize());
        let policy_json = json!({
            "approved_tools": {
                "github::create_issue": { "sha256": empty_sha, "tier": "write" },
                "github::mcp__github__create_issue": { "sha256": empty_sha, "tier": "write" }
            }
        });
        fs::write(tmp.join("docs/tdq/mcp-policy.json"), policy_json.to_string()).unwrap();
        assert!(evaluate_non_lsp_mcp_rust(&tmp, &norm_write, "s1").is_none());
        assert!(matches!(
            handle_pre_tool_use(&write_mcp, &tmp),
            RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Allow
        ));

        // 3b. Schema mutation re-quarantines approved write tool
        let mutated_mcp = HookPayload {
            tool_name: Some("mcp__github__create_issue".to_string()),
            tool_input: Some(json!({ "title": "bug", "_mcp_schema": { "type": "object", "v": 2 } })),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_tool_use(&mutated_mcp, &tmp),
            RouteOutcome::Decided(ref d)
                if d.decision == DecisionKind::Deny
                && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
        ));

        // 4. Corrupt project policy -> fail-closed [TDQ:READONLY] on write, Allow on read
        fs::write(tmp.join("docs/tdq/mcp-policy.json"), "{corrupt").unwrap();
        assert!(matches!(
            handle_pre_tool_use(&write_mcp, &tmp),
            RouteOutcome::Decided(ref d)
                if d.decision == DecisionKind::Deny
                && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
        ));
        assert!(matches!(
            handle_pre_tool_use(&read_mcp, &tmp),
            RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Allow
        ));

        // 5. Kill-switch mcp_quarantine_enabled=false -> Allow unapproved write
        fs::write(
            tmp.join("docs/tdq/config.json"),
            r#"{"p0":{"mcp_quarantine_enabled":false,"breaker_enabled":true}}"#,
        )
        .unwrap();
        assert!(matches!(
            handle_pre_tool_use(&write_mcp, &tmp),
            RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Allow
        ));

        // 6. Circuit breaker open blocks source edit + normal shell, allows docs edit & reset-breaker
        fs::write(
            tmp.join("docs/tdq/state.json"),
            r#"{"active_request":"r1","phase":"implement","lane":"full","spec_approved":true,"plan_approved":true,"p0_runtime":{"breaker":{"open":true,"consecutive_failures":3},"budget":{"hard_stopped":false}}}"#,
        )
        .unwrap();
        let src_edit = HookPayload {
            tool_name: Some("edit_file".to_string()),
            tool_input: Some(json!({ "TargetFile": tmp.join("scripts/app.py").to_string_lossy() })),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_tool_use(&src_edit, &tmp),
            RouteOutcome::Decided(ref d)
                if d.decision == DecisionKind::Deny
                && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
        ));
        let shell_cmd = HookPayload {
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "py -3 -m pytest" })),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_tool_use(&shell_cmd, &tmp),
            RouteOutcome::Decided(ref d)
                if d.decision == DecisionKind::Deny
                && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
        ));
        let unlock_cmd = HookPayload {
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "py -3 scripts/tdq_state.py reset-breaker" })),
            ..Default::default()
        };
        assert!(!matches!(
            handle_pre_tool_use(&unlock_cmd, &tmp),
            RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Deny
        ));
        let chained_unlock_cmd = HookPayload {
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "py -3 scripts/tdq_state.py reset-breaker && rm -rf /" })),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_tool_use(&chained_unlock_cmd, &tmp),
            RouteOutcome::Decided(ref d)
                if d.decision == DecisionKind::Deny
                && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
        ));
        for bypass_cmd in [
            "py -3 scripts/tdq_state.py reset-breaker & rm -rf /",
            "py -3 scripts/tdq_state.py reset-breaker\rrm -rf /",
            "rm -rf / # tdq_state reset-breaker",
            "py -3 scripts/tdq_state.py reset-breaker > evil.py",
            "rm -rf / tdq_state.py reset-breaker",
            r#"python -c "evil()" scripts/tdq_state.py reset-breaker"#,
        ] {
            let bypass_payload = HookPayload {
                tool_name: Some("run_command".to_string()),
                arguments: Some(json!({ "CommandLine": bypass_cmd })),
                ..Default::default()
            };
            assert!(
                matches!(
                    handle_pre_tool_use(&bypass_payload, &tmp),
                    RouteOutcome::Decided(ref d)
                        if d.decision == DecisionKind::Deny
                        && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
                ),
                "Expected unlock bypass denial for {}",
                bypass_cmd
            );
        }
        let approve_cmd = HookPayload {
            tool_name: Some("run_command".to_string()),
            arguments: Some(json!({ "CommandLine": "py -3 scripts/mcp_policy.py approve github create_issue" })),
            ..Default::default()
        };
        assert!(!matches!(
            handle_pre_tool_use(&approve_cmd, &tmp),
            RouteOutcome::Decided(ref d) if d.decision == DecisionKind::Deny
        ));

        // 7. Budget hard_stopped blocks edits even when breaker is closed
        fs::write(
            tmp.join("docs/tdq/state.json"),
            r#"{"active_request":"r1","phase":"implement","lane":"full","spec_approved":true,"plan_approved":true,"p0_runtime":{"breaker":{"open":false,"consecutive_failures":0},"budget":{"hard_stopped":true}}}"#,
        )
        .unwrap();
        assert!(matches!(
            handle_pre_tool_use(&src_edit, &tmp),
            RouteOutcome::Decided(ref d)
                if d.decision == DecisionKind::Deny
                && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
        ));

        // 8. Live telemetry exceeding hard_stop_tokens blocks edits and shell even when hard_stopped=false
        fs::write(
            tmp.join("docs/tdq/state.json"),
            r#"{"active_request":"r1","phase":"implement","lane":"full","spec_approved":true,"plan_approved":true,"p0_runtime":{"breaker":{"open":false,"consecutive_failures":0},"budget":{"hard_stopped":false}}}"#,
        )
        .unwrap();
        fs::write(
            tmp.join("docs/tdq/config.json"),
            r#"{"p0":{"breaker_enabled":true,"budget_caps":{"soft_warn_ratio":0.8,"hard_stop_tokens":100,"hard_stop_usd":null}}}"#,
        )
        .unwrap();
        fs::write(
            tmp.join("docs/tdq/.tdq-agent-telemetry.jsonl"),
            "{\"tokens\":200,\"cost_usd\":0.01}\n",
        )
        .unwrap();
        assert!(matches!(
            handle_pre_tool_use(&src_edit, &tmp),
            RouteOutcome::Decided(ref d)
                if d.decision == DecisionKind::Deny
                && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
        ));
        assert!(matches!(
            handle_pre_tool_use(&shell_cmd, &tmp),
            RouteOutcome::Decided(ref d)
                if d.decision == DecisionKind::Deny
                && d.reason.as_deref().unwrap_or("").contains("[TDQ:READONLY]")
        ));

        let _ = fs::remove_dir_all(&tmp);
    }
}
