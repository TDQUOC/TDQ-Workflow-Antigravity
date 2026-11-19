//! Storage management: state reading, log rotation, CCR cache, and runtime persistence.

use crate::lock::acquire_sidecar_lock;
pub use crate::lock::atomic_write_file;
use serde::{Deserialize, Serialize};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

/// Simplified snapshot of docs/tdq/state.json.
#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct TdqState {
    pub active_request: Option<String>,
    pub lane: Option<String>,
    pub phase: Option<String>,
    pub spec_approved: Option<bool>,
    pub plan_approved: Option<bool>,
    pub muc_gat: Option<String>,
    pub muc_qc: Option<String>,
    pub loai_request: Option<String>,
}

/// Read docs/tdq/state.json safely (read-only, never writes to state.json).
pub fn read_tdq_state(workspace_root: &Path) -> Option<TdqState> {
    let state_path = workspace_root.join("docs").join("tdq").join("state.json");
    let content = fs::read_to_string(&state_path).ok()?;
    serde_json::from_str(&content).ok()
}

/// Ensure and return the runtime directory (.tdq-runtime/).
pub fn get_runtime_dir(workspace_root: &Path) -> PathBuf {
    let dir = workspace_root.join(".tdq-runtime");
    let _ = fs::create_dir_all(&dir);
    dir
}

/// Clean files in .tdq-runtime/ older than max_age (e.g. 7 days).
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
                                if elapsed > max_age {
                                    if fs::remove_file(&path).is_ok() {
                                        cleaned += 1;
                                    }
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
pub fn append_jsonl_record(log_path: &Path, record: &serde_json::Value) -> Result<(), String> {
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

    // Hash or deterministic ID
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

        // Under threshold: 50 lines, 2KB
        let small = "hello world\n".repeat(50);
        assert!(check_and_store_ccr(&small, &tmp).is_none());

        // Over lines threshold: 250 lines
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
