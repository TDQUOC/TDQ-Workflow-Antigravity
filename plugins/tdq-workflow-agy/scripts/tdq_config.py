#!/usr/bin/env python3
"""Read TDQ agent and QC configuration with env > project > plugin precedence.

Usage:
    python3 scripts/tdq_config.py show [--json] [--cwd <path>]
    python3 scripts/tdq_config.py max-qc [--json] [--cwd <path>]

Env:
    TDQ_MAX_QC_SUBAGENTS          Override qc.ultra_max_subagents (positive int or unlimited/0/none).
    TDQ_DOMAIN_ROUTER_ENABLED     Override p1.domain_router_enabled (0/false/no/off or 1/true/yes/on).
    TDQ_ZERO_DOWNGRADE_ENABLED    Override p1.zero_downgrade_enabled (0/false/no/off or 1/true/yes/on).
    PAPERCLIP_BRIDGE_ENABLED      Override paperclip_bridge.enabled (1/0).
    TDQ_PAPERCLIP_BRIDGE_ENABLED  Override paperclip_bridge.enabled (1/0, takes precedence).
    TDQ_PROJECT_DIR               Fallback project root when --cwd is omitted.
    TDQ_LOG=0                     Disable ISO-timestamped diagnostics on stderr.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
import utf8_io  # noqa: F401 — forces UTF-8 stdio on Windows

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MAX_QC_SUBAGENTS = 5
DEFAULT_AUTO_ESCALATE_RETRIES = 2
UNLIMITED_KEYWORDS: tuple[str, ...] = ("0", "unlimited", "none", "khong-gioi-han")
_BOOL_STR_MAP: dict[str, bool] = {
    "1": True,
    "true": True,
    "yes": True,
    "on": True,
    "0": False,
    "false": False,
    "no": False,
    "off": False,
}
_SECTION_BOOL_KEYS: dict[str, tuple[str, ...]] = {
    "p1": ("domain_router_enabled", "zero_downgrade_enabled"),
    "paperclip_bridge": ("enabled",),
}
_SECTION_BOOL_ENV_OVERRIDES: tuple[tuple[str, str, str], ...] = (
    ("TDQ_DOMAIN_ROUTER_ENABLED", "p1", "domain_router_enabled"),
    ("TDQ_ZERO_DOWNGRADE_ENABLED", "p1", "zero_downgrade_enabled"),
    ("PAPERCLIP_BRIDGE_ENABLED", "paperclip_bridge", "enabled"),
    ("TDQ_PAPERCLIP_BRIDGE_ENABLED", "paperclip_bridge", "enabled"),
)

DEFAULT_CONFIG: dict[str, Any] = {
    "qc": {
        "ultra_max_subagents": DEFAULT_MAX_QC_SUBAGENTS,
        "full_light_qc": True,
        "allow_unlimited_keywords": list(UNLIMITED_KEYWORDS),
    },
    "agents": {
        "default_model": "inherit",
        "auto_escalate_retries": DEFAULT_AUTO_ESCALATE_RETRIES,
        "model_ladder": [
            {
                "tier": 1,
                "family": "gemini-3.8-flash",
                "invoke_model": "flash",
                "swarm_models": [
                    "gemini-3.8-flash-low",
                    "gemini-3.8-flash-medium",
                    "gemini-3.8-flash-high",
                ],
                "use_for": "trinh-sat-don-gian",
            },
            {
                "tier": 2,
                "family": "gemini-4-hydrogen",
                "invoke_model": "inherit",
                "swarm_models": [
                    "gemini-4-hydrogen-low",
                    "gemini-4-hydrogen-medium",
                    "gemini-4-hydrogen-high",
                    "gemini-4-hydrogen-xhigh",
                ],
                "use_for": "code-chuan",
            },
            {
                "tier": 3,
                "family": "gemini-4-neon",
                "invoke_model": "inherit",
                "swarm_models": [
                    "gemini-4-neon-low",
                    "gemini-4-neon-medium",
                    "gemini-4-neon-high",
                    "gemini-4-neon-xhigh",
                ],
                "use_for": "suy-luan-sau-qc-rust",
            },
            {
                "tier": 4,
                "family": "gemini-4-carbon",
                "invoke_model": "pro",
                "swarm_models": [
                    "gemini-4-carbon-low",
                    "gemini-4-carbon-medium",
                    "gemini-4-carbon-high",
                ],
                "use_for": "bao-mat-va-leo-thang",
            },
        ],
    },
    "p0": {
        "lease_enabled": True,
        "lease_ttl_sec": 300,
        "breaker_enabled": True,
        "breaker_consecutive_failures": 3,
        "mcp_quarantine_enabled": True,
        "mcp_mode": "balanced",
        "oldest_dispatch_share": 4,
        "budget_caps": {
            "soft_warn_ratio": 0.8,
            "hard_stop_tokens": None,
            "hard_stop_usd": None,
        },
    },
    "p1": {
        "domain_router_enabled": True,
        "zero_downgrade_enabled": True,
    },
    "paperclip_bridge": {
        "enabled": False,
    },
}

ROLE_DEFAULT_TIERS: dict[str, int] = {
    "tdq-explorer": 1,
    "explorer": 1,
    "tdq-implementer": 2,
    "implementer": 2,
    "tdq-refactor-cleaner": 2,
    "refactor-cleaner": 2,
    "tdq-build-resolver": 2,
    "build-resolver": 2,
    "tdq-qc-tester": 3,
    "qc-tester": 3,
    "tdq-reviewer": 3,
    "reviewer": 3,
    "tdq-debugger": 3,
    "debugger": 3,
    "tdq-security-reviewer": 4,
    "security-reviewer": 4,
}


def _log(message: str) -> None:
    """Emit an ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"[{stamp}] tdq_config: {message}", file=sys.stderr)


def _resolve_project_dir(cwd: str | Path | None) -> Path:
    if cwd is not None:
        return Path(cwd)
    env_dir = os.environ.get("TDQ_PROJECT_DIR", "").strip()
    return Path(env_dir) if env_dir else Path.cwd()


def _read_json_object(path: Path, label: str) -> tuple[dict[str, Any] | None, bool]:
    if not path.is_file():
        return None, True
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _log(f"WARN unreadable {label} config at {path}: {exc}")
        return None, False
    if not isinstance(raw, dict):
        _log(f"WARN {label} config at {path} is not a JSON object; using defaults")
        return None, False
    return raw, True


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(base.get(key), dict):
            if isinstance(value, dict):
                _deep_merge(base[key], value)
            else:
                _log(f"WARN ignoring non-object override for section {key!r}")
        else:
            base[key] = copy.deepcopy(value)
    return base


def _parse_env_value(raw: str) -> int | str:
    try:
        return int(raw)
    except ValueError:
        return raw


def _parse_bool_value(raw: Any, label: str) -> bool | None:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int) and raw in (0, 1):
        return bool(raw)
    if isinstance(raw, str):
        norm = raw.strip().lower()
        if norm in _BOOL_STR_MAP:
            return _BOOL_STR_MAP[norm]
    _log(f"WARN invalid boolean {label}={raw!r}; ignoring override")
    return None


def _normalize_section_booleans(
    config: dict[str, Any],
    prev_section: dict[str, Any],
    layer_section: dict[str, Any],
    section: str,
    keys: tuple[str, ...],
) -> None:
    target = config.setdefault(section, {})
    if not isinstance(target, dict):
        return
    for key in keys:
        if key not in layer_section:
            continue
        parsed = _parse_bool_value(layer_section[key], f"{section}.{key}")
        if parsed is not None:
            target[key] = parsed
        elif key in prev_section:
            target[key] = prev_section[key]


def _apply_flat_p1_fallback(config: dict[str, Any], layer: dict[str, Any]) -> None:
    if "domain_router_enabled" not in layer:
        return
    layer_p1 = layer.get("p1")
    if isinstance(layer_p1, dict) and "domain_router_enabled" in layer_p1:
        return
    p1_cfg = config.setdefault("p1", {})
    if not isinstance(p1_cfg, dict):
        return
    parsed = _parse_bool_value(layer["domain_router_enabled"], "domain_router_enabled")
    if parsed is not None:
        p1_cfg["domain_router_enabled"] = parsed


def _merge_config_layer(config: dict[str, Any], layer: dict[str, Any]) -> None:
    prev_sections = {
        sec: copy.deepcopy(config.get(sec)) if isinstance(config.get(sec), dict) else {}
        for sec in _SECTION_BOOL_KEYS
    }
    _deep_merge(config, layer)
    for sec, keys in _SECTION_BOOL_KEYS.items():
        layer_sec = layer.get(sec)
        if isinstance(layer_sec, dict):
            _normalize_section_booleans(config, prev_sections[sec], layer_sec, sec, keys)
    _apply_flat_p1_fallback(config, layer)


def _apply_section_bool_env_overrides(config: dict[str, Any]) -> None:
    for env_name, section, key in _SECTION_BOOL_ENV_OVERRIDES:
        raw_env = os.environ.get(env_name)
        if raw_env is None or not raw_env.strip():
            continue
        section_cfg = config.setdefault(section, {})
        if not isinstance(section_cfg, dict):
            continue
        parsed = _parse_bool_value(raw_env, env_name)
        if parsed is not None:
            section_cfg[key] = parsed


def _apply_env_override(config: dict[str, Any]) -> None:
    raw_env = os.environ.get("TDQ_MAX_QC_SUBAGENTS")
    if raw_env is not None:
        stripped = raw_env.strip()
        if stripped:
            qc_cfg = config.setdefault("qc", {})
            if isinstance(qc_cfg, dict):
                qc_cfg["ultra_max_subagents"] = _parse_env_value(stripped)
    _apply_section_bool_env_overrides(config)


def load_config(cwd: str | Path | None = None) -> dict[str, Any]:
    """Load merged plugin, project, and env configuration with safe defaults."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    plugin_data, plugin_ok = _read_json_object(PLUGIN_ROOT / "tdq-config.json", "plugin")
    if not plugin_ok:
        config = copy.deepcopy(DEFAULT_CONFIG)
    elif plugin_data is not None:
        _merge_config_layer(config, plugin_data)

    project_file = _resolve_project_dir(cwd) / "docs" / "tdq" / "config.json"
    project_data, project_ok = _read_json_object(project_file, "project")
    if not project_ok:
        config = copy.deepcopy(DEFAULT_CONFIG)
    elif project_data is not None:
        _merge_config_layer(config, project_data)

    _apply_env_override(config)
    return config


def _unlimited_keywords(qc_cfg: dict[str, Any]) -> set[str]:
    raw_kw = qc_cfg.get("allow_unlimited_keywords")
    if isinstance(raw_kw, list):
        return {str(item).strip().lower() for item in raw_kw if str(item).strip()}
    return set(UNLIMITED_KEYWORDS)


def _positive_or_unlimited(value: int, raw: Any) -> int | None:
    if value == 0:
        return None
    if value > 0:
        return value
    _log(f"WARN invalid ultra_max_subagents={raw!r}; falling back to {DEFAULT_MAX_QC_SUBAGENTS}")
    return DEFAULT_MAX_QC_SUBAGENTS


def _parse_max_qc(raw: Any, keywords: set[str]) -> int | None:
    if isinstance(raw, bool):
        _log(f"WARN invalid boolean ultra_max_subagents={raw!r}; falling back to {DEFAULT_MAX_QC_SUBAGENTS}")
        return DEFAULT_MAX_QC_SUBAGENTS
    if isinstance(raw, int):
        return _positive_or_unlimited(raw, raw)
    if isinstance(raw, str):
        text = raw.strip().lower()
        if text in keywords:
            return None
        try:
            return _positive_or_unlimited(int(text), raw)
        except ValueError:
            pass
    _log(f"WARN invalid ultra_max_subagents={raw!r}; falling back to {DEFAULT_MAX_QC_SUBAGENTS}")
    return DEFAULT_MAX_QC_SUBAGENTS


def max_qc_subagents(cwd: str | Path | None = None) -> int | None:
    """Return max parallel QC subagents for ultra mode, or None when unlimited."""
    cfg = load_config(cwd=cwd)
    qc_cfg = cfg.get("qc") if isinstance(cfg.get("qc"), dict) else {}
    raw = qc_cfg.get("ultra_max_subagents", DEFAULT_MAX_QC_SUBAGENTS)
    return _parse_max_qc(raw, _unlimited_keywords(qc_cfg))


def _tier_sort_key(entry: dict[str, Any]) -> int:
    raw = entry.get("tier", 99)
    if isinstance(raw, bool):
        return 99
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 99


def _extract_ladder(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    agents_cfg = cfg.get("agents") if isinstance(cfg.get("agents"), dict) else {}
    raw_ladder = agents_cfg.get("model_ladder")
    if (
        not isinstance(raw_ladder, list)
        or not raw_ladder
        or not all(isinstance(item, dict) for item in raw_ladder)
    ):
        _log("WARN invalid agents.model_ladder; falling back to defaults")
        return copy.deepcopy(DEFAULT_CONFIG["agents"]["model_ladder"])
    return sorted(copy.deepcopy(raw_ladder), key=_tier_sort_key)


def model_ladder(cwd: str | Path | None = None) -> list[dict[str, Any]]:
    """Return the ordered 4-tier Gemini model ladder from configuration."""
    return _extract_ladder(load_config(cwd=cwd))


def _normalize_positive_int(value: Any, default: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        _log(f"WARN invalid {name}={value!r}; using {default}")
        return default
    return value


def _pick_swarm_model(entry: dict[str, Any], escalated: bool) -> str:
    models = entry.get("swarm_models")
    if not isinstance(models, list) or not models:
        return str(entry.get("family") or "inherit")
    preferred = ("-xhigh", "-high") if escalated else ("-high",)
    for suffix in preferred:
        for candidate in models:
            if str(candidate).endswith(suffix):
                return str(candidate)
    return str(models[-1])


def _selected_base_tier(entry: dict[str, Any], fallback: int) -> int:
    raw = entry.get("tier")
    return raw if isinstance(raw, int) and not isinstance(raw, bool) else fallback


def resolve_model_for_role(
    role: str, attempt: int = 1, cwd: str | Path | None = None
) -> dict[str, Any]:
    """Resolve model tier recommendation for an agent role and attempt number."""
    cfg = load_config(cwd=cwd)
    ladder = _extract_ladder(cfg)
    agents_cfg = cfg.get("agents") if isinstance(cfg.get("agents"), dict) else {}
    retries = _normalize_positive_int(
        agents_cfg.get("auto_escalate_retries", DEFAULT_AUTO_ESCALATE_RETRIES),
        DEFAULT_AUTO_ESCALATE_RETRIES,
        "auto_escalate_retries",
    )
    norm_attempt = _normalize_positive_int(attempt, 1, "attempt")
    norm_role = (role or "").strip().lower()
    base_tier = ROLE_DEFAULT_TIERS.get(norm_role, 2)

    base_idx = min(
        range(len(ladder)),
        key=lambda idx: abs(_tier_sort_key(ladder[idx]) - base_tier),
    )
    escalated = norm_attempt > retries
    bump = (norm_attempt - retries) if escalated else 0
    target_idx = min(len(ladder) - 1, base_idx + bump)
    selected = ladder[target_idx]
    return {
        "role": norm_role or "unknown",
        "attempt": norm_attempt,
        "escalated": escalated,
        "base_tier": _selected_base_tier(ladder[base_idx], base_tier),
        "tier": selected.get("tier", target_idx + 1),
        "family": selected.get("family", ""),
        "invoke_model": selected.get("invoke_model", "inherit"),
        "swarm_models": list(selected.get("swarm_models") or []),
        "recommended_swarm_model": _pick_swarm_model(selected, escalated),
        "use_for": selected.get("use_for", ""),
    }


def _print_show_text(cfg: dict[str, Any], max_qc: int | None) -> None:
    agents_cfg = cfg.get("agents") if isinstance(cfg.get("agents"), dict) else {}
    cap_label = "unlimited" if max_qc is None else str(max_qc)
    print(f"ultra_max_subagents: {cap_label}")
    print(f"default_model: {agents_cfg.get('default_model', 'inherit')}")
    print(f"auto_escalate_retries: {agents_cfg.get('auto_escalate_retries', DEFAULT_AUTO_ESCALATE_RETRIES)}")
    for tier in _extract_ladder(cfg):
        print(
            f"tier {tier.get('tier')}: {tier.get('family')} "
            f"(invoke={tier.get('invoke_model')}, use_for={tier.get('use_for')})"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect TDQ plugin and project configuration.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_cmd = subparsers.add_parser("show", help="Print effective merged configuration.")
    show_cmd.add_argument("--json", action="store_true", help="Emit JSON output.")
    show_cmd.add_argument("--cwd", default=None, help="Project directory to inspect.")

    max_cmd = subparsers.add_parser("max-qc", help="Print effective ultra QC subagent cap.")
    max_cmd.add_argument("--json", action="store_true", help="Emit JSON output.")
    max_cmd.add_argument("--cwd", default=None, help="Project directory to inspect.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run tdq_config CLI subcommands."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    target_cwd = _resolve_project_dir(args.cwd)
    _log(f"command={args.command} cwd={target_cwd}")

    if args.command == "show":
        cfg = load_config(cwd=target_cwd)
        if args.json:
            print(json.dumps(cfg, indent=2, ensure_ascii=False))
        else:
            _print_show_text(cfg, max_qc_subagents(cwd=target_cwd))
        return 0

    cap = max_qc_subagents(cwd=target_cwd)
    if args.json:
        print(json.dumps({"ultra_max_subagents": cap, "unlimited": cap is None}, ensure_ascii=False))
    else:
        print("unlimited" if cap is None else str(cap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
