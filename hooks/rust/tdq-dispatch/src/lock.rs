//! Cross-platform sidecar file locking and atomic writes.
//! Protects against Windows NTFS ERROR_LOCK_VIOLATION (os error 33).

use std::fs::{self, File, OpenOptions};
use std::path::{Path, PathBuf};
use std::thread;
use std::time::{Duration, Instant};

/// RAII Guard that releases the lock when dropped.
pub struct SidecarLockGuard {
    lock_path: PathBuf,
    _file: Option<File>,
}

impl Drop for SidecarLockGuard {
    fn drop(&mut self) {
        // Drop the file handle first so any OS-level lock is released.
        self._file.take();
        // Best-effort cleanup of sidecar lock file.
        let _ = fs::remove_file(&self.lock_path);
    }
}

/// Acquire an exclusive sidecar lock with a given timeout.
/// The lock is placed at `<target_path>.lock`.
pub fn acquire_sidecar_lock(
    target_path: &Path,
    timeout: Duration,
) -> Result<SidecarLockGuard, String> {
    let lock_path = target_path.with_extension(format!(
        "{}.lock",
        target_path.extension().and_then(|s| s.to_str()).unwrap_or("")
    ));

    // Ensure parent directory exists
    if let Some(parent) = lock_path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    let start = Instant::now();
    let poll_interval = Duration::from_millis(5);

    loop {
        // Attempt to create the lock file exclusively (create_new is atomic on OS level)
        match OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .open(&lock_path)
        {
            Ok(file) => {
                return Ok(SidecarLockGuard {
                    lock_path,
                    _file: Some(file),
                });
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {
                // If the lock file is stale (> 30s old), remove it defensively
                if let Ok(metadata) = fs::metadata(&lock_path) {
                    if let Ok(mod_time) = metadata.modified() {
                        if let Ok(elapsed) = mod_time.elapsed() {
                            if elapsed > Duration::from_secs(30) {
                                let _ = fs::remove_file(&lock_path);
                            }
                        }
                    }
                }

                if start.elapsed() >= timeout {
                    return Err(format!(
                        "Timed out acquiring sidecar lock for {} after {:?}",
                        target_path.display(),
                        timeout
                    ));
                }
                thread::sleep(poll_interval);
            }
            Err(e) => {
                return Err(format!(
                    "Failed to open sidecar lock {}: {}",
                    lock_path.display(),
                    e
                ));
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
    let tmp_path = target_path.with_file_name(format!(
        ".tmp.{}.{}.dat",
        std::process::id(),
        file_name
    ));

    fs::write(&tmp_path, data)?;

    // Atomically rename temporary file over target
    #[cfg(windows)]
    {
        // On Windows, rename over an existing file may fail if not handled cleanly;
        // removing existing target first if present ensures cross-platform consistency.
        if target_path.exists() {
            let _ = fs::remove_file(target_path);
        }
    }

    if let Err(e) = fs::rename(&tmp_path, target_path) {
        let _ = fs::remove_file(&tmp_path);
        return Err(e);
    }

    Ok(())
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
