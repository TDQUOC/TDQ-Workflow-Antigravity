//! tdq-dispatch: standalone Hybrid 2-tier hook router for Google Antigravity 2.0.

use std::env;
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::Instant;
use tdq_dispatch::events::notification::handle_notification;
use tdq_dispatch::events::post_invocation::handle_post_invocation;
use tdq_dispatch::events::post_tool_use::handle_post_tool_use;
use tdq_dispatch::events::pre_invocation::handle_pre_invocation;
use tdq_dispatch::events::pre_tool_use::handle_pre_tool_use;
use tdq_dispatch::events::stop_streak::handle_stop_streak;
use tdq_dispatch::events::user_prompt_submit::handle_user_prompt_submit;
use tdq_dispatch::protocol::{HookDecision, HookPayload};
use tdq_dispatch::storage::now_iso_utc;
use tdq_dispatch::RouteOutcome;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

fn parse_event_arg_from<I: IntoIterator<Item = String>>(args: I) -> Option<String> {
    let vec: Vec<String> = args.into_iter().collect();
    let mut i = 1;
    while i < vec.len() {
        if (vec[i] == "--event" || vec[i] == "-e") && i + 1 < vec.len() {
            return Some(vec[i + 1].clone());
        }
        i += 1;
    }
    if vec.len() > 1 && !vec[1].starts_with('-') {
        return Some(vec[1].clone());
    }
    None
}

fn find_project_ancestor(start: &Path) -> PathBuf {
    let mut current = start.to_path_buf();
    let mut git_root: Option<PathBuf> = None;
    let mut state_root: Option<PathBuf> = None;
    loop {
        if state_root.is_none() && current.join("docs").join("tdq").join("state.json").is_file() {
            state_root = Some(current.clone());
        }
        if git_root.is_none() && current.join(".git").exists() {
            git_root = Some(current.clone());
        }
        match current.parent() {
            Some(parent) if parent != current => current = parent.to_path_buf(),
            _ => break,
        }
    }
    git_root.or(state_root).unwrap_or_else(|| start.to_path_buf())
}

fn resolve_workspace_root(payload: &HookPayload) -> PathBuf {
    if let Ok(env_dir) = env::var("TDQ_PROJECT_DIR") {
        let trimmed = env_dir.trim();
        if !trimmed.is_empty() {
            return PathBuf::from(trimmed);
        }
    }
    let start_candidates = [
        payload.cwd.clone(),
        payload.working_directory.clone(),
        payload.first_workspace_path(),
    ];
    for raw in start_candidates.into_iter().flatten() {
        let p = PathBuf::from(raw.trim());
        if !raw.trim().is_empty() && p.exists() {
            return find_project_ancestor(&p);
        }
    }
    let fallback = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    find_project_ancestor(&fallback)
}

fn resolve_dispatch_script_with(
    plugin_root: Option<&Path>,
    exe_path: Option<&Path>,
    workspace_root: &Path,
) -> Option<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Some(root) = plugin_root {
        candidates.push(root.join("hooks").join("scripts").join("dispatch.py"));
    }
    if let Some(exe) = exe_path {
        if let Some(bin_dir) = exe.parent() {
            if let Some(bundle_root) = bin_dir.parent() {
                candidates.push(bundle_root.join("hooks").join("scripts").join("dispatch.py"));
            }
        }
    }
    candidates.push(
        workspace_root
            .join("plugins")
            .join("tdq-workflow-agy")
            .join("hooks")
            .join("scripts")
            .join("dispatch.py"),
    );
    candidates.push(workspace_root.join("hooks").join("scripts").join("dispatch.py"));
    candidates.into_iter().find(|p| p.is_file())
}

fn resolve_dispatch_script(workspace_root: &Path) -> Option<PathBuf> {
    let env_root = env::var_os("PLUGIN_ROOT")
        .filter(|v| !v.is_empty())
        .map(PathBuf::from);
    let exe = env::current_exe().ok();
    resolve_dispatch_script_with(env_root.as_deref(), exe.as_deref(), workspace_root)
}

fn spawn_python_dispatch(
    program: &str,
    prefix_args: &[&str],
    dispatch_script: &Path,
    event_name: &str,
    raw_stdin: &str,
) -> io::Result<std::process::Output> {
    let mut cmd = Command::new(program);
    cmd.args(prefix_args)
        .arg("-X")
        .arg("utf8")
        .arg(dispatch_script)
        .arg("--event")
        .arg(event_name)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit());
    #[cfg(windows)]
    cmd.creation_flags(CREATE_NO_WINDOW);

    let mut child = cmd.spawn()?;
    if let Some(mut stdin) = child.stdin.take() {
        let _ = stdin.write_all(raw_stdin.as_bytes());
    }
    child.wait_with_output()
}

fn execute_python_fallback(
    event_name: &str,
    raw_stdin: &str,
    workspace_root: &Path,
) -> io::Result<i32> {
    let dispatch_script = resolve_dispatch_script(workspace_root).ok_or_else(|| {
        io::Error::new(
            io::ErrorKind::NotFound,
            "hooks/scripts/dispatch.py not found via PLUGIN_ROOT, current_exe, or workspace",
        )
    })?;
    let primary = if cfg!(windows) { "python" } else { "python3" };
    let output = match spawn_python_dispatch(primary, &[], &dispatch_script, event_name, raw_stdin) {
        Ok(out) => out,
        Err(err) if cfg!(windows) && err.kind() == io::ErrorKind::NotFound => {
            spawn_python_dispatch("py", &["-3"], &dispatch_script, event_name, raw_stdin)?
        }
        Err(err) => return Err(err),
    };
    let _ = io::stdout().write_all(&output.stdout);
    let _ = io::stdout().flush();
    Ok(output.status.code().unwrap_or(0))
}

fn route_event(event_name: &str, payload: &HookPayload, workspace_root: &Path) -> RouteOutcome {
    match event_name {
        "SessionStart" => RouteOutcome::DelegatePython,
        "PreInvocation" => handle_pre_invocation(payload, workspace_root),
        "PostInvocation" => RouteOutcome::Decided(handle_post_invocation(payload, workspace_root)),
        "PreToolUse" => handle_pre_tool_use(payload, workspace_root),
        "PostToolUse" => RouteOutcome::Decided(handle_post_tool_use(payload, workspace_root)),
        "StopStreak" | "Stop" => handle_stop_streak(payload, workspace_root),
        "UserPromptSubmit" => {
            RouteOutcome::Decided(handle_user_prompt_submit(payload, workspace_root))
        }
        "Notification" => RouteOutcome::Decided(handle_notification(payload, workspace_root)),
        _ => RouteOutcome::Decided(HookDecision::empty_json()),
    }
}

fn emit_log(event_name: &str, route: &str, elapsed_ms: f64, sid: &str) {
    if env::var("TDQ_LOG").as_deref() == Ok("0") {
        return;
    }
    eprintln!(
        "[{}] tdq-dispatch: event={} route={} sid={} ms={:.2}",
        now_iso_utc(),
        event_name,
        route,
        sid,
        elapsed_ms
    );
}

fn main() {
    let start = Instant::now();
    let cli_event = parse_event_arg_from(env::args());

    let mut raw_stdin = String::new();
    let _ = io::stdin().read_to_string(&mut raw_stdin);
    let trimmed_stdin = raw_stdin.trim();
    let payload = if trimmed_stdin.is_empty() {
        HookPayload::default()
    } else {
        HookPayload::from_json_str(trimmed_stdin)
    };

    let event_name = cli_event
        .or_else(|| payload.hook_event_name.clone())
        .unwrap_or_else(|| "SessionStart".to_string());
    let workspace_root = resolve_workspace_root(&payload);
    let sid = payload.canonical_session_id();

    if env::var("TDQ_HOOK_ENGINE").as_deref() == Ok("python") {
        if let Ok(exit_code) = execute_python_fallback(&event_name, &raw_stdin, &workspace_root) {
            emit_log(&event_name, "cold-forced", start.elapsed().as_secs_f64() * 1000.0, &sid);
            std::process::exit(exit_code);
        }
    }

    match route_event(&event_name, &payload, &workspace_root) {
        RouteOutcome::Decided(decision) => {
            println!("{}", decision.to_json_string());
            emit_log(&event_name, "hot", start.elapsed().as_secs_f64() * 1000.0, &sid);
        }
        RouteOutcome::DelegatePython => {
            match execute_python_fallback(&event_name, &raw_stdin, &workspace_root) {
                Ok(code) => {
                    emit_log(&event_name, "cold", start.elapsed().as_secs_f64() * 1000.0, &sid);
                    std::process::exit(code);
                }
                Err(err) => {
                    emit_log(
                        &event_name,
                        &format!("cold-err:{}", err),
                        start.elapsed().as_secs_f64() * 1000.0,
                        &sid,
                    );
                    println!("{}", HookDecision::empty_json().to_json_string());
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn test_parse_event_arg() {
        assert_eq!(
            parse_event_arg_from(["tdq-dispatch".to_string(), "--event".to_string(), "PreInvocation".to_string()]),
            Some("PreInvocation".to_string())
        );
        assert_eq!(parse_event_arg_from(["tdq-dispatch".to_string()]), None);
    }

    #[test]
    fn test_resolve_workspace_from_workspace_paths() {
        let tmp = std::env::temp_dir().join(format!("tdq_ws_uri_test_{}", std::process::id()));
        let _ = fs::create_dir_all(&tmp);
        let uri = format!(
            "file:///{}",
            tmp.to_string_lossy().replace('\\', "/").trim_start_matches('/')
        );
        let payload = HookPayload::from_json_str(&format!(r#"{{"workspacePaths": ["{}"]}}"#, uri));
        assert_eq!(resolve_workspace_root(&payload), tmp);
        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_resolve_dispatch_script_prefers_plugin_root_and_exe() {
        let tmp = std::env::temp_dir().join(format!("tdq_plugin_root_test_{}", std::process::id()));
        let plugin = tmp.join("ext-plugin");
        let other_proj = tmp.join("external-proj");
        let dispatch_rel = plugin.join("hooks").join("scripts").join("dispatch.py");
        let _ = fs::create_dir_all(dispatch_rel.parent().unwrap());
        let _ = fs::create_dir_all(&other_proj);
        fs::write(&dispatch_rel, "# stub").unwrap();

        let via_plugin = resolve_dispatch_script_with(Some(&plugin), None, &other_proj);
        assert_eq!(via_plugin, Some(dispatch_rel.clone()));

        let fake_exe = plugin.join("bin").join("tdq-dispatch.exe");
        let via_exe = resolve_dispatch_script_with(None, Some(&fake_exe), &other_proj);
        assert_eq!(via_exe, Some(dispatch_rel));

        let _ = fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_route_event_handles_pre_and_post_invocation() {
        let payload = HookPayload::default();
        let ws = std::env::temp_dir().join(format!("tdq_main_route_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&ws);
        let _ = fs::create_dir_all(&ws);
        assert_eq!(
            route_event("PreInvocation", &payload, &ws),
            RouteOutcome::DelegatePython
        );
        assert_eq!(
            route_event("PostInvocation", &payload, &ws),
            RouteOutcome::Decided(HookDecision::empty_json())
        );
        assert_eq!(
            route_event("SessionStart", &payload, &ws),
            RouteOutcome::DelegatePython
        );
        let _ = fs::remove_dir_all(&ws);
    }
}
