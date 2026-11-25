#!/usr/bin/env python3
"""Load, route, and enforce TDQ domain packs and zero-downgrade locks.

Env:
    TDQ_DOMAIN_ROUTER_ENABLED   Override p1.domain_router_enabled (1/0).
    TDQ_ZERO_DOWNGRADE_ENABLED  Override p1.zero_downgrade_enabled (1/0).
    TDQ_PROJECT_DIR             Fallback project root when cwd is omitted.
    TDQ_LOG=0                   Disable ISO-timestamped diagnostics on stderr.
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

import tdq_config
import utf8_io

DEFAULT_DOMAIN_ID = "code-build"
DEFAULT_DOMAINS_DIR = Path(__file__).resolve().parent / "defaults" / "domains"
PROJECT_DOMAINS_REL = Path("docs") / "tdq" / "domains"
STATE_REL = Path("docs") / "tdq" / "state.json"

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

_BUILTIN_CODE_BUILD: dict[str, Any] = {
    "schema_version": 1,
    "domain_id": DEFAULT_DOMAIN_ID,
    "title": "Engineering Code and Feature Delivery",
    "default_work_kind": "build",
    "allow_downgrade": False,
    "escalate_on_code_edit": False,
    "preferred_lane": "full",
    "default_muc_qc": "standard",
    "preferred_skills": ["tdq-intake", "tdq-spec", "tdq-plan", "tdq-build"],
    "keywords_en": ["implement", "fix", "refactor", "feature", "bug", "test", "api", "script"],
    "keywords_vi_ascii": ["sua loi", "tinh nang", "viet code", "nang cap", "tai cau truc"],
}


def _log(message: str) -> None:
    """Emit an ISO-timestamped diagnostic line to stderr unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"[{stamp}] tdq_domains: {message}", file=sys.stderr)


def _resolve_cwd(cwd: str | Path | None) -> Path:
    if cwd is not None:
        return Path(cwd)
    env_dir = os.environ.get("TDQ_PROJECT_DIR", "").strip()
    return Path(env_dir) if env_dir else Path.cwd()


def _parse_bool_flag(raw: Any, default: bool, label: str) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int) and raw in (0, 1):
        return bool(raw)
    if isinstance(raw, str):
        norm = raw.strip().lower()
        if norm in _BOOL_MAP:
            return _BOOL_MAP[norm]
    _log(f"WARN invalid boolean {label}={raw!r}; using {default}")
    return default


def _read_pack_file(path: Path, source_label: str) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _log(f"WARN unreadable {source_label} domain pack at {path}: {exc}")
        return None
    if not isinstance(raw, dict):
        _log(f"WARN {source_label} domain pack at {path} is not a JSON object")
        return None
    domain_id = raw.get("domain_id")
    if not isinstance(domain_id, str) or not domain_id.strip():
        _log(f"WARN {source_label} domain pack at {path} missing domain_id; skipping")
        return None
    normalized = copy.deepcopy(raw)
    normalized["domain_id"] = domain_id.strip()
    return normalized


def _merge_pack_entry(
    base: dict[str, Any] | None, incoming: dict[str, Any], did: str
) -> dict[str, Any]:
    merged = copy.deepcopy(base) if base is not None else {}
    merged.update(copy.deepcopy(incoming))
    merged["domain_id"] = did
    return merged


def _load_dir_packs(
    directory: Path, packs: dict[str, dict[str, Any]], label: str
) -> None:
    if not directory.is_dir():
        return
    for path in sorted(directory.glob("*.json")):
        parsed = _read_pack_file(path, label)
        if parsed is None:
            continue
        did = parsed["domain_id"]
        packs[did] = _merge_pack_entry(packs.get(did), parsed, did)


def load_domain_packs(cwd: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Load default domain packs and merge project overrides from docs/tdq/domains/."""
    packs: dict[str, dict[str, Any]] = {}
    _load_dir_packs(DEFAULT_DOMAINS_DIR, packs, "default")
    if DEFAULT_DOMAIN_ID not in packs:
        packs[DEFAULT_DOMAIN_ID] = copy.deepcopy(_BUILTIN_CODE_BUILD)
    project_dir = _resolve_cwd(cwd) / PROJECT_DOMAINS_REL
    _load_dir_packs(project_dir, packs, "override")
    return packs


def _p1_flag_enabled(
    cwd: Path, config: dict[str, Any] | None, env_name: str, key: str
) -> bool:
    raw_env = os.environ.get(env_name)
    if raw_env is not None and raw_env.strip():
        return _parse_bool_flag(raw_env, True, env_name)
    cfg = config if isinstance(config, dict) else tdq_config.load_config(cwd=cwd)
    p1_cfg = cfg.get("p1")
    if isinstance(p1_cfg, dict) and key in p1_cfg:
        return _parse_bool_flag(p1_cfg[key], True, f"p1.{key}")
    if key in cfg:
        return _parse_bool_flag(cfg[key], True, key)
    return True


def _tokenize_for_routing(text: str) -> tuple[list[str], set[str]]:
    from skill_router import bo_dau, tach_tu  # lazy import keeps hook imports decoupled

    ascii_text = bo_dau(str(text or ""))
    raw_tokens = tach_tu(ascii_text, bo_hu_tu=False)
    filtered_set = set(tach_tu(ascii_text, bo_hu_tu=True))
    return raw_tokens, filtered_set


def _extract_pack_keywords(
    pack: dict[str, Any],
) -> tuple[list[tuple[str, ...]], set[str]]:
    phrases: list[tuple[str, ...]] = []
    singles: set[str] = set()
    seen_phrases: set[tuple[str, ...]] = set()
    for field in ("keywords_en", "keywords_vi_ascii"):
        items = pack.get(field)
        if not isinstance(items, list):
            continue
        for kw in items:
            words, _ = _tokenize_for_routing(str(kw))
            if len(words) > 1 and tuple(words) not in seen_phrases:
                seen_phrases.add(tuple(words))
                phrases.append(tuple(words))
            elif len(words) == 1:
                singles.add(words[0])
    return phrases, singles


def _score_pack(
    pack: dict[str, Any],
    padded_prompt: str,
    raw_set: set[str],
    filtered_set: set[str],
) -> int:
    phrases, singles = _extract_pack_keywords(pack)
    score = 0
    matched_phrase_tokens: set[str] = set()
    unmatched_phrase_tokens: set[str] = set()
    for pw in phrases:
        if f" {' '.join(pw)} " in padded_prompt:
            score += 2
            matched_phrase_tokens.update(pw)
        else:
            unmatched_phrase_tokens.update(pw)
    score += sum(1 for tok in singles if tok in raw_set)
    partial_tokens = unmatched_phrase_tokens - singles - matched_phrase_tokens
    score += sum(1 for tok in partial_tokens if tok in filtered_set)
    return score


def _resolve_route_inputs(
    prompt: str | Path | None,
    cwd: str | Path | None,
    prompt_text: str | None,
) -> tuple[str, Path]:
    if prompt_text is not None:
        raw_cwd = cwd if cwd is not None else prompt
        return str(prompt_text), _resolve_cwd(raw_cwd)
    if isinstance(prompt, Path):
        return ("" if cwd is None else str(cwd)), prompt
    if (
        isinstance(prompt, str)
        and isinstance(cwd, str)
        and os.path.isdir(prompt)
        and not os.path.isdir(cwd)
    ):
        return cwd, Path(prompt)
    return ("" if prompt is None else str(prompt)), _resolve_cwd(cwd)


def _select_best_pack(
    packs: dict[str, dict[str, Any]], prompt: str
) -> tuple[str, str, dict[str, int]]:
    raw_tokens, filtered_set = _tokenize_for_routing(prompt)
    if not raw_tokens:
        return DEFAULT_DOMAIN_ID, "empty_prompt_fallback", {}
    padded_prompt = f" {' '.join(raw_tokens)} "
    raw_set = set(raw_tokens)
    scores = {
        did: _score_pack(pack, padded_prompt, raw_set, filtered_set)
        for did, pack in packs.items()
    }
    top_score = max(scores.values(), default=0)
    if top_score <= 0:
        return DEFAULT_DOMAIN_ID, "no_keyword_match_fallback", scores
    leaders = [did for did, val in scores.items() if val == top_score]
    if len(leaders) > 1:
        return DEFAULT_DOMAIN_ID, "ambiguous_tie_fallback", scores
    return leaders[0], f"keyword_score={top_score}", scores


def _route_domain_detail(
    prompt: str | Path | None = None,
    cwd: str | Path | None = None,
    explicit: str | None = None,
    *,
    prompt_text: str | None = None,
) -> tuple[dict[str, Any], str, bool, dict[str, int]]:
    text, target_cwd = _resolve_route_inputs(prompt, cwd, prompt_text)
    packs = load_domain_packs(target_cwd)
    enabled = _p1_flag_enabled(
        target_cwd, None, "TDQ_DOMAIN_ROUTER_ENABLED", "domain_router_enabled"
    )
    if not enabled:
        return copy.deepcopy(packs[DEFAULT_DOMAIN_ID]), "router_disabled", False, {}
    if isinstance(explicit, str) and explicit.strip():
        exp_id = explicit.strip()
        if exp_id in packs:
            return copy.deepcopy(packs[exp_id]), "explicit", True, {}
        _log(f"WARN unknown explicit domain {explicit!r}; falling back to {DEFAULT_DOMAIN_ID}")
        return copy.deepcopy(packs[DEFAULT_DOMAIN_ID]), "unknown_explicit_fallback", True, {}
    selected_id, reason, scores = _select_best_pack(packs, text)
    return copy.deepcopy(packs[selected_id]), reason, True, scores


def route_domain(
    prompt: str | Path | None = None,
    cwd: str | Path | None = None,
    explicit: str | None = None,
    *,
    prompt_text: str | None = None,
) -> dict[str, Any]:
    """Route a prompt to the best matching domain pack, falling back to code-build."""
    pack, reason, _enabled, _scores = _route_domain_detail(
        prompt, cwd, explicit, prompt_text=prompt_text
    )
    _log(f"route domain={pack['domain_id']} reason={reason}")
    return pack


def _requires_code_escalation(pack: dict[str, Any]) -> bool:
    if bool(pack.get("escalate_on_code_edit", False)):
        return True
    return str(pack.get("default_work_kind", "")).strip().lower() == "investigate"


def _is_non_escalating_code_pack(domain_id: str, pack: dict[str, Any] | None) -> bool:
    if domain_id == DEFAULT_DOMAIN_ID:
        return True
    if pack is None:
        return False
    return not _requires_code_escalation(pack)


def can_transition_domain(
    current_domain: str | None,
    target_domain: str,
    packs: dict[str, dict[str, Any]] | None = None,
    downgrade_locked: bool = False,
) -> tuple[bool, str]:
    """Allow one-way escalation to code-build; block downgrades once locked or in code."""
    resolved_packs = packs if packs is not None else load_domain_packs(None)
    to_id = str(target_domain or "").strip()
    if not to_id or to_id not in resolved_packs:
        return False, f"Unknown target domain: {target_domain!r}"
    to_pack = resolved_packs[to_id]
    to_non_code = _requires_code_escalation(to_pack)
    from_id = str(current_domain or "").strip()
    if from_id == to_id:
        return True, f"domain unchanged ({to_id})"
    if downgrade_locked and to_non_code:
        return False, f"Zero-downgrade lock active: cannot switch to {to_id!r}"
    if not from_id:
        return True, f"initial domain set to {to_id}"
    from_pack = resolved_packs.get(from_id)
    if _is_non_escalating_code_pack(from_id, from_pack) and to_non_code:
        allow_down = bool(from_pack.get("allow_downgrade", False)) if from_pack else False
        if not allow_down:
            return False, f"Downgrade blocked: cannot move from {from_id!r} to {to_id!r}"
    return True, f"transition allowed: {from_id} -> {to_id}"


def should_block_code_edit(
    cwd: str | Path | None,
    state: dict[str, Any] | None,
    config: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Return (True, reason) when code edits outside docs/ require escalate-to-build."""
    if not isinstance(state, dict) or not state.get("active_request"):
        return False, "no active request"
    target_cwd = _resolve_cwd(cwd)
    if not _p1_flag_enabled(
        target_cwd, config, "TDQ_ZERO_DOWNGRADE_ENABLED", "zero_downgrade_enabled"
    ):
        return False, "zero_downgrade_disabled"
    work_kind = str(state.get("work_kind") or "").strip().lower()
    if work_kind == "investigate":
        return True, "work_kind=investigate requires escalate-to-build before editing code"
    domain_id = state.get("domain_id")
    if isinstance(domain_id, str) and domain_id.strip():
        did = domain_id.strip()
        pack = load_domain_packs(target_cwd).get(did)
        if pack is not None and _requires_code_escalation(pack):
            return True, f"domain_id={did} requires escalate-to-build before editing code"
    return False, "code edits allowed"


def _load_state_file(cwd: Path, state_file: str | None) -> dict[str, Any] | None:
    path = Path(state_file) if state_file else (cwd / STATE_REL)
    if not path.is_file():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _log(f"WARN unreadable state file at {path}: {exc}")
        return None
    return parsed if isinstance(parsed, dict) else None


def _cmd_list(args: argparse.Namespace) -> int:
    packs = load_domain_packs(_resolve_cwd(args.cwd))
    if args.json:
        print(json.dumps(packs, indent=2, ensure_ascii=True))
        return 0
    for did in sorted(packs):
        p = packs[did]
        esc = str(bool(p.get("escalate_on_code_edit", False))).lower()
        print(
            f"{did} | work_kind={p.get('default_work_kind')} | "
            f"escalate_on_code_edit={esc} | lane={p.get('preferred_lane')}"
        )
    return 0


def _cmd_route(args: argparse.Namespace) -> int:
    prompt_val = args.prompt if args.prompt is not None else args.prompt_pos
    if prompt_val is None and not args.explicit:
        raise ValueError("route requires --prompt <text>, positional prompt, or --explicit")
    pack, reason, enabled, scores = _route_domain_detail(
        prompt_val or "", _resolve_cwd(args.cwd), args.explicit
    )
    _log(f"route domain={pack['domain_id']} reason={reason}")
    if args.json:
        payload = {**pack, "route_reason": reason, "router_enabled": enabled, "scores": scores}
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(f"{pack['domain_id']} (work_kind={pack.get('default_work_kind')}, reason={reason})")
    return 0


def _cmd_check_transition(args: argparse.Namespace) -> int:
    packs = load_domain_packs(_resolve_cwd(args.cwd))
    allowed, reason = can_transition_domain(
        args.from_domain, args.to_domain, packs, downgrade_locked=args.locked
    )
    if args.json:
        payload = {
            "allowed": allowed,
            "from_domain": args.from_domain,
            "to_domain": args.to_domain,
            "downgrade_locked": args.locked,
            "reason": reason,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(f"{'allow' if allowed else 'deny'}: {reason}")
    return 0 if allowed else 1


def _cmd_check_edit(args: argparse.Namespace) -> int:
    target_cwd = _resolve_cwd(args.cwd)
    state = _load_state_file(target_cwd, args.state_file)
    blocked, reason = should_block_code_edit(target_cwd, state)
    if args.json:
        print(json.dumps({"blocked": blocked, "reason": reason}, indent=2, ensure_ascii=True))
    else:
        print(f"{'block' if blocked else 'allow'}: {reason}")
    return 1 if blocked else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and route TDQ domain packs.")
    sub = parser.add_subparsers(dest="command", required=True)

    list_cmd = sub.add_parser("list", help="List effective merged domain packs.")
    list_cmd.add_argument("--cwd", default=None, help="Project directory.")
    list_cmd.add_argument("--json", action="store_true", help="Emit JSON output.")

    route_cmd = sub.add_parser("route", help="Route a prompt to a domain pack.")
    route_cmd.add_argument("prompt_pos", nargs="?", default=None, help="Prompt text.")
    route_cmd.add_argument("--prompt", default=None, help="Prompt text.")
    route_cmd.add_argument("--explicit", default=None, help="Explicit domain_id override.")
    route_cmd.add_argument("--cwd", default=None, help="Project directory.")
    route_cmd.add_argument("--json", action="store_true", help="Emit JSON output.")

    tr_cmd = sub.add_parser("check-transition", help="Check domain transition rules.")
    tr_cmd.add_argument("--from", dest="from_domain", default=None, help="Current domain_id.")
    tr_cmd.add_argument("--to", dest="to_domain", required=True, help="Target domain_id.")
    tr_cmd.add_argument("--locked", action="store_true", help="Set downgrade_locked=True.")
    tr_cmd.add_argument("--cwd", default=None, help="Project directory.")
    tr_cmd.add_argument("--json", action="store_true", help="Emit JSON output.")

    ed_cmd = sub.add_parser("check-edit", help="Check whether code edit is blocked.")
    ed_cmd.add_argument("--cwd", default=None, help="Project directory.")
    ed_cmd.add_argument("--state-file", default=None, help="Optional state JSON path.")
    ed_cmd.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for domain pack inspection and routing."""
    utf8_io.force_utf8()
    args = _build_parser().parse_args(argv)
    _log(f"command={args.command} cwd={_resolve_cwd(args.cwd)}")
    handlers = {
        "list": _cmd_list,
        "route": _cmd_route,
        "check-transition": _cmd_check_transition,
        "check-edit": _cmd_check_edit,
    }
    try:
        return handlers[args.command](args)
    except ValueError as exc:
        _log(f"ERROR {exc}")
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
