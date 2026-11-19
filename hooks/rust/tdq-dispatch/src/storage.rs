//! Storage management: state reading, unified runtime dir, locking, and CCR persistence.

use crate::lock::acquire_sidecar_lock;
pub use crate::lock::atomic_write_file;
use crate::protocol::{GuidanceRepo, ReminderEntry};
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

/// Snapshot of docs/tdq/state.json (read-only mirror; only tdq_state.py writes state).
#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct TdqState {
    pub active_request: Option<String>,
    pub lane: Option<String>,
    pub phase: Option<String>,
    pub spec_approved: Option<bool>,
    pub plan_approved: Option<bool>,
    pub quick_approved: Option<bool>,
    pub muc_gat: Option<String>,
    pub muc_qc: Option<String>,
    pub loai_request: Option<String>,
    pub plan_file: Option<String>,
    pub implement_mode: Option<String>,
    pub implement_pause: Option<Value>,
    pub doc_lang: Option<String>,
    pub updated_at: Option<String>,
}

/// Read docs/tdq/state.json safely (read-only, never writes to state.json).
pub fn read_tdq_state(workspace_root: &Path) -> Option<TdqState> {
    let state_path = workspace_root.join("docs").join("tdq").join("state.json");
    let content = fs::read_to_string(&state_path).ok()?;
    serde_json::from_str(&content).ok()
}

/// Return normalized phase or `"idle"` when missing/invalid.
pub fn effective_phase(state: &TdqState) -> &str {
    match state.phase.as_deref().unwrap_or("idle") {
        p @ ("idle" | "analyze" | "spec" | "plan" | "implement" | "qc" | "report") => p,
        _ => "idle",
    }
}

/// Return the missing approval gate for the active lane, mirroring `tdq_state.cong_dang_cho`.
pub fn cong_dang_cho(state: &TdqState) -> Option<&'static str> {
    let lane = state.lane.as_deref();
    match lane {
        Some("quick") => {
            if state.quick_approved != Some(true) {
                Some("quick")
            } else {
                None
            }
        }
        Some("full") => {
            if state.spec_approved != Some(true) {
                Some("spec")
            } else if state.plan_approved != Some(true) {
                Some("plan")
            } else {
                None
            }
        }
        _ => {
            if state.spec_approved != Some(true) {
                Some("spec")
            } else if state.plan_approved != Some(true) {
                Some("plan")
            } else if state.quick_approved != Some(true) {
                Some("quick")
            } else {
                None
            }
        }
    }
}

/// Ensure and return the single canonical runtime directory (`docs/tdq/.tdq-runtime/`).
pub fn get_runtime_dir(workspace_root: &Path) -> PathBuf {
    let dir = workspace_root.join("docs").join("tdq").join(".tdq-runtime");
    let _ = fs::create_dir_all(&dir);
    dir
}

/// Return canonical `turns-<sid>.jsonl` path inside `docs/tdq/.tdq-runtime/`.
pub fn shard_turn_path(workspace_root: &Path, sid: &str) -> PathBuf {
    get_runtime_dir(workspace_root).join(format!("turns-{}.jsonl", sid))
}

/// Return canonical `pending-reminders-<sid>.jsonl` path inside `docs/tdq/.tdq-runtime/`.
pub fn pending_reminders_path(workspace_root: &Path, sid: &str) -> PathBuf {
    get_runtime_dir(workspace_root).join(format!("pending-reminders-{}.jsonl", sid))
}

/// Return ISO timestamp seconds string from Unix epoch without external crates.
pub fn now_iso_utc() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let days = (secs / 86_400) as i64;
    let rem = secs % 86_400;
    let (y, m, d) = civil_from_days(days);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        y,
        m,
        d,
        rem / 3_600,
        (rem % 3_600) / 60,
        rem % 60
    )
}

fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let y = (yoe as i64) + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    (y + if m <= 2 { 1 } else { 0 }, m as u32, d as u32)
}

/// Per-session turn-meta JSON shared with `_common.py` (`turn-meta-<sid>.json`).
#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct TurnMeta {
    #[serde(default)]
    pub last_user_sig: String,
    #[serde(default)]
    pub turn_closed: bool,
    #[serde(default)]
    pub prompt_sha: String,
}

/// Read `docs/tdq/.tdq-runtime/turn-meta-<sid>.json` fail-open.
pub fn read_turn_meta(workspace_root: &Path, sid: &str) -> Option<TurnMeta> {
    let path = get_runtime_dir(workspace_root).join(format!("turn-meta-{}.json", sid));
    let content = fs::read_to_string(&path).ok()?;
    serde_json::from_str(&content).ok()
}

/// Persist `docs/tdq/.tdq-runtime/turn-meta-<sid>.json` under sidecar lock.
pub fn write_turn_meta(workspace_root: &Path, sid: &str, meta: &TurnMeta) -> Result<(), String> {
    let path = get_runtime_dir(workspace_root).join(format!("turn-meta-{}.json", sid));
    let _guard = acquire_sidecar_lock(&path, Duration::from_millis(200))?;
    let data = serde_json::to_vec(meta).map_err(|e| e.to_string())?;
    atomic_write_file(&path, &data).map_err(|e| e.to_string())
}

/// Mark `turn_closed = true` in `turn-meta-<sid>.json` matching `_common.mark_turn_closed`.
pub fn mark_turn_closed(workspace_root: &Path, sid: &str) {
    if sid.trim().is_empty() {
        return;
    }
    let mut meta = read_turn_meta(workspace_root, sid).unwrap_or_default();
    if meta.turn_closed {
        return;
    }
    meta.turn_closed = true;
    let _ = write_turn_meta(workspace_root, sid, &meta);
}

/// Subagent registration entry inside `sessions.json`.
#[derive(Debug, Clone, Deserialize, Default)]
pub struct SessionRoleRecord {
    #[serde(default)]
    pub role: String,
    #[serde(default)]
    pub task: String,
}

/// Look up subagent role registered in `docs/tdq/.tdq-runtime/sessions.json`.
pub fn read_sessions_role(workspace_root: &Path, sid: &str) -> Option<SessionRoleRecord> {
    let path = get_runtime_dir(workspace_root).join("sessions.json");
    let content = fs::read_to_string(&path).ok()?;
    let map: HashMap<String, SessionRoleRecord> = serde_json::from_str(&content).ok()?;
    map.get(sid).cloned()
}

/// Task checkbox state mirroring `tdq_state.plan_tick_state()`.
#[derive(Debug, Clone, Default)]
pub struct PlanTickState {
    pub exists: bool,
    pub total: usize,
    pub doing_count: usize,
    pub dispatched_count: usize,
    pub done_count: usize,
    pub sha: String,
}

impl PlanTickState {
    pub fn has_doing(&self) -> bool {
        self.doing_count > 0 || self.dispatched_count > 0
    }

    pub fn all_done(&self) -> bool {
        self.total > 0 && self.done_count == self.total
    }
}

fn task_line_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"^\s*-\s*\[( |~|x|>)\]\s*\*\*([A-Za-z][A-Za-z0-9.]*)\*\*")
            .unwrap_or_else(|_| Regex::new(r"$^").expect("fallback regex"))
    })
}

/// Inspect active plan file checkboxes and SHA-256 hash.
pub fn read_plan_tick_state(workspace_root: &Path, state: &TdqState) -> PlanTickState {
    let rel_or_abs = match state.plan_file.as_deref() {
        Some(p) if !p.trim().is_empty() => PathBuf::from(p),
        _ => match state.active_request.as_deref() {
            Some(req) if !req.trim().is_empty() => PathBuf::from("docs")
                .join("tdq")
                .join("plan")
                .join(format!("{}.md", req)),
            _ => return PlanTickState::default(),
        },
    };
    let plan_path = if rel_or_abs.is_absolute() {
        rel_or_abs
    } else {
        workspace_root.join(rel_or_abs)
    };
    let bytes = match fs::read(&plan_path) {
        Ok(b) => b,
        Err(_) => return PlanTickState::default(),
    };
    let sha = format!("{:x}", Sha256::digest(&bytes));
    let content = String::from_utf8_lossy(&bytes);
    let re = task_line_regex();
    let (mut total, mut doing_count, mut dispatched_count, mut done_count) = (0, 0, 0, 0);
    for line in content.lines() {
        if let Some(caps) = re.captures(line) {
            total += 1;
            match caps.get(1).map(|m| m.as_str()) {
                Some("~") => doing_count += 1,
                Some(">") => dispatched_count += 1,
                Some("x") => done_count += 1,
                _ => {}
            }
        }
    }
    PlanTickState {
        exists: true,
        total,
        doing_count,
        dispatched_count,
        done_count,
        sha,
    }
}

/// Read JSONL rows from `turns-<sid>.jsonl` fail-open.
pub fn read_turn_rows(workspace_root: &Path, sid: &str) -> Vec<Value> {
    let path = shard_turn_path(workspace_root, sid);
    let Ok(content) = fs::read_to_string(&path) else {
        return Vec::new();
    };
    content
        .lines()
        .filter_map(|line| {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                None
            } else {
                serde_json::from_str::<Value>(trimmed).ok()
            }
        })
        .collect()
}

/// Count source `code_edit` observations for a given `plan_sha` in the current turn.
pub fn count_code_edits_for_sha(workspace_root: &Path, sid: &str, plan_sha: &str) -> usize {
    read_turn_rows(workspace_root, sid)
        .iter()
        .filter(|row| {
            row.get("kind").and_then(|v| v.as_str()) == Some("observe")
                && row.get("event").and_then(|v| v.as_str()) == Some("code_edit")
                && row.get("plan_sha").and_then(|v| v.as_str()) == Some(plan_sha)
        })
        .count()
}

/// Return true if reminder `code` was already recorded in `turns-<sid>.jsonl`.
pub fn already_reminded(workspace_root: &Path, sid: &str, code: &str) -> bool {
    let clean = code
        .trim()
        .trim_start_matches("[TDQ:")
        .trim_end_matches(']')
        .to_ascii_uppercase();
    read_turn_rows(workspace_root, sid).iter().any(|row| {
        let is_remind = row.get("kind").and_then(|v| v.as_str()) == Some("remind")
            || row.get("event").and_then(|v| v.as_str()) == Some("remind");
        if !is_remind {
            return false;
        }
        let row_code = row
            .get("code")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .trim_start_matches("[TDQ:")
            .trim_end_matches(']')
            .to_ascii_uppercase();
        row_code == clean
    })
}

/// Queue a deduplicated dual-channel reminder into `pending-reminders-<sid>.jsonl`.
pub fn queue_pending_reminder(
    workspace_root: &Path,
    sid: &str,
    code: &str,
    detail: &str,
) -> bool {
    let qpath = pending_reminders_path(workspace_root, sid);
    let Ok(_guard) = acquire_sidecar_lock(&qpath, Duration::from_millis(200)) else {
        return false;
    };
    let entry = GuidanceRepo::build_reminder_entry(code, detail);
    if let Ok(existing) = fs::read_to_string(&qpath) {
        for line in existing.lines() {
            if let Ok(prev) = serde_json::from_str::<ReminderEntry>(line) {
                if prev.code.eq_ignore_ascii_case(&entry.code) {
                    return false;
                }
            }
        }
    }
    let Ok(mut raw) = serde_json::to_string(&entry) else {
        return false;
    };
    raw.push('\n');
    let Ok(mut file) = OpenOptions::new().create(true).append(true).open(&qpath) else {
        return false;
    };
    file.write_all(raw.as_bytes()).is_ok() && file.flush().is_ok()
}

/// Atomically read and clear `pending-reminders-<sid>.jsonl` under sidecar lock.
pub fn pop_pending_reminders(workspace_root: &Path, sid: &str) -> Vec<ReminderEntry> {
    let qpath = pending_reminders_path(workspace_root, sid);
    if !qpath.is_file() {
        return Vec::new();
    }
    let Ok(_guard) = acquire_sidecar_lock(&qpath, Duration::from_millis(200)) else {
        return Vec::new();
    };
    let Ok(content) = fs::read_to_string(&qpath) else {
        return Vec::new();
    };
    let rows: Vec<ReminderEntry> = content
        .lines()
        .filter_map(|line| {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                None
            } else {
                serde_json::from_str::<ReminderEntry>(trimmed).ok()
            }
        })
        .collect();
    if !rows.is_empty() {
        let _ = fs::remove_file(&qpath);
    }
    rows
}

/// Clean stale runtime files in legacy and canonical `.tdq-runtime/` dirs older than max_age.
pub fn clean_old_runtime_files(workspace_root: &Path, max_age: Duration) -> usize {
    let mut cleaned = 0;
    let dirs = [
        workspace_root.join(".tdq-runtime"),
        workspace_root.join("docs").join("tdq").join(".tdq-runtime"),
    ];

    let now = SystemTime::now();

    for dir in &dirs {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_file() {
                    if let Ok(meta) = path.metadata() {
                        if let Ok(modified) = meta.modified() {
                            if let Ok(elapsed) = now.duration_since(modified) {
                                if elapsed > max_age && fs::remove_file(&path).is_ok() {
                                    cleaned += 1;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    cleaned
}

/// Append a JSON record to a JSONL log file under sidecar lock protection.
pub fn append_jsonl_record(log_path: &Path, record: &Value) -> Result<(), String> {
    let _guard = acquire_sidecar_lock(log_path, Duration::from_millis(200))?;

    let mut line = serde_json::to_string(record).map_err(|e| e.to_string())?;
    line.push('\n');

    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_path)
        .map_err(|e| e.to_string())?;

    file.write_all(line.as_bytes())
        .map_err(|e| e.to_string())?;
    file.flush().map_err(|e| e.to_string())?;

    Ok(())
}

/// CCR thresholds: content > 32KB or >= 200 lines.
pub const CCR_BYTE_LIMIT: usize = 32 * 1024;
pub const CCR_LINE_LIMIT: usize = 200;

/// Store large response in CCR store and return reference marker if threshold exceeded.
pub fn check_and_store_ccr(content: &str, workspace_root: &Path) -> Option<String> {
    let bytes_len = content.len();
    let lines_count = content.lines().count();

    if bytes_len <= CCR_BYTE_LIMIT && lines_count < CCR_LINE_LIMIT {
        return None;
    }

    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut hasher = DefaultHasher::new();
    content.hash(&mut hasher);
    let hash_id = format!("{:016x}", hasher.finish());

    let ccr_dir = get_runtime_dir(workspace_root).join("ccr");
    let _ = fs::create_dir_all(&ccr_dir);
    let ccr_file = ccr_dir.join(format!("{}.txt", hash_id));

    let _ = atomic_write_file(&ccr_file, content.as_bytes());

    Some(format!(
        "[CCR:{} bytes={} lines={}]",
        hash_id, bytes_len, lines_count
    ))
}

/// State tracking consecutive stops to detect infinite loops.
#[derive(Debug, Serialize, Deserialize, Default)]
pub struct StopStreak {
    #[serde(default)]
    pub sha: String,
    #[serde(default)]
    pub count: u32,
}

/// Increment consecutive stop counter when `plan_sha` stays unchanged.
pub fn record_stop_streak(workspace_root: &Path, plan_sha: &str) -> u32 {
    let streak_path = workspace_root.join("docs").join("tdq").join("stop_streak.json");
    let _guard = acquire_sidecar_lock(&streak_path, Duration::from_millis(200));

    let mut current: StopStreak = fs::read_to_string(&streak_path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();

    if !plan_sha.is_empty() && current.sha == plan_sha {
        current.count += 1;
    } else {
        current.sha = plan_sha.to_string();
        current.count = 1;
    }

    if let Ok(data) = serde_json::to_vec(&current) {
        let _ = atomic_write_file(&streak_path, &data);
    }

    current.count
}

/// Reset consecutive stop streak to zero.
pub fn reset_stop_streak(workspace_root: &Path) {
    let streak_path = workspace_root.join("docs").join("tdq").join("stop_streak.json");
    let _guard = acquire_sidecar_lock(&streak_path, Duration::from_millis(200));

    let current = StopStreak {
        sha: String::new(),
        count: 0,
    };
    if let Ok(data) = serde_json::to_vec(&current) {
        let _ = atomic_write_file(&streak_path, &data);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_read_state_json() {
        let tmp = std::env::temp_dir().join(format!("tdq_storage_test_{}", std::process::id()));
        let state_dir = tmp.join("docs").join("tdq");
        let _ = fs::create_dir_all(&state_dir);

        let sample = r#"{
            "active_request": "2026-11-19-demo",
            "lane": "full",
            "phase": "spec",
            "spec_approved": true,
            "muc_gat": "full"
        }"#;
        fs::write(state_dir.join("state.json"), sample).unwrap();

        let state = read_tdq_state(&tmp).unwrap();
        assert_eq!(state.active_request.as_deref(), Some("2026-11-19-demo"));
        assert_eq!(state.phase.as_deref(), Some("spec"));
        assert_eq!(state.spec_approved, Some(true));
        assert_eq!(state.muc_gat.as_deref(), Some("full"));
        assert_eq!(cong_dang_cho(&state), Some("plan"));
        assert_eq!(
            get_runtime_dir(&tmp),
            tmp.join("docs").join("tdq").join(".tdq-runtime")
        );

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_turn_meta_pending_and_plan_tick() {
        let tmp = std::env::temp_dir().join(format!("tdq_runtime_unified_{}", std::process::id()));
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq").join("plan"));

        let meta = TurnMeta {
            last_user_sig: "ui:10:t".to_string(),
            turn_closed: false,
            prompt_sha: "abc123".to_string(),
        };
        assert!(write_turn_meta(&tmp, "s1", &meta).is_ok());
        mark_turn_closed(&tmp, "s1");
        assert!(read_turn_meta(&tmp, "s1").unwrap().turn_closed);

        assert!(queue_pending_reminder(&tmp, "s1", "TICK", "edit 5"));
        assert!(!queue_pending_reminder(&tmp, "s1", "TICK", "dup"));
        let popped = pop_pending_reminders(&tmp, "s1");
        assert_eq!(popped.len(), 1);
        assert!(pop_pending_reminders(&tmp, "s1").is_empty());

        let plan_rel = "docs/tdq/plan/2026-11-19-demo.md";
        fs::write(
            tmp.join(plan_rel),
            "- [x] **T1.1** done\n- [~] **T1.2** doing\n- [>] **T1.3** sub\n- [ ] **T2.1** todo\n",
        )
        .unwrap();
        let st = TdqState {
            active_request: Some("2026-11-19-demo".to_string()),
            plan_file: Some(plan_rel.to_string()),
            ..Default::default()
        };
        let tick = read_plan_tick_state(&tmp, &st);
        assert!(tick.exists);
        assert_eq!(tick.total, 4);
        assert_eq!(tick.doing_count, 1);
        assert_eq!(tick.dispatched_count, 1);
        assert_eq!(tick.done_count, 1);

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_append_jsonl() {
        let tmp = std::env::temp_dir().join(format!("tdq_jsonl_test_{}", std::process::id()));
        let _ = fs::create_dir_all(&tmp);
        let log_file = tmp.join("test.jsonl");

        let rec1 = serde_json::json!({"turn": 1, "status": "ok"});
        let rec2 = serde_json::json!({"turn": 2, "status": "ok"});

        assert!(append_jsonl_record(&log_file, &rec1).is_ok());
        assert!(append_jsonl_record(&log_file, &rec2).is_ok());

        let lines: Vec<String> = fs::read_to_string(&log_file)
            .unwrap()
            .lines()
            .map(|s| s.to_string())
            .collect();
        assert_eq!(lines.len(), 2);

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_ccr_threshold() {
        let tmp = std::env::temp_dir().join(format!("tdq_ccr_test_{}", std::process::id()));
        let _ = fs::create_dir_all(&tmp);

        let small = "hello world\n".repeat(50);
        assert!(check_and_store_ccr(&small, &tmp).is_none());

        let large_lines = "line item\n".repeat(250);
        let marker = check_and_store_ccr(&large_lines, &tmp);
        assert!(marker.is_some());
        assert!(marker.unwrap().contains("[CCR:"));

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_stop_streak() {
        let tmp = std::env::temp_dir().join(format!("tdq_streak_test_{}", std::process::id()));
        let _ = fs::create_dir_all(tmp.join("docs").join("tdq"));

        assert_eq!(record_stop_streak(&tmp, "sha1"), 1);
        assert_eq!(record_stop_streak(&tmp, "sha1"), 2);
        assert_eq!(record_stop_streak(&tmp, "sha2"), 1);
        reset_stop_streak(&tmp);
        assert_eq!(record_stop_streak(&tmp, "sha1"), 1);

        let _ = fs::remove_dir_all(&tmp);
    }
}
