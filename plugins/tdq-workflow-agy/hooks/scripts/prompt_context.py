#!/usr/bin/env python3
"""UserPromptSubmit — open a new turn.

Three jobs:
1. Wipe this session's turn ledger (the compliance-matching scope is one turn).
2. Emit TDQ:APPROVE when something waits for approval AND the prompt matches an approval
   sign (spec §2.9.2). Ambiguous → do not emit, and tell the agent to ASK rather than guess.
3. Emit TDQ:NEXT — exactly 1 line of `next --brief`.
4. Emit TDQ:WORKTREE while the worktree ledger still holds an open row.

Budget ceiling: ≤3 lines / 240 chars (spec §2.7). Silent when idle.
"""
import os as _tdq_os, sys as _tdq_sys
_tdq_here = _tdq_os.path.dirname(_tdq_os.path.abspath(__file__))
_tdq_scripts = _tdq_os.path.normpath(_tdq_os.path.join(_tdq_here, '..', '..', 'scripts'))
for _p in (_tdq_scripts, _tdq_here):
    if _tdq_os.path.isdir(_p) and _p not in _tdq_sys.path:
        _tdq_sys.path.insert(0, _p)
import utf8_io  # noqa: E402,F401
import hashlib
import json
import os
import re
import sys

from _common import (INVESTIGATE_GON_TEXT, _RUNTIME_STATE, _shard_turn_path,
                     already_reminded, approve_hint, detect_subagent, emit_context,
                     emit_user_markdown, flush_pending_channels, is_agy,
                     payload_cwd, plan_mode, read_payload, read_turn_meta,
                     session_id, write_turn_meta)
# Keep this AFTER `from _common`: `_common` is what injects `scripts/` into sys.path. Use a
# from-import (not module attribute access) so graphify can emit the cross-file `calls` edge.
from tdq_state import (MODE_ALIASES, _info, effective_lane,  # noqa: E402
                       effective_mode, effective_phase, lenh_cho_project, liet_ke_modes, load,
                       muc_gat_hieu_luc, normalize_mode, phase_key,
                       prompt_context_last, prompt_context_save, render_next,
                       sha256_noi_dung, turn_log_append, turn_log_clear,
                       turn_snapshot, work_kind_hieu_luc)

MAX_LINES = 3
MAX_CHARS = 240

MA_GON = "TDQ:GON"
# The pointer line has its own budget: the 3-line/240-char ceiling of spec §2.7 keeps its
# numbers and now measures the standing block (the one before the [TDQ:GON] marker) only.
MAX_GON_CHARS = 200
NHAC_GON = ("[{ma}] muc_gat={muc} · build less than asked: climb the ladder from rung 1 "
            "(nothing new) before adding a file, class or layer. A "
            "`ponytail:` marker owes a cap and an upgrade path.")  # no-marker: allow — law text

# An approval sign = (a) a word of agreement AND (b) the object waiting for approval.
AGREE = re.compile(r"\b(duyệt|duyet|ok|oke|okay|đồng\s*ý|dong\s*y|chốt|chot|"  # i18n-allow
                   r"approve[sd]?|approved|accept(?:ed)?|confirm(?:ed)?|agree[d]?|yes|yep|"
                   r"lgtm|go\s*ahead|proceed|ship\s*it|sounds\s*good|looks\s*good|"
                   r"làm\s*đi|lam\s*di|tiến\s*hành|tien\s*hanh|"  # i18n-allow
                   r"triển\s*khai|trien\s*khai|triển|trien|thực\s*hiện|thuc\s*hien)\b", re.IGNORECASE)  # i18n-allow
OBJECT = re.compile(r"\b(spec|plan|quick|mini-?plan)\b", re.IGNORECASE)
# Vietnamese/English aliases of lane quick. "nhanh" is a very common adjective in ordinary
# Vietnamese requests ("do it quickly for me"), so it only counts as an approval when it
# stands RIGHT AFTER the word of agreement — it does not share the path of OBJECT above, which only needs to appear anywhere
# in the sentence.
APPROVE_FAST = re.compile(
    r"\b(duyệt|duyet|chốt|chot|approve[sd]?|confirm|pick|choose)\s+"  # i18n-allow
    r"(chế\s*độ\s*nhanh|che\s*do\s*nhanh|nhanh|express|quick|fast)\b",  # i18n-allow
    re.IGNORECASE)
PRONOUN = re.compile(r"(cái\s*này|cai\s*nay|cái\s*đó|cai\s*do|cái\s*trên|cai\s*tren|"  # i18n-allow
                     r"\bthis\b|\bthat\b|\bthe\s+above\b)", re.IGNORECASE)
# A question — or a hedge — is not an approval, even when both components are present.
# The English half matters as much as the Vietnamese one: "ok but not yet" carries the word
# of agreement AND the object, so without this blocker it would read as a clean approval.
QUESTION = re.compile(
    r"(\?|\bchưa\b|\bchua\b|\bkhông\b\s*$|\bko\b\s*$"  # i18n-allow
    r"|\bnot\s+yet\b|\bnot\s+sure\b|\bnot\b|\bdon'?t\b|\bnope\b|\bno\b\s*$"
    r"|\bhold\s+on\b|\bwait\b|\bmaybe\b|\breject(?:ed)?\b|\bcancel\b"
    r"|\bnhưng\b|\bnhung\b|\bbut\b|\bconfirm\b|\bxác\s*nhận\b|\bxac\s*nhan\b"  # i18n-allow
    r"|\bnếu\b|\bneu\b|\bif\b)",  # i18n-allow
    re.IGNORECASE)
# Built from MODE_ALIASES: every spelling `normalize_mode` understands must also be heard
# at the mode gate, and adding a mode costs one row in the alias table instead of an edit to
# the regex here. Longest alias first, because the regex takes the FIRST matching branch
# ("inline implement" must be tried before "inline"). Spaces inside an alias widen to \s+ so
# "sub  agent" gets in, while the \b at both ends keeps "mainline" and "inlineable" out.
_MODE_BI_DANH = "|".join(
    re.escape(alias).replace(r"\ ", r"\s+")
    for alias in sorted(MODE_ALIASES, key=len, reverse=True))
MODE = re.compile(r"\b(%s)\b" % _MODE_BI_DANH, re.IGNORECASE)
# Every gate template invites the user to answer with a letter, so a bare letter is a valid
# answer at all 4 gates. Accepted ONLY when it STANDS ALONE (an optional choose-prefix and a
# short tail are allowed): a full sentence such as "Approve? not sure" must miss.
# a-d, not just a-b: the option lists of the interview template run up to D.
# Enhanced for 1a, 1. a, câu 1a, 1) a at single gate (O01).
LETTER = re.compile(
    r"^\s*(?:chọn\s+|chon\s+|choose\s+|option\s+|pick\s+|answer\s+)?"
    r"(?:(?:câu\s+)?1[.:)\-\s]*)?"
    r"(?:chọn\s+|chon\s+|choose\s+|option\s+|pick\s+|answer\s+)?"
    r"([a-d])\b\s*(?:nhé|nhe|đi|di|please|thanks|!|\.)?\s*$",
    re.IGNORECASE)
# At the 3 approval gates the recommendation always sits at option A (interview.md), so A —
# and only A — is the approving letter. b/c/d there answer some other question: they are not
# read as an approval, so the agent has to ASK instead of guessing.
APPROVE_LETTER = "a"
RE_DIRECT = re.compile(r"(?:^|\s|[^\w])_tdq_direct(?:\s|[^\w]|$)", re.IGNORECASE)

NON_HUMAN_RE = re.compile(
    r"(?:<notification\b|<system-reminder\b|<cross-session|<system\b|<TDQ_WORKFLOW\b|"
    r"\[(?:tool_result|notification|system|cross-session))",
    re.IGNORECASE)

OPENCODE_WRAPPER_RE = re.compile(r"<TDQ_WORKFLOW>.*?</TDQ_WORKFLOW>", re.IGNORECASE | re.DOTALL)


def _tach_prompt_thuc(prompt):
    """Strip <TDQ_WORKFLOW>...</TDQ_WORKFLOW> wrapper inserted automatically by OpenCode plugin (O03)."""
    if not prompt:
        return ""
    return OPENCODE_WRAPPER_RE.sub("", str(prompt)).strip()


QUOTED_SPEECH_RE = re.compile(
    r"""(?i)(?:the user said|claude asked|trích dẫn|người dùng nói)\s*:\s*["'“]"""
)

_GIT_GRANT_META_RE = re.compile(
    r"(?i)(?:\bmở\s+request\b|\bopen\s+request\b|"  # i18n-allow
    r"\b(?:update|cập\s*nhật|sửa|chỉnh)\b[^\n]{0,30}\bhook\b|"  # i18n-allow
    r"\b(?:viết|duyệt|lập|sửa)\b[^\n]{0,20}\b(?:spec|plan|brief)\b|"  # i18n-allow
    r"\btest\b[^\n]{0,20}\bhook\b)"
)
_GIT_GRANT_NEG_RE = re.compile(
    r"(?i)\b(?:không|khong|ko|chưa|chua|đừng|not|don'?t|do\s+not|"  # i18n-allow
    r"never|cancel|wait|hold\s+on|maybe|nope|no)\b"
)
_GIT_GRANT_PUSH_RE = re.compile(
    r"(?i)(?:\bgit\s+push\b|"
    r"\bpush\b[^\n]{0,40}\b(?:lên|len|origin|upstream|remote|dev|main|nhánh|nhanh|branch|code|đi|di|now|it|changes|này|nay)\b|"  # i18n-allow
    r"\b(?:duyệt|duyet|cho\s*phép|cho\s*phep|allow|approve[sd]?|ok|okay|oke|đồng\s*ý|dong\s*y|chốt|chot|chạy|chay|run|thực\s*hiện|thuc\s*hien|giúp|giup|hãy|hay)\b[^\n]{0,40}\bpush\b|"  # i18n-allow
    r"\bđẩy\b[^\n]{0,24}\b(?:code|lên|nhánh|origin|upstream|remote)\b)"  # i18n-allow
)
_GIT_GRANT_RESET_RE = re.compile(r"(?i)\b(?:git\s+)?reset\s+(?:--hard|hard)\b")
_GIT_GRANT_CLEAN_RE = re.compile(
    r"(?i)\b(?:git\s+)?clean\b[^\n]{0,24}(?:--force\b|-[a-z]*f[a-z]*\b)"
)


def _has_prompt_grant_blockers(trimmed):
    """Reject quoted, system, question, negation, and meta-hook prompts before granting git."""
    if not trimmed or "?" in trimmed:
        return True
    if len(trimmed) >= 2 and (
        (trimmed[0] == '"' and trimmed[-1] == '"')
        or (trimmed[0] == "'" and trimmed[-1] == "'")
        or (trimmed[0] == "\u201c" and trimmed[-1] == "\u201d")
    ):
        return True
    return bool(
        NON_HUMAN_RE.search(trimmed)
        or QUOTED_SPEECH_RE.search(trimmed)
        or _GIT_GRANT_META_RE.search(trimmed)
        or _GIT_GRANT_NEG_RE.search(trimmed)
    )


def extract_git_grants(prompt):
    """Extract verified single-turn git grants (`clean_f`, `push`, `reset_hard`)."""
    trimmed = _tach_prompt_thuc(prompt)
    if _has_prompt_grant_blockers(trimmed):
        return []
    grants = []
    if _GIT_GRANT_CLEAN_RE.search(trimmed):
        grants.append("clean_f")
    if _GIT_GRANT_PUSH_RE.search(trimmed):
        grants.append("push")
    if _GIT_GRANT_RESET_RE.search(trimmed):
        grants.append("reset_hard")
    return grants


_SETUPFULLY_RE = re.compile(r"\bsetupfully\s+tdq-workflow\b", re.IGNORECASE)
_SETUPFULLY_Q_PHRASE_RE = re.compile(
    r"(?i)(?:\blà\s+gì\b|\bthế\s+nào\b|\bnhư\s+nào\b|\bcách\s+(?:chạy|dùng)\b|\bwhat\s+is\b|\bhow\s+to\b)"
)
_SETUPFULLY_QUOTED_RE = re.compile(
    r"""(["'`“])[^"'`”]*\bsetupfully\s+tdq-workflow\b[^"'`”]*\1"""
)


def extract_setupfully_trigger(prompt):
    """Return True only when a genuine user prompt invokes `setupfully tdq-workflow`."""
    trimmed = _tach_prompt_thuc(prompt)
    if _has_prompt_grant_blockers(trimmed):
        return False
    if _SETUPFULLY_Q_PHRASE_RE.search(trimmed) or _SETUPFULLY_QUOTED_RE.search(trimmed):
        return False
    return bool(_SETUPFULLY_RE.search(trimmed))


def _evaluate_setup_setup_line(prompt, is_new_turn):
    """Return `[TDQ:SETUP]` directive when setupfully or restart resume applies, else ''."""
    try:
        import tdq_setup_state
        res = tdq_setup_state.evaluate_restart_resume(is_new_turn=bool(is_new_turn))
        action = res.get("action")
        if action == "run_verify":
            return (
                "[TDQ:SETUP] Antigravity restarted after Phase-1 setup — run NOW: "
                "`py -3 -X utf8 scripts/tdq_setup.py --post-restart-verify` and close the loop."
            )
        if action == "remind_restart":
            return (
                "[TDQ:SETUP] Setup Phase 1 completed — close and restart Antigravity completely "
                "(same IDE process detected), then send any message to run 6-layer verification."
            )
    except Exception:  # noqa: BLE001
        pass
    if is_new_turn and extract_setupfully_trigger(prompt):
        return (
            "[TDQ:SETUP] Explicit setupfully user consent received — run Phase-1 setup end-to-end "
            "without asking manifest approval: `py -3 -X utf8 scripts/tdq_setup.py --setupfully`."
        )
    return ""


def _emit_setup_hooks(cwd, prompt, is_new_turn, user_md_fn=None):
    """Emit [TDQ:SETUP] directive line and optional Antigravity user_markdown card."""
    line = _evaluate_setup_setup_line(prompt, is_new_turn)
    if not line:
        return False
    final_line = lenh_cho_project(line, cwd)
    emit_context([final_line])
    if callable(user_md_fn):
        user_md_fn(final_line)
    return True


def _an_toan_by(prompt):
    """Sanitize user prompt for --by flag to prevent command injection and quote breakage (O01)."""
    clean_p = _tach_prompt_thuc(prompt)
    if not clean_p:
        return "user"
    safe = re.sub(r'["\'`$;|&<>\\{}\n\r]', ' ', clean_p[:60])
    safe = " ".join(safe.split())
    return safe or "user"


def looks_like_approval(prompt, target, chon_duoc=None):
    if not prompt:
        return False
    # Check for quotes and non-human / system tags (O01)
    prompt = _tach_prompt_thuc(prompt)
    if not prompt:
        return False
    p_strip = prompt.strip()
    if (p_strip.startswith(('"', "'", "“")) and p_strip.endswith(('"', "'", "”")) and len(p_strip) >= 2):
        return False
    if NON_HUMAN_RE.search(prompt) or QUOTED_SPEECH_RE.search(prompt):
        return False
    if QUESTION.search(prompt):
        return False
    letter = LETTER.match(prompt)
    if target == "mode":
        # An answer at the mode gate is usually bare: "main", "subagent", "choose A".
        # No word of agreement is required — the plan is already approved, this only
        # picks how to run it. A letter counts exactly when it names one of the options
        # that were OFFERED: reading "C" as an answer on a 2-option gate would record a
        # mode the user never saw, so `mode_from_answer` is the single judge of range.
        return bool(MODE.search(prompt)
                    or (letter and mode_from_answer(prompt, None, chon_duoc)))
    if letter:
        return letter.group(1).lower() == APPROVE_LETTER
    if target == "quick" and APPROVE_FAST.search(prompt):
        return True
    if not AGREE.search(prompt):
        return False
    match = OBJECT.search(prompt)
    if match:
        said = match.group(1).lower().replace("-", "")
        return said == target or (target == "quick" and said in ("quick", "miniplan"))
    # With no object named, only an explicit pointing pronoun is accepted ("approve this").
    # "ok", "ok I get it" are NOT approvals — when it is ambiguous, let the agent ASK.
    return bool(PRONOUN.search(prompt))


def mode_mac_dinh():
    """The mode list with NO probe — only the modes needing nothing outside this machine.

    Without a probe there is no right to claim an outside engine is alive, so it is not
    offered. Taken from `liet_ke_modes`; no mode name is typed by hand here.
    """
    return [row["ma"] for row in liet_ke_modes(kiem_codex=lambda: (False, "not probed"))
            if row["chon_duoc"]]


def thu_tu_mode(planned, chon_duoc=None):
    """Option order at the mode gate — EXACTLY the letters A, B, C… the user sees.

    The rule: the mode the plan proposes sits at A (the interview template always parks the
    proposal at A), and the rest keep the order of the `modes --json` list. One rule serves
    both the printing side and the reading side, so a letter never points at the wrong mode.
    """
    ds = list(chon_duoc) if chon_duoc is not None else mode_mac_dinh()
    if not ds:
        return []
    dau = planned if planned in ds else ds[0]
    return [dau] + [ma for ma in ds if ma != dau]


def mode_from_answer(prompt, planned, chon_duoc=None):
    """An answer at the mode gate -> the machine identifier, or None if unreadable.

    The mode name typed out beats the letter — naming a mode is an unambiguous intent, even
    when that mode is currently unofferable (the implement gate will print the reason, and
    silently overriding the user is worse). A letter is read through `thu_tu_mode`: exactly
    the list that was printed, nothing more.
    """
    found = MODE.search(prompt or "")
    if found:
        said = normalize_mode(found.group(0))
        if said:
            return said
    letter = LETTER.match(prompt or "")
    if not letter:
        return None
    thu_tu = thu_tu_mode(planned, chon_duoc)
    chi_so = ord(letter.group(1).lower()) - ord("a")
    if 0 <= chi_so < len(thu_tu):
        return thu_tu[chi_so]
    return None


def _nhac_worktree(cwd):
    """One line, only while the ledger holds an open row — silent the rest of the time.

    Outside the 3-line/240-char budget on purpose: it is not part of the standing context,
    it appears only while disk is being wasted, and it disappears the moment `sweep --clean`
    runs. A ledger that is missing or corrupt says nothing, so it prints nothing: a nudge
    that cries wolf gets ignored, and this one has to still be believed weeks from now.
    """
    try:
        import tdq_worktree_registry as so_wt
        mo = so_wt.dong_mo(cwd)
    except Exception:
        return
    if mo:
        emit_context([lenh_cho_project(f"[TDQ:WORKTREE] {len(mo)} worktree(s) still open — run: "
                                       "python3 scripts/tdq_team.py sweep", cwd)])


def _subagent_anchor_line(cwd, payload, sub):
    """Build a static <600c recovery anchor for a subagent on compact/resume."""
    src = str(payload.get("source") or "").strip().lower()
    if src not in ("compact", "resume"):
        return ""
    state = load(cwd, heal=False) or {}
    req = str(state.get("active_request") or "").strip()
    if not req:
        return ""
    wk = work_kind_hieu_luc(state)
    pha = effective_phase(state, warn=False)
    role = sub.get("role") or "subagent"
    task = sub.get("task") or "none"
    line = (
        f"[TDQ:ANCHOR] Subagent {src}: request={req} kind={wk} phase={pha} "
        f"role={role} task={task} artifacts=docs/tdq/artifacts/{req}/"
    )
    return line[:595]


def _nhac_gon(cwd, state, payload, session):
    """One pointer line at phase `implement` — never the law body.

    This channel does NOT read `chung.md` off disk: `UserPromptSubmit` shares a single 30s
    budget with every other hook on the event, and the body belongs to the SessionStart /
    SubagentStart channels. Printed after the standing block so nothing can clip that block.
    Measured 2026-09-17: dedupe here only holds inside one process — `main` clears the turn
    ledger on entry, so under bug #10871 the second PID starts from a wiped ledger.
    """
    if effective_phase(state, warn=False) != "implement":
        return
    muc = muc_gat_hieu_luc(state)
    if muc == "off" or already_reminded(cwd, payload, MA_GON):
        return
    tmpl = INVESTIGATE_GON_TEXT if work_kind_hieu_luc(state) == "investigate" else NHAC_GON
    dong = _truncate(tmpl.format(ma=MA_GON, muc=muc), MAX_GON_CHARS)
    # `so_dong` here is 1, not the body's size: this channel injects the pointer line and
    # nothing else, and the field means "law lines THIS channel put in the context".
    turn_log_append(cwd, "remind", session=session, code=MA_GON,
                    event="UserPromptSubmit", muc_gat=muc,
                    so_dong=len(dong.splitlines()))
    emit_context([dong])


_TAIL_BYTES = 65536


def _prompt_sha(payload):
    text = str(
        (payload or {}).get("prompt")
        or (payload or {}).get("user_message")
        or (payload or {}).get("lastUserInput")
        or ""
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else ""


def _is_human_user_input(rec):
    """True when rec is a human USER_INPUT entry (blank or USER_EXPLICIT source)."""
    if not isinstance(rec, dict) or rec.get("type") != "USER_INPUT":
        return False
    src = str(rec.get("source") or "").strip().lower()
    return src in ("", "user_explicit")


def _parse_human_user_line(raw_line):
    text = raw_line.decode("utf-8", "replace").strip()
    if not text:
        return None
    try:
        rec = json.loads(text)
    except ValueError:
        return None
    return rec if _is_human_user_input(rec) else None


def _read_last_human_user_record(tpath):
    """Read <= 64 KB tail of transcriptPath in O(1) and return (last_human_rec, last_end)."""
    if not isinstance(tpath, str) or not tpath or not os.path.isfile(tpath):
        return None, 0
    try:
        with open(tpath, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            start = max(0, fh.tell() - _TAIL_BYTES)
            fh.seek(start)
            if start > 0:
                fh.readline()
            last_rec, last_end = None, start
            while True:
                raw_line = fh.readline()
                if not raw_line:
                    break
                rec = _parse_human_user_line(raw_line)
                if rec is not None:
                    last_rec, last_end = rec, fh.tell()
    except OSError:
        return None, 0
    return last_rec, last_end


def _extract_transcript_human_prompt(tpath):
    """Return text content of the last human USER_INPUT record from <= 64 KB tail."""
    last_rec, _ = _read_last_human_user_record(tpath)
    if last_rec is None:
        return ""
    return str(last_rec.get("content") or "")


def _extract_transcript_user_sig(tpath, prev_meta, prompt_sha=""):
    """Read <= 64 KB tail of transcriptPath in O(1) for the last human USER_INPUT signature."""
    last_rec, last_end = _read_last_human_user_record(tpath)
    if last_rec is not None:
        step_idx = last_rec.get("step_index")
        created = last_rec.get("created_at") or last_rec.get("timestamp") or ""
        if step_idx is not None or created:
            return f"ui:{step_idx}:{created}"
        return f"ui_pos:{last_end}"
    prev_sig = str((prev_meta or {}).get("last_user_sig") or "")
    prev_psha = str((prev_meta or {}).get("prompt_sha") or "")
    if prompt_sha and prev_psha and prompt_sha != prev_psha:
        return f"ui_big:{prompt_sha}"
    if prev_sig.startswith("ui") and not (prev_meta or {}).get("turn_closed"):
        return prev_sig
    return None


def _extract_user_turn_sig(payload, prev_meta):
    """Compute user-turn signature from transcriptPath tail or fallback prompt."""
    tpath = (payload or {}).get("transcriptPath") or (payload or {}).get("transcript_path")
    psha = _prompt_sha(payload)
    sig = _extract_transcript_user_sig(tpath, prev_meta, prompt_sha=psha)
    if sig is not None:
        return sig
    if psha:
        return "prompt:" + psha
    return ""


def _detect_new_user_turn(cwd, payload, sid):
    """Detect whether this PreInvocation starts a new user turn or continues mid-turn."""
    meta = read_turn_meta(cwd, sid)
    sig = _extract_user_turn_sig(payload, meta)
    turns_exists = os.path.isfile(_shard_turn_path(cwd, sid))
    if not meta:
        return True, sig
    if meta.get("turn_closed"):
        return True, sig
    if sig != meta.get("last_user_sig"):
        return True, sig
    if not sig and not turns_exists:
        return True, sig
    return False, sig


def _is_stale_or_nonhuman_grant_turn(payload, prev_meta, sig):
    src = str((payload or {}).get("source") or "").strip().lower()
    if src in ("compact", "resume", "system"):
        return True
    prev_sig = str((prev_meta or {}).get("last_user_sig") or "")
    return bool((prev_meta or {}).get("turn_closed") is True and sig and prev_sig and sig == prev_sig)


def _mint_agy_turn_meta(cwd, payload, sid, sig):
    prev_meta = read_turn_meta(cwd, sid)
    shard = _shard_turn_path(cwd, sid)
    if os.path.isfile(shard):
        try:
            os.remove(shard)
        except OSError:
            pass
    st_cur = load(cwd, heal=False) or {}
    stale = _is_stale_or_nonhuman_grant_turn(payload, prev_meta, sig)
    if stale:
        grants = []
        keep_closed = bool(prev_meta.get("turn_closed") is True)
    else:
        raw_prompt = str(payload.get("prompt") or payload.get("user_message") or payload.get("lastUserInput") or "")
        if not raw_prompt.strip():
            raw_prompt = _extract_transcript_human_prompt(payload.get("transcriptPath") or payload.get("transcript_path"))
        grants = extract_git_grants(raw_prompt)
        keep_closed = False
    _RUNTIME_STATE["git_grants"] = list(grants)
    write_turn_meta(cwd, sid, {"last_user_sig": sig, "turn_closed": keep_closed, "prompt_sha": _prompt_sha(payload), "phase_anchor": str(prev_meta.get("phase_anchor") or ""), "mode": str(st_cur.get("implement_mode") or ""), "git_grants": grants})
    if grants:
        _info(f"prompt_context: git_grant minted sid={sid} grants={grants}")


def _agy_pre_invocation_hook(payload, cwd):
    sid = session_id(payload)
    model_text, user_md = flush_pending_channels(cwd, sid)
    if model_text:
        emit_context([model_text])
    if user_md:
        emit_user_markdown(user_md)
    sub = detect_subagent(payload, cwd)
    if sub.get("is_subagent"):
        _RUNTIME_STATE["new_user_turn"] = False
        anc = _subagent_anchor_line(cwd, payload, sub)
        if anc:
            emit_context([anc])
        return True, False
    is_new, sig = _detect_new_user_turn(cwd, payload, sid)
    _RUNTIME_STATE["new_user_turn"] = is_new
    if is_new:
        _mint_agy_turn_meta(cwd, payload, sid, sig)
    return False, is_new


def _agy_phase_anchor(cwd, state, payload, sid):
    """Inject 1-line [TDQ:GON], [TDQ:QC], or [TDQ:PLAIN] once per phase entry or post-compaction."""
    req = str((state or {}).get("active_request") or "")
    pha = effective_phase(state, warn=False)
    if not req or pha not in ("implement", "qc", "spec", "plan", "report"):
        return
    meta = read_turn_meta(cwd, sid)
    anchor = f"{req}:{pha}"
    is_compact = str(payload.get("source") or "").lower() in ("compact", "resume")
    if not is_compact and meta.get("phase_anchor") == anchor:
        return
    if pha == "implement":
        muc = muc_gat_hieu_luc(state)
        if muc != "off":
            tmpl = INVESTIGATE_GON_TEXT if work_kind_hieu_luc(state) == "investigate" else NHAC_GON
            cap_lim = MAX_GON_CHARS if work_kind_hieu_luc(state) == "investigate" else min(MAX_GON_CHARS, 160)
            dong = _truncate(tmpl.format(ma=MA_GON, muc=muc), cap_lim)
            emit_context([dong])
    elif pha == "qc":
        emit_context(["[TDQ:QC] QC gate: verify DoD with evidence, run tdq-qc-tester, check clean-code invariants."])
    else:
        plain_hint = _truncate(
            f"[TDQ:PLAIN] ({pha}) Layer-1 front (chat & Tóm tắt dễ hiểu): 10-15s plain "  # i18n-allow
            "prose (<=120w, <=6 backticks/100w, <=2 ·/line); push path:line below.",
            MAX_CHARS,
        )
        emit_context([plain_hint])
    meta["phase_anchor"] = anchor
    write_turn_meta(cwd, sid, meta)


def main():
    payload = read_payload()
    cwd = payload_cwd(payload)
    sid = session_id(payload)
    agy_mode = is_agy()
    is_new_turn = True
    if agy_mode:
        should_stop, is_new_turn = _agy_pre_invocation_hook(payload, cwd)
        if should_stop:
            return
    else:
        sub = detect_subagent(payload, cwd)
        if sub.get("is_subagent"):
            anc = _subagent_anchor_line(cwd, payload, sub)
            if anc:
                emit_context([anc])
                return
    prompt = str(payload.get("prompt") or payload.get("user_message") or payload.get("lastUserInput") or "")
    if agy_mode and not prompt.strip():
        prompt = _extract_transcript_human_prompt(payload.get("transcriptPath") or payload.get("transcript_path"))
    if not agy_mode or is_new_turn:
        turn_log_clear(cwd, sid)
        turn_log_append(cwd, "turn_start", session=sid, **turn_snapshot(cwd))
        git_grants = list(_RUNTIME_STATE.get("git_grants") or []) if agy_mode else extract_git_grants(prompt)
        if git_grants:
            turn_log_append(cwd, "signal", session=sid, event="git_grant",
                            target="git_grant", grants=git_grants)
            if not agy_mode:
                _info(f"prompt_context: git_grant minted sid={sid} grants={git_grants}")
        _nhac_worktree(cwd)
        _emit_setup_hooks(cwd, prompt, is_new_turn=is_new_turn, user_md_fn=emit_user_markdown if agy_mode else None)

    # No OPEN request (open = active_request exists AND phase != idle) → point at intake.
    # The INTAKE line comes FIRST so _truncate (which cuts from the tail) never clips it.
    if RE_DIRECT.search(prompt):
        intake = (
            "[TDQ:INTAKE] Yêu cầu chứa '_tdq_direct' → chạy chế độ direct: "  # i18n-allow
            "tự động phân tích & tìm kiếm, lập mini-plan và chỉ dừng ở 1 cổng duyệt "  # i18n-allow
            "mini-plan (không hỏi chọn pipeline, không phỏng vấn)."  # i18n-allow
        )
    else:
        intake = ("[TDQ:INTAKE] No request is open — unless this prompt belongs to an intake round "
                  "already running, open tdq-workflow:tdq-intake (or tdq-intake).")
    state = load(cwd)
    if state is None or not state.get("active_request"):
        _emit(cwd, sid, [intake])
        return
    # phase_key, not the raw phase: a running lane quick keeps the raw phase=idle — comparing
    # raw would fire INTAKE wrongly and swallow the APPROVE line of quick.
    if phase_key(state) == "idle":
        _emit(cwd, sid, [intake, render_next(cwd, state, brief=True)])
        return

    lane = effective_lane(state, warn=False)
    pending = None
    if lane == "quick" and not state.get("quick_approved"):
        pending = "quick"
    elif lane == "full" and state.get("spec_file") and not state.get("spec_approved"):
        pending = "spec"
    elif lane == "full" and state.get("spec_approved") and state.get("plan_file") \
            and not state.get("plan_approved"):
        pending = "plan"
    elif lane == "full" and state.get("plan_approved") \
            and effective_phase(state, warn=False) == "mode" \
            and not effective_mode(state, warn=False):
        # The mode gate: the plan is approved but the user has not picked how to run it. The
        # answer here is usually a bare "main"/"subagent", so it is detected separately.
        pending = "mode"

    lines = [render_next(cwd, state, brief=True)]

    if pending:
        # The APPROVE line comes BEFORE NEXT: _truncate cuts from the tail — better to clip
        # the project path than to clip the hint / approve command (the clipped-hint bug of
        # 2026-08-02).
        lines = []
        prompt = payload.get("prompt") or ""
        planned = plan_mode(cwd, state) if pending in ("plan", "mode") else None
        # The mode list is built only at the mode gate itself: `liet_ke_modes(cwd=...)`
        # probes the outside engine in a sub-process, too costly to run on every prompt.
        chon_duoc = ([row["ma"] for row in liet_ke_modes(cwd=cwd) if row["chon_duoc"]]
                     if pending == "mode" else None)
        matched = looks_like_approval(prompt, pending, chon_duoc)
        turn_log_append(cwd, "signal", session=sid, event="approve_pending",
                        target=pending, matched=matched, mode_conflict=False)
        if matched:
            mode = ""
            if pending == "mode":
                # The mode gate: the answer IS the mode. Picking a different mode than the
                # plan proposed is no conflict — a proposal is only a proposal, the user
                # settles it. Normalised to the machine identifier: the user typing "inline"
                # must still run --mode main, else state holds a string outside VALID_MODES.
                said = mode_from_answer(prompt, planned, chon_duoc) or planned or "main"
                lines.append("[TDQ:APPROVE] The user just picked a mode → run NOW: "
                             f"python3 scripts/tdq_state.py approve plan --mode {said} "
                             f"--by \"{_an_toan_by(prompt)}\"")
                lines.append(render_next(cwd, state, brief=True))
                _emit(cwd, sid, lines, critical=True)
                return
            if pending == "plan":
                found = MODE.search(prompt)
                said = normalize_mode(found.group(0)) if found else None
                if said and planned and said != planned:
                    # The mode in the approval sentence differs from the mode SETTLED in the
                    # plan — it must not be recorded by guessing, the agent has to ASK the
                    # user to confirm.
                    turn_log_append(cwd, "signal", session=sid, event="approve_pending",
                                    target=pending, matched=matched, mode_conflict=True)
                    lines.append(f"[TDQ:APPROVE] ⚠️ The approval says mode {said} but the plan "
                                 f"settled {planned} — ASK the user to confirm the mode first, "
                                 f"do not run approve yet.")
                    _emit(cwd, sid, lines, critical=True)
                    return
                # No mode named → do NOT insert a placeholder: a missing mode is valid now,
                # phase `mode` right after will ask. A placeholder makes the agent ask a beat early.
                mode = f" --mode {said}" if said else ""
            lines.append(f"[TDQ:APPROVE] The user just approved {pending} → run NOW: "
                         f"python3 scripts/tdq_state.py approve {pending}{mode} "
                         f"--by \"{_an_toan_by(prompt)}\"")
        else:
            waiting = ("the user to pick a mode" if pending == "mode"
                       else f"{pending} approval")
            lines.append(f"[TDQ:APPROVE] Waiting for {waiting}. This prompt is NOT clearly an "
                         f"approval → do not guess: ASK again, or print "
                         f"\"{approve_hint(pending, planned)}\".")
        lines.append(render_next(cwd, state, brief=True))
        # No dedupe: every turn must see the "do not guess an approval" warning again —
        # compacting it to "(same as last turn)" here would swallow that very safety warning.
        _emit(cwd, sid, lines, critical=True)
        return

    # spec approved but the file changed afterwards → warn (the approval trace no longer matches)
    rel, sha = state.get("spec_file"), state.get("spec_sha256")
    drifted = False
    if state.get("spec_approved") and rel and sha:
        path = rel if os.path.isabs(rel) else os.path.join(cwd, rel)
        try:
            # The same hash function used when the approval was recorded
            # (`tdq_state._cli_approve`) — copying the hashing rule out here would let the two
            # sides drift apart and then disagree.
            drifted = sha256_noi_dung(path) != sha
        except OSError:
            drifted = True
        if drifted:
            lines.append("[TDQ:APPROVE] ⚠️ The spec changed after approval (sha256 mismatch) — "
                         "present it to the user for re-approval.")
    _emit(cwd, sid, lines, critical=drifted)
    if agy_mode:
        _agy_phase_anchor(cwd, state, payload, sid)
    else:
        _nhac_gon(cwd, state, payload, sid)
        _nhac_qc(cwd, state, payload, sid)
        _nhac_plain(cwd, state, payload, sid)


def _nhac_plain(cwd, state, payload, session):
    """At presentation phases, inject a concise [TDQ:PLAIN] Layer-1 recency reminder."""
    pha = effective_phase(state, warn=False)
    if pha not in ("spec", "plan", "report"):
        return
    ma_plain = "TDQ:PLAIN"
    if already_reminded(cwd, payload, f"{ma_plain}:{pha}"):
        return
    dong = _truncate(
        f"[{ma_plain}] ({pha}) Layer-1 front (chat & Tóm tắt dễ hiểu): 10-15s plain "  # i18n-allow
        "prose (<=120w, <=6 backticks/100w, <=2 ·/line); push path:line below.",
        MAX_CHARS,
    )
    turn_log_append(cwd, "remind", session=session, code=f"{ma_plain}:{pha}",
                    event="UserPromptSubmit", so_dong=1)
    emit_context([dong])


def _nhac_qc(cwd, state, payload, session):
    """At phase `qc`, inject the 5 SOLID questions and DoD reminder when QC is invoked."""
    if effective_phase(state, warn=False) != "qc":
        return
    prompt = (payload.get("prompt") or "").lower()
    if not any(k in prompt for k in ("qc", "kiểm tra", "dod")):
        return
    ma_qc = "TDQ:QC"
    if already_reminded(cwd, payload, ma_qc):
        return
    dong = (
        f"[{ma_qc}] Quality Control checklist: verify DoD items with evidence; "
        "check 5 SOLID questions (clean-code.md); ensure zero false red tests."
    )
    turn_log_append(cwd, "remind", session=session, code=ma_qc,
                    event="UserPromptSubmit", so_dong=1)
    emit_context([dong])


def _truncate(text, limit=MAX_CHARS):
    if len(text) <= limit:
        return text
    cut = limit - 1
    # A22: a cut landing inside inline code leaves half a command looking like a real one —
    # an odd backtick count means we are inside a span, so step back before the opening one.
    if text[:cut].count("`") % 2 == 1:
        cut = text.rfind("`", 0, cut)
    return text[:cut].rstrip() + "…"


def _compact(text):
    """The previous turn printed exactly this — replace it with a short line, same code."""
    match = re.match(r"^\[(TDQ:[A-Z]+)\]", text)
    code = match.group(1) if match else "TDQ"
    return f"[{code}] (same as last turn — unchanged)"


def _emit(cwd, session, lines, critical=False):
    """Emit standing prompt context, skipping same-as-last-turn repeats on Antigravity."""
    text = lenh_cho_project(_truncate("\n".join(lines[:MAX_LINES])), cwd)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if is_agy():
        is_new = bool(_RUNTIME_STATE.get("new_user_turn", True))
        if is_new or prompt_context_last(cwd, session) != digest:
            prompt_context_save(cwd, session, digest)
            emit_context([text])
        return
    if critical:
        emit_context([text])
        return
    if prompt_context_last(cwd, session) == digest:
        text = _compact(text)
    else:
        prompt_context_save(cwd, session, digest)
    emit_context([text])


if __name__ == "__main__":
    main()
