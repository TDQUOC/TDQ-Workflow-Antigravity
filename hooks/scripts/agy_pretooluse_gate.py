#!/usr/bin/env python3
"""PreToolUse (Antigravity/agy) — hard deny on 2 fixed, pre-existing rules.

Unlike Claude Code's PreToolUse (`hooks/scripts/bash_gate.py`), which reminds normally but denies pre-implement sub-agent mutation,
agy's PreToolUse deny is a genuine hard block (see
docs/tdq/brief/2026-09-03-1440-kiem-tuong-thich-3-host.md, sources N5–N6). This hook
enforces exactly 2 cases that are already-locked project rules, not "not yet approved"
gates (locked decision docs/kien-truc.md § Đã chốt 2026-07-29 forbids a `deny` used to gate
on approval state — the 2 cases below are unconditional naming/write rules instead):

  (a) a branch/worktree name starting with claude|antigravity|gemini|codex
      — ported from BAN/BRANCH_PATTERNS/WORKTREE in `hooks/scripts/bash_gate.py`.
  (b) writing docs/tdq/state.json or STATE.md straight through the shell — ported from
      STATE_WRITES in the same file, tightened here: a `python3`/`open(...)` command is only
      counted as a WRITE when it names an actual write mode ("w"/"a"/"x"); a read
      (`cat`, `head`/`tail`, `sed -n`, or `open()` with no mode / mode "r") is never denied.

Google publishes no official PreToolUse INPUT schema (checked 2026-09-03; the field list in
source N5 is third-party), so `_first_command` tries several plausible field paths for the
shell command text, and this hook never raises: an unparsable payload, or a command it cannot
find, is silently allowed. Silence on allow is deliberate — a malformed or bare `{}` reply
makes agy deny EVERY tool call with `invalid_args` (source N6). The output side emits both
documented deny spellings; see `_deny`.
"""
import base64
import datetime
import json
import os
import re
import sys

# `utf8_io` lives in scripts/, which is not on sys.path when a hook is spawned directly.
sys.path.insert(0, os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")))
import utf8_io  # noqa: E402,F401 — imported for its side effect: stdout/stderr become UTF-8

BAN = re.compile(r"^(claude|antigravity|gemini|codex)", re.IGNORECASE)
BRANCH_PATTERNS = [
    re.compile(r"git\s+checkout\s+-b\s+(\S+)"),
    re.compile(r"git\s+switch\s+(?:-c|--create)\s+(\S+)"),
    re.compile(r"git\s+branch\s+(?!-)(\S+)"),
]
WORKTREE = re.compile(r"git\s+worktree\s+add\s+(?:-b\s+(\S+)\s+)?(\S+)")

STATE = r"docs/tdq/(?:state\.json|STATE\.md|\.tdq-runtime(?:/[^\s'\";&|<>()]*)?)"
STATE_WRITES = [
    re.compile(r">{1,2}\s*['\"]?\S*" + STATE),
    re.compile(r"\btee\b[^|;&]*" + STATE),
    re.compile(r"\bsed\b[^;|&]*\s-i[^;|&]*" + STATE),
    re.compile(r"\b(?:mv|cp)\b[^;|&]*" + STATE),
    re.compile(r"\btruncate\b[^;|&]*" + STATE),
    # `open(...)` only counts as a write when a write-capable mode is named in the same call —
    # a bare `open(path)` or an explicit mode "r" is a read and must never be denied.
    re.compile(r"\bopen\([^)]*" + STATE + r"[^)]*['\"](?:w|a|x)[a-z+]*['\"]"),
    re.compile(r"\b(?:Set-Content|Add-Content|Out-File|Copy-Item|Move-Item)\b[^;|&]*" + STATE, re.IGNORECASE),
]

# The command field, tried across several plausible agy PreToolUse payload shapes.
_CMD_PATHS = (
    ("toolCall", "args", "CommandLine"),
    ("toolCall", "args", "command"),
    ("tool_input", "command"),
    ("tool_input", "CommandLine"),
    ("toolInput", "command"),
    ("toolInput", "CommandLine"),
    ("input", "command"),
    ("arguments", "command"),
    ("arguments", "CommandLine"),
    ("command",),
    ("CommandLine",),
)


def _first_command(payload):
    """The shell command text off the payload, or "" when no known shape carries one."""
    if not isinstance(payload, dict):
        return ""
    for path in _CMD_PATHS:
        node = payload
        for key in path:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        if isinstance(node, str) and node.strip():
            return node
    return ""


def _clean(raw):
    return raw.strip("'\"")


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


def _extract_agy_cmd_subs(part):
    out, i, n = [], 0, len(part)
    in_s = in_d = esc = False
    while i < n:
        ch = part[i]
        if esc:
            esc = False
        elif ch == "\\" and not in_s:
            esc = True
        elif not in_s and ch == "$" and part[i:i + 2] == "$(":
            depth, j, ins, ind, es2 = 1, i + 2, False, False, False
            while j < n and depth > 0:
                c2 = part[j]
                if es2:
                    es2 = False
                elif c2 == "\\" and not ins:
                    es2 = True
                elif c2 == "'" and not ind:
                    ins = not ins
                elif c2 == '"' and not ins:
                    ind = not ind
                elif not ins and not ind:
                    depth += 1 if c2 == "(" else (-1 if c2 == ")" else 0)
                j += 1
            if depth == 0:
                out.append(part[i + 2:j - 1])
                i = j
                continue
        elif not in_s and ch == "`":
            end = part.find("`", i + 1)
            if end != -1:
                out.append(part[i + 1:end])
                i = end + 1
                continue
        elif ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        i += 1
    return out


_AGY_SH_WRAP = re.compile(r"(?:^|[\s;|&])(?:[^\s;|&\"'`]*[/\\])?(?:bash|sh|zsh|dash|ksh)\b[^\n;|&]*?\s-(?:[a-z]*c[a-z]*)\b\s*", re.IGNORECASE)
_AGY_CMD_WRAP = re.compile(r"(?:^|[\s;|&])(?:[^\s;|&\"'`]*[/\\])?cmd(?:\.exe)?\b[^\n;|&]*?\s+/[ck]", re.IGNORECASE)
_AGY_PS_WRAP = re.compile(r"(?:^|[\s;|&])(?:[^\s;|&\"'`]*[/\\])?(?:pwsh|powershell)(?:\.exe)?\b[^\n;|&]*?\s+-(?:c|co|com|comm|comma|comman|command)\b\s*", re.IGNORECASE)
_AGY_ENC_WRAP = re.compile(r"(?:^|[\s;|&])(?:[^\s;|&\"'`]*[/\\])?(?:pwsh|powershell)(?:\.exe)?\b[^\n;|&]*?\s+-(?:e|en|enc|enco|encod|encode|encoded|encodedc|encodedco|encodedcom|encodedcomm|encodedcomma|encodedcomman|encodedcommand)\b\s*([^\s;|&]+)", re.IGNORECASE)
_AGY_NON_WRITERS = frozenset({"git", "pytest", "cargo", "rg", "grep", "egrep", "fgrep", "findstr", "jq", "cat", "head", "tail", "type", "get-content", "gc"})
_AGY_WRITE_OP_RE = re.compile(
    r"(?:>{1,2}\s*\S+|\b(?:tee|mv|cp|truncate|rm|del|erase|rmdir|rd|copy|move|dd|install|ln|mklink|Set-Content|Add-Content|Out-File|Copy-Item|Move-Item|Remove-Item|New-Item|Set-Item|Clear-Content|sc|ac|cpi|mi|ri|ni|si|clc)\b|"
    r"\bsed\b[^;|&]*\s-i\b|\[(?:System\.)?IO\.File\]::|\bopen\([^)]*['\"](?:w|a|x|r\+|w\+)|"
    r"\b(?:write_text|write_bytes|os\.(?:remove|unlink|replace|rename)|shutil\.(?:copy|copy2|copyfile|move|rmtree)|json\.dump)\b|"
    r"\.(?:unlink|rmdir)\b|writeFile|writeFileSync|appendFile|rmSync|unlinkSync|createWriteStream)",
    re.IGNORECASE,
)


def _split_agy_segments(cmd):
    segs, buf = [], []
    in_s = in_d = esc = False
    for ch in cmd:
        if esc:
            buf.append(ch)
            esc = False
            continue
        if ch == "\\" and not in_s:
            esc = True
            buf.append(ch)
            continue
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif not in_s and not in_d and ch in ";\n&|":
            s = "".join(buf).strip()
            if s:
                segs.append(s)
            buf.clear()
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        segs.append(tail)
    return segs


def _agy_extract_subs(part):
    subs = _extract_agy_cmd_subs(part)
    for pat in (_AGY_SH_WRAP, _AGY_PS_WRAP, _AGY_CMD_WRAP):
        for m in pat.finditer(part):
            rest = part[m.end():]
            if pat is _AGY_CMD_WRAP and not rest.startswith((" ", "\t", "'", '"')):
                continue
            r = rest.lstrip()
            if not r:
                continue
            if r[0] in ("'", '"'):
                q, buf, esc = r[0], [], False
                for c in r[1:]:
                    if esc:
                        buf.append(c)
                        esc = False
                    elif c == "\\" and q == '"':
                        esc = True
                    elif c == q:
                        subs.append("".join(buf))
                        break
                    else:
                        buf.append(c)
            elif r[0] == "{":
                end = r.rfind("}")
                if end > 0:
                    subs.append(r[1:end])
            else:
                subs.append(r)
    for m in _AGY_ENC_WRAP.finditer(part):
        try:
            subs.append(base64.b64decode(m.group(1).strip("'\"")).decode("utf-16-le"))
        except (ValueError, UnicodeDecodeError):
            pass
    return subs


def _branch_names(cmd, _depth=0):
    names = []
    norm = re.sub(r"\bgit\b(?:\s+-(?:C|c|git-dir|work-tree)\s+(?:\"[^\"]*\"|'[^']*'|\S+))+", "git", cmd)
    for target in (cmd, norm):
        for pattern in BRANCH_PATTERNS:
            names += [_clean(m) for m in pattern.findall(target)]
        for b_name, path in WORKTREE.findall(target):
            if b_name:
                names.append(_clean(b_name))
            if path:
                names.append(_clean(path).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1])
    if _depth < 4:
        for sub in _agy_extract_subs(cmd):
            names += _branch_names(sub, _depth + 1)
    return names


def _writes_state_depth(cmd, depth, seen_cd):
    for seg in _split_agy_segments(cmd):
        col = _collapse_cmd_paths(seg)
        low = col.lower()
        first = low.split(None, 1)[0].rsplit("/", 1)[-1].removesuffix(".exe") if low else ""
        if first in ("cd", "chdir", "set-location", "sl", "pushd") and ("docs/tdq" in low or ".tdq-runtime" in low):
            seen_cd = True
        has_tgt = ("docs/tdq/state.json" in low or "docs/tdq/state.md" in low or ".tdq-runtime" in low
                   or (seen_cd and any(k in low for k in ("state.json", "state.md", "turn-meta-"))))
        has_redir = bool(re.search(r"(?<![0-9=<>-])>{1,2}\s*\S*(?:docs/tdq/(?:state\.json|state\.md)|\.tdq-runtime|turn-meta-|state\.json|state\.md)", col, re.IGNORECASE))
        if has_tgt and (has_redir or (first not in _AGY_NON_WRITERS and _AGY_WRITE_OP_RE.search(col))):
            return True
        if depth < 4 and any(_writes_state_depth(sub, depth + 1, seen_cd) for sub in _agy_extract_subs(seg)):
            return True
    return False


def _writes_state(cmd):
    return _writes_state_depth(cmd, 0, False)


def _log(msg):
    """One timestamped stderr line naming the matched case. Off with TDQ_LOG=0.

    Deliberately self-contained rather than importing `scripts/tdq_state.py` like
    `agy_stop_gate.py` does: this hook runs on EVERY tool call, so the hot path stays a
    stdlib-only import. Same shape as `tdq_state._info`.
    """
    if os.environ.get("TDQ_LOG", "1") == "0":
        return
    dau_thoi_gian = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"[{dau_thoi_gian}] ℹ️ {msg}", file=sys.stderr)


def _deny(reason):
    """Emit BOTH deny spellings in one payload.

    `allow_tool: false` is the contract documented for agy agent hooks (third-party guide,
    read 2026-09-03); `decision: "deny"` is the Claude-Code-style key this hook was first
    written against. Google publishes no official schema, so neither can be dropped on
    evidence — and an unknown extra key is inert, whereas guessing wrong means the deny is
    silently ignored. `reason`/`message` are duplicated for the same reason.
    """
    _log(f"agy PreToolUse deny — {reason}")
    print(json.dumps({
        "allow_tool": False,
        "decision": "deny",
        "reason": reason,
        "message": reason,
    }, ensure_ascii=False))


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, UnicodeDecodeError):
        return
    cmd = _first_command(payload)
    if not cmd:
        return

    banned = [name for name in _branch_names(cmd) if BAN.match(name)]
    if banned:
        _deny(f"[TDQ:GIT] branch/worktree name '{banned[0]}' breaks the fixed naming rule — "
              "drop the claude|antigravity|gemini|codex prefix, name it after the work.")
        return

    if _writes_state(cmd):
        _deny("[TDQ:STATE] writing docs/tdq/state.json or STATE.md straight through the shell "
              "is not allowed — use python3 scripts/tdq_state.py set|approve|init|reset.")
        return


if __name__ == "__main__":
    main()
