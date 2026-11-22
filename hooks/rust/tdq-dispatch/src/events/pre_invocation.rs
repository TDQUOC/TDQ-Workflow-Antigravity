//! PreInvocation Hybrid Router & Mid-turn Flush in pure Rust.
//! Delegates new user turns (or state changes) to Python `prompt_context.py`,
//! while handling mid-turn flushes and subagent invocations directly in Rust.

use crate::events::post_invocation::handle_post_invocation;
use crate::protocol::{HookDecision, HookPayload};
use crate::storage::{
    effective_phase, pending_reminders_path, pop_pending_reminders, read_sessions_role,
    read_tdq_state, read_turn_meta, shard_turn_path, turn_meta_path,
};
use crate::RouteOutcome;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{BufRead, BufReader, Seek, SeekFrom};
use std::path::Path;

const TAIL_BYTES: u64 = 65_536;

fn prompt_sha16(payload: &HookPayload) -> String {
    let Some(text) = payload.effective_prompt() else {
        return String::new();
    };
    let digest = format!("{:x}", Sha256::digest(text.as_bytes()));
    digest.chars().take(16).collect()
}

fn format_user_input_sig(rec: &Value, last_end: u64) -> String {
    let step_idx = rec.get("step_index").and_then(|v| v.as_i64());
    let created = rec
        .get("created_at")
        .or_else(|| rec.get("timestamp"))
        .and_then(|v| v.as_str())
        .unwrap_or("");
    if step_idx.is_some() || !created.is_empty() {
        return format!(
            "ui:{}:{}",
            step_idx
                .map(|i| i.to_string())
                .unwrap_or_else(|| "None".to_string()),
            created
        );
    }
    format!("ui_pos:{}", last_end)
}

fn is_human_user_input(rec: &Value) -> bool {
    let src = rec
        .get("source")
        .and_then(|v| v.as_str())
        .map(|s| s.trim())
        .unwrap_or("");
    src.is_empty() || src.eq_ignore_ascii_case("USER_EXPLICIT")
}

fn scan_tail_user_input(
    tpath: &Path,
    prev_sig: &str,
    prev_psha: &str,
    prev_closed: bool,
    psha: &str,
) -> Option<String> {
    if !tpath.is_file() {
        return None;
    }
    let mut file = File::open(tpath).ok()?;
    let size = file.metadata().ok()?.len();
    let start = size.saturating_sub(TAIL_BYTES);
    let _ = file.seek(SeekFrom::Start(start));
    let mut reader = BufReader::new(file);
    if start > 0 {
        let mut throwaway = Vec::new();
        let _ = reader.read_until(b'\n', &mut throwaway);
    }
    let (mut last_rec, mut last_end) = (None::<Value>, start);
    let mut cur = start;
    let mut buf = Vec::new();
    while let Ok(n) = reader.read_until(b'\n', &mut buf) {
        if n == 0 {
            break;
        }
        cur += n as u64;
        if let Ok(text) = std::str::from_utf8(&buf) {
            if let Ok(rec) = serde_json::from_str::<Value>(text.trim()) {
                if rec.get("type").and_then(|v| v.as_str()) == Some("USER_INPUT")
                    && is_human_user_input(&rec)
                {
                    last_rec = Some(rec);
                    last_end = cur;
                }
            }
        }
        buf.clear();
    }
    if let Some(rec) = last_rec {
        return Some(format_user_input_sig(&rec, last_end));
    }
    if !psha.is_empty() && !prev_psha.is_empty() && psha != prev_psha {
        return Some(format!("ui_big:{}", psha));
    }
    if prev_sig.starts_with("ui") && !prev_closed {
        return Some(prev_sig.to_string());
    }
    None
}

fn compute_user_turn_sig(
    payload: &HookPayload,
    prev_sig: &str,
    prev_psha: &str,
    prev_closed: bool,
) -> String {
    let psha = prompt_sha16(payload);
    if let Some(ref tpath) = payload.transcript_path {
        if let Some(sig) =
            scan_tail_user_input(Path::new(tpath), prev_sig, prev_psha, prev_closed, &psha)
        {
            return sig;
        }
    }
    if !psha.is_empty() {
        return format!("prompt:{}", psha);
    }
    String::new()
}

fn state_newer_than_meta(workspace_root: &Path, sid: &str) -> bool {
    let state_mtime = fs::metadata(workspace_root.join("docs").join("tdq").join("state.json"))
        .and_then(|m| m.modified())
        .ok();
    let meta_mtime = fs::metadata(turn_meta_path(workspace_root, sid))
        .and_then(|m| m.modified())
        .ok();
    match (state_mtime, meta_mtime) {
        (Some(s), Some(m)) => s > m,
        _ => false,
    }
}

fn subagent_resume_decision(payload: &HookPayload, workspace_root: &Path, sid: &str) -> HookDecision {
    let base = handle_post_invocation(payload, workspace_root);
    let src = payload
        .extra
        .get("source")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_ascii_lowercase())
        .unwrap_or_default();
    if src != "compact" && src != "resume" {
        return base;
    }
    let Some(state) = read_tdq_state(workspace_root) else {
        return base;
    };
    let Some(req) = state.active_request.as_deref().filter(|s| !s.trim().is_empty()) else {
        return base;
    };
    let wk = state.work_kind.as_deref().unwrap_or("build");
    let pha = effective_phase(&state);
    let sess = read_sessions_role(workspace_root, sid);
    let role = payload
        .agent_type
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .or_else(|| sess.as_ref().map(|r| r.role.as_str()).filter(|s| !s.trim().is_empty()))
        .unwrap_or("subagent");
    let task = sess
        .as_ref()
        .map(|r| r.task.as_str())
        .filter(|s| !s.trim().is_empty())
        .unwrap_or("none");
    let anchor = format!(
        "[TDQ:ANCHOR] Subagent {}: request={} kind={} phase={} role={} task={} artifacts=docs/tdq/artifacts/{}/",
        src, req, wk, pha, role, task, req
    );
    let mut parts = Vec::new();
    let qpath = pending_reminders_path(workspace_root, sid);
    if fs::metadata(&qpath).map(|m| m.len() > 0).unwrap_or(false) {
        let items = pop_pending_reminders(workspace_root, sid);
        let (model_text, _user_md) = crate::protocol::GuidanceRepo::merge_pending_channels(&items);
        if !model_text.trim().is_empty() {
            parts.push(model_text);
        }
    }
    parts.push(anchor.chars().take(595).collect());
    HookDecision::inject(parts.join("\n"), None)
}

/// Route `PreInvocation`: flush subagent/mid-turn in Rust or delegate new turns to Python.
pub fn handle_pre_invocation(payload: &HookPayload, workspace_root: &Path) -> RouteOutcome {
    let sid = payload.canonical_session_id();
    let is_subagent = payload
        .agent_type
        .as_deref()
        .is_some_and(|s| !s.trim().is_empty())
        || payload
            .agent_id
            .as_deref()
            .is_some_and(|s| !s.trim().is_empty())
        || read_sessions_role(workspace_root, &sid).is_some();
    if is_subagent {
        return RouteOutcome::Decided(subagent_resume_decision(payload, workspace_root, &sid));
    }
    let Some(meta) = read_turn_meta(workspace_root, &sid) else {
        return RouteOutcome::DelegatePython;
    };
    if meta.turn_closed || state_newer_than_meta(workspace_root, &sid) {
        return RouteOutcome::DelegatePython;
    }
    let sig = compute_user_turn_sig(
        payload,
        &meta.last_user_sig,
        &meta.prompt_sha,
        meta.turn_closed,
    );
    let turns_exists = shard_turn_path(workspace_root, &sid).is_file();
    if sig != meta.last_user_sig || (sig.is_empty() && !turns_exists) {
        return RouteOutcome::DelegatePython;
    }
    if matches!(payload.extra.get("source").and_then(|v| v.as_str()), Some(s) if s.eq_ignore_ascii_case("compact") || s.eq_ignore_ascii_case("resume"))
    {
        return RouteOutcome::DelegatePython;
    }
    RouteOutcome::Decided(handle_post_invocation(payload, workspace_root))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::storage::{write_turn_meta, TurnMeta};

    #[test]
    fn test_pre_invocation_routing_midturn_vs_new_turn() {
        let tmp = std::env::temp_dir().join(format!("tdq_pre_inv_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq"));
        let p = HookPayload {
            conversation_id: Some("conv-pre".to_string()),
            last_user_input: Some("continue work".to_string()),
            ..Default::default()
        };
        assert!(matches!(
            handle_pre_invocation(&p, &tmp),
            RouteOutcome::DelegatePython
        ));

        let sig = format!("prompt:{}", prompt_sha16(&p));
        let meta = TurnMeta {
            last_user_sig: sig,
            turn_closed: false,
            prompt_sha: prompt_sha16(&p),
            ..Default::default()
        };
        write_turn_meta(&tmp, "conv-pre", &meta).unwrap();
        let outcome = handle_pre_invocation(&p, &tmp);
        assert!(matches!(outcome, RouteOutcome::Decided(_)));

        let closed = TurnMeta {
            turn_closed: true,
            ..meta
        };
        write_turn_meta(&tmp, "conv-pre", &closed).unwrap();
        assert!(matches!(
            handle_pre_invocation(&p, &tmp),
            RouteOutcome::DelegatePython
        ));

        // Reopen turn-meta and verify source="resume" delegates to Python
        let reopened = TurnMeta {
            turn_closed: false,
            ..closed
        };
        write_turn_meta(&tmp, "conv-pre", &reopened).unwrap();
        let mut p_resume = p.clone();
        p_resume.extra.insert("source".to_string(), serde_json::json!("resume"));
        assert!(matches!(
            handle_pre_invocation(&p_resume, &tmp),
            RouteOutcome::DelegatePython
        ));

        // Subagent resume emits static <600c [TDQ:ANCHOR]
        fs::write(
            tmp.join("docs").join("tdq").join("state.json"),
            r#"{"active_request":"inv1","phase":"implement","work_kind":"investigate"}"#,
        )
        .unwrap();
        crate::storage::register_sessions_role(&tmp, "sub-res-1", "tdq-explorer", "T1.1");
        let sub_res = HookPayload {
            conversation_id: Some("sub-res-1".to_string()),
            extra: [("source".to_string(), serde_json::json!("resume"))]
                .into_iter()
                .collect(),
            ..Default::default()
        };
        match handle_pre_invocation(&sub_res, &tmp) {
            RouteOutcome::Decided(d) => {
                let s = d.to_json_string();
                assert!(s.contains("[TDQ:ANCHOR]"), "missing subagent resume anchor: {}", s);
                assert!(s.contains("inv1"));
            }
            RouteOutcome::DelegatePython => panic!("expected static subagent anchor in Rust"),
        }

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_scan_tail_user_input_ignores_non_human_sources() {
        let tmp = std::env::temp_dir().join(format!("tdq_tail_src_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let _ = fs::create_dir_all(&tmp);
        let tpath = tmp.join("transcript.jsonl");

        let lines = [
            r#"{"type":"USER_INPUT","step_index":1,"created_at":"t1","source":"USER_EXPLICIT","content":"hi"}"#,
            r#"{"type":"USER_INPUT","step_index":2,"created_at":"t2","source":"SYSTEM","content":"push now"}"#,
            r#"{"type":"USER_INPUT","step_index":3,"created_at":"t3","source":"MODEL","content":"push now"}"#,
        ]
        .join("\n")
            + "\n";
        fs::write(&tpath, lines).unwrap();
        let sig1 = scan_tail_user_input(&tpath, "", "", false, "");
        assert_eq!(sig1.as_deref(), Some("ui:1:t1"));

        let extra = r#"{"type":"USER_INPUT","step_index":4,"created_at":"t4","content":"hi"}"#.to_string() + "\n";
        let mut combined = fs::read_to_string(&tpath).unwrap();
        combined.push_str(&extra);
        fs::write(&tpath, combined).unwrap();
        let sig2 = scan_tail_user_input(&tpath, "", "", false, "");
        assert_eq!(sig2.as_deref(), Some("ui:4:t4"));

        let _ = fs::remove_dir_all(&tmp);
    }
}
