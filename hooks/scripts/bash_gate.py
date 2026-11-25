#!/usr/bin/env python3
"""PreToolUse (Bash) — observe/remind; deny sub-agent mutation before implement.

1. Observe into the turn ledger: `state_cli` when the command calls scripts/tdq_state.py,
   `next_run` when that command is `next`. This is the evidence letting stop_gate know the
   agent really ran the command, instead of trusting an echo line the model printed itself.
2. Remind:
   TDQ:GIT   — a branch/worktree name starting with claude|antigravity|gemini|codex; a commit
               message carrying AI traces ("generated with…", Co-Authored-By).
   TDQ:STATE — writing docs/tdq/state.json | STATE.md straight through the shell (redirect,
               tee, sed -i, mv/cp, truncate, inline python).
   TDQ:OUTPUT— a command dumping a whole file/history into context with no line limit.
"""
import base64
import os
import re

from _common import (
    block,
    detect_subagent,
    echo_line,
    is_agy,
    observe,
    payload_cwd,
    read_payload,
    remind,
    remind_force,
    turn_rows,
)
# Keep this AFTER `from _common`: `_common` is what injects `scripts/` into sys.path.
from tdq_state import _info  # noqa: E402

BAN = re.compile(r"^(claude|antigravity|gemini|codex)", re.IGNORECASE)
BRANCH_PATTERNS = [
    re.compile(r"git\s+checkout\s+-b\s+(\S+)"),
    re.compile(r"git\s+switch\s+(?:-c|--create)\s+(\S+)"),
    re.compile(r"git\s+branch\s+(?!-)(\S+)"),
]
WORKTREE = re.compile(r"git\s+worktree\s+add\s+(?:-b\s+(\S+)\s+)?(\S+)")
BAD_MSG = [
    re.compile(r"generated\s+with.{0,40}?(claude|gemini|codex|antigravity)", re.IGNORECASE | re.DOTALL),
    re.compile(r"được\s+tạo\s+(?:cùng|với|bởi).{0,40}?(claude|gemini|codex|antigravity)", re.IGNORECASE | re.DOTALL),  # i18n-allow
    re.compile(r"co-authored-by:.{0,60}?(claude|gemini|codex|antigravity)", re.IGNORECASE),
]
STATE = r"docs/tdq/(?:state\.json|STATE\.md|\.tdq-runtime(?:/[^\s'\";&|<>()]*)?)"
STATE_WRITES = [
    re.compile(r">{1,2}\s*['\"]?\S*" + STATE),
    re.compile(r"\btee\b[^|;&]*" + STATE),
    re.compile(r"\bsed\b[^;|&]*\s-i[^;|&]*" + STATE),
    re.compile(r"\b(?:mv|cp)\b[^;|&]*" + STATE),
    re.compile(r"\btruncate\b[^;|&]*" + STATE),
    re.compile(r"\bpython3?\b[^;|&]*" + STATE),
    re.compile(r"\bopen\([^)]*" + STATE),
]
# Commands that tend to dump their whole content into context. Every output is re-read by the
# model on EVERY remaining API call of the session, so one needless dump multiplies itself
# hundreds of times over.
DUMP = re.compile(
    r"(?:^|[|;&]|\bthen\b|\bdo\b)\s*(cat|git\s+log|git\s+diff|git\s+show|ls\s+-R)\b")
# Signs the command ALREADY limits itself — one sign is enough to stay silent.
GIOI_HAN = re.compile(
    r"\|\s*(?:head|tail|wc|jq|sed\s+-n)\b"      # piped into a trimming command
    r"|\b(?:head|tail)\b"
    r"|(?:^|\s)-[a-zA-Z]*[nc]\s*\d"              # -n 20 · -c 500 · -n20
    r"|--stat\b|--name-only\b|--oneline\b|--shortstat\b|--numstat\b"
    r"|\|\s*grep\b[^|]*\s-[a-zA-Z]*[clq]\b")
# `cat > f <<EOF` WRITES a file rather than reading one — a reminder here is just noise.
CAT_GHI = re.compile(r"\bcat\b[^|;&]*(?:<<|>)")

STATE_CLI = re.compile(r"tdq_state\.py\s+(\w[\w-]*)")
# nhanh|express are the CLI aliases of quick (see LANE_ALIASES in tdq_state).  # i18n-allow
APPROVE_CLI = re.compile(r"tdq_state\.py\s+approve\s+(spec|plan|quick|nhanh|express)\b")
SETPHASE_CLI = re.compile(r"tdq_state\.py\s+set\b.*?\bphase=(\w+)")
NEXT_PHASE_TARGET = {"plan": "spec", "implement": "plan"}
# CLI aliases → the gate name prompt_context writes into `signal` rows. `approve plan --mode`
# is also the answer to the mode gate, so a matched `mode` signal opens it too.
SIGNAL_TARGETS = {"nhanh": ("quick",), "express": ("quick",), "plan": ("plan", "mode")}  # i18n-allow
SHELL_MUTATOR = re.compile(
    r"(?:^\s*(?:rm\b|del\b|erase\b|rmdir\b|mklink\b|sed\b.*(?:^|\s)-i(?:\s|$)|(?:cp|mv|tee|truncate)\b|"
    r"(?:Set-Content|Add-Content|Out-File|Copy-Item|Move-Item|Remove-Item|New-Item|Set-Item)\b)|"
    r"\b(?:python3?|py)\b.*\b(?:open\([^)]*['\"](?:w|a|x)['\"]|write_text\b|write_bytes\b|"
    r"os\.(?:remove|unlink|replace|rename)\b|shutil\.(?:copy|move|rmtree)\b)|"
    r"\bnode\b.*(?:\b(?:writeFile|writeFileSync|appendFile|appendFileSync|rmSync|unlinkSync|createWriteStream)\b|"
    r"fs\.promises\.(?:writeFile|unlink|rm))|"
    r"\bgit\b(?:\s+-C\s+(?:\"[^\"]*\"|'[^']*'|\S+))?\s+(?:commit|add|rm|mv|reset|checkout|switch|clean|push|merge|rebase|cherry-pick)\b)",
    re.IGNORECASE | re.DOTALL,
)
_SHELL_WRAPPER_RE = re.compile(
    r"(?:^|\s)(?:(?:bash|sh|zsh|dash|ksh|pwsh|powershell(?:\.exe)?)\b[^\n]*?\s-(?:[a-z]*c|Command)|cmd(?:\.exe)?\b[^\n]*?\s+/[ck])\s+",
    re.IGNORECASE,
)
STDOUT_WRITE = re.compile(r"(?<![<=!-])(?:>>|(?<![>=])>(?![=&]))\s*(\S+)")
DOCS_ARTIFACT = re.compile(r"docs[\\/]tdq[\\/]artifacts[\\/]", re.IGNORECASE)


def _latest_signal(rows, targets):
    """The LATEST kind="signal" row matching one of targets (walking the turn ledger backwards)."""
    for row in reversed(rows):
        if row.get("kind") == "signal" and row.get("target") in targets:
            return row
    return None


def _check_signal_mismatch(cwd, payload, target, rows):
    """Deny an approval the user's own prompt this turn did not give.

    One user prompt opens one gate: prompt_context classifies the prompt and writes a `signal`
    row. A `turn_start` row proves that hook ran this turn, so a missing or unmatched signal
    means the approval came from the agent, not the user (play3clone 2026-11-08: "1a", then
    `approve spec` + `approve plan` in the same turn). No `turn_start` → a host without the
    prompt hook: keep the old reminder rather than deadlock every approval.
    """
    targets = SIGNAL_TARGETS.get(target, (target,))
    row = _latest_signal(rows, targets)
    if row is not None and row.get("matched") is True and not row.get("mode_conflict"):
        return
    lines = [
        (f"The user's prompt this turn did not approve {target} (or the mode differs) "
         "— STOP, do not run this command."),
        f"How: present {target}, END the turn, wait for the user's own approval message.",
        echo_line("TDQ:APPROVE", "asked again and got a clear confirmation"),
    ]
    if any(r.get("kind") == "turn_start" for r in rows):
        _info(f"bash_gate: block TDQ:APPROVE · target={target} · "
              f"signal={'none' if row is None else 'unmatched'}")
        block(cwd, payload, "TDQ:APPROVE", lines, day_du=True)
    if row is not None:
        remind_force(cwd, payload, "TDQ:APPROVE", lines)


def _clean(raw):
    return raw.strip("'\"")


_PS_WRITE_PATTERN = re.compile(
    r"(?:Set-Content|Add-Content|Out-File|Copy-Item|Move-Item|Remove-Item|New-Item)\b|\[(?:System\.)?IO\.File\]::",
    re.IGNORECASE,
)


def _split_shell_segments(cmd, seps=(";", "&", "|", "\n")):
    """Split a shell command on separators only when outside single/double quotes."""
    cmd = _neutralize_comment_quotes(cmd)
    segments, buf = [], []
    in_single = in_double = escaped = False
    for ch in cmd:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == "\\" and not in_single:
            escaped = True
            buf.append(ch)
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double and ch in seps:
            seg = "".join(buf).strip()
            if seg:
                segments.append(seg)
            buf.clear()
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        segments.append(tail)
    return segments


def _mask_quoted_shell_ops(part):
    """Replace shell redirection/separator chars inside quotes so `>` in strings is not misread."""
    part = _neutralize_comment_quotes(part)
    out = []
    in_single = in_double = escaped = False
    for ch in part:
        if escaped:
            out.append("_" if (in_single or in_double) and ch in ";|&><\n" else ch)
            escaped = False
            continue
        if ch == "\\" and not in_single:
            escaped = True
            out.append(ch)
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif (in_single or in_double) and ch in ";|&><\n":
            out.append("_")
            continue
        out.append(ch)
    return "".join(out)


def _scan_paren_body(part, start_inner):
    depth, idx, n = 1, start_inner, len(part)
    in_s = in_d = esc = False
    while idx < n:
        ch = part[idx]
        if esc:
            esc = False
        elif ch == "\\" and not in_s:
            esc = True
        elif ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif not in_s and not in_d:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return part[start_inner:idx], idx + 1
        idx += 1
    return None, -1


def _extract_command_substitutions(part):
    part = _neutralize_comment_quotes(part)
    out, idx, n = [], 0, len(part)
    in_s = in_d = esc = False
    while idx < n:
        ch = part[idx]
        if esc:
            esc = False
        elif ch == "\\" and not in_s:
            esc = True
        elif not in_s and ch == "$" and part[idx:idx + 2] == "$(":
            body, end_idx = _scan_paren_body(part, idx + 2)
            if body is not None:
                out.append(body)
                idx = end_idx
                continue
        elif not in_s and ch == "`":
            end_bt = part.find("`", idx + 1)
            if end_bt != -1:
                out.append(part[idx + 1:end_bt])
                idx = end_bt + 1
                continue
        elif ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        idx += 1
    return out


def _decode_ps_encoded_command(raw):
    trimmed = raw.strip().strip("'\"")
    if not trimmed:
        return None
    try:
        raw_bytes = base64.b64decode(trimmed, validate=True)
    except ValueError:
        try:
            padded = trimmed + ("=" * (-len(trimmed) % 4))
            raw_bytes = base64.b64decode(padded, validate=True)
        except ValueError:
            return None
    if len(raw_bytes) < 2:
        return None
    even = raw_bytes[:len(raw_bytes) - (len(raw_bytes) % 2)]
    try:
        return even.decode("utf-16-le")
    except UnicodeDecodeError:
        return None


def _extract_brace_body(rest):
    depth = 0
    in_s = in_d = esc = False
    for idx, ch in enumerate(rest):
        if esc:
            esc = False
            continue
        if ch == "\\" and not in_s:
            esc = True
        elif ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif not in_s and not in_d:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth = max(0, depth - 1)
                if depth == 0:
                    return rest[1:idx]
    return None


def _extract_wrapper_body_arg(raw_rest):
    rest = raw_rest.lstrip()
    if not rest:
        return None
    quote = rest[0]
    if quote == "{":
        return _extract_brace_body(rest)
    if quote not in ("'", '"'):
        return rest
    buf, escaped = [], False
    for ch in rest[1:]:
        if escaped:
            buf.append(ch)
            escaped = False
        elif ch == "\\" and quote == '"':
            escaped = True
        elif ch == quote:
            return "".join(buf)
        else:
            buf.append(ch)
    return None


_SH_WRAP_RE = re.compile(r"(?:^|[\s;|&])(?:[^\s;|&\"'`]*[/\\])?(?:bash|sh|zsh|dash|ksh)\b[^\n;|&]*?\s-(?:[a-z]*c[a-z]*)\b\s*", re.IGNORECASE)
_CMD_WRAP_RE = re.compile(r"(?:^|[\s;|&])(?:[^\s;|&\"'`]*[/\\])?cmd(?:\.exe)?\b[^\n;|&]*?\s+/[ck]", re.IGNORECASE)
_PS_WRAP_RE = re.compile(r"(?:^|[\s;|&])(?:[^\s;|&\"'`]*[/\\])?(?:pwsh|powershell)(?:\.exe)?\b[^\n;|&]*?\s+-(?:c|co|com|comm|comma|comman|command)\b\s*", re.IGNORECASE)
_PS_ENC_RE = re.compile(r"(?:^|[\s;|&])(?:[^\s;|&\"'`]*[/\\])?(?:pwsh|powershell)(?:\.exe)?\b[^\n;|&]*?\s+-(?:e|en|enc|enco|encod|encode|encoded|encodedc|encodedco|encodedcom|encodedcomm|encodedcomma|encodedcomman|encodedcommand)\b\s*([^\s;|&]+)", re.IGNORECASE)


def _extract_shell_subcommands(part):
    """Extract command substitutions and nested shell wrapper payloads."""
    subs = _extract_command_substitutions(part)
    for pat in (_SH_WRAP_RE, _PS_WRAP_RE):
        for match in pat.finditer(part):
            arg = _extract_wrapper_body_arg(part[match.end():])
            if arg:
                subs.append(arg)
    for match in _CMD_WRAP_RE.finditer(part):
        rest = part[match.end():]
        if rest.startswith((" ", "\t", "'", '"')):
            arg = _extract_wrapper_body_arg(rest)
            if arg:
                subs.append(arg)
    for match in _PS_ENC_RE.finditer(part):
        dec = _decode_ps_encoded_command(match.group(1))
        if dec:
            subs.append(dec)
    return subs


def _part_stdout_targets(part, _depth=0):
    """Find non-null stdout redirect targets outside quotes, recursing into nested shells."""
    targets = [
        t for t in STDOUT_WRITE.findall(_mask_quoted_shell_ops(part))
        if not t.startswith(("&", "=")) and t.strip("'\"").lower() not in ("/dev/null", "$null", "nul")
    ]
    if _depth < 4:
        for sub in _extract_shell_subcommands(part):
            for sub_part in _split_shell_segments(sub):
                targets.extend(_part_stdout_targets(sub_part, _depth + 1))
    return targets


def _is_shell_write(cmd, _depth=0):
    if _depth > 4 or not cmd:
        return False
    if _PS_WRITE_PATTERN.search(cmd) or re.search(r"\b(?:tee|rm|mv)\b|\bsed\s+-i\b", cmd):
        return True
    for part in _split_shell_segments(cmd):
        if SHELL_MUTATOR.search(part) or _part_stdout_targets(part, _depth):
            return True
        if any(_is_shell_write(sub, _depth + 1) for sub in _extract_shell_subcommands(part)):
            return True
    return False


_GIT_VALUE_FLAGS = frozenset({
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env",
})
_PUSH_VALUE_FLAGS = frozenset({
    "--repo", "-o", "--push-option", "--receive-pack", "--exec", "--upload-pack",
})
_BRANCH_TAIL_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_INTAKE_BRANCH_KINDS = frozenset({"feature", "bugfix", "hotfix", "chore", "docs"})


_PS_HERESTRING_CTX_RE = re.compile(
    r"(?:^|[\s;|&(])(?:[^\s;|&\"']*[/\\])?(?:powershell|pwsh)(?:\.exe)?\b"
    r"|\$[A-Za-z_][A-Za-z0-9_]*"
    r"|\b(?:Set|Get|Add|Out|Write|Copy|Move|Remove|New|Clear|Invoke|Select)-[A-Za-z]+\b",
    re.IGNORECASE,
)


def _has_ps_herestring_context(cmd):
    return bool(_PS_HERESTRING_CTX_RE.search(cmd))


def _herestring_body_safe_for_strip(body, quote):
    if quote == '"':
        return '"' not in body and "$(" not in body and "`" not in body
    out_of_quote = False
    for ch in body:
        if ch == "'":
            out_of_quote = not out_of_quote
        elif out_of_quote and not (("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch in "_./:-"):
            return False
    return not out_of_quote


def _ps_herestring_end(cmd, body_start, quote):
    term = "\n" + quote + "@"
    idx = cmd.find(term, max(0, body_start - 1))
    while idx != -1:
        after = idx + len(term)
        if after == len(cmd) or cmd[after] in "\r\n \t;|&)":
            return after
        idx = cmd.find(term, idx + 1)
    return -1


_COMMENT_DELIMS = frozenset(" \t\r\n;|&({")
_HERESTRING_DELIMS = frozenset(" \t\r\n=(,;|&{+:")


def _try_neutralize_comment_step(cmd, i):
    if cmd.startswith("<#", i):
        end_idx = cmd.find("#>", i + 2)
        if end_idx != -1:
            inner = "".join(" " if c in "'\"@<>" else c for c in cmd[i + 2:end_idx])
            return f"  {inner}  ", end_idx + 2
    if cmd[i] == "#" and (i == 0 or cmd[i - 1] in _COMMENT_DELIMS):
        nl = cmd.find("\n", i)
        j = len(cmd) if nl == -1 else nl
        return "".join(" " if c in "'\"@" else c for c in cmd[i:j]), j
    return None, i


def _neutralize_comment_quotes(cmd):
    out, i, n = [], 0, len(cmd)
    in_s = in_d = esc = False
    while i < n:
        if not in_s and not in_d:
            rep, next_i = _try_neutralize_comment_step(cmd, i)
            if rep is not None:
                out.append(rep)
                i = next_i
                continue
        ch = cmd[i]
        if esc:
            esc = False
        elif ch == "\\" and not in_s and in_d:
            esc = True
        elif ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        out.append(ch)
        i += 1
    return "".join(out)


def _strip_powershell_herestrings(cmd):
    """Strip static PS here-strings in PS context and neutralize unquoted comment quotes everywhere."""
    ps_ctx = _has_ps_herestring_context(cmd)
    out, i, n = [], 0, len(cmd)
    in_s = in_d = esc = False
    while i < n:
        if not in_s and not in_d:
            rep, next_i = _try_neutralize_comment_step(cmd, i)
            if rep is not None:
                out.append(rep)
                i = next_i
                continue
            if ps_ctx and (i == 0 or cmd[i - 1] in _HERESTRING_DELIMS) and cmd[i:i + 2] in ("@'", '@"'):
                q = cmd[i + 1]
                step = 3 if cmd[i + 2:i + 3] == "\n" else (4 if cmd[i + 2:i + 4] == "\r\n" else 0)
                if step:
                    after = _ps_herestring_end(cmd, i + step, q)
                    if after != -1 and _herestring_body_safe_for_strip(cmd[i + step:max(i + step, after - 3)], q):
                        out.append(" ")
                        i = after
                        continue
        ch = cmd[i]
        if esc:
            esc = False
        elif ch == "\\" and not in_s and in_d:
            esc = True
        elif ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        out.append(ch)
        i += 1
    return "".join(out)


def _tokenize_command(cmd):
    """Tokenize shell command honoring quotes and preserving empty quoted tokens."""
    cmd = _neutralize_comment_quotes(cmd)
    tokens, current = [], []
    in_single = in_double = had_token = False
    i, n = 0, len(cmd)
    while i < n:
        ch = cmd[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            had_token = True
        elif ch == '"' and not in_single:
            in_double = not in_double
            had_token = True
        elif ch == "\\" and in_double and i + 1 < n and cmd[i + 1] in ('"', "\\"):
            i += 1
            current.append(cmd[i])
            had_token = True
        elif ch.isspace() and not in_single and not in_double:
            if had_token or current:
                tokens.append("".join(current))
                current = []
                had_token = False
        else:
            current.append(ch)
            had_token = True
        i += 1
    if had_token or current:
        tokens.append("".join(current))
    return tokens


def _is_env_assignment(tok):
    if "=" not in tok:
        return False
    lhs, _ = tok.split("=", 1)
    return bool(lhs) and not lhs.startswith("-") and all(
        c.isascii() and (c.isalnum() or c in "_:") for c in lhs
    )


def _cmd_basename_no_exe(tok):
    base = tok.replace("\\", "/").rsplit("/", 1)[-1].strip().lower()
    return base.removesuffix(".exe")


def _skip_command_wrappers(tokens):
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if _is_env_assignment(tok):
            i += 1
            continue
        base = _cmd_basename_no_exe(tok)
        if base == "env":
            i += 1
            while i < len(tokens):
                t = tokens[i]
                if _is_env_assignment(t) or t in ("-i", "--ignore-environment", "-0", "--null"):
                    i += 1
                elif t in ("-u", "--unset", "-C", "--chdir", "-S", "--split-string"):
                    i = min(i + 2, len(tokens))
                elif t.startswith(("--unset=", "--chdir=", "--split-string=")):
                    i += 1
                else:
                    break
        elif base in ("command", "time", "nohup", "exec"):
            i += 1
        elif base == "rtk":
            i += 1
            if i < len(tokens) and tokens[i].lower() == "bypass":
                i += 1
        else:
            break
    return tokens[i:]


def _parse_git_subcommand(args):
    i = 0
    while i < len(args):
        tok = args[i]
        if not tok.startswith("-") or tok == "--":
            break
        i += 2 if tok in _GIT_VALUE_FLAGS else 1
    if i >= len(args) or args[i].startswith("-"):
        return None, []
    return args[i], args[i + 1:]


def _has_ai_trailer(args):
    return any(
        "co-authored-by:" in arg.lower() or any(p.search(arg) for p in BAD_MSG)
        for arg in args
    )


def _is_force_push_args(args):
    after_dd = skip_val = False
    for arg in args:
        if skip_val:
            skip_val = False
            continue
        if arg == "--":
            after_dd = True
            continue
        if not after_dd and arg in _PUSH_VALUE_FLAGS:
            skip_val = True
            continue
        low = arg.lower()
        flag_force = not after_dd and (
            low in ("-f", "--force", "--force-with-lease", "--force-if-includes")
            or low.startswith("--force-with-lease=")
            or (low.startswith("-") and not low.startswith("--") and "f" in low[1:])
        )
        if flag_force or (not low.startswith("-") and low.startswith("+")):
            return True
    return False


def _classify_git_tokens(args):
    subcmd, rest = _parse_git_subcommand(args)
    if not subcmd:
        return None
    if _has_ai_trailer(rest):
        return "co_authored_trailer"
    sub = subcmd.lower()
    if sub == "push":
        return "force_push_forbidden" if _is_force_push_args(rest) else "push_needs_approval"
    before_dd = []
    for a in rest:
        if a == "--":
            break
        before_dd.append(a)
    if sub == "reset" and "--hard" in before_dd:
        return "reset_hard_needs_approval"
    if sub == "clean" and any(
        a == "--force" or (a.startswith("-") and not a.startswith("--") and "f" in a[1:])
        for a in before_dd
    ):
        return "clean_force_needs_approval"
    return None


def _collect_git_violations_depth(part, depth, out):
    toks = _tokenize_command(part)
    cmd_toks = _skip_command_wrappers(toks)
    if cmd_toks and _cmd_basename_no_exe(cmd_toks[0]) == "git":
        v = _classify_git_tokens(cmd_toks[1:])
        if v and v not in out:
            out.append(v)
    if depth < 4:
        for sub in _extract_shell_subcommands(part):
            for seg in _split_shell_segments(sub):
                _collect_git_violations_depth(seg, depth + 1, out)


def collect_git_policy_violations(raw_cmd):
    """Collect git policy violations across shell segments and nested shells."""
    cleaned = _strip_powershell_herestrings(raw_cmd)
    out = []
    for seg in _split_shell_segments(cleaned):
        _collect_git_violations_depth(seg, 0, out)
    return out


def inspect_git_command_safety(raw_cmd):
    """Return the highest-priority git policy violation string, or None."""
    violations = collect_git_policy_violations(raw_cmd)
    for hard in ("co_authored_trailer", "force_push_forbidden"):
        if hard in violations:
            return hard
    return violations[0] if violations else None


def is_pure_intake_branch_create(raw_cmd):
    """True only for single-segment Step-3b branch creation under allowed kinds."""
    cleaned = _strip_powershell_herestrings(raw_cmd)
    segments = _split_shell_segments(cleaned)
    if len(segments) != 1:
        return False
    seg = segments[0]
    if _extract_shell_subcommands(seg) or _part_stdout_targets(seg, 0):
        return False
    toks = _tokenize_command(seg)
    if len(toks) != 4 or _cmd_basename_no_exe(toks[0]) != "git":
        return False
    sub, flag, branch = toks[1].lower(), toks[2], toks[3]
    ok_verb = (sub == "switch" and flag in ("-c", "--create")) or (
        sub == "checkout" and flag == "-b"
    )
    if not ok_verb or BAN.match(branch) or "/" not in branch:
        return False
    kind, tail = branch.split("/", 1)
    return kind in _INTAKE_BRANCH_KINDS and bool(_BRANCH_TAIL_RE.match(tail))


def _collapse_path_token(tok):
    if "/" not in tok and "\\" not in tok:
        return tok
    norm = tok.replace("\\", "/")
    stack = []
    for seg in norm.split("/"):
        if not seg or seg == ".":
            continue
        if seg == "..":
            if stack and stack[-1] != "..":
                stack.pop()
            else:
                stack.append("..")
        else:
            stack.append(seg)
    return ("/" if norm.startswith("/") else "") + "/".join(stack)


def _collapse_cmd_paths(raw):
    seps = set(" \t\r\n'\";&|><(){},=")
    out, cur = [], []
    for ch in raw:
        if ch in seps:
            if cur:
                out.append(_collapse_path_token("".join(cur)))
                cur = []
            out.append(ch)
        else:
            cur.append(ch)
    if cur:
        out.append(_collapse_path_token("".join(cur)))
    return "".join(out)


def _is_state_or_runtime_text(low, seen_cd_tdq, seen_cd_runtime):
    return (
        seen_cd_runtime
        or "docs/tdq/state.json" in low
        or "docs/tdq/state.md" in low
        or ".tdq-runtime" in low
        or (
            seen_cd_tdq
            and any(k in low for k in (
                "state.json", "state.md", "turn-meta-",
                "sessions.json", "turns-", "checkpoint-",
            ))
        )
    )


_NON_STATE_WRITER_CMDS = frozenset({
    "git", "pytest", "cargo", "rg", "grep", "egrep", "fgrep", "findstr",
    "jq", "cat", "head", "tail", "type", "get-content", "gc",
})
_STATE_POS_PS_RE = re.compile(
    r"(?is)(?:\b(?:tee|mv|cp|truncate|rm|del|erase|rmdir|rd|copy|move|dd|install|ln|mklink|"
    r"set-content|add-content|out-file|copy-item|move-item|remove-item|new-item|set-item|clear-content|"
    r"sc|ac|cpi|mi|ri|ni|si|clc)\b|\bsed\b[^;|&]*\s-i\b|\[(?:system\.)?io\.file\]::)"
)
_STATE_PY_NODE_RE = re.compile(
    r"(?is)(?:\bopen\([^)]*['\"](?:w|a|x|r\+|w\+)|write_text\b|write_bytes\b|\.unlink\b|\.rmdir\b|"
    r"\bos\.(?:remove|unlink|replace|rename)\b|\bshutil\.(?:copy|copy2|copyfile|move|rmtree)\b|"
    r"\bjson\.dump\b|writefile|writefilesync|appendfile|rmsync|unlinksync|createwritestream)"
)


def _mutates_tdq_state_depth(raw_cmd, depth, seen_cd_tdq, seen_cd_runtime=False):
    for raw_seg in _split_shell_segments(raw_cmd):
        col = _collapse_cmd_paths(raw_seg)
        low = col.lower()
        cmd_toks = _skip_command_wrappers(_tokenize_command(col))
        base = _cmd_basename_no_exe(cmd_toks[0]) if cmd_toks else ""
        if base in ("cd", "chdir", "set-location", "sl", "pushd"):
            if ".tdq-runtime" in low:
                seen_cd_tdq = True
                seen_cd_runtime = True
            elif "docs/tdq" in low:
                seen_cd_tdq = True
        redir_hit = any(
            _is_state_or_runtime_text(_collapse_path_token(t).lower(), seen_cd_tdq, seen_cd_runtime)
            for t in _part_stdout_targets(col, 0)
        )
        op_hit = base not in _NON_STATE_WRITER_CMDS and bool(
            _STATE_POS_PS_RE.search(low) or _STATE_PY_NODE_RE.search(low)
        )
        if redir_hit or (_is_state_or_runtime_text(low, seen_cd_tdq, seen_cd_runtime) and op_hit):
            return True
        if depth < 4 and any(_mutates_tdq_state_depth(sub, depth + 1, seen_cd_tdq, seen_cd_runtime) for sub in _extract_shell_subcommands(raw_seg)):
            return True
    return False


def mutates_tdq_state(raw_cmd):
    """Detect direct or wrapped shell writes to docs/tdq/state.json, STATE.md, or .tdq-runtime/."""
    return _mutates_tdq_state_depth(_strip_powershell_herestrings(raw_cmd), 0, False, False)


def _branch_candidates_from_git(args):
    subcmd, rest = _parse_git_subcommand(args)
    if not subcmd:
        return []
    sub, out, i = subcmd.lower(), [], 0
    if sub in ("checkout", "switch"):
        flags = ("-b", "-B", "-c", "-C", "--create", "--force-create", "--orphan")
        while i < len(rest):
            if rest[i] in flags and i + 1 < len(rest):
                out.append(rest[i + 1])
                i += 2
            else:
                i += 1
    elif sub == "branch":
        pos = next((a for a in rest if not a.startswith("-")), None)
        if pos:
            out.append(pos)
    elif sub == "worktree" and rest and rest[0].lower() == "add":
        i = 1
        while i < len(rest):
            if rest[i] in ("-b", "-B") and i + 1 < len(rest):
                out.append(rest[i + 1])
                i += 2
            else:
                if not rest[i].startswith("-"):
                    out.append(rest[i].replace("\\", "/").rstrip("/").rsplit("/", 1)[-1])
                i += 1
    return out


def _collect_banned_branch_depth(cmd, depth):
    for seg in _split_shell_segments(cmd):
        cmd_toks = _skip_command_wrappers(_tokenize_command(seg))
        if cmd_toks and _cmd_basename_no_exe(cmd_toks[0]) == "git":
            for cand in _branch_candidates_from_git(cmd_toks[1:]):
                if BAN.match(cand):
                    return cand
        if depth < 4:
            for sub in _extract_shell_subcommands(seg):
                hit = _collect_banned_branch_depth(sub, depth + 1)
                if hit:
                    return hit
    return None


def has_banned_ai_branch(raw_cmd):
    """Return banned AI-prefixed branch or worktree basename if present."""
    return _collect_banned_branch_depth(_strip_powershell_herestrings(raw_cmd), 0)


def _enforce_agy_bash_guards(payload, cwd):
    info = detect_subagent(payload, cwd)
    agy = is_agy()
    if not agy and not info.get("is_subagent"):
        return False
    cmd = str((payload.get("tool_input") or {}).get("command") or "")
    role = (info.get("role") or "").lower()
    if any(r in role for r in ("reviewer", "qc-tester", "browser", "explorer", "debugger")) and _is_shell_write(cmd):
        block(cwd, payload, "READONLY", [f"Read-only subagent `{role}` cannot mutate files via shell."])
        return True
    norm_cmd = cmd.replace("\\", "/")
    if agy and _PS_WRITE_PATTERN.search(cmd) and ("docs/tdq/state.json" in norm_cmd or "docs/tdq/STATE.md" in norm_cmd):
        block(cwd, payload, "GATE", ["Do not mutate TDQ state via PowerShell; use tdq_state.py CLI."])
        return True
    if agy and mutates_tdq_state(cmd):
        block(cwd, payload, "STATE", ["Direct mutation of TDQ state or docs/tdq/.tdq-runtime/ is prohibited."])
        return True
    if agy and has_banned_ai_branch(cmd):
        block(cwd, payload, "TDQ:GIT", ["AI-prefixed branch names are banned; name the branch after the work."])
        return True
    if agy and re.search(r"git\s+(?:checkout\s+-[bB]|switch\s+-[cC]|branch)\s+['\"]?(?:claude|antigravity|gemini|codex)[-_]", cmd, re.IGNORECASE):
        block(cwd, payload, "TDQ:GIT", ["AI-prefixed branch names are banned; name the branch after the work."])
        return True
    return False


def _check_git_conventions(cmd, cwd, payload, rows):
    """Warn on banned branch/worktree prefixes or AI traces in git commit messages."""
    branch_names = []
    for pattern in BRANCH_PATTERNS:
        branch_names += [_clean(m) for m in pattern.findall(cmd)]
    for b_name, path in WORKTREE.findall(cmd):
        if b_name:
            branch_names.append(_clean(b_name))
        if path:
            branch_names.append(os.path.basename(_clean(path).rstrip("/")))
    extra_br = has_banned_ai_branch(cmd)
    if extra_br and extra_br not in branch_names:
        branch_names.append(extra_br)
    for name in branch_names:
        if BAN.match(name):
            remind(cwd, payload, "TDQ:GIT", [
                f"The branch/worktree name '{name}' breaks the convention — rename it first.",
                "How: drop the claude|antigravity|gemini|codex prefix, name it after the work.",
                echo_line("TDQ:GIT", "renamed it to match the convention"),
            ], rows=rows)

    if re.search(r"git\b.*\bcommit\b", cmd, re.DOTALL):
        for pattern in BAD_MSG:
            if pattern.search(cmd):
                remind(cwd, payload, "TDQ:GIT", [
                    "The commit message carries AI traces — that breaks the convention.",
                    "How: drop 'generated with …', 'được tạo cùng/với AI' and any AI Co-Authored-By.",  # i18n-allow
                    echo_line("TDQ:GIT", "fixed the commit message"),
                ], rows=rows)


def _check_bash_reminders(cmd, cwd, payload, rows, state, suppress_output_remind=False):
    """Run approve/setphase, branch/commit conventions, dump, and state-write checks."""
    approve_match = APPROVE_CLI.search(cmd)
    if approve_match:
        _check_signal_mismatch(cwd, payload, approve_match.group(1), rows)
    setphase_match = SETPHASE_CLI.search(cmd)
    if setphase_match:
        target = NEXT_PHASE_TARGET.get(setphase_match.group(1))
        # A gate already approved needs no fresh consent: QC fix round returns with `set phase=implement`.
        if target and not state.get(f"{target}_approved"):
            _check_signal_mismatch(cwd, payload, target, rows)

    _check_git_conventions(cmd, cwd, payload, rows)

    if not suppress_output_remind and DUMP.search(cmd) and not GIOI_HAN.search(cmd) and not CAT_GHI.search(cmd):
        remind(cwd, payload, "TDQ:OUTPUT", [
            ("This command dumps its whole content into context — every output is re-read on "
             "every API call after it."),
            ("How: limit it inside the command (`head`/`tail`/`sed -n`/`-n`/`--stat`/"
             "`--oneline`), or use Read with `offset`/`limit`. Genuinely need the whole file? "
             "Then run it — quality outranks context cost."),
            echo_line("TDQ:OUTPUT", "limited the output, or confirmed the whole is needed"),
        ], rows=rows)

    if mutates_tdq_state(cmd):
        remind(cwd, payload, "TDQ:STATE", [
            "Do not write the state file straight through the shell.",
            "How: python3 scripts/tdq_state.py set|approve|init|reset.",
            echo_line("TDQ:STATE", "wrote state through the CLI"),
        ], rows=rows)


def _is_p0_unlock_cmd(cmd):
    """Return True only when standalone shell segments run a P0 unlock CLI."""
    if not cmd or any(tok in cmd for tok in ("|", "`", "$(", "\n")):
        return False
    segments = [seg.strip() for seg in re.split(r"(?:&&|;)", cmd) if seg.strip()]
    if not segments:
        return False
    has_unlock = False
    for seg in segments:
        lower = seg.lower()
        if lower.startswith("cd ") or lower.startswith("cd\t"):
            continue
        is_reset_breaker = "tdq_state" in lower and "reset-breaker" in lower
        is_mcp_approve = "mcp_policy" in lower and ("approve" in lower or "reset" in lower)
        if not (is_reset_breaker or is_mcp_approve):
            return False
        has_unlock = True
    return has_unlock


def _kiem_p0_bash_guard(cwd, payload, cmd, state):
    """Block shell commands when P0 circuit breaker is open or budget hard-stopped."""
    if _is_p0_unlock_cmd(cmd):
        return False
    p0_rt = (state or {}).get("p0_runtime") or {}
    breaker = p0_rt.get("breaker") or {}
    cfg = __import__("tdq_config").load_config(cwd)
    if (cfg.get("p0") or {}).get("breaker_enabled", True) and breaker.get("open"):
        reason = str(breaker.get("reason") or "circuit breaker is open")
        __import__("_common").block(
            cwd,
            payload,
            "TDQ:READONLY",
            [
                f"P0 Circuit Breaker open ({reason}) — shell commands blocked.",
                "How: py -3 scripts/tdq_state.py reset-breaker",
            ],
            day_du=True,
        )
        return True
    budget = p0_rt.get("budget") or {}
    hard_stopped = bool(budget.get("hard_stopped"))
    if not hard_stopped:
        status = __import__("tdq_timing").check_budget_status(cwd, config=cfg)
        hard_stopped = status.get("state") == "hard_stop"
    if hard_stopped:
        __import__("_common").block(
            cwd,
            payload,
            "TDQ:READONLY",
            [
                "P0 Budget hard stop reached — shell commands blocked.",
                "How: adjust budget caps or reset state before continuing.",
            ],
            day_du=True,
        )
        return True
    return False


def eval_bash(payload, suppress_output_remind=False):
    """Evaluate bash gate rules for an already-read payload; return True to allow continuing."""
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not isinstance(cmd, str) or not cmd:
        return True
    cwd = payload_cwd(payload)
    if _enforce_agy_bash_guards(payload, cwd):
        return False
    rows = turn_rows(cwd, payload)  # P0-3: read once, reused by every check below
    state = __import__("tdq_state").load(cwd) or {}
    if _kiem_p0_bash_guard(cwd, payload, cmd, state):
        return False
    parts = _split_shell_segments(cmd, seps=(";", "&"))
    mutates_outside_docs = any(
        (SHELL_MUTATOR.search(part) and (not DOCS_ARTIFACT.search(part) or ".." in part))
        or any(
            not DOCS_ARTIFACT.search(_collapse_path_token(target)) or ".." in _collapse_path_token(target)
            for target in _part_stdout_targets(part)
        )
        for part in parts)
    if (payload.get("agent_id") or payload.get("agentId")) and state.get("active_request") \
            and state.get("phase") not in ("implement", "qc") and mutates_outside_docs:
        block(cwd, payload, "TDQ:TEAM", [
            "A sub-agent may not mutate the project through Bash/PowerShell before implement.",
            "Return structured output, or write only the assigned report under docs/tdq/artifacts/.",
            "The TDQ leader remains the state and source writer.",
        ])
        return False

    # (1) observe
    for sub in STATE_CLI.findall(cmd):
        observe(cwd, payload, "state_cli", cmd=sub)
        if sub == "next":
            observe(cwd, payload, "next_run")

    # (2) remind — the phase-advance guard (approve/set phase=) outranks GIT/STATE
    _check_bash_reminders(cmd, cwd, payload, rows, state,
                          suppress_output_remind=suppress_output_remind)
    return True


def main():
    eval_bash(read_payload())


if __name__ == "__main__":
    main()
