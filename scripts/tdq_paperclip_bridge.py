#!/usr/bin/env python3
"""One-way Paperclip CLI bridge (disabled by default, stdlib only).

Usage:
    python3 scripts/tdq_paperclip_bridge.py [--cwd <dir>] status [--json]
    python3 scripts/tdq_paperclip_bridge.py [--cwd <dir>] pull --issue <id> [--lane quick|full] [--json]
    python3 scripts/tdq_paperclip_bridge.py [--cwd <dir>] push-report --slug <slug> --issue <id> [--json]

Exit codes:
    0  Success
    2  Invalid CLI argument, unsafe URL, missing input file, or malformed issue id
    3  Bridge is disabled (default enabled=false or corrupt project bridge config)
    4  Missing required token, HTTP/network failure, or tdq_state.py subprocess failure
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import tdq_config
import tdq_domains
import utf8_io

EXIT_OK = 0
EXIT_SYNTAX = 2
EXIT_DISABLED = 3
EXIT_IO_ERROR = 4

_BOOL_MAP: dict[str, bool] = {
    "1": True,
    "true": True,
    "yes": True,
    "on": True,
    "0": False,
    "false": False,
    "no": False,
    "off": False,
}
_DEFAULT_ENDPOINTS: dict[str, str] = {
    "health": "/health",
    "issue": "/issues/{issue_id}",
    "comments": "/issues/{issue_id}/comments",
}
_FALLBACK_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "enabled": False,
    "transport": "cli-one-way",
    "base_url": "http://127.0.0.1:3100/api",
    "token_env_var": "PAPERCLIP_API_TOKEN",
    "timeout_sec": 5.0,
    "default_lane": "full",
    "endpoints": copy.deepcopy(_DEFAULT_ENDPOINTS),
}
BRIDGE_DEFAULT_PATH = Path(__file__).resolve().parent / "defaults" / "paperclip-bridge.default.json"
PROJECT_BRIDGE_REL = Path("docs") / "tdq" / "paperclip-bridge.json"
_WORD_RE = re.compile(r"[a-z0-9]+")
_SUMMARY_PREFIX = "> **T\u00f3m t\u1eaft d\u1ec5 hi\u1ec3u:**"
_URL_RE = re.compile(r"https?://\S+?\.html")


def _log(message: str) -> None:
    """Emit an ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"[{stamp}] tdq_paperclip_bridge: {message}", file=sys.stderr)


def _resolve_cwd(cwd: str | Path | None) -> Path:
    if cwd is not None:
        return Path(cwd)
    env_dir = os.environ.get("TDQ_PROJECT_DIR", "").strip()
    return Path(env_dir) if env_dir else Path.cwd()


def _parse_bool(raw: Any, label: str) -> bool | None:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int) and raw in (0, 1):
        return bool(raw)
    if isinstance(raw, str):
        norm = raw.strip().lower()
        if norm in _BOOL_MAP:
            return _BOOL_MAP[norm]
    _log(f"WARN invalid boolean {label}={raw!r}; ignoring")
    return None


def _read_json_layer(path: Path, label: str) -> tuple[dict[str, Any] | None, bool]:
    if not path.is_file():
        return None, True
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _log(f"WARN unreadable {label} bridge config at {path}: {exc}")
        return None, False
    if not isinstance(parsed, dict):
        _log(f"WARN {label} bridge config at {path} is not a JSON object")
        return None, False
    return parsed, True


def _merge_bridge_layer(cfg: dict[str, Any], layer: dict[str, Any]) -> None:
    for key, val in layer.items():
        if key == "endpoints" and isinstance(val, dict):
            endpoints = cfg.setdefault("endpoints", {})
            if isinstance(endpoints, dict):
                endpoints.update({k: str(v) for k, v in val.items()})
        elif key == "enabled":
            parsed = _parse_bool(val, "enabled")
            if parsed is not None:
                cfg["enabled"] = parsed
        else:
            cfg[key] = copy.deepcopy(val)


def _apply_bridge_env_overrides(cfg: dict[str, Any]) -> None:
    for env_name in ("PAPERCLIP_BRIDGE_ENABLED", "TDQ_PAPERCLIP_BRIDGE_ENABLED"):
        raw = os.environ.get(env_name)
        if raw is not None and raw.strip():
            parsed = _parse_bool(raw, env_name)
            if parsed is not None:
                cfg["enabled"] = parsed
    if url := os.environ.get("PAPERCLIP_API_URL", "").strip():
        cfg["base_url"] = url
    if tok_var := os.environ.get("PAPERCLIP_TOKEN_ENV", "").strip():
        cfg["token_env_var"] = tok_var
    if raw_to := os.environ.get("PAPERCLIP_TIMEOUT_SEC", "").strip():
        try:
            val = float(raw_to)
            if val > 0:
                cfg["timeout_sec"] = val
        except ValueError:
            _log(f"WARN invalid PAPERCLIP_TIMEOUT_SEC={raw_to!r}; keeping default")


def load_bridge_config(cwd: str | Path | None = None) -> dict[str, Any]:
    """Load merged defaults, project bridge config, tdq_config, and env overrides."""
    target_cwd = _resolve_cwd(cwd)
    cfg = copy.deepcopy(_FALLBACK_CONFIG)
    default_data, default_ok = _read_json_layer(BRIDGE_DEFAULT_PATH, "default")
    if default_ok and default_data is not None:
        _merge_bridge_layer(cfg, default_data)

    proj_data, proj_ok = _read_json_layer(target_cwd / PROJECT_BRIDGE_REL, "project")
    if not proj_ok:
        cfg["enabled"] = False
        return cfg

    explicit_proj_enabled = isinstance(proj_data, dict) and "enabled" in proj_data
    if proj_data is not None:
        _merge_bridge_layer(cfg, proj_data)

    if not explicit_proj_enabled:
        global_bridge = tdq_config.load_config(cwd=target_cwd).get("paperclip_bridge")
        if isinstance(global_bridge, dict) and "enabled" in global_bridge:
            parsed = _parse_bool(global_bridge["enabled"], "tdq_config.paperclip_bridge.enabled")
            if parsed is not None:
                cfg["enabled"] = parsed

    _apply_bridge_env_overrides(cfg)
    return cfg


def validate_base_url(base_url: str) -> str:
    """Ensure base_url uses http/https with a non-empty network host."""
    raw = str(base_url or "").strip()
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Unsafe or malformed base_url: {base_url!r}")
    return raw.rstrip("/")


def build_endpoint_url(base_url: str, template: str, issue_id: str | None = None) -> str:
    """Validate base_url and safely encode issue_id into the endpoint path."""
    clean_base = validate_base_url(base_url)
    path_tmpl = "/" + str(template or "").lstrip("/")
    if "{issue_id}" in path_tmpl:
        clean_id = str(issue_id or "").strip()
        if not clean_id or any(ord(ch) < 32 for ch in clean_id):
            raise ValueError(f"Invalid issue_id: {issue_id!r}")
        encoded = urllib.parse.quote(clean_id, safe="")
        path_tmpl = path_tmpl.replace("{issue_id}", encoded)
    return f"{clean_base}{path_tmpl}"


def resolve_api_token(cfg: dict[str, Any], required: bool = False) -> str | None:
    """Resolve Bearer token from configured env var; fail closed if required."""
    env_var = str(cfg.get("token_env_var") or "PAPERCLIP_API_TOKEN").strip()
    env_var = env_var or "PAPERCLIP_API_TOKEN"
    token = os.environ.get(env_var, "").strip()
    if token:
        return token
    if required:
        raise RuntimeError(f"Missing required API token in environment variable {env_var}")
    return None


def redact_secrets(text: str, secrets: Iterable[str]) -> str:
    """Scrub secret strings from error/log text before emission."""
    out = str(text)
    for secret in secrets:
        if secret:
            out = out.replace(secret, "***")
    return out


def _decode_json_object(raw_bytes: bytes, url: str) -> dict[str, Any]:
    data = json.loads(raw_bytes.decode("utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object from {url}, got {type(data).__name__}")
    return data


def http_json_request(
    method: str,
    url: str,
    timeout_sec: float = 5.0,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform a validated stdlib HTTP JSON request with secret redaction on error."""
    validate_base_url(url)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json", "User-Agent": "tdq-paperclip-bridge/1.0"}
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
    secrets = (token,) if token else ()
    try:
        with urllib.request.urlopen(req, timeout=float(timeout_sec)) as resp:
            raw_bytes = resp.read()
        return _decode_json_object(raw_bytes, url)
    except urllib.error.HTTPError as exc:
        err_body = exc.read(512).decode("utf-8", errors="replace") if exc.fp else ""
        msg = redact_secrets(f"HTTP {exc.code} on {method} {url}: {exc.reason} {err_body}", secrets)
        raise RuntimeError(msg) from None
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        UnicodeDecodeError,
        ValueError,
        TypeError,
    ) as exc:
        msg = redact_secrets(f"Request error on {method} {url}: {exc}", secrets)
        raise RuntimeError(msg) from None


def fetch_issue_json(
    base_url: str,
    issue_id: str,
    token: str,
    timeout_sec: float = 5.0,
    issue_endpoint: str = "/issues/{issue_id}",
) -> dict[str, Any]:
    """Fetch one Paperclip issue JSON object by id."""
    url = build_endpoint_url(base_url, issue_endpoint, issue_id=issue_id)
    return http_json_request("GET", url, timeout_sec=timeout_sec, token=token)


def _slugify_topic(issue_id: str, title: str) -> str:
    from skill_router import bo_dau

    combined = bo_dau(f"{issue_id} {title}".strip()).casefold()
    words = _WORD_RE.findall(combined)[:5]
    return "-".join(words) if words else "paperclip-issue"


def map_issue_to_tdq_init(
    issue_payload: dict[str, Any],
    cwd: str | Path | None = None,
    default_lane: str = "full",
    now_dt: datetime | None = None,
) -> dict[str, Any]:
    """Map Paperclip issue JSON into validated TDQ init parameters via P1 router."""
    issue_id = str(issue_payload.get("id") or issue_payload.get("issue_id") or "").strip()
    title = str(issue_payload.get("title") or "").strip()
    description = str(issue_payload.get("description") or "").strip()
    prompt_text = f"{title} {description}".strip() or issue_id or "paperclip task"
    target_cwd = _resolve_cwd(cwd)

    pack = tdq_domains.route_domain(prompt_text, target_cwd)
    domain_id = str(pack.get("domain_id") or "code-build")
    work_kind = str(pack.get("default_work_kind") or "build")
    raw_lane = str(issue_payload.get("lane") or pack.get("preferred_lane") or default_lane).strip()
    lane = raw_lane if raw_lane in {"quick", "full"} else "full"

    dt = now_dt if now_dt is not None else datetime.now().astimezone()
    slug = f"{dt.strftime('%Y-%m-%d-%H%M')}-{_slugify_topic(issue_id, title)}"
    return {
        "bridge_action": "pull",
        "paperclip_issue_id": issue_id,
        "tdq_slug": slug,
        "tdq_work_kind": work_kind,
        "tdq_domain_id": domain_id,
        "tdq_lane": lane,
        "brief_file": f"docs/tdq/brief/{slug}.md",
        "authority": "tdq_state.py",
    }


def _render_brief_markdown(mapped: dict[str, Any], issue_payload: dict[str, Any]) -> str:
    issue_id = mapped["paperclip_issue_id"] or "unknown"
    title = str(issue_payload.get("title") or issue_id).strip()
    desc = str(issue_payload.get("description") or "").strip() or title
    soul_line = (
        "Soul: ch\u1ea5t l\u01b0\u1ee3ng > runtime > context cost \u00b7 "
        "lu\u1eadt g\u1ed1c: skills/tdq-conventions/references/soul.md"
    )
    route_line = (
        f"- **\u0110\u1ecbnh tuy\u1ebfn P1:** `domain_id={mapped['tdq_domain_id']}` \u00b7 "
        f"`work_kind={mapped['tdq_work_kind']}` \u00b7 `lane={mapped['tdq_lane']}`"
    )
    lines = [
        f"# Brief \u2014 {issue_id}: {title}",
        soul_line,
        "",
        "## Nguy\u00ean v\u0103n",
        "",
        f"> Paperclip `{issue_id}` \u2014 {title}",
        "",
        f"- **M\u1ee5c ti\u00eau:** {desc}",
        route_line,
        "",
        "## Hi\u1ec3u & ki\u1ebfn th\u1ee9c",
        "",
        "## H\u1ecfi \u0111\u00e1p",
        "",
    ]
    return "\n".join(lines)


def _run_state_cli(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    state_script = Path(__file__).resolve().parent / "tdq_state.py"
    env = dict(os.environ)
    env["TDQ_PROJECT_DIR"] = str(cwd)
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(state_script), *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"tdq_state.py {args[0]} failed (rc={proc.returncode}): {detail}")
    return proc


def run_status(cwd: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Ping Paperclip /health endpoint (token optional)."""
    endpoints = cfg.get("endpoints") if isinstance(cfg.get("endpoints"), dict) else {}
    url = build_endpoint_url(cfg["base_url"], endpoints.get("health", "/health"))
    token = resolve_api_token(cfg, required=False)
    timeout_sec = float(cfg.get("timeout_sec", 5.0))
    resp = http_json_request("GET", url, timeout_sec=timeout_sec, token=token)
    return {"bridge_action": "status", "url": url, "ok": bool(resp.get("ok", True)), "health": resp}


def run_pull(
    cwd: Path,
    cfg: dict[str, Any],
    issue_id: str,
    lane_override: str | None = None,
    bo_qua_lsp: str | None = None,
) -> dict[str, Any]:
    """Pull one Paperclip issue, route domain via P1, call tdq_state.py init, and write brief."""
    endpoints = cfg.get("endpoints") if isinstance(cfg.get("endpoints"), dict) else {}
    validate_base_url(cfg["base_url"])
    issue_tmpl = endpoints.get("issue", "/issues/{issue_id}")
    build_endpoint_url(cfg["base_url"], issue_tmpl, issue_id=issue_id)
    token = resolve_api_token(cfg, required=True)
    issue_data = fetch_issue_json(
        cfg["base_url"], issue_id, token or "", float(cfg.get("timeout_sec", 5.0)), issue_tmpl
    )
    mapped = map_issue_to_tdq_init(issue_data, cwd=cwd, default_lane=cfg.get("default_lane", "full"))
    if lane_override in {"quick", "full"}:
        mapped["tdq_lane"] = lane_override
    reason = bo_qua_lsp or "Pulled via tdq_paperclip_bridge; LSP checked during analyze phase"
    _run_state_cli(
        cwd,
        [
            "init",
            mapped["tdq_slug"],
            mapped["tdq_lane"],
            "--kind",
            mapped["tdq_work_kind"],
            "--lang",
            "vi",
            "--bo-qua-lsp",
            reason,
        ],
    )
    brief_path = cwd / mapped["brief_file"]
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(_render_brief_markdown(mapped, issue_data), encoding="utf-8")
    _run_state_cli(
        cwd,
        [
            "set",
            f"domain_id={mapped['tdq_domain_id']}",
            f"brief_file={mapped['brief_file']}",
        ],
    )
    return mapped


def extract_report_summary(
    report_md_path: Path, state_snapshot: dict[str, Any], issue_id: str
) -> dict[str, Any]:
    """Extract compact report summary and optional HTML URL from a TDQ report file."""
    if not report_md_path.is_file():
        raise FileNotFoundError(f"Report file not found: {report_md_path}")
    text = report_md_path.read_text(encoding="utf-8")
    summary = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(_SUMMARY_PREFIX):
            summary = stripped[len(_SUMMARY_PREFIX) :].strip()
            break
    if not summary:
        body_lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
        summary = " ".join(body_lines)[:400]
    url_match = _URL_RE.search(text)
    payload: dict[str, Any] = {
        "bridge_action": "push-report",
        "paperclip_issue_id": issue_id,
        "tdq_request": str(state_snapshot.get("active_request") or report_md_path.stem),
        "tdq_phase": str(state_snapshot.get("phase") or "report"),
        "report_relpath": f"docs/tdq/reports/{report_md_path.name}",
        "summary": summary[:600],
    }
    if url_match:
        payload["report_url"] = url_match.group(0)
    return payload


def run_push_report(cwd: Path, cfg: dict[str, Any], slug: str, issue_id: str) -> dict[str, Any]:
    """Push compact TDQ report summary one-way to Paperclip issue comments."""
    endpoints = cfg.get("endpoints") if isinstance(cfg.get("endpoints"), dict) else {}
    url = build_endpoint_url(
        cfg["base_url"], endpoints.get("comments", "/issues/{issue_id}/comments"), issue_id=issue_id
    )
    report_path = cwd / "docs" / "tdq" / "reports" / f"{slug}.md"
    if not report_path.is_file():
        raise FileNotFoundError(f"Report file not found: {report_path}")
    token = resolve_api_token(cfg, required=True)
    state_proc = _run_state_cli(cwd, ["get"])
    try:
        state_data = json.loads(state_proc.stdout)
        if not isinstance(state_data, dict):
            state_data = {}
    except ValueError:
        state_data = {}
    payload = extract_report_summary(report_path, state_data, issue_id)
    timeout_sec = float(cfg.get("timeout_sec", 5.0))
    resp = http_json_request("POST", url, timeout_sec=timeout_sec, token=token, payload=payload)
    return {**payload, "url": url, "response": resp}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="One-way Paperclip CLI bridge for TDQ.")
    parser.add_argument("--cwd", default=None, help="Target project root directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    st = sub.add_parser("status", help="Check Paperclip server health endpoint.")
    st.add_argument("--json", action="store_true", help="Emit JSON output.")

    pl = sub.add_parser("pull", help="Pull one issue from Paperclip and run tdq_state init.")
    pl.add_argument("--issue", required=True, help="Paperclip issue identifier.")
    pl.add_argument("--lane", choices=("quick", "full"), default=None, help="Override TDQ lane.")
    pl.add_argument("--bo-qua-lsp", default=None, help="Optional LSP skip reason.")
    pl.add_argument("--json", action="store_true", help="Emit JSON output.")

    pr = sub.add_parser("push-report", help="Push TDQ report summary to a Paperclip issue.")
    pr.add_argument("--slug", required=True, help="Completed TDQ request slug.")
    pr.add_argument("--issue", required=True, help="Paperclip issue identifier.")
    pr.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser


def _dispatch(args: argparse.Namespace, cwd: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    if args.command == "status":
        return run_status(cwd, cfg)
    if args.command == "pull":
        return run_pull(cwd, cfg, args.issue, lane_override=args.lane, bo_qua_lsp=args.bo_qua_lsp)
    return run_push_report(cwd, cfg, args.slug, args.issue)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the disabled-by-default one-way Paperclip bridge."""
    utf8_io.force_utf8()
    args = _build_parser().parse_args(argv)
    target_cwd = _resolve_cwd(args.cwd)
    cfg = load_bridge_config(cwd=target_cwd)
    _log(f"command={args.command} cwd={target_cwd} enabled={cfg.get('enabled', False)}")
    if not cfg.get("enabled", False):
        _log("bridge disabled (enabled=false); exiting 3 without network access")
        return EXIT_DISABLED
    try:
        result = _dispatch(args, target_cwd, cfg)
    except (ValueError, FileNotFoundError) as exc:
        _log(f"ERROR input: {exc}")
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_SYNTAX
    except RuntimeError as exc:
        _log(f"ERROR runtime: {exc}")
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_IO_ERROR
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result.get('bridge_action')}: ok")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
