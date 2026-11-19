//! Cross-platform sidecar file locking and atomic writes.
//! Uses OS advisory/byte-range locking (`std::fs::File::try_lock`) matching Python
//! `with_ntfs_lock` so lock anchor files left on disk never cause false timeouts.

use std::fs::{self, File, OpenOptions, TryLockError};
use std::path::{Path, PathBuf};
use std::thread;
use std::time::{Duration, Instant};

/// RAII Guard that releases the OS file lock when dropped.
pub struct SidecarLockGuard {
    _file: Option<File>,
}

impl Drop for SidecarLockGuard {
    fn drop(&mut self) {
        // Closing the handle releases the OS lock atomically; keep the anchor file
        // on disk to avoid create/unlink races with Python's msvcrt.locking().
        self._file.take();
    }
}

/// Build the canonical `<target_path>.lock` path without replacing existing extensions.
pub fn sidecar_lock_path(target_path: &Path) -> PathBuf {
    let mut os_str = target_path.as_os_str().to_os_string();
    os_str.push(".lock");
    PathBuf::from(os_str)
}

/// Acquire an exclusive OS sidecar lock at `<target_path>.lock` with bounded timeout.
pub fn acquire_sidecar_lock(
    target_path: &Path,
    timeout: Duration,
) -> Result<SidecarLockGuard, String> {
    let lock_path = sidecar_lock_path(target_path);
    if let Some(parent) = lock_path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    let start = Instant::now();
    let poll_interval = Duration::from_millis(5);

    loop {
        let file = match OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(&lock_path)
        {
            Ok(f) => f,
            Err(e)
                if e.kind() == std::io::ErrorKind::PermissionDenied
                    && start.elapsed() < timeout =>
            {
                thread::sleep(poll_interval);
                continue;
            }
            Err(e) => {
                return Err(format!(
                    "Failed to open sidecar lock {}: {}",
                    lock_path.display(),
                    e
                ));
            }
        };

        match file.try_lock() {
            Ok(()) => return Ok(SidecarLockGuard { _file: Some(file) }),
            Err(TryLockError::WouldBlock) => {
                drop(file);
                if start.elapsed() >= timeout {
                    return Err(format!(
                        "Timed out acquiring sidecar lock for {} after {:?}",
                        target_path.display(),
                        timeout
                    ));
                }
                thread::sleep(poll_interval);
            }
            Err(TryLockError::Error(e)) => {
                return Err(format!("Failed locking {}: {}", lock_path.display(), e));
            }
        }
    }
}

/// Write data to target_path atomically using a temporary file in the same directory.
pub fn atomic_write_file(target_path: &Path, data: &[u8]) -> std::io::Result<()> {
    if let Some(parent) = target_path.parent() {
        fs::create_dir_all(parent)?;
    }

    let file_name = target_path
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("tmp");
    let tmp_path =
        target_path.with_file_name(format!(".tmp.{}.{}.dat", std::process::id(), file_name));

    fs::write(&tmp_path, data)?;

    // Atomically rename temporary file over target with bounded Windows lock backoff.
    let mut last_err = None;
    for attempt in 0..5u64 {
        #[cfg(windows)]
        {
            if target_path.exists() {
                let _ = fs::remove_file(target_path);
            }
        }
        match fs::rename(&tmp_path, target_path) {
            Ok(()) => return Ok(()),
            Err(e) => {
                last_err = Some(e);
                thread::sleep(Duration::from_millis(5 * (attempt + 1)));
            }
        }
    }
    let _ = fs::remove_file(&tmp_path);
    Err(last_err.unwrap_or_else(|| std::io::Error::other("rename failed")))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sidecar_lock_lifecycle() {
        let tmp_dir = std::env::temp_dir().join(format!("tdq_lock_test_{}", std::process::id()));
        let _ = fs::create_dir_all(&tmp_dir);
        let test_file = tmp_dir.join("state.json");

        // 1. Acquire lock
        let guard = acquire_sidecar_lock(&test_file, Duration::from_millis(100));
        assert!(guard.is_ok());

        // 2. Second acquire should timeout
        let second_try = acquire_sidecar_lock(&test_file, Duration::from_millis(50));
        assert!(second_try.is_err());

        // 3. Drop guard and acquire again
        drop(guard);
        let third_try = acquire_sidecar_lock(&test_file, Duration::from_millis(100));
        assert!(third_try.is_ok());

        let _ = fs::remove_dir_all(&tmp_dir);
    }

    #[test]
    fn test_sidecar_lock_succeeds_with_existing_anchor_file() {
        let tmp_dir = std::env::temp_dir().join(format!("tdq_lock_anchor_{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp_dir);
        let _ = fs::create_dir_all(&tmp_dir);
        let test_file = tmp_dir.join("pending-reminders-s1.jsonl");
        let anchor_lock = sidecar_lock_path(&test_file);
        fs::write(&anchor_lock, b"").unwrap();

        let guard = acquire_sidecar_lock(&test_file, Duration::from_millis(100));
        assert!(
            guard.is_ok(),
            "must acquire OS lock even when Python leaves anchor .lock file: {:?}",
            guard.err()
        );

        let _ = fs::remove_dir_all(&tmp_dir);
    }

    #[test]
    fn test_atomic_write() {
        let tmp_dir = std::env::temp_dir().join(format!("tdq_atomic_test_{}", std::process::id()));
        let _ = fs::create_dir_all(&tmp_dir);
        let test_file = tmp_dir.join("sample.txt");

        let res = atomic_write_file(&test_file, b"hello atomic world");
        assert!(res.is_ok());
        assert_eq!(
            fs::read_to_string(&test_file).unwrap(),
            "hello atomic world"
        );

        let _ = fs::remove_dir_all(&tmp_dir);
    }
}
