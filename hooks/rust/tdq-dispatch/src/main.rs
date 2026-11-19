//! tdq-dispatch: standalone native hook binary for Google Antigravity.

use std::env;
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use tdq_dispatch::events::notification::handle_notification;
use tdq_dispatch::events::post_tool_use::handle_post_tool_use;
use tdq_dispatch::events::pre_tool_use::handle_pre_tool_use;
use tdq_dispatch::events::session_start::handle_session_start;
use tdq_dispatch::events::stop_streak::handle_stop_streak;
use tdq_dispatch::events::user_prompt_submit::handle_user_prompt_submit;
use tdq_dispatch::protocol::{HookDecision, HookPayload};

fn parse_event_arg() -> String {
    let args: Vec<String> = env::args().collect();
    let mut i = 1;
    while i < args.len() {
        if (args[i] == "--event" || args[i] == "-e") && i + 1 < args.len() {
            return args[i + 1].clone();
        }
        i += 1;
    }
    // Fallback: check first arg
    if args.len() > 1 && !args[1].starts_with('-') {
        return args[1].clone();
    }
    "SessionStart".to_string()
}

fn resolve_workspace_root(payload: &HookPayload) -> PathBuf {
    if let Some(ref cwd) = payload.cwd {
        let p = PathBuf::from(cwd);
        if p.exists() {
            return p;
        }
    }
    env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn execute_python_fallback(event_name: &str, raw_stdin: &str, workspace_root: &Path) -> io::Result<i32> {
    let python_exe = if cfg!(windows) { "python" } else { "python3" };

    // Search candidate paths for dispatch.py
    let candidates = [
        workspace_root
            .join("plugins")
            .join("tdq-workflow-agy")
            .join("hooks")
            .join("scripts")
            .join("dispatch.py"),
        workspace_root
            .join("hooks")
            .join("scripts")
            .join("dispatch.py"),
    ];

    let dispatch_script = candidates
        .iter()
        .find(|p| p.exists())
        .cloned()
        .unwrap_or_else(|| candidates[0].clone());

    let mut child = Command::new(python_exe)
        .arg("-X")
        .arg("utf8")
        .arg(&dispatch_script)
        .arg("--event")
        .arg(event_name)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()?;

    if let Some(mut stdin) = child.stdin.take() {
        let _ = stdin.write_all(raw_stdin.as_bytes());
    }

    let output = child.wait_with_output()?;
    let _ = io::stdout().write_all(&output.stdout);

    Ok(output.status.code().unwrap_or(0))
}

fn main() {
    let event_name = parse_event_arg();

    // Read full stdin
    let mut raw_stdin = String::new();
    let _ = io::stdin().read_to_string(&mut raw_stdin);
    let trimmed_stdin = raw_stdin.trim();
    let payload = if trimmed_stdin.is_empty() {
        HookPayload::default()
    } else {
        HookPayload::from_json_str(trimmed_stdin)
    };

    let workspace_root = resolve_workspace_root(&payload);

    // Debug logging if TDQ_DEBUG=1
    if env::var("TDQ_DEBUG").as_deref() == Ok("1") {
        let now = std::time::SystemTime::now();
        let duration = now.duration_since(std::time::UNIX_EPOCH).unwrap_or_default();
        let secs = duration.as_secs();
        eprintln!(
            "[{}.{:03}Z] [DEBUG] tdq-dispatch: event={} sid={:?} cwd={}",
            secs,
            duration.subsec_millis(),
            event_name,
            payload.session_id,
            workspace_root.display()
        );
    }

    // Check for explicit Python fallback request
    if env::var("TDQ_HOOK_ENGINE").as_deref() == Ok("python") {
        if let Ok(exit_code) = execute_python_fallback(&event_name, &raw_stdin, &workspace_root) {
            std::process::exit(exit_code);
        }
    }

    // Native Rust dispatch
    let decision = match event_name.as_str() {
        "SessionStart" => handle_session_start(&payload, &workspace_root),
        "UserPromptSubmit" => handle_user_prompt_submit(&payload, &workspace_root),
        "PreToolUse" => handle_pre_tool_use(&payload, &workspace_root),
        "PostToolUse" => handle_post_tool_use(&payload, &workspace_root),
        "StopStreak" | "Stop" => handle_stop_streak(&payload, &workspace_root),
        "Notification" => handle_notification(&payload, &workspace_root),
        _ => HookDecision::allow(),
    };

    println!("{}", decision.to_json_string());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_event_arg() {
        assert_eq!(parse_event_arg(), "SessionStart");
    }
}
