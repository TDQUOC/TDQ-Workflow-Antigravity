#!/usr/bin/env python3
"""Team-mode orchestration: the leader assigns the WHOLE plan, sub-agents run in parallel.

Eight sub-commands, used in exactly this order:
    assign      — read the whole plan, write the map docs/tdq/team/<slug>.json
    audit       — audit the map: a task the leader kept against the rules exits non-zero
    wave        — print the next wave (assignable tasks touching no locked area)
    open <task> — create a branch + its own git worktree for one task
    sweep       — sweep every worktree of every request; --clean removes the safe ones
    check <task>— probe for conflicts with the integration branch, WITHOUT touching the repo
    merge <task>— merge the task's branch into the integration branch (blocked until `check` passes)
    clean       — remove every worktree of the request, prune .git/worktrees clean

The old Vietnamese names (phan-cong, kiem-ke, cum, mo, soat, kiem, hop, don) still work as
hidden aliases; the table lives in scripts/tdq_ten_lenh.py.

Why this tool instead of letting the model wing it: the decision "assign this task or
keep it" must be MACHINE-CHECKABLE. When the model judges itself, nobody can prove
whether it bent the rule (the user picked subagent, the leader did the work on main).

Exit code: 0 = fine · 1 = rule broken / conflict / missing facts · 2 = wrong usage.
Env: TDQ_PROJECT_DIR anchors the project · TDQ_LOG=0 mutes the log · TDQ_WORKTREE_DIR moves worktrees.
"""
import os as _tdq_os, sys as _tdq_sys
_tdq_here = _tdq_os.path.dirname(_tdq_os.path.abspath(__file__))
_tdq_scripts = _tdq_os.path.normpath(_tdq_os.path.join(_tdq_here, '..', '..', 'scripts'))
for _p in (_tdq_scripts, _tdq_here):
    if _tdq_os.path.isdir(_p) and _p not in _tdq_sys.path:
        _tdq_sys.path.insert(0, _p)
import utf8_io  # noqa: E402,F401
import argparse
import ast
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime

GIT_TIMEOUT = 120

U09_STATUS = "HOLD"
U09_REASON = (
    "Chưa đủ history/corpus case để mở advisory hoặc speculative probe; "
    "giữ nguyên git merge-tree probe hiện hữu phân biệt clean/conflict/error."
)

# --- plan reading rules ------------------------------------------------------
# Task line: `- [ ] **T1.1** (n3 e5m) work — Test: ...`
_TASK = re.compile(r"^(\s*)-\s*\[( |~|x|>)\]\s*\*\*([A-Za-z][A-Za-z0-9.]*)\*\*\s*(.*)$")
_PHASE = re.compile(r"^##\s*(P\d+)\b")
# A path declared in backticks: needs a `/` and an extension — `true` or `T1.1` do not count.
_PATH = re.compile(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`")
_SECTION_PATH = re.compile(
    r"`[^`]*`"
    r"|(?<![:/@A-Za-z0-9_.\-`])([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)(?![A-Za-z0-9_./\-`])"
)
ROOT_FILES = {
    "CLAUDE.md", "AGENTS.md", "Cargo.toml",
    "pyproject.toml", "package.json", "pyrightconfig.json",
    "tdq-config.json",
}
_FENCE = re.compile(r"^\s*(```|~~~)")
_REF_WITH_SYMS = re.compile(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`\s*\(([^)]+)\)")
_SWEEP_LABEL = re.compile(
    r"(?:[\(\[]\s*sweep\s*[\)\]]|(?:loại|type|nhãn|nhan_loai)\s*:\s*[^.\n]*\bsweep\b)"  # i18n-allow
)
_IGNORED_PROJ_PREFIXES = (
    "tiến độ:", "tiến độ inline:", "tiến độ hoàn tất:",  # i18n-allow
    "progress:", "progress inline:", "status:",
    "vị trí neo:", "neo & công cụ:", "tham chiếu:", "contract-delta:",  # i18n-allow
)
# Same task-code rule as `_TASK` above: `T1`, `T2A.1`, `T2.4b`, `QC1.1` are valid declarations
# in a `- Cần:` line; missing them makes the dependency graph falsely sparse.  # i18n-allow
_TASK_REF = re.compile(r"\b(?:T\d+[A-Za-z]*\.\d+[a-z]?|T\d+[A-Za-z]*|QC\d+(?:\.\d+)?)\b")
# Dependency label in the plan: `- Cần: T1.1, T2.3`.  # i18n-allow
NHAN_CAN = "Cần:"  # i18n-allow
# Time-estimate label in the plan: `(n3 e20m)` → 20 minutes.
_UOC_LUONG = re.compile(r"\be(\d+)m\b")

# CLOSED set of reasons for keeping a task with the leader. Anything else bends the rule.
LY_DO_GIU = {
    "phu-thuoc": "the task depends on another task that is not finished",  # i18n-allow
    "vung-khoa": "no separate file area is declared, so it cannot be split off",  # i18n-allow
    "mcp": "the task needs an MCP tool a sub-agent does not have",  # i18n-allow
    "file-luat": "it edits the very rule/hook file the leader runs on",  # i18n-allow
    # A shared contract (data types, constants, message shapes, registries) must be
    # built FIRST and only then branched out: if every sub-agent guesses its own shape,
    # the mismatch between the copies only shows up after the merge.
    "hop-dong": "the task defines a shared contract that later tasks read",  # i18n-allow
}
# Rule/hook file prefixes: a sub-agent editing these saws the plank the leader is
# standing on — the leader has to do them itself.
TIEN_TO_FILE_LUAT = ("skills/", "hooks/", "agents/", "rules/", ".claude/", ".codex/", ".agents/",
                     "CLAUDE.md", "AGENTS.md")
# Branch/worktree name prefixes that are banned (CLAUDE.md §2).
TEN_CAM = ("claude", "antigravity", "gemini", "codex")

# Cap on branches running at once. 4, because coordination failure points grow as n(n-1)/2:
# 4 agents is 6 points, 10 agents is already 45 (research round 1, section 4). This is an
# UPPER cap — fewer ready tasks means fewer launched, never wait to fill up to 4.
TRAN_SONG_SONG = 4

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)
import tdq_config  # noqa: E402
import tdq_state  # noqa: E402
import tdq_ten_lenh  # noqa: E402
import tdq_worktree_registry as so_wt  # noqa: E402


# --------------------------------------------------------------- log service
def _log_enabled():
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message):
    """Log service: one ISO-timestamped line on stderr. Muted with TDQ_LOG=0."""
    if _log_enabled():
        print(f"[{datetime.now().isoformat(timespec='seconds')}] {message}",
              file=sys.stderr)


def _loi(message):
    """Error messages always go to stderr, regardless of TDQ_LOG."""
    print(message, file=sys.stderr)


def _project_dir():
    """Neo theo project: TDQ_PROJECT_DIR > git root > cwd."""
    env = os.environ.get("TDQ_PROJECT_DIR")
    if env:
        return env
    start = current = os.getcwd()
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return start
        current = parent


# ------------------------------------------------------------- read the plan
class Task:
    """One task of the plan, with everything readable off its own line."""

    def __init__(self, ma, trang_thai, phase):
        self.ma = ma
        self.trang_thai = trang_thai      # " " | "~" | "x" | ">"
        self.phase = phase
        self.text = []                    # the task line + its child lines
        self.vung_file = []
        self.tham_chieu = []
        self.sinh_ra = []
        self.nhan_loai = ""
        self.can_mcp = False
        self.worktree_required = True
        self._sections = []               # parallel section key for each self.text entry
        self._has_cham = False
        self._tham_chieu_syms = {}

    @property
    def xong(self):
        return self.trang_thai == "x"

    @property
    def da_giao(self):
        return self.trang_thai == ">"


def _line_indent(line):
    prefix = line[:len(line) - len(line.lstrip(" \t"))]
    return len(prefix.expandtabs(4))


def _classify_section(body):
    low = body.strip().lstrip("*").lower()
    if low.startswith(("chạm:", "cham:")):  # i18n-allow
        return "cham"
    if low.startswith(("tham chiếu:", "tham chieu:")):  # i18n-allow
        return "tham_chieu"
    if low.startswith("sinh ra:"):  # i18n-allow
        return "sinh_ra"
    if low.startswith(("vị trí neo:", "neo & công cụ:")):  # i18n-allow
        return "neo"
    if low.startswith("contract-delta:"):
        return "contract_delta"
    if low.startswith(("tiến độ:", "tiến độ inline:", "tiến độ hoàn tất:",  # i18n-allow
                       "progress:", "progress inline:", "status:")):
        return "progress"
    return "other"


def _extract_paths(text, allow_bare=False):
    out = []
    if allow_bare:
        candidates = []
        for match in _SECTION_PATH.finditer(text):
            tok = match.group(0)
            if tok.startswith("`"):
                bt = _PATH.fullmatch(tok)
                if bt:
                    candidates.append(bt.group(1))
            elif match.group(1):
                candidates.append(match.group(1))
    else:
        candidates = _PATH.findall(text)
    for duong in candidates:
        if ("/" in duong or duong in ROOT_FILES) and duong not in out:
            out.append(duong)
    return out


def _record_tham_chieu_syms(task, line_text):
    for duong, raw_syms in _REF_WITH_SYMS.findall(line_text):
        if "/" not in duong and duong not in ROOT_FILES:
            continue
        bucket = task._tham_chieu_syms.setdefault(duong, [])
        for raw in raw_syms.split(","):
            sym = raw.strip().strip("`").rstrip("()")
            if sym and sym not in bucket:
                bucket.append(sym)


def _record_section_items(task, section, line_text):
    if section == "cham":
        for duong in _extract_paths(line_text, allow_bare=True):
            if duong not in task.vung_file:
                task.vung_file.append(duong)
        return
    if section == "tham_chieu":
        for duong in _extract_paths(line_text, allow_bare=True):
            if duong not in task.tham_chieu:
                task.tham_chieu.append(duong)
        _record_tham_chieu_syms(task, line_text)
        return
    if section == "sinh_ra":
        for duong in _extract_paths(line_text, allow_bare=True):
            if duong not in task.sinh_ra:
                task.sinh_ra.append(duong)


def _detect_nhan_loai(task):
    sources = []
    if task.text:
        sources.append(task.text[0].lower())
    for dong in task.text[1:]:
        low = dong.strip().lower()
        if low.startswith(("loại:", "nhãn:", "nhan:", "nhan_loai:", "type:", "label:")):  # i18n-allow
            sources.append(low)
    joined = " ".join(sources)
    if "dong-bo-chu-ky" in joined:
        return "dong-bo-chu-ky"
    if "uniform mechanical sweep" in joined or _SWEEP_LABEL.search(joined):
        return "sweep"
    return ""


def _update_fence(fence_marker, line):
    m_fence = _FENCE.match(line)
    if not m_fence:
        return fence_marker, False
    marker = m_fence.group(1)
    if fence_marker is None:
        return marker, True
    if marker == fence_marker:
        return None, True
    return fence_marker, True


def _feed_bullet_line(hien_tai, body, indent, sec_state):
    if sec_state["indent"] is None or indent <= sec_state["indent"]:
        sec_state["indent"] = indent
        sec_state["sec"] = _classify_section(body)
        if sec_state["sec"] == "cham":
            hien_tai._has_cham = True
    sec = sec_state["sec"] or "other"
    hien_tai.text.append(body)
    hien_tai._sections.append(sec)
    _record_section_items(hien_tai, sec, body)


def _feed_continuation_line(hien_tai, stripped, indent, sec_state):
    has_sub = sec_state["indent"] is not None and indent >= sec_state["indent"]
    sec = sec_state["sec"] if has_sub else "header"
    truoc = hien_tai.text[-1].rstrip()
    hien_tai.text[-1] = (truoc + " " + stripped) if truoc else stripped
    if sec in ("cham", "tham_chieu", "sinh_ra"):
        _record_section_items(hien_tai, sec, stripped)


def _feed_task_line(hien_tai, line, sec_state, task_indent):
    stripped = line.strip()
    if not stripped:
        return True
    indent = _line_indent(line)
    if indent <= task_indent:
        return False
    if stripped.startswith("- "):
        _feed_bullet_line(hien_tai, stripped[2:], indent, sec_state)
    else:
        _feed_continuation_line(hien_tai, stripped, indent, sec_state)
    return True


def is_artifact_only_paths(paths):
    """True when paths is non-empty and every target stays cleanly under docs/tdq/{artifacts,research}/."""
    if not paths or not isinstance(paths, (list, tuple)):
        return False
    for raw in paths:
        if not isinstance(raw, str):
            return False
        norm = raw.replace("\\", "/").strip()
        if not norm or norm.startswith("/") or "\x00" in norm or ":" in norm:
            return False
        if ".." in [seg for seg in norm.split("/") if seg]:
            return False
        art_ok = norm.startswith("docs/tdq/artifacts/") and len(norm) > len("docs/tdq/artifacts/")
        res_ok = norm.startswith("docs/tdq/research/") and len(norm) > len("docs/tdq/research/")
        if not (art_ok or res_ok):
            return False
    return True


def _finalize_tasks(tasks):
    for t in tasks:
        if not t._has_cham and t.text:
            for duong in _extract_paths(t.text[0]):
                if duong not in t.vung_file:
                    t.vung_file.append(duong)
        explicit_no_wt = False
        for dong in t.text:
            if dong.startswith("Dùng:") and dong.rstrip().endswith("(mcp)"):  # i18n-allow
                t.can_mcp = True
            low = dong.strip().lower()
            if (low.startswith("worktree:") and "no_worktree" in low) or "`no_worktree`" in low:
                explicit_no_wt = True
        t.nhan_loai = _detect_nhan_loai(t)
        all_targets = list(t.vung_file) + list(t.sinh_ra)
        if explicit_no_wt or (all_targets and is_artifact_only_paths(all_targets)):
            t.worktree_required = False


def doc_plan(duong_dan):
    """Return the list of Tasks in the exact order they appear in the plan."""
    with open(duong_dan, encoding="utf-8") as f:
        lines = f.read().splitlines()
    tasks = []
    phase = "P0"
    hien_tai = None
    sec_state = {"sec": None, "indent": None}
    task_indent = 0
    fence_marker = None
    for line in lines:
        fence_marker, toggled = _update_fence(fence_marker, line)
        if toggled or fence_marker is not None:
            continue
        m_phase = _PHASE.match(line)
        if m_phase:
            phase = m_phase.group(1)
            hien_tai = None
            continue
        m_task = _TASK.match(line)
        if m_task:
            task_indent = _line_indent(line)
            hien_tai = Task(m_task.group(3), m_task.group(2), phase)
            hien_tai.text.append(m_task.group(4))
            hien_tai._sections.append("header")
            sec_state = {"sec": None, "indent": None}
            tasks.append(hien_tai)
            continue
        if hien_tai is not None and not _feed_task_line(hien_tai, line, sec_state, task_indent):
            hien_tai = None
    _finalize_tasks(tasks)
    return tasks


def doc_phu_thuoc(tasks):
    """Map task code → set of task codes that must finish FIRST, read off the dependency line.

    A task declaring no such line returns the empty set — it claims no dependency.
    A code pointing at itself and a code absent from the plan are both skipped: a sloppy plan
    still schedules, and the linter catches the mistakes instead of crashing the wave command.
    """
    co_that = {t.ma for t in tasks}
    ket_qua = {}
    for t in tasks:
        can = set()
        for dong in t.text:
            if not dong.strip().startswith(NHAN_CAN):
                continue
            phan = dong.split(":", 1)[1] if ":" in dong else ""
            for ref in _TASK_REF.findall(phan):
                if ref != t.ma and ref in co_that:
                    can.add(ref)
        ket_qua[t.ma] = can
    return ket_qua


def _phut_uoc_luong(task):
    """Estimated minutes read off the `(n3 e20m)` label. Undeclared counts as 1 minute.

    Default 1 and not 0: an undeclared task still costs time, and 0 would make the whole
    branch holding it vanish from the critical-path comparison.
    """
    for dong in task.text:
        m = _UOC_LUONG.search(dong)
        if m:
            return int(m.group(1))
    return 1


# The task line ends with `— Test: <criterion>`; a runnable criterion states the command in
# backticks. Prose after `Test:` ("đọc lại thấy đủ 3 mục") carries nothing to run.  # i18n-allow
_TEST = re.compile(r"Test\s*:\s*(.*)$", re.S)
_LENH_NGOAC = re.compile(r"`([^`]+)`")


def lay_lenh_test(task):
    """The command a task's `Test:` says to run, or None when there is none to run."""
    for dong in task.text:
        m = _TEST.search(dong)
        if not m:
            continue
        lenh = _LENH_NGOAC.search(m.group(1))
        if lenh:
            return lenh.group(1).strip()
    return None


def chieu_phan_cong(tasks):
    """Compute the assignment projection object and mode for a list of tasks (O06).

    The projection captures all fields that participate in assignment and scheduling:
    task order, phase, task code (ID), contract/description, test, dependencies,
    file zones, MCP requirements, and estimates.

    In explicit mode (at least one task declares explicit `Cần:`), progress checkbox
    states and progress note lines are excluded from the projection.
    In legacy-conservative mode (no task declares explicit `Cần:`), checkbox states
    are included to preserve conservative legacy behavior.
    """
    phu_thuoc = doc_phu_thuoc(tasks)
    mode = "explicit" if any(phu_thuoc.values()) else "legacy-conservative"
    chieu = []
    for t in tasks:
        cac_dong = []
        sections = getattr(t, "_sections", [])
        for idx, dong in enumerate(t.text[1:], start=1):
            d_strip = dong.strip()
            sec = sections[idx] if idx < len(sections) else ""
            if sec in ("progress", "neo", "tham_chieu", "contract_delta"):
                continue
            if d_strip.lower().startswith(_IGNORED_PROJ_PREFIXES):
                continue
            cac_dong.append(d_strip)

        item = {
            "ma": t.ma,
            "phase": t.phase,
            "mo_ta": t.text[0].strip() if t.text else "",
            "dong_hop_dong": cac_dong,
            "vung_file": sorted(t.vung_file),
            "can_mcp": bool(t.can_mcp),
            "uoc_luong": _phut_uoc_luong(t),
            "test": lay_lenh_test(t),
            "deps": sorted(phu_thuoc.get(t.ma, ())),
        }
        if mode == "legacy-conservative":
            item["trang_thai"] = t.trang_thai
        chieu.append(item)
    return chieu, mode


def tinh_sha_projection(tasks):
    """(sha256_hex, mode) of canonical JSON representation of assignment projection."""
    chieu, mode = chieu_phan_cong(tasks)
    chuan = json.dumps(chieu, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    sha = hashlib.sha256(chuan.encode("utf-8")).hexdigest()
    return sha, mode


def ghi_ban_do_atomic(duong, ban_do):
    """Write assignment map atomically via mkstemp + replace in the target directory."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    noi_dung = json.dumps(ban_do, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(duong), prefix=".team-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(noi_dung)
        os.replace(tmp, duong)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def kiem_tra_stale(plan_path, ban_do):
    """Check if the plan on disk has changed in a way that makes ban_do stale.

    Returns (is_stale: bool, reason: str).
    """
    if not isinstance(ban_do, dict):
        return True, "Assignment map is not a valid object"

    proj_version = ban_do.get("projection_version")
    if proj_version is not None and proj_version != "v1":
        # Unknown future version — per spec: Unknown version/unparseable không giả current.
        return True, f"Unknown projection version '{proj_version}'"

    if not os.path.isfile(plan_path):
        return True, f"Plan file not found: {plan_path}"

    current_tasks = doc_plan(plan_path)
    if not current_tasks:
        return True, "The plan holds no readable task"

    if proj_version == "v1":
        stored_mode = ban_do.get("projection_mode", "legacy-conservative")
        current_sha, current_mode = tinh_sha_projection(current_tasks)
        if stored_mode == "explicit":
            if current_mode != "explicit":
                return True, "Plan dependencies were removed (mode changed to legacy-conservative)"
            stored_sha = ban_do.get("plan_assignment_sha")
            if stored_sha != current_sha:
                return True, "Plan structure or task assignment dependencies changed"
            return False, ""
        else:  # stored_mode == "legacy-conservative"
            # Legacy plans without explicit dependencies remain conservative per spec:
            # any content change to the plan file invalidates the map.
            if ban_do.get("plan_sha") != sha_file(plan_path):
                return True, "Plan file content changed (legacy-conservative whole-file SHA)"
            return False, ""

    # Legacy map without projection_version
    stored_plan_sha = ban_do.get("plan_sha")
    if stored_plan_sha != sha_file(plan_path):
        return True, "The plan changed after assignment (legacy map without projection version)"
    return False, ""


def b_level(tasks, phu_thuoc):
    """Task code → total minutes of the LONGEST path from that task to the end of the graph.

    This is the schedule's `b-level`: a task with a large b-level sits on the critical path;
    launched early the team finishes early, launched late every other branch waits on it.
    """
    sau = {t.ma: [] for t in tasks}                 # task code → the tasks waiting on it
    for t in tasks:
        for c in phu_thuoc.get(t.ma, ()):
            if c in sau:
                sau[c].append(t.ma)
    phut = {t.ma: _phut_uoc_luong(t) for t in tasks}
    nho = {}

    def tinh(ma, dang_di):
        if ma in nho:
            return nho[ma]
        if ma in dang_di:                           # cycle: cut it, never hang
            return 0
        dang_di.add(ma)
        ket_qua = phut[ma] + max((tinh(k, dang_di) for k in sau[ma]), default=0)
        dang_di.discard(ma)
        nho[ma] = ket_qua
        return ket_qua

    return {t.ma: tinh(t.ma, set()) for t in tasks}


def _la_file_luat(duong):
    return duong.startswith(TIEN_TO_FILE_LUAT)


def quyet_dinh_task(task, tasks):
    """(quyet_dinh, ly_do) for one task. Default is ASSIGN — keeping it needs a reason."""
    if task.can_mcp:
        return "tu_lam", "mcp"
    if not task.vung_file:
        return "tu_lam", "vung-khoa"
    if any(_la_file_luat(d) for d in task.vung_file):
        return "tu_lam", "file-luat"
    if any(doc_phu_thuoc(tasks).values()):
        # The plan declared `Cần:` → a dependency is a SCHEDULING constraint (`chia_dot` handles it),  # i18n-allow
        # not a reason to keep the task. Keeping it here would let a `Cần:` line kill parallelism.  # i18n-allow
        return "giao", ""
    chua_xong = {t.ma for t in tasks if not t.xong}
    for dong in task.text:
        for ref in _TASK_REF.findall(dong):
            if ref != task.ma and ref in chua_xong:
                return "tu_lam", "phu-thuoc"
    return "giao", ""


def chia_dot(tasks, quyet_dinh, project_root="."):
    """Assign a wave number to each task. Wave 1 runs first, same wave = in parallel.

    At least one task declares a dependency line → order by the DEPENDENCY GRAPH: a task sits
    after every task it declares, and is otherwise pulled as early as possible, even across
    phase boundaries. No task declares one → fall back to the old rule by phase name, so plans
    written before this rule produce exactly the same waves as before.

    Rule for both paths: two tasks touching the same file are never in the same wave (TCAS collision checked).
    """
    phu_thuoc = doc_phu_thuoc(tasks)
    if not any(phu_thuoc.values()):
        _log("chia-dot → no task declares a dependency line, falling back to phase-name order")
        return _chia_dot_theo_phase(tasks, project_root)
    khai = sum(1 for v in phu_thuoc.values() if v)
    _log(f"chia-dot → {khai}/{len(tasks)} task(s) declare dependencies, ordering by graph")
    return _chia_dot_theo_phu_thuoc(tasks, phu_thuoc, project_root)


# ------------------------------------------------------------- TCAS AST Analysis
def extract_ast_imports(file_path):
    """Parse a python file using ast.parse and extract imported module names."""
    if not os.path.isfile(file_path) or not file_path.endswith(".py"):
        return set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)
    except Exception:
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                imports.add(parts[0])
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                parts = node.module.split(".")
                imports.add(parts[0])
                imports.add(node.module)
    return imports


def file_to_module_names(rel_path):
    """Convert relative file path to possible module import names."""
    p = rel_path.replace("\\", "/")
    if not p.endswith(".py"):
        return set()
    p_no_ext = p[:-3]
    parts = p_no_ext.split("/")
    names = {parts[-1]}  # e.g., 'stop_batch_checker'
    dotted = ".".join(parts)
    names.add(dotted)    # e.g., 'hooks.scripts.stop_batch_checker'
    for i in range(1, len(parts)):
        names.add(".".join(parts[i:]))
    return names


def detect_tcas_collision(task_a_files, task_b_files, project_root="."):
    """Detect if task_b imports code modified by task_a, or vice-versa."""
    # 1. Direct file collision
    direct = set(task_a_files) & set(task_b_files)
    if direct:
        return True, f"Direct file collision: {direct}"

    # 2. TCAS AST Import Dependency Analysis
    mod_names_a = set()
    for f in task_a_files:
        mod_names_a.update(file_to_module_names(f))

    mod_names_b = set()
    for f in task_b_files:
        mod_names_b.update(file_to_module_names(f))

    for fb in task_b_files:
        full_b = os.path.join(project_root, fb)
        imports_b = extract_ast_imports(full_b)
        hit = imports_b & mod_names_a
        if hit:
            return True, f"TCAS AST collision: {fb} imports modified module {hit}"

    for fa in task_a_files:
        full_a = os.path.join(project_root, fa)
        imports_a = extract_ast_imports(full_a)
        hit = imports_a & mod_names_b
        if hit:
            return True, f"TCAS AST collision: {fa} imports modified module {hit}"

    return False, ""


def _dot_som_nhat(task, dot_toi_thieu, tasks_theo_dot, project_root="."):
    """The earliest wave from `dot_toi_thieu` on that touches no other task's files (TCAS aware)."""
    dot = dot_toi_thieu
    files = set(task.vung_file)
    while True:
        co_va_cham = False
        for other in tasks_theo_dot.get(dot, []):
            va_cham, ly_do = detect_tcas_collision(other.vung_file, files, project_root)
            if va_cham:
                _log(f"tcas-collision → {task.ma} collisions with {other.ma} ({ly_do}) at wave {dot}")
                co_va_cham = True
                break
        if not co_va_cham:
            break
        dot += 1
    tasks_theo_dot.setdefault(dot, []).append(task)
    return dot


def _chia_dot_theo_phu_thuoc(tasks, phu_thuoc, project_root="."):
    """Topological order: each task sits after the largest wave of the tasks it needs (TCAS aware)."""
    con_lai = {t.ma: t for t in tasks}
    dot_theo_task = {}
    tasks_theo_dot = {}
    while con_lai:
        san_sang = [t for t in con_lai.values()
                    if all(c in dot_theo_task for c in phu_thuoc[t.ma])]
        cat_vong = not san_sang
        if cat_vong:
            _log(f"chia-dot → cut the dependency cycle at {', '.join(sorted(con_lai))}")
            san_sang = list(con_lai.values())
        for t in san_sang:
            nen = max((dot_theo_task.get(c, 0) for c in phu_thuoc[t.ma]), default=0) + 1
            dot_theo_task[t.ma] = _dot_som_nhat(t, nen, tasks_theo_dot, project_root)
            del con_lai[t.ma]
    return dot_theo_task


def _chia_dot_theo_phase(tasks, project_root="."):
    """Old rule: phase order IS dependency order; split files inside each phase (TCAS aware)."""
    dot_theo_task = {}
    nen = 0
    for phase in sorted({t.phase for t in tasks}, key=_khoa_phase):
        trong_phase = [t for t in tasks if t.phase == phase]
        tasks_theo_dot = {}
        for t in trong_phase:
            dot_rel = _dot_som_nhat(t, 1, tasks_theo_dot, project_root)
            dot_theo_task[t.ma] = nen + dot_rel
        nen += max(tasks_theo_dot.keys(), default=0)
    return dot_theo_task


def _khoa_phase(ten):
    so = re.findall(r"\d+", ten)
    return (int(so[0]) if so else 0, ten)


# ------------------------------------------------------------- the map
def duong_ban_do(project, slug):
    return os.path.join(project, "docs", "tdq", "team", f"{slug}.json")


def sha_file(duong_dan):
    h = hashlib.sha256()
    with open(duong_dan, "rb") as f:
        for khoi in iter(lambda: f.read(65536), b""):
            h.update(khoi)
    return h.hexdigest()


def _boi_canh(project, can_ban_do=True):
    """(slug, plan_path, ban_do|None), or raises LoiLuat."""
    state = tdq_state.load(project, heal=False) or {}
    slug = state.get("active_request")
    if not slug:
        raise LoiLuat("No request is open — nothing to assign.")
    rel = state.get("plan_file") or os.path.join("docs", "tdq", "plan", f"{slug}.md")
    plan = rel if os.path.isabs(rel) else os.path.join(project, rel)
    if not os.path.isfile(plan):
        raise LoiLuat(f"Plan not found: {plan}")
    ban_do = None
    duong = duong_ban_do(project, slug)
    if os.path.isfile(duong):
        try:
            with open(duong, encoding="utf-8") as f:
                ban_do = json.load(f)
        except (ValueError, UnicodeDecodeError) as loi:
            raise LoiLuat(f"The assignment map is broken ({duong}): {loi}. "
                          f"Run again: python3 scripts/tdq_team.py assign")
    elif can_ban_do:
        raise LoiLuat("No assignment map yet. Run: "
                      "python3 scripts/tdq_team.py assign")
    if can_ban_do:
        if ban_do is None:
            raise LoiLuat("No assignment map yet. Run: "
                          "python3 scripts/tdq_team.py assign")
        stale, ly_do = kiem_tra_stale(plan, ban_do)
        if stale:
            raise LoiLuat(f"The plan changed after assignment — the map is stale ({ly_do}). "
                          f"Run again: python3 scripts/tdq_team.py assign")
    return slug, plan, ban_do


def _boi_canh_ban_do(project):
    """(slug, plan_path, ban_do) guaranteed non-None ban_do, or raises LoiLuat."""
    slug, plan, ban_do = _boi_canh(project, can_ban_do=True)
    if ban_do is None:
        raise LoiLuat("No assignment map yet. Run: python3 scripts/tdq_team.py assign")
    return slug, plan, ban_do


class LoiLuat(Exception):
    """Rule broken or facts missing — exit 1, with the command that fixes it."""


# ------------------------------------------------------------- sub-commands
def lenh_phan_cong(project, _args):
    slug, plan, _ = _boi_canh(project, can_ban_do=False)
    tasks = doc_plan(plan)
    if not tasks:
        raise LoiLuat(f"The plan holds no readable task: {plan}")
    quyet = {t.ma: quyet_dinh_task(t, tasks) for t in tasks}
    dot = chia_dot(tasks, quyet, project_root=project)
    proj_sha, proj_mode = tinh_sha_projection(tasks)
    ban_do = {
        "slug": slug,
        "plan_file": os.path.relpath(plan, project),
        "plan_sha": sha_file(plan),
        "projection_version": "v1",
        "projection_mode": proj_mode,
        "plan_assignment_sha": proj_sha,
        "tasks": {
            t.ma: {
                "quyet_dinh": quyet[t.ma][0],
                "ly_do": quyet[t.ma][1],
                "vung_file": t.vung_file,
                "dot": dot[t.ma],
                **({} if t.worktree_required else {"worktree_required": False}),
            } for t in tasks
        },
    }
    duong = duong_ban_do(project, slug)
    ghi_ban_do_atomic(duong, ban_do)
    giao = sum(1 for r in ban_do["tasks"].values() if r["quyet_dinh"] == "giao")
    _log(f"assign → {len(tasks)} task(s) · assigned {giao} · kept {len(tasks) - giao} "
         f"· {max(dot.values())} wave(s)")
    print(f"Map: {os.path.relpath(duong, project)}")
    print(f"Assigned to sub-agents: {giao}/{len(tasks)} task(s) · {max(dot.values())} wave(s)")
    for ma, rec in ban_do["tasks"].items():
        if rec["quyet_dinh"] == "tu_lam":
            print(f"  KEPT {ma} — {rec['ly_do']}: {LY_DO_GIU[rec['ly_do']]}")
    for duong_nong, ma_list in _file_nong(tasks):
        _log(f"assign → HOT FILE {duong_nong} touched by {len(ma_list)} task(s)")
        print(f"  HOT FILE {duong_nong} — {len(ma_list)} tasks touch it: "
              f"{', '.join(ma_list)}")
        print("     Suggestion: pull the shared change into ONE task in an earlier wave, "
              "so the rest branch off a settled file.")
    return 0


def _file_nong(tasks):
    """Paths declared by 2+ tasks → [(path, [task codes])], most-touched first.

    Gap H3: worktrees do nothing for a file EVERY branch has to edit (a registry, an index,
    a manifest). Research N3: split the shared change out as its own step, run it first.
    """
    theo_duong = {}
    for t in tasks:
        for duong in t.vung_file:
            theo_duong.setdefault(duong.replace(os.sep, "/"), []).append(t.ma)
    nong = [(d, ma) for d, ma in theo_duong.items() if len(ma) >= 2]
    nong.sort(key=lambda x: (-len(x[1]), x[0]))
    return nong


def lenh_kiem_ke(project, _args):
    _slug, _plan, ban_do = _boi_canh_ban_do(project)
    van_de = []
    for ma, rec in ban_do["tasks"].items():
        if rec.get("quyet_dinh") == "giao":
            # An assigned task with an empty file area is an empty promise: hook [TDQ:TEAM] has
            # nothing to compare, so the leader may edit any file. The cheapest way around the rule.
            if not rec.get("vung_file"):
                van_de.append(f"Assigned: {ma} — recorded as handed to a sub-agent but the file area is "
                              f"EMPTY, the hook can block nobody")
            thieu = [k for k in ("quyet_dinh", "ly_do", "vung_file", "dot")
                     if k not in rec]
            if thieu:
                van_de.append(f"Assigned: {ma} — the record is missing field(s) {', '.join(thieu)}")
            continue
        thieu = [k for k in ("quyet_dinh", "ly_do", "vung_file", "dot") if k not in rec]
        if thieu:
            van_de.append(f"Kept: {ma} — the record is missing field(s) {', '.join(thieu)}")
        if rec.get("quyet_dinh") != "tu_lam":
            van_de.append(f"Kept: {ma} — decision \"{rec.get('quyet_dinh')}\" "
                          f"is not valid (only giao / tu_lam)")
            continue
        ly_do = (rec.get("ly_do") or "").strip()
        if not ly_do:
            van_de.append(f"Kept: {ma} — kept by the leader with NO reason")
        elif ly_do not in LY_DO_GIU:
            van_de.append(f"Kept: {ma} — reason \"{ly_do}\" is not one of the "
                          f"{len(LY_DO_GIU)} groups ({', '.join(sorted(LY_DO_GIU))})")
    tong = len(ban_do["tasks"])
    giao = sum(1 for r in ban_do["tasks"].values() if r.get("quyet_dinh") == "giao")
    _log(f"audit → {giao}/{tong} assigned · {len(van_de)} problem(s)")
    if van_de:
        for dong in van_de:
            _loi(dong)
        _loi("Fix: python3 scripts/tdq_team.py assign (or hand-fix the map to use "
             f"the {len(LY_DO_GIU)} reason groups)")
        return 1
    print(f"Map clean: {giao}/{tong} task(s) assigned to sub-agents.")
    return 0


def _tien_quyet(tasks, phu_thuoc, dot_theo_task):
    """Task code → set of task codes that must be DONE before it is launched.

    The plan declares dependency lines → take them verbatim. An old plan declaring none →
    infer from the wave numbers, keeping the old "wave N finishes before wave N+1" behaviour.
    """
    if any(phu_thuoc.values()):
        return {ma: set(phu_thuoc[ma]) for ma in tasks}
    return {ma: {khac for khac in tasks
                 if dot_theo_task.get(khac, 0) < dot_theo_task.get(ma, 0)}
            for ma in tasks}


def _ly_do_hoan(ma, tien_quyet, tasks, khoa, vung_file):
    """The SPECIFIC reason a task cannot be launched yet, or None when it can."""
    thieu = sorted(c for c in tien_quyet[ma]
                   if c in tasks and not tasks[c].xong)
    if thieu:
        return "waiting on unfinished task(s): " + ", ".join(thieu)
    dung = [d for d in vung_file if d in khoa]
    if dung:
        return "touches a locked area: " + ", ".join(sorted(dung))
    return None


def lenh_cum(project, _args):
    _slug, plan, ban_do = _boi_canh_ban_do(project)
    danh_sach = doc_plan(plan)
    tasks = {t.ma: t for t in danh_sach}
    phu_thuoc = doc_phu_thuoc(danh_sach)
    diem_gang = b_level(danh_sach, phu_thuoc)
    dot_theo_task = {ma: rec.get("dot", 0) for ma, rec in ban_do["tasks"].items()}
    tien_quyet = _tien_quyet(tasks, phu_thuoc, dot_theo_task)

    khoa = {}                               # file → the task holding it
    dang_bay = [ma for ma, t in tasks.items() if t.da_giao]
    for ma in dang_bay:
        for duong in tasks[ma].vung_file:
            khoa[duong] = ma
    con_lai = [ma for ma, rec in ban_do["tasks"].items()
               if rec["quyet_dinh"] == "giao"
               and ma in tasks and not tasks[ma].xong and not tasks[ma].da_giao]
    if not con_lai:
        _log("cum → NO assignable task left")
        print("DONE: no task left to hand to a sub-agent.")
        return 0
    if khoa:
        print("Locked areas: " + ", ".join(
            f"{duong} ({ma})" for duong, ma in sorted(khoa.items())))

    # Critical path first: the task stretching the total the most gets a slot first.
    con_lai.sort(key=lambda ma: (-diem_gang.get(ma, 0), ma))
    phat, hoan, cho_slot = [], [], []
    da_dat = dict(khoa)                     # including files taken in this very round
    for ma in con_lai:
        vung = ban_do["tasks"][ma]["vung_file"]
        ly_do = _ly_do_hoan(ma, tien_quyet, tasks, da_dat, vung)
        if ly_do:
            hoan.append((ma, ly_do))
            continue
        # The cap counts tasks still in flight: launching round after round while counting
        # only this round would open 4 more branches every time, making the cap moot.
        if len(dang_bay) + len(phat) >= TRAN_SONG_SONG:
            _log(f"cum → {ma} is ready but hits the {TRAN_SONG_SONG}-branch cap "
                 f"({len(dang_bay)} in flight), waiting for a slot")
            cho_slot.append(ma)
            continue
        phat.append(ma)
        for duong in vung:
            da_dat[duong] = ma

    print(f"Ready: {len(phat)} task(s)")
    for ma in phat:
        print(f"  {ma}  {' '.join(ban_do['tasks'][ma]['vung_file'])}")
    # Say exactly why each task is not launched: the leader must tell "the map missed a
    # task" apart from "the task is legitimately blocked".
    for ma, ly_do in hoan:
        print(f"  HELD {ma} — {ly_do}")
    if cho_slot:
        print(f"  WAITING FOR A SLOT: {len(cho_slot)} task(s) (cap {TRAN_SONG_SONG} branches at "
              f"once, {len(dang_bay)} in flight): " + ", ".join(sorted(cho_slot)))
    _log(f"cum → launch {len(phat)} · hold {len(hoan)} · waiting for a slot {len(cho_slot)}")
    return 0


# ------------------------------------------------------------- git
def _git(cwd, *args, check=True):
    # errors="replace": `git merge-tree` prints object contents to stdout, which may hold
    # non-UTF-8 bytes (a binary file, or a string cut mid-character). On the default the
    # whole `kiem` command dies with UnicodeDecodeError — a failure that only shows up on
    # a real run, never in tests using pure ASCII files.
    proc = None
    for attempt in range(3):
        proc = tdq_ten_lenh.chay_subprocess(["git", "-c", "core.longpaths=true", "-C", cwd, *args], capture_output=True,
                                            encoding="utf-8", text=True, errors="replace", timeout=GIT_TIMEOUT)
        if proc.returncode == 0 or not check:
            return proc
        if attempt < 2 and (args[:1] == ("worktree",) or ".lock" in (proc.stderr or "")):
            time.sleep(0.15 * (attempt + 1))
            continue
        break
    if proc is None:
        raise LoiLuat(f"git {' '.join(args)} could not be run")
    raise LoiLuat(f"git {' '.join(args)} failed ({proc.returncode}): "
                  f"{proc.stderr.strip() or proc.stdout.strip()}")


def _la_repo(project):
    proc = tdq_ten_lenh.chay_subprocess(["git", "-C", project, "rev-parse", "--git-dir"],
                                        capture_output=True,
                                        encoding="utf-8", errors="replace", text=True, timeout=GIT_TIMEOUT)
    return proc.returncode == 0


def _ten_nhanh(slug, ma_task):
    """`tdq/<slug>/<task>` — never starts with a name banned by CLAUDE.md §2."""
    ten = f"tdq/{slug}/{ma_task.lower()}"
    assert not ten.startswith(TEN_CAM)
    return ten


def _nhanh_hien_tai(project):
    ra = _git(project, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    return ra.stdout.strip() if ra.returncode == 0 else ""


def _nhanh_tich_hop(project, slug):
    """The branch every task branch merges into — the REQUEST branch when there is one.

    `tdq-intake` step 3b opens `<loại>/<mô tả>` for the request and records it in state, so
    the team has a branch of its own to gather into and the old middle tier disappears: that
    third branch was what stayed behind as an orphan when a request ended. Only a project
    whose request never opened a branch (no git at intake time, or a plan run by hand) falls
    back to the old integration name, so those runs keep working exactly as before.
    """
    nhanh = (tdq_state.load(project, heal=False) or {}).get("nhanh_request")
    return nhanh or f"tdq/{slug}/tich-hop"


def _thu_muc_goc_worktree(project):
    goc = os.environ.get("TDQ_WORKTREE_DIR") or os.path.join(project, ".tdq-worktrees")
    os.makedirs(goc, exist_ok=True)
    # The directory hides itself from `git status` — no need to touch the user's .gitignore.
    bo_qua = os.path.join(goc, ".gitignore")
    if not os.path.exists(bo_qua):
        with open(bo_qua, "w", encoding="utf-8") as f:
            f.write("*\n")
    return goc


def _duong_worktree(project, slug, ten):
    return os.path.join(_thu_muc_goc_worktree(project), slug, ten)


def _co_nhanh(project, nhanh):
    return _git(project, "rev-parse", "--verify", "--quiet", nhanh,
                check=False).returncode == 0


def _bao_dam_tich_hop(project, slug):
    """(branch, directory the merge runs in) for the branch the wave gathers into.

    The request branch is already checked out in the main working tree — git allows one
    checkout per branch — so the merge runs right there. Any other case keeps a worktree of
    its own, so a merge never lands on the branch the user happens to stand on.
    """
    nhanh = _nhanh_tich_hop(project, slug)
    if _nhanh_hien_tai(project) == nhanh:
        return nhanh, project
    duong = _duong_worktree(project, slug, "tich-hop")
    if not _co_nhanh(project, nhanh):
        _git(project, "branch", nhanh, "HEAD")
        _log(f"created the integration branch {nhanh}")
    if not os.path.isdir(duong):
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        _git(project, "worktree", "add", duong, nhanh)
        _log(f"integration worktree → {duong}")
    return nhanh, duong


# ------------------------------------------------- the worktree ledger, seen from git
def _liet_ke_worktree(project):
    """`git worktree list --porcelain` → [{duong_dan, nhanh, khoa}].

    Read the lock flag here rather than guessing later: a locked worktree that git
    refuses to remove must come back to the user as a reason, not as a raw git error.
    """
    ra = _git(project, "worktree", "list", "--porcelain").stdout
    muc, hien = [], None
    for dong in ra.splitlines():
        if dong.startswith("worktree "):
            hien = {"duong_dan": dong.split(" ", 1)[1], "nhanh": "", "khoa": False}
            muc.append(hien)
        elif hien is None:
            continue
        elif dong.startswith("branch "):
            hien["nhanh"] = dong.split(" ", 1)[1].replace("refs/heads/", "")
        elif dong == "locked" or dong.startswith("locked "):
            hien["khoa"] = True
    return muc


def _khoa_khong(project, duong):
    that = os.path.realpath(duong)
    return any(w["khoa"] for w in _liet_ke_worktree(project)
               if os.path.realpath(w["duong_dan"]) == that)


def _file_ban(duong):
    """Up to 5 paths the cleanup would destroy — enough for the user to recognise them."""
    proc = _git(duong, "status", "--porcelain", check=False)
    return [d[3:].strip() for d in proc.stdout.splitlines()[:5]]


# Ignored files git deletes without a word. These regenerate by themselves, so they are
# not worth blocking a cleanup over; anything else ignored is data we cannot judge, and
# unknown data is never deleted on the user's behalf.
RAC_SINH_LAI = ("__pycache__", ".pytest_cache", ".DS_Store", ".venv", "node_modules",
                ".mypy_cache", ".ruff_cache")


def _file_bo_qua_dang_ke(duong):
    """Ignored files that do NOT regenerate — `.env`, local keys, scratch data.

    `git worktree remove` deletes them silently, with or without --force, so they have to
    be caught here or they are gone for good.
    """
    proc = _git(duong, "status", "--porcelain", "--ignored=matching", check=False)
    ra = []
    for dong in proc.stdout.splitlines():
        if not dong.startswith("!! "):
            continue
        ten = dong[3:].strip()
        if not any(phan in ten for phan in RAC_SINH_LAI):
            ra.append(ten)
    return ra[:5]


def _sach(duong):
    proc = _git(duong, "status", "--porcelain", check=False)
    return (proc.returncode == 0 and not proc.stdout.strip()
            and not _file_bo_qua_dang_ke(duong))


def _thay_doi_da_theo_doi(project):
    """Tracked files changed in the working tree or the index, as git prints them.

    Untracked files are deliberately NOT counted: a TDQ run always carries some (the plan,
    `state.json`, the working log), and a merge neither commits nor overwrites them — git
    refuses on its own if it would. What must block is a TRACKED change, because
    `merge --no-ff` commits whatever is staged along with the merge.
    """
    ra = _git(project, "status", "--porcelain", check=False)
    dong = [d for d in ra.stdout.splitlines() if d[:2] != "??"]
    return "\n".join(dong)


def _da_merge(project, nhanh, tich_hop):
    """Every commit of the branch already lives in the integration branch."""
    if not _co_nhanh(project, tich_hop):
        return False
    return _git(project, "merge-base", "--is-ancestor", nhanh, tich_hop,
                check=False).returncode == 0


def _ly_do_chan_thu_muc(project, ma_task, nhanh, duong):
    """Reasons that make deleting the DIRECTORY unsafe. The merge state is not one of them.

    Split out of `_ly_do_chan` because two callers only ever remove the directory and keep
    the branch: the legacy `don`, and the rows `soat` finds with no ledger entry.
    """
    chung = {"ma_task": ma_task, "duong_dan": duong, "nhanh": nhanh}
    if _khoa_khong(project, duong):
        return dict(chung, ly_do="khoa")
    proc = _git(duong, "status", "--porcelain", check=False)
    if proc.returncode != 0 or proc.stdout.strip():
        return dict(chung, ly_do="ban", chi_tiet=", ".join(_file_ban(duong)))
    # Kept apart from `ban`: the way out is a different command, and calling an ignored
    # `build/` directory "uncommitted changes" sends the user after options that no-op.
    bo_qua = _file_bo_qua_dang_ke(duong)
    if bo_qua:
        return dict(chung, ly_do="bo-qua", chi_tiet=", ".join(bo_qua))
    return None


def _ly_do_chan(project, ma_task, nhanh, duong, tich_hop):
    """The three conditions for deleting. Returns None when all three hold.

    Deleting a worktree destroys work that exists nowhere else, so this stays a
    whitelist: anything not proven safe is a reason to keep and to ask.
    """
    chan = _ly_do_chan_thu_muc(project, ma_task, nhanh, duong)
    if chan is not None:
        return chan
    if _co_nhanh(project, nhanh) and not _da_merge(project, nhanh, tich_hop):
        return {"ma_task": ma_task, "duong_dan": duong, "nhanh": nhanh,
                "ly_do": "chua-merge"}
    return None


def _ly_do_tu_choi(project, ma_task, nhanh, duong, loi):
    """Turn git's refusal into a blocking reason — `khoa` ONLY when it really is locked.

    A permission error labelled "locked" sends the user to `worktree unlock`, which cannot
    fix it. The wrong label is worse than a generic one: it costs a command that no-ops.
    """
    return {"ma_task": ma_task, "duong_dan": duong, "nhanh": nhanh,
            "ly_do": "khoa" if _khoa_khong(project, duong) else "git-tu-choi",
            "chi_tiet": loi}


def _go_thu_muc(project, duong):
    """Remove one worktree directory. Returns None on success, else git's own reason.

    `check=False`: git refusing (a lock set behind our back, a mount held open) must not
    abort the sweep halfway — the whole point of the sweep is the block printed at the end.
    """
    proc = _git(project, "worktree", "remove", duong, check=False)
    if proc.returncode == 0:
        return None
    return (proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["git refused"]


def _thu_don(project, slug, ma_task, nhanh, duong, tich_hop):
    """Try to clean one worktree. Returns None on success, else the suggestion item."""
    chan = _ly_do_chan(project, ma_task, nhanh, duong, tich_hop)
    if chan is not None:
        _log(f"keep {ma_task} — {chan['ly_do']}")
        return chan
    # No --force: `_ly_do_chan` above already proved the worktree is clean, so git's own
    # refusal stays in place as the last safety net instead of being switched off.
    loi = _go_thu_muc(project, duong)
    if loi is not None:
        _log(f"keep {ma_task} — git refused: {loi[0]}")
        return _ly_do_tu_choi(project, ma_task, nhanh, duong, loi[0])
    _git(project, "worktree", "prune")
    # `-D` and not `-d`: `-d` measures against HEAD, which is the user's own branch, not
    # the integration branch. `_da_merge` above already proved the commits are safe.
    if _co_nhanh(project, nhanh) and nhanh != tich_hop:
        _git(project, "branch", "-D", nhanh, check=False)
    so_wt.dong_dong(project, slug, ma_task, "merged")
    _log(f"cleaned {ma_task} → worktree {duong} + branch {nhanh} removed")
    return None


def _in_goi_y(muc):
    """The suggestion block is the LAST thing printed — it is what the user must act on."""
    khoi = so_wt.khoi_goi_y(muc)
    if khoi:
        print(khoi)


def _tao_ntfs_junction_sharing(project_dir, worktree_dir):
    """Link heavy dependencies (.venv, node_modules) via NTFS Junction on Windows 11."""
    if sys.platform != "win32":
        return []
    try:
        proj_drive = os.path.splitdrive(os.path.abspath(project_dir))[0].upper()
        wt_drive = os.path.splitdrive(os.path.abspath(worktree_dir))[0].upper()
        if proj_drive != wt_drive:
            return []

        targets = ["node_modules", ".venv"]
        linked = []
        for tgt in targets:
            src = os.path.join(project_dir, tgt)
            dst = os.path.join(worktree_dir, tgt)
            if os.path.isdir(src) and not os.path.exists(dst):
                res = tdq_ten_lenh.chay_subprocess(
                    ["cmd.exe", "/c", "mklink", "/J", os.path.abspath(dst), os.path.abspath(src)],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    text=True,
                    timeout=10,
                )
                if res.returncode == 0:
                    linked.append(tgt)
        return linked
    except Exception:
        return []


def lenh_mo(project, args):
    slug, plan, ban_do = _boi_canh_ban_do(project)
    ma = args.task
    if ma not in ban_do["tasks"]:
        raise LoiLuat(f"The map holds no task {ma}.")
    rec = ban_do["tasks"][ma]
    if rec["quyet_dinh"] != "giao":
        raise LoiLuat(f"{ma} is marked tu_lam ({rec['ly_do']}) — no branch is opened. "
                      f"The leader does this task itself.")
    if rec.get("worktree_required") is False:
        _log(f"mo {ma} → no_worktree (artifact-only shard mode)")
        print(f"{ma}: no_worktree (artifact-only shard mode; no branch/worktree opened)")
        return 0
    if not _la_repo(project):
        raise LoiLuat("This directory is not a git repo — no worktree can be opened.")
    tich_hop, _ = _bao_dam_tich_hop(project, slug)
    nhanh = _ten_nhanh(slug, ma)
    duong = _duong_worktree(project, slug, ma.lower())
    if os.path.isdir(duong):
        raise LoiLuat(f"{ma} already has a worktree: {duong}")
    # BEFORE git touches anything: a worktree opened against a ledger that cannot be
    # written is invisible to `soat` and to the qc gate — exactly the orphan this
    # request exists to abolish.
    so_wt.kiem_ghi_duoc(project)
    if not _co_nhanh(project, nhanh):
        _git(project, "branch", nhanh, tich_hop)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    _git(project, "worktree", "add", duong, nhanh)
    # Only AFTER git succeeded: a row written any earlier is a row that lies.
    so_wt.mo_dong(project, slug, ma, nhanh, duong)
    so_wt.ghi_md(project)
    junctions = _tao_ntfs_junction_sharing(project, duong)
    _log(f"mo {ma} → branch {nhanh} · worktree {duong}")
    print(f"{ma}: branch {nhanh}")
    print(f"  worktree: {duong}")
    if junctions:
        print(f"  ntfs junctions: {', '.join(junctions)}")
        _log(f"mo {ma} → ntfs junctions: {', '.join(junctions)}")
    print(f"  file area: {' '.join(rec['vung_file']) or '(not declared)'}")
    print(f"  base: {tich_hop}")
    return 0


def _nhanh_cua(project, slug, ban_do, ten):
    """Accepts a task code or a full branch name, returns the branch name."""
    if ten in ban_do["tasks"]:
        return _ten_nhanh(slug, ten)
    return ten


def _do_xung_dot(project, tich_hop, nhanh):
    """Three-way `git merge-tree`: touches NEITHER the index nor the working tree."""
    base = _git(project, "merge-base", tich_hop, nhanh).stdout.strip()
    proc = _git(project, "merge-tree", base, tich_hop, nhanh, check=False)
    ra = proc.stdout
    xung_dot = proc.returncode != 0 or "<<<<<<<" in ra or "CONFLICT" in ra
    return xung_dot, _file_xung_dot(ra) if xung_dot else []


# `git merge-tree <base> <A> <B>` prints "changed in both" blocks, with the path on the
# `  our  100644 <sha> <path>` line — NOT in the diff shape `+++ b/<path>`. Only take a
# block that really carries a conflict marker, so cleanly merged files are not named.
_KHOI_CA_HAI = re.compile(r"^(?:changed in both|added in both)$", re.M)
_DUONG_DAN = re.compile(r"^\s+(?:base|our|their)\s+\d+\s+[0-9a-f]+\s+(.+)$", re.M)


def _file_xung_dot(ra):
    ten = set()
    for phan in _KHOI_CA_HAI.split(ra)[1:]:
        if "<<<<<<<" in phan or "CONFLICT" in phan:
            ten.update(m.strip() for m in _DUONG_DAN.findall(phan))
    if not ten:                                  # another shape (CONFLICT (content): a/b)
        ten.update(m.strip() for m in re.findall(r"^CONFLICT \(.+?\): (.+)$", ra, re.M))
    return sorted(ten)


def _task_theo_ma(project, ma):
    """The Task of the current plan carrying this code, or None (a full branch name)."""
    _slug, plan, _ = _boi_canh(project, can_ban_do=False)
    for t in doc_plan(plan):
        if t.ma.lower() == str(ma).lower():
            return t
    return None


TOAN_TU_SHELL = ("&&", "||", "|", ">", "<")


def chuan_hoa_lenh_test(lenh):
    """`Test:` của plan → (lệnh chạy được ở máy này, danh sách cảnh báo).

    Mọi plan trong repo viết `Test: python3 -m pytest …`, mà Windows không có tên lệnh `python3`
    trên PATH — dòng test sẽ đỏ vì lý do sai hoàn toàn, và `merge` từ chối một nhánh thực ra lành
    lặn. Đổi đúng token ĐẦU TIÊN sang chính Python đang chạy: chắc chắn tồn tại, chắc chắn cùng
    phiên bản với tiến trình gọi. Mọi dạng khác (`pytest`, `mypython3 x`) giữ nguyên.

    Toán tử shell chỉ CẢNH BÁO chứ không chặn: cú pháp của `cmd.exe` khác `sh`, nhưng nhiều plan
    cũ đang dùng, và từ chối chạy sẽ hỏng chúng.
    """
    canh_bao = []
    phan = lenh.split(" ", 1)
    if phan[0] == "python3":
        # Đường dẫn có dấu cách (rất thường gặp trên Windows: `C:\Program Files\…`) phải bọc
        # nháy, nếu không shell cắt đôi nó thành hai tham số.
        exe = f'"{sys.executable}"' if " " in sys.executable else sys.executable
        lenh = " ".join([exe] + phan[1:])
    if any(t in lenh for t in TOAN_TU_SHELL):
        canh_bao.append(f"dòng `Test:` dùng toán tử shell — cú pháp cmd.exe khác sh: {lenh}")
    return lenh, canh_bao


def chay_test_task(duong, task, timeout=600):
    """Run the task's own check inside its worktree → (exit code, command, output).

    Exit code None means the plan named no command — that is a PLAN defect, not a code one,
    and the caller reports it differently.
    """
    lenh = lay_lenh_test(task)
    if lenh is None:
        return None, None, ""
    lenh, canh_bao = chuan_hoa_lenh_test(lenh)
    for cau in canh_bao:
        _log(f"WARN {cau}")
    proc = tdq_ten_lenh.chay_subprocess(lenh, shell=True, cwd=duong, capture_output=True,
                                         encoding="utf-8", errors="replace", text=True, timeout=timeout)
    return proc.returncode, lenh, (proc.stdout + proc.stderr)


def _kiem_test_cua_task(project, slug, ma, nhanh):
    """Run the task's own check → (reason it failed or None, the command that was run).

    The sub-agent's `TICK-READY` is its own claim; this is the independent verification,
    so nothing unproven reaches the integration branch. Two failures are told apart: the
    plan naming no command (PLAN) and the command coming back red (CODE).
    """
    task = _task_theo_ma(project, ma)
    if task is None:                       # a raw branch name, no task line to read
        return None, None
    duong = _duong_worktree(project, slug, str(ma).lower())
    ma_thoat, lenh, ra = chay_test_task(duong, task)
    if ma_thoat is None:
        _log(f"check {nhanh} → PLAN error, no test command")
        _loi(f"PLAN error at {task.ma}: the `Test:` line names no command to run.")
        _loi("Fix: write the check as a command in backticks, then run `check` again.")
        return "plan", None
    if ma_thoat != 0:
        _log(f"check {nhanh} → CODE error, the test is red")
        _loi(f"CODE error at {task.ma}: `{lenh}` exited {ma_thoat} in {duong}.")
        _loi(ra.strip()[-2000:])
        return "code", lenh
    return None, lenh


def lenh_kiem(project, args):
    slug, _plan, ban_do = _boi_canh_ban_do(project)
    if not _la_repo(project):
        raise LoiLuat("This directory is not a git repo.")
    tich_hop = _nhanh_tich_hop(project, slug)
    nhanh = _nhanh_cua(project, slug, ban_do, args.task)
    if not _co_nhanh(project, nhanh):
        raise LoiLuat(f"No branch {nhanh}. Open it first: "
                      f"python3 scripts/tdq_team.py open {args.task}")
    xung_dot, file_dung = _do_xung_dot(project, tich_hop, nhanh)
    _log(f"check {nhanh} → {'CONFLICT' if xung_dot else 'clean'}")
    if xung_dot:
        print(f"CONFLICT: {nhanh} does not merge cleanly into {tich_hop}")
        for duong in file_dung:
            print(f"  {duong}")
        print("How to fix: resolve it inside the task's worktree, then run `kiem` again.")
        return 1
    # The sub-agent's own `TICK-READY` is its own claim. Verify it here instead: run the
    # task's `Test:` inside its worktree, so nothing unproven reaches the integration branch.
    ly_do, lenh = _kiem_test_cua_task(project, slug, args.task, nhanh)
    if ly_do is not None:
        return 1
    if lenh:
        print(f"Test of {args.task} passed: `{lenh}`")
    print(f"Clean: {nhanh} merges into {tich_hop}.")
    return 0


def _rebase_len_tich_hop(project, slug, ma, nhanh, tich_hop):
    """Rebase the task branch onto the integration tip → None on success, the error text else.

    Run inside the task's own worktree: that is where the branch is checked out, and where a
    human can look afterwards. A failing rebase is aborted immediately — a worktree left in
    the middle of a rebase is worse than no rebase at all.
    """
    duong = _duong_worktree(project, slug, str(ma).lower())
    if not os.path.isdir(duong):
        return None                              # nothing checked out to rebase
    if _git(project, "merge-base", "--is-ancestor", tich_hop, nhanh,
            check=False).returncode == 0:
        return None                              # already on top of it
    _git(project, "config", "rerere.enabled", "true")
    proc = _git(duong, "rebase", tich_hop, check=False)
    if proc.returncode != 0:
        _git(duong, "rebase", "--abort", check=False)
        return proc.stdout + proc.stderr
    _log(f"rebase {nhanh} → onto {tich_hop}")
    return None


def lenh_hop(project, args):
    slug, _plan, ban_do = _boi_canh_ban_do(project)
    if not _la_repo(project):
        raise LoiLuat("This directory is not a git repo.")
    tich_hop, duong_tich_hop = _bao_dam_tich_hop(project, slug)
    nhanh = _nhanh_cua(project, slug, ban_do, args.task)
    if not _co_nhanh(project, nhanh):
        raise LoiLuat(f"No branch {nhanh}.")
    # Merging into the request branch means merging into the leader's own working tree. Doing
    # that on top of uncommitted work is how a merge eats changes nobody asked it to touch —
    # the same rule the intake step and the report step follow: stop, name the files, ask.
    ban = _thay_doi_da_theo_doi(project) if duong_tich_hop == project else ""
    if ban:
        raise LoiLuat(
            f"Tracked files are modified, so {nhanh} cannot be merged into {tich_hop} yet — "
            f"`merge --no-ff` would sweep them into the merge commit. Commit or set them "
            f"aside, then run merge again:\n{ban}")
    # Gap H2: the branch was opened at the start of the wave, so by the time the second agent
    # merges, its base is already old. Rebase onto the current integration tip FIRST, in the
    # task's own worktree, so every merge accounts for everything that landed before it.
    loi_rebase = _rebase_len_tich_hop(project, slug, args.task, nhanh, tich_hop)
    if loi_rebase is not None:
        _log(f"merge {nhanh} → BLOCKED by a failed rebase")
        _loi(f"BLOCKED: {nhanh} does not rebase onto {tich_hop} — the rebase was aborted, "
             f"the worktree is back where it was.")
        _loi(loi_rebase.strip()[-2000:])
        _loi(f"Run `python3 scripts/tdq_team.py check {args.task}` once it is settled.")
        _in_goi_y([{"ma_task": args.task, "nhanh": nhanh, "ly_do": "rebase-hong",
                    "duong_dan": _duong_worktree(project, slug, args.task.lower())}])
        return 1
    xung_dot, file_dung = _do_xung_dot(project, tich_hop, nhanh)
    if xung_dot:
        _log(f"merge {nhanh} → BLOCKED by a conflict")
        _loi(f"BLOCKED: {nhanh} conflicts with {tich_hop} at "
             f"{', '.join(file_dung) or '(file unknown)'}.")
        _loi(f"Run `python3 scripts/tdq_team.py check {args.task}` for the detail, "
             f"merge only once it is resolved.")
        _in_goi_y([{"ma_task": args.task, "nhanh": nhanh, "ly_do": "xung-dot",
                    "duong_dan": _duong_worktree(project, slug, args.task.lower())}])
        return 1
    # The branch merges cleanly — but clean is not the same as correct. Verify the task's own
    # test before the integration branch takes a single commit.
    ly_do, _lenh = _kiem_test_cua_task(project, slug, args.task, nhanh)
    if ly_do is not None:
        _log(f"merge {nhanh} → BLOCKED by a red test ({ly_do})")
        _loi(f"BLOCKED: {nhanh} is NOT merged — fix it in the worktree, then run "
             f"`python3 scripts/tdq_team.py check {args.task}` again.")
        _in_goi_y([{"ma_task": args.task, "nhanh": nhanh, "ly_do": f"test-{ly_do}",
                    "duong_dan": _duong_worktree(project, slug, args.task.lower())}])
        return 1
    # rerere: a conflict repeating across waves is remembered with its resolution (research §2).
    _git(project, "config", "rerere.enabled", "true")
    _git(duong_tich_hop, "merge", "--no-ff", "-m",
         f"merge {nhanh} into {tich_hop}", nhanh)
    _log(f"merge {nhanh} → into {tich_hop}")
    print(f"Merged {nhanh} into {tich_hop}.")
    print(f"Gathered on: {tich_hop} ({duong_tich_hop})")
    duong = _duong_worktree(project, slug, args.task.lower())
    if not os.path.isdir(duong):
        so_wt.dong_dong(project, slug, args.task, "bien-mat")
        so_wt.ghi_md(project)
        return 0
    chan = _thu_don(project, slug, args.task, nhanh, duong, tich_hop)
    so_wt.ghi_md(project)
    if chan is None:
        print(f"Cleaned up: worktree removed, branch {nhanh} deleted.")
        return 0
    _in_goi_y([chan])
    return 0


def _kich_thuoc(duong):
    """Bytes on disk. Symlinks are skipped — a link is not the space it points at."""
    tong = 0
    for goc, _thu_muc, ten_file in os.walk(duong):
        for ten in ten_file:
            p = os.path.join(goc, ten)
            if not os.path.islink(p):
                try:
                    tong += os.path.getsize(p)
                except OSError:
                    pass
    return tong


def _doc_mb(byte):
    return byte / (1024 * 1024)


def _tuoi_ngay(tao_luc):
    try:
        return (datetime.now() - datetime.fromisoformat(tao_luc)).days
    except (TypeError, ValueError):
        return 0


def lenh_soat(project, args):
    """Sweep every worktree the ledger knows about, across ALL requests.

    Why across all requests and not just the open one: `don` only ever saw the current
    slug, so a worktree of a finished request could never be reached again — that is the
    exact way disk usage grows without anyone noticing.
    """
    if not _la_repo(project):
        raise LoiLuat("This directory is not a git repo.")
    goc = os.path.realpath(_thu_muc_goc_worktree(project))
    dong = so_wt.dong_mo(project)

    # A row whose directory is gone was cleaned by hand; close it instead of nagging.
    con_lai, da_dong = [], 0
    for ban_ghi in dong:
        duong = ban_ghi.get("duong_dan")
        if duong and os.path.isdir(duong):
            con_lai.append(ban_ghi)
            continue
        # A row with no path can never be acted on, and it would keep the qc gate shut
        # forever. Close it — losing a broken row beats deadlocking the workflow.
        ly_do = "bien-mat" if duong else "thieu-duong-dan"
        so_wt.dong_dong(project, ban_ghi.get("slug"), ban_ghi.get("ma_task"), ly_do)
        da_dong += 1
        print(f"closed row {ban_ghi.get('ma_task')}: {ly_do}")
    if da_dong:
        # Without prune git keeps the dead entry in .git/worktrees and refuses to open
        # the same task again.
        _git(project, "worktree", "prune")

    canh_bao, goi_y, tong_byte = [], [], 0
    print("| Task | Request | Path | Age (days) | Size (MB) | Clean? | Merged? |")
    print("|---|---|---|---|---|---|---|")
    for ban_ghi in con_lai:
        duong, nhanh, slug = ban_ghi["duong_dan"], ban_ghi["nhanh"], ban_ghi["slug"]
        tich_hop = _nhanh_tich_hop(project, slug)
        byte = _kich_thuoc(duong)
        tong_byte += byte
        tuoi = _tuoi_ngay(ban_ghi.get("tao_luc"))
        sach = _sach(duong)
        merged = _da_merge(project, nhanh, tich_hop)
        print(f"| {ban_ghi['ma_task']} | {slug} | {duong} | {tuoi} | "
              f"{_doc_mb(byte):.1f} | {'yes' if sach else 'no'} | "
              f"{'yes' if merged else 'no'} |")
        if tuoi > so_wt.TRAN_TUOI_NGAY:
            canh_bao.append(f"WARNING: {ban_ghi['ma_task']} is {tuoi} days old "
                            f"(threshold {so_wt.TRAN_TUOI_NGAY} days) — clean it up.")
        if args.don:
            chan = _thu_don(project, slug, ban_ghi["ma_task"], nhanh, duong, tich_hop)
            if chan is None:
                print(f"  cleaned: {ban_ghi['ma_task']}")
                tong_byte -= byte
                continue
            goi_y.append(chan)
        else:
            chan = _ly_do_chan(project, ban_ghi["ma_task"], nhanh, duong, tich_hop)
            if chan is not None:
                goi_y.append(chan)
    if not con_lai:
        print("(the ledger holds no open worktree)")

    biet = {os.path.realpath(d["duong_dan"]) for d in con_lai if d.get("duong_dan")}
    ngoai, la = [], []
    for w in _liet_ke_worktree(project)[1:]:
        that = os.path.realpath(w["duong_dan"])
        if not that.startswith(goc):
            ngoai.append(w["duong_dan"])
        elif that not in biet:
            la.append(w)
    if la:
        # The integration worktree lands here, and so does anything left behind by an
        # older version of this tool. In scope, so it is cleaned — but only its
        # DIRECTORY: the integration branch is what holds the merged work (decision D5).
        print("")
        print("In scope, no ledger row:")
        for w in la:
            duong = w["duong_dan"]
            print(f"  {duong}")
            if not args.don:
                continue
            chan = _ly_do_chan_thu_muc(project, os.path.basename(duong),
                                       w.get("nhanh", ""), duong)
            if chan is None:
                loi = _go_thu_muc(project, duong)
                if loi is None:
                    print(f"  cleaned: {duong}")
                    continue
                chan = _ly_do_tu_choi(project, os.path.basename(duong),
                                      w.get("nhanh", ""), duong, loi[0])
            goi_y.append(chan)
        _git(project, "worktree", "prune")
    if ngoai:
        print("")
        print("Out of scope (listed only, never removed — they live outside "
              f"{goc}):")
        for duong in ngoai:
            print(f"  {duong}")

    if _doc_mb(tong_byte) > so_wt.TRAN_TONG_MB:
        canh_bao.append(f"WARNING: worktrees take {_doc_mb(tong_byte):.0f} MB "
                        f"(threshold {so_wt.TRAN_TONG_MB} MB) — clean them up.")
    so_wt.ghi_md(project)
    _log(f"sweep → {len(con_lai)} open · {_doc_mb(tong_byte):.1f} MB · "
         f"{len(goi_y)} kept back")
    for dong_canh in canh_bao:
        print(dong_canh)
    _in_goi_y(goi_y)
    # Spec §2 output 4: a dirty worktree exits non-zero. Not merged yet is a normal state
    # of a running wave, so it is reported without failing the command.
    return 1 if any(m["ly_do"] in ("ban", "bo-qua") for m in goi_y) else 0


def lenh_don(project, args):
    slug, _plan, _ban_do = _boi_canh(project, can_ban_do=False)
    if not _la_repo(project):
        raise LoiLuat("This directory is not a git repo.")
    task = getattr(args, "task", None)
    if task:
        duong = _duong_worktree(project, slug, task.lower())
        nhanh = _ten_nhanh(slug, task)
        tich_hop = _nhanh_tich_hop(project, slug)
        if not os.path.isdir(duong):
            so_wt.dong_dong(project, slug, task, "bien-mat")
            so_wt.ghi_md(project)
            print(f"Worktree for {task} already cleaned.")
            _log(f"clean {task} → already cleaned")
            return 0
        chan = _thu_don(project, slug, task, nhanh, duong, tich_hop)
        so_wt.ghi_md(project)
        if chan is not None:
            _in_goi_y([chan])
            return 1
        print(f"Removed worktree of {task}, pruned.")
        return 0
    goc = os.path.join(_thu_muc_goc_worktree(project), slug)
    ra = _git(project, "worktree", "list", "--porcelain").stdout
    duong_list = [d.split(" ", 1)[1] for d in ra.splitlines() if d.startswith("worktree ")]
    da_go = 0
    # realpath on both sides: on macOS `/var` is a symlink of `/private/var`, so comparing
    # by abspath misses and `don` silently removes nothing.
    goc_that = os.path.realpath(goc)
    giu = []
    for duong in duong_list:
        if os.path.realpath(duong).startswith(goc_that):
            # An end-of-wave cleanup must never be the thing that eats work nobody
            # committed yet: keep it, name it, let the user decide.
            chan = _ly_do_chan_thu_muc(project, os.path.basename(duong), "", duong)
            if chan is not None:
                giu.append(chan)
                continue
            # `git worktree remove`, NOT `rm -rf`: deleting by hand leaves junk in
            # .git/worktrees and git still thinks the worktree is alive (research §2).
            loi = _go_thu_muc(project, duong)
            if loi is not None:
                giu.append(_ly_do_tu_choi(project, os.path.basename(duong), "",
                                          duong, loi[0]))
                continue
            da_go += 1
    _git(project, "worktree", "prune")
    _log(f"clean → removed {da_go} worktree(s), kept {len(giu)}")
    print(f"Removed {da_go} worktree(s) of {slug}, pruned.")
    _in_goi_y(giu)
    return 0


# ------------------------------------------- anti rule-bending (used by the hook)

# Which run modes hand work to a TEAM of branches. Declared explicitly, one line
# per mode, rather than inferred from `!= "subagent"`: mode `codex` also hands
# work away, but to one external agent while the leader stays on the main branch,
# so the anti-rule-bending warning does not apply to it. That "does not apply" has
# to be a line a reader can find, not a side effect of a string comparison.
MODE_QUA_DOI = {
    "main": False,
    "subagent": True,
    "codex": False,
}


def kiem_bang_qua_doi(valid_modes, bang):
    """A mode nobody declared would silently inherit `False` from `.get` and lose
    the warning without anyone noticing. Fail at load time, naming the mode."""
    thieu = [m for m in valid_modes if m not in bang]
    if thieu:
        raise RuntimeError(
            "MODE_QUA_DOI thiếu khai cho mode: " + ", ".join(thieu)  # i18n-allow
            + " — mỗi mode trong VALID_MODES phải khai đi qua đội hay không.")  # i18n-allow
    return True


kiem_bang_qua_doi(tdq_state.VALID_MODES, MODE_QUA_DOI)


def canh_bao_lach_luat(cwd, rel_target):
    """The user picked team mode but the leader types code of a task it promised away → warn.

    Returns None when there is nothing to say. Returns dict {kieu, ma, nhanh} on a finding.
    This function is the ONLY place deciding "is the rule being bent" — the hook only prints.
    Only inspected when: phase implement + a mode declared in MODE_QUA_DOI as going
    through a team + the file sits in the area of a task recorded as `giao` that has
    no branch of its own yet.
    """
    try:
        state = tdq_state.load(cwd, heal=False) or {}
        if tdq_state.effective_phase(state, warn=False) != "implement":
            return None
        mode = tdq_state.effective_mode(state, warn=False)
        if not mode or not MODE_QUA_DOI.get(mode):
            return None
        slug = state.get("active_request")
        if not slug:
            return None
        rel = state.get("plan_file") or os.path.join("docs", "tdq", "plan", f"{slug}.md")
        plan = rel if os.path.isabs(rel) else os.path.join(cwd, rel)
        if not os.path.isfile(plan):
            return None
        duong = duong_ban_do(cwd, slug)
        if not os.path.isfile(duong):
            return {"kieu": "chua-phan-cong", "ma": None, "nhanh": None}
        try:
            with open(duong, encoding="utf-8") as f:
                ban_do = json.load(f)
        except (ValueError, UnicodeDecodeError):
            # A map that cannot be read = nobody can prove this task was assigned or kept.
            # Failing open here throws wide the very door the map exists to guard.
            return {"kieu": "ban-do-hong", "ma": None, "nhanh": None}
        if not isinstance(ban_do, dict) or not isinstance(ban_do.get("tasks"), dict):
            return {"kieu": "ban-do-hong", "ma": None, "nhanh": None}
        stale, _ly_do = kiem_tra_stale(plan, ban_do)
        if stale:
            return {"kieu": "chua-phan-cong", "ma": None, "nhanh": None}
        muc_tieu = rel_target.replace(os.sep, "/")
        tasks = {t.ma: t for t in doc_plan(plan)}
        for ma, rec in ban_do.get("tasks", {}).items():
            if muc_tieu not in [d.replace(os.sep, "/") for d in rec.get("vung_file", [])]:
                continue
            if rec.get("quyet_dinh") != "giao":
                return None                      # the leader legitimately kept this task
            t = tasks.get(ma)
            if t is not None and t.xong:
                return None                      # already merged; editing on is the leader's job
            if rec.get("worktree_required") is False and is_artifact_only_paths([muc_tieu]):
                return None                      # no_worktree artifact shard does not open branch
            nhanh = _ten_nhanh(slug, ma)
            if _la_repo(cwd) and _co_nhanh(cwd, nhanh):
                return None                      # the sub-agent already has its own place to work
            return {"kieu": "da-giao-thieu-nhanh" if (t and t.da_giao) else "chua-mo-nhanh",
                    "ma": ma, "nhanh": nhanh}
        return None
    except Exception:
        # This function must never kill the hook — silence is worse than a false block.
        return None


def ngoai_vung_khai(cwd, abs_target):
    """A write from inside a task's worktree, aimed outside that task's `Chạm:`.  # i18n-allow

    Returns None when there is nothing to say — including every write made outside a task
    worktree, so mode `main` never meets this fence. Otherwise {ma, vung_file, duong}.
    Gap H1: `Chạm:` was a hand-written declaration nobody checked, so two agents of one wave  # i18n-allow
    could land on the same undeclared file and only find out at merge time.
    """
    try:
        goc = os.path.realpath(os.environ.get("TDQ_WORKTREE_DIR")
                               or os.path.join(cwd, ".tdq-worktrees"))
        that = os.path.realpath(abs_target)
        if not that.startswith(goc + os.sep):
            return None
        phan = that[len(goc) + 1:].split(os.sep)
        if len(phan) < 3:                       # <slug>/<task>/<path…>
            return None
        slug, ten_wt, duong = phan[0], phan[1], "/".join(phan[2:])
        if ten_wt == "tich-hop":                # the integration worktree owns everything
            return None
        # tests/ is exempt for the same reason the tick gate exempts it: the red step writes
        # a failing test before there is anything to declare.
        if duong.startswith("tests/"):
            return None
        state = tdq_state.load(cwd, heal=False) or {}
        rel = state.get("plan_file") or os.path.join("docs", "tdq", "plan", f"{slug}.md")
        plan = rel if os.path.isabs(rel) else os.path.join(cwd, rel)
        if not os.path.isfile(plan):
            return None
        for t in doc_plan(plan):
            if t.ma.lower() != ten_wt.lower():
                continue
            vung = [d.replace(os.sep, "/") for d in t.vung_file]
            if not vung or duong in vung:
                return None                     # nothing declared = nothing to enforce
            _log(f"gate → {t.ma} writes {duong}, outside its declared area")
            return {"ma": t.ma, "vung_file": vung, "duong": duong}
        return None
    except Exception:
        # Same doctrine as canh_bao_lach_luat: this must never be what kills the hook.
        return None


def lenh_go(project, args):
    """Show what is stuck between the task branch and the integration branch — change nothing.

    Gap H4: until now a conflict only ever produced a refusal. Whoever had to settle it went
    looking by hand. This prints the files and BOTH sides so the decision can be made at once.
    Deliberately read-only: no checkout, no merge, no write into any worktree.
    """
    slug, _plan, ban_do = _boi_canh(project)
    if not _la_repo(project):
        raise LoiLuat("This directory is not a git repo.")
    tich_hop = _nhanh_tich_hop(project, slug)
    nhanh = _nhanh_cua(project, slug, ban_do, args.task)
    if not _co_nhanh(project, nhanh):
        raise LoiLuat(f"No branch {nhanh}. Open it first: "
                      f"python3 scripts/tdq_team.py open {args.task}")
    xung_dot, file_dung = _do_xung_dot(project, tich_hop, nhanh)
    duong_wt = _duong_worktree(project, slug, str(args.task).lower())
    print(f"Branch:      {nhanh}")
    print(f"Integration: {tich_hop}")
    print(f"Worktree:    {duong_wt}")
    if not xung_dot:
        _log(f"resolve {nhanh} → nothing stuck")
        print("Nothing is stuck: this branch merges cleanly.")
        return 0
    _log(f"resolve {nhanh} → {len(file_dung)} file(s) stuck")
    for duong in file_dung:
        print(f"\n=== {duong} ===")
        for ten, phia in ((tich_hop, "integration"), (nhanh, "task branch")):
            noi = _git(project, "show", f"{ten}:{duong}", check=False)
            noi_dung = noi.stdout if noi.returncode == 0 else "(the file does not exist here)"
            print(f"--- {phia} ({ten}) ---")
            print(noi_dung.rstrip()[:4000])
    print("\nNothing was changed. Settle it in the worktree above, then run "
          f"`python3 scripts/tdq_team.py check {args.task}`.")
    return 1


# ------------------------------------------------------------------ packet
MAX_PACKET_INLINE_FILES = 2
MAX_PACKET_SPAN_LINES = 120
PACKET_BOUNDARY_LINES = 3
_LINE_HINT_RE = re.compile(r"(?:\bL|:)(\d+)(?:-L?(\d+))?\b")
_BACKTICK_IDENT = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*(?:\(\))?)`")
_NON_PY_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".rs", ".ps1")
_NON_PY_DECL = re.compile(
    r"^\s*(?:"
    r"(?:export\s+(?:default\s+)?)?(?:async\s+)?(?:function\*?|class|interface|type|const)\s+([A-Za-z_][A-Za-z0-9_-]*)"
    r"|(?:pub(?:\([^)]*\))?\s+)?(?:async\s+|unsafe\s+)?(?:fn|struct|enum|trait|mod|impl(?:\s*<[^>]*>)?)\s+([A-Za-z_][A-Za-z0-9_]*)"
    r")"
)
_HANDOFF_SCHEMA_PATH = os.path.join(
    os.path.dirname(SCRIPTS_DIR), "skills", "tdq-conventions", "references", "handoff-schema.json"
)
_HANDOFF_MAX_NOTES = 1500
_HANDOFF_ALLOWED_STATUS = {"done", "completed", "failed", "blocked"}
_DEFAULT_HANDOFF_REQUIRED = (
    "task_id", "status", "files", "test_result", "branch", "merge_ready", "tick_ready", "notes",
)
_DEFAULT_HANDOFF_PROPS = set(_DEFAULT_HANDOFF_REQUIRED) | {
    "test_verdict", "blocker", "role", "model", "effort", "elapsed_s", "worktree_required",
}


def _slug_from_plan(project, plan, state):
    plan_slug = os.path.splitext(os.path.basename(plan))[0]
    rel_state = state.get("plan_file") or ""
    if not rel_state or not state.get("active_request"):
        return plan_slug
    abs_state = rel_state if os.path.isabs(rel_state) else os.path.join(project, rel_state)
    if os.path.realpath(abs_state) == os.path.realpath(plan):
        return state["active_request"]
    return plan_slug


def _load_ban_do_optional(project, slug):
    duong_map = duong_ban_do(project, slug)
    if not os.path.isfile(duong_map):
        return None
    try:
        with open(duong_map, encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict) and isinstance(loaded.get("tasks"), dict):
            return loaded
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return None


def _resolve_packet_plan(project, args):
    plan_arg = getattr(args, "plan", None)
    state = tdq_state.load(project, heal=False) or {}
    if plan_arg:
        plan = plan_arg if os.path.isabs(plan_arg) else os.path.join(project, plan_arg)
        if not os.path.isfile(plan):
            raise LoiLuat(f"Plan not found: {plan}")
        slug = _slug_from_plan(project, plan, state)
    else:
        slug, plan, _ = _boi_canh(project, can_ban_do=False)
    return slug, plan, _load_ban_do_optional(project, slug)


def _find_packet_task(tasks, task_id, plan_path):
    target = str(task_id)
    for t in tasks:
        if t.ma == target:
            return t
    for t in tasks:
        if t.ma.lower() == target.lower():
            return t
    raise LoiLuat(f"Task {task_id} not found in plan: {plan_path}")


def _wave_from_map(task, tasks_map):
    my_dot = tasks_map[task.ma].get("dot", 1)
    max_dot = max((r.get("dot", 1) for r in tasks_map.values()), default=1)
    peers = []
    for ma, rec in tasks_map.items():
        if rec.get("dot") == my_dot and ma != task.ma and rec.get("quyet_dinh") == "giao":
            peers.append(ma)
    return my_dot, max_dot, peers


def _wave_from_plan(task, tasks):
    quyet = {t.ma: ("giao", "") for t in tasks}
    dots = chia_dot(tasks, quyet)
    my_dot = dots.get(task.ma, 1)
    max_dot = max(dots.values(), default=1)
    peers = [t.ma for t in tasks if dots.get(t.ma) == my_dot and t.ma != task.ma]
    return my_dot, max_dot, peers


def _packet_wave_info(task, tasks, ban_do):
    tasks_map = ban_do.get("tasks", {}) if ban_do else {}
    if task.ma in tasks_map:
        my_dot, max_dot, peers = _wave_from_map(task, tasks_map)
    else:
        my_dot, max_dot, peers = _wave_from_plan(task, tasks)
    peer_text = f"parallel with {', '.join(peers[:4])}" if peers else "sequential"
    return f"wave {my_dot}/{max_dot} · {peer_text}"


def _add_ident_candidates(line, candidates):
    for ident in _BACKTICK_IDENT.findall(line):
        clean = ident[:-2] if ident.endswith("()") else ident
        if clean and clean not in candidates:
            candidates.append(clean)
        if "." in clean:
            tail = clean.split(".")[-1]
            if tail and tail not in candidates:
                candidates.append(tail)


def _extract_symbol_candidates(task):
    candidates = []
    line_hints = []
    for line in task.text:
        _add_ident_candidates(line, candidates)
        for m in _LINE_HINT_RE.finditer(line):
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else start
            line_hints.append((start, end))
    return candidates, line_hints


def _extract_py_signature(lines, node):
    start = node.lineno
    body = getattr(node, "body", None) or []
    body_first = body[0].lineno if body else start + 1
    if body_first <= start:
        raw = lines[start - 1].split(":", 1)[0].strip() + ":"
        return " ".join(raw.split())
    header = " ".join(lines[idx].strip() for idx in range(start - 1, min(body_first - 1, len(lines))))
    header = " ".join(header.split()).replace("( ", "(").replace(" )", ")")
    return header


def _walk_ast_scope(stmts, prefix, lines, out):
    for node in stmts:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        qual = f"{prefix}.{node.name}" if prefix else node.name
        decs = getattr(node, "decorator_list", ())
        start = min([node.lineno] + [d.lineno for d in decs])
        end = getattr(node, "end_lineno", node.lineno) or node.lineno
        is_cls = isinstance(node, ast.ClassDef)
        out.append({
            "name": node.name,
            "qual": qual,
            "start": start,
            "end": end,
            "sig": _extract_py_signature(lines, node),
            "top": not prefix,
            "is_cls": is_cls,
        })
        if is_cls:
            _walk_ast_scope(node.body, qual, lines, out)


def _parse_py_nodes(file_path, lines):
    try:
        tree = ast.parse("\n".join(lines), filename=file_path)
    except SyntaxError:
        return []
    nodes = []
    _walk_ast_scope(tree.body, "", lines, nodes)
    return nodes


def _match_py_by_hints(nodes, line_hints):
    hits = []
    for n in nodes:
        if any(not (n["end"] < hs or n["start"] > he) for hs, he in line_hints):
            hits.append(n)
    non_cls = [n for n in hits if not n["is_cls"]]
    return non_cls or hits


def _dedup_spans(matched):
    spans, seen = [], set()
    for n in matched:
        key = (n["start"], n["end"])
        if key not in seen:
            seen.add(key)
            spans.append((n["qual"], n["start"], n["end"]))
    return spans


def _select_spans_for_py(nodes, total_lines, candidates, line_hints):
    matched = [n for n in nodes if n["name"] in candidates or n["qual"] in candidates]
    if not matched and line_hints:
        matched = _match_py_by_hints(nodes, line_hints)
    if not matched:
        matched = [n for n in nodes if n["top"]][:3]
    return _dedup_spans(matched) or [(None, 1, max(1, total_lines))]


def _build_span_entry(rel_norm, lines, total, sym_name, start, end, force_read_exact):
    span_len = end - start + 1
    if force_read_exact or span_len > MAX_PACKET_SPAN_LINES:
        return {
            "path": rel_norm,
            "symbol": sym_name,
            "start_line": start,
            "end_line": end,
            "mode": "read-exact",
            "directive": f"READ-EXACT: {rel_norm}:{start}-{end}",
        }
    ctx_start = max(1, start - PACKET_BOUNDARY_LINES)
    ctx_end = min(total, end + PACKET_BOUNDARY_LINES)
    snippet = "\n".join(f"{ln:4d}: {lines[ln - 1]}" for ln in range(ctx_start, ctx_end + 1))
    return {
        "path": rel_norm,
        "symbol": sym_name,
        "start_line": start,
        "end_line": end,
        "ctx_start": ctx_start,
        "ctx_end": ctx_end,
        "mode": "inline",
        "content": snippet,
    }


def _match_non_py_decl(raw):
    m = _NON_PY_DECL.match(raw)
    if not m:
        return None
    return m.group(1) or m.group(2)


def _find_brace_block_end(lines, start_idx):
    depth = 0
    seen_brace = False
    limit = min(len(lines), start_idx + MAX_PACKET_SPAN_LINES + 5)
    for idx in range(start_idx, limit):
        text = lines[idx]
        opens = text.count("{")
        closes = text.count("}")
        if opens:
            seen_brace = True
        depth += opens - closes
        if seen_brace and depth <= 0:
            return idx + 1
        if not seen_brace and (idx > start_idx or ";" in text) and idx - start_idx >= 3:
            return idx + 1
    return min(len(lines), start_idx + 1)


def _parse_non_py_nodes(lines):
    nodes = []
    for idx, raw in enumerate(lines):
        name = _match_non_py_decl(raw)
        if not name:
            continue
        start = idx + 1
        end = _find_brace_block_end(lines, idx)
        sig = " ".join(raw.strip().split())
        nodes.append({
            "name": name,
            "qual": name,
            "start": start,
            "end": max(start, end),
            "sig": sig,
            "top": not raw.startswith((" ", "\t")),
            "is_cls": False,
        })
    return nodes


def _render_target_spans(project, task):
    candidates, line_hints = _extract_symbol_candidates(task)
    entries = []
    for idx, rel_path in enumerate(task.vung_file):
        rel_norm = rel_path.replace("\\", "/")
        abs_path = rel_path if os.path.isabs(rel_path) else os.path.join(project, rel_path)
        if not os.path.isfile(abs_path):
            entries.append({"path": rel_norm, "symbol": None, "start_line": 0,
                            "end_line": 0, "mode": "new-file", "content": ""})
            continue
        with open(abs_path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        total = max(1, len(lines))
        if abs_path.endswith(".py"):
            spans = _select_spans_for_py(_parse_py_nodes(abs_path, lines), total, candidates, line_hints)
        elif abs_path.endswith(_NON_PY_EXTENSIONS):
            spans = _select_spans_for_py(_parse_non_py_nodes(lines), total, candidates, line_hints)
        else:
            spans = [(None, 1, total)]
        force_rx = idx >= MAX_PACKET_INLINE_FILES
        for sym_name, start, end in spans:
            entries.append(_build_span_entry(rel_norm, lines, total, sym_name, start, end, force_rx))
    return entries


def _match_ref_signatures(nodes, wanted):
    if wanted:
        sigs = [n["sig"] for n in nodes
                if n["name"] in wanted or n["qual"] in wanted
                or any(n["qual"].endswith("." + w) for w in wanted)]
        if sigs:
            return sigs
    return [n["sig"] for n in nodes if n["top"]][:5]


def _non_py_signatures(lines, wanted):
    sigs = []
    for raw in lines:
        name = _match_non_py_decl(raw)
        if name and (not wanted or name in wanted):
            sigs.append(" ".join(raw.strip().split()))
        if len(sigs) >= 5:
            break
    return sigs


def _extract_ref_signatures(project, task):
    results = []
    for rel_path in task.tham_chieu:
        rel_norm = rel_path.replace("\\", "/")
        abs_path = rel_path if os.path.isabs(rel_path) else os.path.join(project, rel_path)
        wanted = set(task._tham_chieu_syms.get(rel_path, []))
        if not os.path.isfile(abs_path):
            results.append({"path": rel_norm, "signatures": ["(file not found)"]})
            continue
        with open(abs_path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        if abs_path.endswith(".py"):
            sigs = _match_ref_signatures(_parse_py_nodes(abs_path, lines), wanted)
        else:
            sigs = _non_py_signatures(lines, wanted)
        results.append({"path": rel_norm, "signatures": sigs or ["(no signature found)"]})
    return results


def _merge_bullet_cont(all_bullets, section_bullets, in_section, current, stripped):
    merged = current + " " + stripped
    all_bullets[-1] = merged
    if in_section and section_bullets:
        section_bullets[-1] = merged
    return merged


def _parse_kien_truc_bullets(lines):
    in_section = False
    section_bullets, all_bullets = [], []
    current = None
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("## "):
            in_section = stripped.lower().startswith(("## luật gọi", "## invariants"))  # i18n-allow
            current = None
        elif stripped.startswith("- "):
            current = stripped[2:].strip()
            all_bullets.append(current)
            if in_section:
                section_bullets.append(current)
        elif current is not None and stripped and raw.startswith((" ", "\t")):
            current = _merge_bullet_cont(all_bullets, section_bullets, in_section, current, stripped)
        else:
            current = None
    return section_bullets or all_bullets


def _read_kien_truc_invariants(project, task, limit=3):
    path = os.path.join(project, "docs", "kien-truc.md")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as fh:
        bullets = _parse_kien_truc_bullets(fh.read().splitlines())
    tokens = set()
    for rel in task.vung_file + task.sinh_ra + task.tham_chieu:
        norm = rel.replace("\\", "/")
        parts = norm.split("/")
        if len(parts) > 1:
            tokens.add(parts[0] + "/")
        tokens.add(parts[-1])
    scored = []
    for idx, text in enumerate(bullets):
        score = sum(1 for tok in tokens if tok and tok in text)
        scored.append((-score, idx, text))
    scored.sort()
    return [item[2] for item in scored[:limit]]


def _load_handoff_schema(project=None):
    candidates = []
    if project:
        candidates.append(
            os.path.join(project, "skills", "tdq-conventions", "references", "handoff-schema.json")
        )
    candidates.append(_HANDOFF_SCHEMA_PATH)
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if isinstance(loaded, dict):
                    return loaded
            except (OSError, ValueError, UnicodeDecodeError) as exc:
                _log(f"WARN cannot read handoff-schema.json ({path}): {exc}")
    return {
        "required": list(_DEFAULT_HANDOFF_REQUIRED),
        "properties": {k: {} for k in _DEFAULT_HANDOFF_PROPS},
        "additionalProperties": False,
    }


def _check_handoff_field_types(payload, props, errs):
    checks = {
        "task_id": (str, True),
        "status": (str, True),
        "test_result": (str, True),
        "branch": (str, False),
        "notes": (str, False),
        "blocker": (str, False),
        "role": (str, False),
        "model": (str, False),
        "effort": (str, False),
    }
    for key, (typ, non_empty) in checks.items():
        if key not in payload:
            continue
        val = payload[key]
        if not isinstance(val, typ) or (non_empty and not val.strip()):
            errs.append(f"field {key!r} must be a non-empty string" if non_empty else f"field {key!r} must be a string")
    if "files" in payload:
        files = payload["files"]
        if not isinstance(files, list) or not all(isinstance(x, str) for x in files):
            errs.append("field 'files' must be a list of strings")
    for bkey in ("merge_ready", "tick_ready", "worktree_required"):
        if bkey in payload and not isinstance(payload[bkey], bool):
            errs.append(f"field {bkey!r} must be a boolean")
    if "elapsed_s" in payload:
        ev = payload["elapsed_s"]
        if isinstance(ev, bool) or not isinstance(ev, (int, float)) or ev < 0:
            errs.append("field 'elapsed_s' must be a non-negative number")
    allowed = props.get("status", {}).get("enum") or sorted(_HANDOFF_ALLOWED_STATUS)
    if isinstance(payload.get("status"), str) and payload["status"] not in allowed:
        errs.append(f"invalid status {payload['status']!r}; allowed: {', '.join(allowed)}")
    if "test_verdict" in payload:
        verdicts = props.get("test_verdict", {}).get("enum") or ["pass", "fail"]
        tv = payload["test_verdict"]
        if not isinstance(tv, str) or tv not in verdicts:
            errs.append(f"invalid test_verdict {tv!r}; allowed: {', '.join(verdicts)}")


def validate_handoff_payload(payload, project=None):
    """Validate a handoff payload against the unified handoff-schema.json."""
    if not isinstance(payload, dict):
        return False, ["payload must be a JSON object"]
    schema = _load_handoff_schema(project)
    required = schema.get("required") or list(_DEFAULT_HANDOFF_REQUIRED)
    props = schema.get("properties") or {}
    errs = [f"missing required field: {field}" for field in required if field not in payload]
    if schema.get("additionalProperties") is False and props:
        for key in sorted(payload):
            if key not in props:
                errs.append(f"unknown field: {key}")
    _check_handoff_field_types(payload, props, errs)
    max_notes = props.get("notes", {}).get("maxLength", _HANDOFF_MAX_NOTES)
    if isinstance(payload.get("notes"), str) and len(payload["notes"]) > max_notes:
        errs.append(f"notes length {len(payload['notes'])} exceeds maxLength {max_notes}")
    if isinstance(payload.get("blocker"), str) and len(payload["blocker"]) > 500:
        errs.append(f"blocker length {len(payload['blocker'])} exceeds maxLength 500")
    return (len(errs) == 0), errs


def _to_bool_flag(raw):
    text = str(raw).strip().lower()
    if text in ("yes", "true", "1", "co", "ready"):
        return True
    if text in ("no", "false", "0", "khong", "none"):
        return False
    return None


def _normalize_handoff_dict(raw):
    data = dict(raw)
    if "files" not in data and "modified_files" in data:
        data["files"] = data.pop("modified_files")
    if "notes" not in data and "summary" in data:
        data["notes"] = data.pop("summary")
    if "test_result" not in data:
        cmd = str(data.pop("test_command", "") or "").strip()
        verdict = str(data.get("test_verdict", "") or "").strip()
        if cmd or verdict:
            data["test_result"] = f"{cmd} -> {verdict}".strip(" ->")
    if isinstance(data.get("status"), str):
        data["status"] = data["status"].strip().lower()
    return data


def _extract_json_handoff(raw_text):
    stripped = raw_text.strip()
    candidates = [stripped]
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if m:
        candidates.insert(0, m.group(1))
    for blob in candidates:
        if not blob.startswith("{"):
            continue
        try:
            obj = json.loads(blob)
            if isinstance(obj, dict):
                return _normalize_handoff_dict(obj)
        except ValueError:
            continue
    return None


def _apply_handoff_kv(out, key, val):
    k = key.strip().upper().replace("_", "-")
    v = val.strip()
    if k in ("TASK", "TASK-ID"):
        out["task_id"] = v
    elif k == "STATUS":
        out["status"] = v.lower()
    elif k == "FILES":
        items = [p.strip() for p in v.split(",") if p.strip()]
        out["files"] = [] if items == ["(none)"] else items
    elif k in ("TEST", "TEST-RESULT"):
        out["test_result"] = v
    elif k == "BRANCH":
        parts = [seg.strip() for seg in v.split("|")]
        out["branch"] = parts[0]
        for seg in parts[1:]:
            if ":" in seg:
                sk, sv = seg.split(":", 1)
                _apply_handoff_kv(out, sk, sv)
    elif k == "MERGE-READY":
        b = _to_bool_flag(v)
        out["merge_ready"] = v if b is None else b
    elif k == "TICK-READY":
        b = _to_bool_flag(v)
        out["tick_ready"] = v if b is None else b
    elif k == "WORKTREE-REQUIRED":
        b = _to_bool_flag(v)
        out["worktree_required"] = v if b is None else b
    elif k == "NOTES":
        out["notes"] = v
    elif k == "BLOCKER":
        out["blocker"] = v
    elif k in ("ROLE", "MODEL", "EFFORT"):
        out[k.lower()] = v


def parse_handoff_from_text(raw_text):
    """Parse either a JSON block or a 7-line digest handoff message into a normalized dict."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}
    as_json = _extract_json_handoff(raw_text)
    if as_json is not None:
        return as_json
    out = {}
    last_key = None
    for line in raw_text.splitlines():
        m = re.match(r"^\s*([A-Za-z_-]+)\s*:\s*(.*)$", line)
        if m and m.group(1).upper().replace("_", "-") in {
            "TASK", "TASK-ID", "STATUS", "FILES", "TEST", "TEST-RESULT",
            "BRANCH", "MERGE-READY", "TICK-READY", "WORKTREE-REQUIRED", "NOTES", "BLOCKER",
            "ROLE", "MODEL", "EFFORT",
        }:
            last_key = m.group(1).upper().replace("_", "-")
            _apply_handoff_kv(out, last_key, m.group(2))
        elif last_key == "NOTES" and line.strip():
            out["notes"] = (out.get("notes", "") + "\n" + line.strip()).strip()
    return out


def _active_slug_or_default(project, slug=None):
    if slug:
        return slug
    state = tdq_state.load(project, heal=False) or {}
    return state.get("active_request") or "default"


def blackboard_path(project, slug):
    return os.path.join(project, ".tdq-runtime", "blackboard", f"{slug}.json")


def blackboard_read(project, slug=None):
    """Read shared blackboard JSON for the request, returning an empty structure if absent."""
    resolved = _active_slug_or_default(project, slug)
    path = blackboard_path(project, resolved)
    if not os.path.isfile(path):
        return {"slug": resolved, "entries": [], "updated_at": ""}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("entries"), list):
            return data
        _log(f"WARN invalid blackboard format in {path}")
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        _log(f"WARN failed to read blackboard {path}: {exc}")
    return {"slug": resolved, "entries": [], "updated_at": "", "corrupt": True}


@contextlib.contextmanager
def _ntfs_lock(lock_path, timeout_s=5.0):
    """Cross-platform non-blocking polling lock for NTFS/POSIX JSONL writes."""
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    deadline = time.monotonic() + timeout_s
    if sys.platform != "win32":
        fd = None
        while fd is None:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Lock timeout on {lock_path}")
                time.sleep(0.01)
        try:
            yield
        finally:
            os.close(fd)
            try:
                os.unlink(lock_path)
            except OSError:
                pass
        return
    import msvcrt
    fh = open(lock_path, "a+b")
    acquired = False
    try:
        while not acquired:
            try:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                acquired = True
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Lock timeout on {lock_path}")
                time.sleep(0.01)
        yield
    finally:
        if acquired:
            try:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        fh.close()


def _atomic_write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tdq_", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def blackboard_record(
    project,
    task_id,
    status,
    summary,
    *,
    slug=None,
    role="unknown",
    model="",
    files=None,
    error="",
    test_command="",
    root_cause="",
):
    """Append a structured handoff/diagnostic entry to .tdq-runtime/blackboard/<slug>.json."""
    resolved = _active_slug_or_default(project, slug)
    path = blackboard_path(project, resolved)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {
        "task_id": str(task_id),
        "role": str(role or "unknown"),
        "status": str(status),
        "summary": str(summary)[:500],
        "error": str(error)[:500],
        "root_cause": str(root_cause)[:300],
        "files": list(files or []),
        "model": str(model or ""),
        "test_command": str(test_command or ""),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    with _ntfs_lock(path + ".lock"):
        board = blackboard_read(project, resolved)
        board.pop("corrupt", None)
        board.setdefault("entries", []).append(entry)
        board["updated_at"] = entry["timestamp"]
        _atomic_write_text(path, json.dumps(board, ensure_ascii=False, indent=2) + "\n")
    _log(f"blackboard record slug={resolved} task={task_id} status={status}")
    return entry


def suggest_escalation(project, slug, task_id, max_retries=None):
    """Return auto-escalation hint when failed/blocked attempts meet auto_escalate_retries."""
    cfg = tdq_config.load_config(cwd=project)
    agents_cfg = cfg.get("agents") if isinstance(cfg.get("agents"), dict) else {}
    threshold = max_retries if isinstance(max_retries, int) and max_retries > 0 else int(
        agents_cfg.get("auto_escalate_retries", tdq_config.DEFAULT_AUTO_ESCALATE_RETRIES) or 2
    )
    board = blackboard_read(project, slug)
    failures = [
        e for e in board.get("entries", [])
        if str(e.get("task_id", "")).upper() == str(task_id).upper()
        and str(e.get("status", "")).lower() in ("failed", "blocked")
    ]
    if len(failures) < threshold:
        return None
    tier_info = tdq_config.resolve_model_for_role(
        "tdq-build-resolver", attempt=len(failures) + 1, cwd=project
    )
    return {
        "task_id": task_id,
        "failures": len(failures),
        "threshold": threshold,
        "recommended_agent": "tdq-build-resolver",
        "recommended_tier": tier_info.get("tier"),
        "recommended_model": tier_info.get("recommended_swarm_model") or tier_info.get("invoke_model"),
        "last_error": failures[-1].get("error") or failures[-1].get("summary", ""),
    }


_MINI_SPEC_OTHER_KEYS = (
    "chạm:", "cần:", "dùng:", "tham chiếu:", "giao tiếp:",
    "neo & công cụ:", "trước → sau:", "sinh ra:", "tiến độ inline:",
)


def _split_req_giu_nguyen(req_part):
    low = req_part.lower()
    for sep in ("ngoài phạm vi:", "giữ nguyên:"):
        if sep in low:
            idx = low.index(sep)
            return req_part[:idx].rstrip(" ·").strip(), req_part[idx + len(sep):].strip()
    return req_part, ""


def _extract_mini_spec_fields(task):
    fields = {"req": "", "giu_nguyen": "", "ears": "", "logic": "", "ca_goc": ""}
    logic_lines = []
    in_logic = False
    for line in task.text[1:]:
        raw_stripped = line.strip()
        body = raw_stripped[2:].strip() if raw_stripped.startswith("- ") else raw_stripped
        low = body.lower()
        if low.startswith("req:"):
            in_logic = False
            req, giu = _split_req_giu_nguyen(body[4:].strip())
            fields["req"] = req
            if giu:
                fields["giu_nguyen"] = giu
        elif low.startswith(("ngoài phạm vi:", "giữ nguyên:")):
            in_logic = False
            fields["giu_nguyen"] = body.split(":", 1)[1].strip()
        elif low.startswith(("tiêu chí chấp nhận", "ears:")):
            in_logic = False
            fields["ears"] = body.split(":", 1)[1].strip()
        elif low.startswith("logic cốt lõi:"):
            in_logic = True
            val = body.split(":", 1)[1].strip()
            if val:
                logic_lines.append(val)
        elif low.startswith("ca góc hiểm"):
            in_logic = False
            fields["ca_goc"] = body.split(":", 1)[1].strip()
        elif raw_stripped.startswith("- ") or low.startswith(_MINI_SPEC_OTHER_KEYS):
            in_logic = False
        elif in_logic and body:
            logic_lines.append(body)
    fields["logic"] = " ".join(logic_lines).strip()
    vung = ", ".join(task.vung_file) if task.vung_file else "(none declared)"
    fields["ranh_gioi"] = "; ".join(p for p in (fields["giu_nguyen"], f"Chỉ sửa {vung}") if p)
    cmd = lay_lenh_test(task) or "(none declared)"
    fields["tu_kiem"] = "; ".join(p for p in (fields["ca_goc"], f"Test: {cmd}") if p)
    return fields


def _build_packet_payload(project, slug, task, tasks, ban_do):
    goc = os.environ.get("TDQ_WORKTREE_DIR") or os.path.join(project, ".tdq-worktrees")
    wt_dir = (
        os.path.join(goc, slug, task.ma.lower())
        if task.worktree_required
        else "(no_worktree — root cwd, write ONLY artifact shards)"
    )
    base_branch = _nhanh_tich_hop(project, slug)
    files_str = ", ".join(task.vung_file) if task.vung_file else "(none declared)"
    task_head = task.text[0] if task.text else ""
    mini_spec = _extract_mini_spec_fields(task)
    board = blackboard_read(project, slug)
    failures = [
        e for e in board.get("entries", [])
        if str(e.get("task_id", "")).upper() == task.ma.upper()
        and str(e.get("status", "")).lower() in ("failed", "blocked")
    ][-3:]
    escalation = suggest_escalation(project, slug, task.ma)
    prompt_fields = {
        "TASK": f"{task.ma} — {task_head}",
        "CỤM": _packet_wave_info(task, tasks, ban_do),  # i18n-allow
        "BASE": base_branch,
        "WORKTREE": wt_dir,
        "VÙNG FILE": f"{files_str} — DO NOT edit files outside this list",  # i18n-allow
        "TEST": lay_lenh_test(task) or "(none declared)",
        "TRẢ VỀ": "exact 7-line format (TASK/STATUS/FILES/TEST/BRANCH/MERGE-READY/TICK-READY/NOTES, <= 1,500 chars)",  # i18n-allow
    }
    return {
        "task_id": task.ma,
        "worktree_required": bool(task.worktree_required),
        "prompt_fields": prompt_fields,
        "mini_spec": mini_spec,
        "blackboard_failures": failures,
        "escalation_hint": escalation,
        "vung_file": list(task.vung_file),
        "tham_chieu": list(task.tham_chieu),
        "sinh_ra": list(task.sinh_ra),
        "symbol_spans": _render_target_spans(project, task),
        "reference_signatures": _extract_ref_signatures(project, task),
        "invariants": _read_kien_truc_invariants(project, task, limit=3),
    }


def _append_packet_sections(lines, payload):
    for sp in payload["symbol_spans"]:
        if sp["mode"] == "read-exact":
            lines.append(f"- {sp['directive']}")
        elif sp["mode"] == "new-file":
            lines.append(f"- [NEW FILE] `{sp['path']}`")
        else:
            label = f"`{sp['path']}` :: `{sp['symbol']}`" if sp["symbol"] else f"`{sp['path']}`"
            lines.append(f"### {label} (L{sp['start_line']}-L{sp['end_line']}, ctx L{sp['ctx_start']}-L{sp['ctx_end']})")
            lines.extend(["```", sp["content"], "```"])
    if payload["reference_signatures"]:
        lines.extend(["", "## Reference Signatures"])
        for ref in payload["reference_signatures"]:
            lines.extend(f"- `{ref['path']}`: `{sig}`" for sig in ref["signatures"])
    if payload["invariants"]:
        lines.extend(["", "## Architecture Invariants (docs/kien-truc.md)"])
        lines.extend(f"- {inv}" for inv in payload["invariants"])
    failures = payload.get("blackboard_failures") or []
    esc = payload.get("escalation_hint")
    if failures or esc:
        lines.extend(["", "## Blackboard"])
        for item in failures:
            lines.append(f"- [{item.get('timestamp', '')}] {item.get('role')}: {item.get('error') or item.get('summary')}")
        if esc:
            lines.append(
                f"- ESCALATE: {esc['failures']}/{esc['threshold']} fails -> use {esc['recommended_agent']} ({esc['recommended_model']})"
            )


def _format_packet_md(payload):
    pf = payload["prompt_fields"]
    ms = payload.get("mini_spec") or {}
    lines = [
        f"TASK: {pf['TASK']}",
        f"CỤM: {pf['CỤM']}",  # i18n-allow
        f"BASE: {pf['BASE']}",
        f"WORKTREE: {pf['WORKTREE']}",
        f"VÙNG FILE: {pf['VÙNG FILE']}",  # i18n-allow
        f"TEST: {pf['TEST']}",
        f"TRẢ VỀ: {pf['TRẢ VỀ']}",  # i18n-allow
        "",
        "## Mini-Spec",
        f"- Req: {ms.get('req') or '(none)'}",
        f"- GIỮ NGUYÊN: {ms.get('giu_nguyen') or '(none)'}",  # i18n-allow
        f"- EARS: {ms.get('ears') or '(none)'}",
        f"- Logic cốt lõi: {ms.get('logic') or '(none)'}",  # i18n-allow
        f"- RANH GIỚI: {ms.get('ranh_gioi') or '(none)'}",  # i18n-allow
        f"- TỰ KIỂM: {ms.get('tu_kiem') or '(none)'}",  # i18n-allow
        "",
        "## Symbol-Spans",
    ]
    _append_packet_sections(lines, payload)
    return "\n".join(lines)


def lenh_packet(project, args):
    """Build and print a self-contained task dispatch packet (`md` or `json`)."""
    slug, plan_path, ban_do = _resolve_packet_plan(project, args)
    tasks = doc_plan(plan_path)
    if not tasks:
        raise LoiLuat(f"The plan holds no readable task: {plan_path}")
    task = _find_packet_task(tasks, args.task, plan_path)
    payload = _build_packet_payload(project, slug, task, tasks, ban_do)
    fmt = getattr(args, "format", "md") or "md"
    _log(f"packet {task.ma} → files={len(task.vung_file)} refs={len(task.tham_chieu)} format={fmt}")
    if fmt == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(_format_packet_md(payload))
    return 0


def lenh_validate_handoff(project, args):
    """Validate a subagent handoff JSON or 7-line digest against handoff-schema.json."""
    if getattr(args, "file", None):
        if not os.path.isfile(args.file):
            raise LoiLuat(f"Handoff file not found: {args.file}")
        try:
            with open(args.file, encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
        except OSError as exc:
            raise LoiLuat(f"Cannot read handoff file {args.file}: {exc}") from exc
    elif getattr(args, "text", None) is not None:
        raw = args.text
    else:
        raw = sys.stdin.read()
    payload = parse_handoff_from_text(raw)
    ok, errs = validate_handoff_payload(payload, project=project)
    if getattr(args, "json", False):
        print(json.dumps({"ok": ok, "errors": errs, "payload": payload}, ensure_ascii=False, indent=2))
    elif ok:
        print(f"VALID handoff for {payload.get('task_id')} ({payload.get('status')})")
    else:
        for err in errs:
            _loi(f"INVALID handoff: {err}")
    return 0 if ok else 1


def lenh_blackboard(project, args):
    """Read, append, or clear .tdq-runtime/blackboard/<slug>.json."""
    slug = _active_slug_or_default(project, getattr(args, "slug", None))
    action = getattr(args, "action", "read") or "read"
    if action == "record":
        if not args.task or not args.status:
            raise LoiLuat("blackboard record requires --task and --status")
        entry = blackboard_record(
            project,
            args.task,
            args.status,
            args.summary or "",
            slug=slug,
            role=args.role or "unknown",
            model=args.model or "",
            error=args.error or "",
        )
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0
    if action == "clear":
        path = blackboard_path(project, slug)
        if os.path.isfile(path):
            os.remove(path)
        print(f"Cleared blackboard: {path}")
        return 0
    board = blackboard_read(project, slug)
    if args.task:
        board["entries"] = [
            e for e in board.get("entries", [])
            if str(e.get("task_id", "")).upper() == str(args.task).upper()
        ]
    if getattr(args, "json", False):
        print(json.dumps(board, ensure_ascii=False, indent=2))
    else:
        print(f"Blackboard {slug}: {len(board.get('entries', []))} entry(ies)")
        for e in board.get("entries", []):
            print(f"- {e.get('task_id')} [{e.get('status')}] ({e.get('role')}): {e.get('error') or e.get('summary')}")
    return 0


def _evidence_dir(project, slug):
    clean = str(slug or "").strip()
    if not clean or not re.fullmatch(r"[A-Za-z0-9._-]+", clean) or ".." in clean:
        raise LoiLuat(f"Invalid request slug for evidence store: {slug!r}")
    return os.path.join(project, "docs", "tdq", "artifacts", clean)


def _read_text_arg(inline_val, file_path, label):
    if file_path:
        if not os.path.isfile(file_path):
            raise LoiLuat(f"{label} file not found: {file_path}")
        with open(file_path, encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    return str(inline_val or "").strip()


def evidence_add(
    project, *, slug=None, shard="", claim="", claim_file=None, source="",
    excerpt="", excerpt_file=None, confidence="medium", role="unknown", status="confirmed",
):
    """Append one evidence claim atomically to a shard `.ev.jsonl` or `evidence.jsonl`."""
    resolved = _active_slug_or_default(project, slug)
    ev_dir = _evidence_dir(project, resolved)
    claim_txt = _read_text_arg(claim, claim_file, "--claim-file")
    excerpt_txt = _read_text_arg(excerpt, excerpt_file, "--excerpt-file")
    source_txt = str(source or "").strip()
    if not claim_txt or not source_txt:
        raise LoiLuat("evidence add requires non-empty claim (--claim/--claim-file) and --source")
    clean_shard = re.sub(r"[^A-Za-z0-9._-]", "_", str(shard or "").strip())
    target = os.path.join(ev_dir, f"{clean_shard}.ev.jsonl" if clean_shard else "evidence.jsonl")
    os.makedirs(ev_dir, exist_ok=True)
    digest = hashlib.sha256(f"{clean_shard}|{source_txt}|{claim_txt}".encode("utf-8")).hexdigest()[:12]
    row = {
        "id": digest, "ts": datetime.now().isoformat(timespec="seconds"), "shard": clean_shard,
        "role": str(role or "unknown"), "claim": claim_txt, "source": source_txt,
        "excerpt": excerpt_txt, "confidence": str(confidence or "medium"), "status": str(status or "confirmed"),
    }
    with _ntfs_lock(target + ".lock"):
        with open(target, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
    _log(f"evidence add slug={resolved} shard={clean_shard or 'main'} id={digest}")
    return row


def _read_jsonl_rows(path):
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if s:
                out.append(json.loads(s))
    return out


def _md_cell(val):
    return str(val or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def evidence_render(project, *, slug=None, out=None):
    """Render deterministic Markdown table from docs/tdq/artifacts/<slug>/evidence.jsonl."""
    resolved = _active_slug_or_default(project, slug)
    ev_dir = _evidence_dir(project, resolved)
    ev_path = os.path.join(ev_dir, "evidence.jsonl")
    md_path = out or os.path.join(ev_dir, "evidence-log.md")
    with _ntfs_lock(ev_path + ".lock"):
        rows = _read_jsonl_rows(ev_path)
    ordered = sorted(rows, key=lambda r: (str(r.get("shard") or ""), str(r.get("id") or "")))
    lines = [
        f"# Evidence Log — {resolved}", "",
        "| # | ID | Shard | Claim | Source | Confidence |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(ordered, 1):
        lines.append(
            f"| {i} | `{r.get('id', '')}` | `{_md_cell(r.get('shard') or '-')}` "
            f"| {_md_cell(r.get('claim'))} | `{_md_cell(r.get('source'))}` | `{_md_cell(r.get('confidence'))}` |"
        )
    _atomic_write_text(md_path, "\n".join(lines) + "\n")
    _log(f"evidence render slug={resolved} rows={len(ordered)}")
    return md_path


def evidence_merge(project, *, slug=None):
    """Merge all `*.ev.jsonl` shards into `evidence.jsonl` under NTFS lock and render log."""
    resolved = _active_slug_or_default(project, slug)
    ev_dir = _evidence_dir(project, resolved)
    ev_path = os.path.join(ev_dir, "evidence.jsonl")
    os.makedirs(ev_dir, exist_ok=True)
    with _ntfs_lock(ev_path + ".lock"):
        merged, seen = [], set()
        shard_files = sorted(
            os.path.join(ev_dir, fn) for fn in os.listdir(ev_dir) if fn.endswith(".ev.jsonl")
        )
        for src_path in [ev_path] + shard_files:
            for row in _read_jsonl_rows(src_path):
                key = row.get("id") or (row.get("claim"), row.get("source"))
                if key not in seen:
                    seen.add(key)
                    merged.append(row)
        body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in merged)
        _atomic_write_text(ev_path, body)
    md_path = evidence_render(project, slug=resolved)
    _log(f"evidence merge slug={resolved} count={len(merged)} shards={len(shard_files)}")
    return merged, md_path


def lenh_evidence(project, args):
    """CLI handler for `evidence add|merge|render`."""
    slug = _active_slug_or_default(project, getattr(args, "slug", None))
    action = getattr(args, "action", "render") or "render"
    if action == "add":
        row = evidence_add(
            project, slug=slug, shard=getattr(args, "shard", "") or "",
            claim=getattr(args, "claim", "") or "", claim_file=getattr(args, "claim_file", None),
            source=getattr(args, "source", "") or "", excerpt=getattr(args, "excerpt", "") or "",
            excerpt_file=getattr(args, "excerpt_file", None), confidence=getattr(args, "confidence", "medium") or "medium",
            role=getattr(args, "role", "unknown") or "unknown", status=getattr(args, "status", "confirmed") or "confirmed",
        )
        print(json.dumps(row, ensure_ascii=False) if getattr(args, "json", False) else f"Evidence added: {row['id']}")
    elif action == "merge":
        rows, md_path = evidence_merge(project, slug=slug)
        if getattr(args, "json", False):
            print(json.dumps({"slug": slug, "count": len(rows), "md_path": md_path}, ensure_ascii=False))
        else:
            print(f"Evidence merged: {len(rows)} row(s) -> {md_path}")
    else:
        md_path = evidence_render(project, slug=slug, out=getattr(args, "out", None))
        print(json.dumps({"slug": slug, "md_path": md_path}, ensure_ascii=False) if getattr(args, "json", False) else f"Rendered: {md_path}")
    return 0


# ------------------------------------------------------------------ CLI
LENH = {
    "assign": (lenh_phan_cong, "read the whole plan, write the assignment map"),
    "audit": (lenh_kiem_ke, "audit the map: a kept task must cite 1 closed reason"),
    "wave": (lenh_cum, "print the next wave, minus the locked file areas"),
    "open": (lenh_mo, "create a branch + worktree for one task"),
    "check": (lenh_kiem, "probe for conflicts with the integration branch, repo untouched"),
    "merge": (lenh_hop, "merge the task's branch into the integration branch"),
    "sweep": (lenh_soat, "sweep every worktree of every request: age, size, clean, merged"),
    "clean": (lenh_don, "remove the request's worktrees and prune"),
    "resolve": (lenh_go, "show every stuck file with both sides, changing nothing"),
    "packet": (lenh_packet, "build a self-contained task dispatch packet"),
    "validate-handoff": (lenh_validate_handoff, "validate a handoff JSON or 7-line digest against handoff-schema.json"),
    "blackboard": (lenh_blackboard, "read or record shared runtime diagnostics in .tdq-runtime/blackboard"),
    "evidence": (lenh_evidence, "add, merge, or render investigation evidence shards under docs/tdq/artifacts/<slug>/"),
}
BANG_TEN = tdq_ten_lenh.BANG_DOI_TEN["tdq_team.py"]


def build_parser():
    p = argparse.ArgumentParser(
        prog="tdq_team.py",
        description="Team-mode orchestration: the leader assigns, sub-agents run in parallel.")
    sub = p.add_subparsers(dest="lenh")
    for ten, (_ham, mo_ta) in LENH.items():
        con = sub.add_parser(ten, help=mo_ta)
        if ten in ("open", "check", "merge", "resolve"):
            con.add_argument("task", help="task code (T1.1) or the full branch name")
        if ten == "packet":
            con.add_argument("task", help="task code (T1.1)")
            con.add_argument("--plan", default=None, help="path to the plan markdown file")
            con.add_argument("--format", choices=("md", "json"), default="md",
                             help="output format (md or json)")
        if ten == "validate-handoff":
            con.add_argument("--file", default=None, help="path to JSON or text handoff file")
            con.add_argument("--text", default=None, help="raw handoff JSON or 7-line digest string")
            con.add_argument("--json", action="store_true", help="emit JSON verdict output")
        if ten == "blackboard":
            con.add_argument("action", nargs="?", choices=("read", "record", "clear"), default="read")
            con.add_argument("--slug", default=None, help="request slug (default: active_request)")
            con.add_argument("--task", default=None, help="task ID filter or target")
            con.add_argument("--status", default=None, help="entry status (done|failed|blocked)")
            con.add_argument("--summary", default="", help="short status summary")
            con.add_argument("--role", default="unknown", help="agent role name")
            con.add_argument("--model", default="", help="model ID used")
            con.add_argument("--error", default="", help="error diagnostic snippet")
            con.add_argument("--json", action="store_true", help="emit JSON output")
        if ten == "evidence":
            con.add_argument("action", choices=("add", "merge", "render"), help="evidence action")
            con.add_argument("--slug", default=None, help="request slug (default: active_request)")
            con.add_argument("--shard", default="", help="optional worker shard ID (writes <shard>.ev.jsonl)")
            con.add_argument("--claim", default="", help="claim summary text")
            con.add_argument("--claim-file", default=None, help="UTF-8 file path containing claim text")
            con.add_argument("--source", default="", help="file:line or URL+ts citation")
            con.add_argument("--excerpt", default="", help="optional supporting excerpt")
            con.add_argument("--excerpt-file", default=None, help="UTF-8 file path containing excerpt")
            con.add_argument("--confidence", default="medium", choices=("high", "medium", "low"))
            con.add_argument("--role", default="unknown", help="worker role name")
            con.add_argument("--status", default="confirmed", choices=("confirmed", "disputed", "open"))
            con.add_argument("--out", default=None, help="optional output path for render")
            con.add_argument("--json", action="store_true", help="emit JSON output")
        if ten == "clean":
            con.add_argument("task", nargs="?", default=None,
                             help="optional task code (T1.1) or branch name to clean")
        if ten == "sweep":
            con.add_argument("--clean", "--don", dest="don", action="store_true",
                             help="also remove every worktree that passes all 3 conditions")
    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Resolve a hidden alias (`hop` → `merge`) before argparse sees it, so `--help`
    # keeps advertising the English names only.
    if argv and not argv[0].startswith("-"):
        chinh_thuc = tdq_ten_lenh.giai_ten(argv[0], BANG_TEN)
        if chinh_thuc is not None:
            argv[0] = chinh_thuc
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.lenh:
        parser.print_usage(sys.stderr)
        _loi("Missing sub-command. Available: " + " · ".join(LENH))
        return 2
    project = _project_dir()
    _log(f"{args.lenh} · project={project}")
    try:
        return LENH[args.lenh][0](project, args)
    except LoiLuat as exc:
        _loi(str(exc))
        return 1
    except so_wt.LoiSo as exc:
        _loi(f"The worktree ledger is unusable: {exc}")
        _loi("Fix docs/tdq/worktrees.json (or delete it) before opening any worktree.")
        return 1
    except subprocess.TimeoutExpired:
        _loi("git took too long — aborted, nothing else touched.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
