//! PreInvocation Hybrid Router & Mid-turn Flush in pure Rust.
//! Delegates new user turns (or state changes) to Python `prompt_context.py`,
//! while handling mid-turn flushes and subagent invocations directly in Rust.

use crate::events::post_invocation::handle_post_invocation;
use crate::protocol::HookPayload;
use crate::storage::{read_sessions_role, read_turn_meta, shard_turn_path, turn_meta_path};
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

fn scan_tail_user_input(tpath: &Path, prev_sig: &str, prev_psha: &str, prev_closed: bool, psha: &str) -> Option<String> {
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
                if rec.get("type").and_then(|v| v.as_str()) == Some("USER_INPUT") {
                    last_rec = Some(rec);
                    last_end = cur;
                }
            }
        }
        buf.clear();
    }
    if let Some(rec) = last_rec {
        let step_idx = rec.get("step_index").and_then(|v| v.as_i64());
        let created = rec.get("created_at").or_else(|| rec.get("timestamp")).and_then(|v| v.as_str()).unwrap_or("");
        if step_idx.is_some() || !created.is_empty() {
            return Some(format!(
                "ui:{}:{}",
                step_idx.map(|i| i.to_string()).unwrap_or_else(|| "None".to_string()),
                created
            ));
        }
        return Some(format!("ui_pos:{}", last_end));
    }
    if !psha.is_empty() && !prev_psha.is_empty() && psha != prev_psha {
        return Some(format!("ui_big:{}", psha));
    }
    if prev_sig.starts_with("ui") && !prev_closed {
        return Some(prev_sig.to_string());
    }
    None
}

fn compute_user_turn_sig(payload: &HookPayload, prev_sig: &str, prev_psha: &str, prev_closed: bool) -> String {
    let psha = prompt_sha16(payload);
    if let Some(ref tpath) = payload.transcript_path {
        if let Some(sig) = scan_tail_user_input(Path::new(tpath), prev_sig, prev_psha, prev_closed, &psha) {
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

/// Route `PreInvocation`: flush subagent/mid-turn in Rust or delegate new turns to Python.
pub fn handle_pre_invocation(payload: &HookPayload, workspace_root: &Path) -> RouteOutcome {
    let sid = payload.canonical_session_id();
    let is_subagent = payload.agent_type.as_deref().is_some_and(|s| !s.trim().is_empty())
        || payload.agent_id.as_deref().is_some_and(|s| !s.trim().is_empty())
        || read_sessions_role(workspace_root, &sid).is_some();
    if is_subagent {
        return RouteOutcome::Decided(handle_post_invocation(payload, workspace_root));
    }
    let Some(meta) = read_turn_meta(workspace_root, &sid) else {
        return RouteOutcome::DelegatePython;
    };
    if meta.turn_closed || state_newer_than_meta(workspace_root, &sid) {
        return RouteOutcome::DelegatePython;
    }
    let sig = compute_user_turn_sig(payload, &meta.last_user_sig, &meta.prompt_sha, meta.turn_closed);
    let turns_exists = shard_turn_path(workspace_root, &sid).is_file();
    if sig != meta.last_user_sig || (sig.is_empty() && !turns_exists) {
        return RouteOutcome::DelegatePython;
    }
    if matches!(payload.extra.get("source").and_then(|v| v.as_str()), Some(s) if s.eq_ignore_ascii_case("compact")) {
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
        assert!(matches!(handle_pre_invocation(&p, &tmp), RouteOutcome::DelegatePython));

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

        let closed = TurnMeta { turn_closed: true, ..meta };
        write_turn_meta(&tmp, "conv-pre", &closed).unwrap();
        assert!(matches!(handle_pre_invocation(&p, &tmp), RouteOutcome::DelegatePython));

        let _ = fs::remove_dir_all(&tmp);
    }
}
