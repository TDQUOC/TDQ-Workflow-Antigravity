#!/usr/bin/env python3
"""Install and prove every dependency the workflow searches with (stdlib only).

One command, four jobs, in this order:
  1. run the ladder of `tdq_lsp.py` and INSTALL what is missing and allowed
  2. check the configuration each layer needs is actually right
  3. re-run `tdq_lsp.kiem_mot_lenh` — the same ladder + three-layer smoke + total line that
     `tdq_lsp.py check` prints — so both commands judge the machine the same way
  4. write down, as debt, everything it could not fix by itself

Exit code: the one `kiem_mot_lenh` returns (0 total ĐẠT, 3 a rung blocks, 4 a layer failed).

Why this file exists next to `tdq_lsp.py` instead of inside it: `tdq_lsp.py` carries a hard
promise — it NEVER installs, it only diagnoses and prints the command. This script is the opposite
half. Since 0.59.0 intake runs it on every request without asking (the user's choice, 2B): it
installs agent-lsp from its release, the language servers, declares a language that appeared since
last time in MCP `lsp`, and stops orphan agent-lsp brokers. Keeping the two promises in two files
is what keeps each one readable.

The consent is not unlimited. A command only runs when it matches the declared allow-list
below; anything else becomes a line of debt, never a silent skip and never a guess.

The CLI also declares the lsp MCP server for Codex (`tdq_codex_mcp.khai_mcp_codex`).

`--nen` is the other mode: the detached background build a SessionStart hook spawns (installs,
graphify graph) under a pid lock, ending in the readiness stamp
`docs/tdq/.tdq-san-sang.json`. See `khoi_tao_nen`.

Env: TDQ_PROJECT_DIR anchors the project; TDQ_LOG=0 silences the log.
"""
import argparse
from contextlib import contextmanager
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import Any, Optional
import urllib.request
import zipfile
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)
import archify_delivery  # noqa: E402
import lsp_module  # noqa: E402
import plugin_tiers  # noqa: E402 — ghi enabledPlugins nguyên tử + .bak
import search_rules  # noqa: E402
import tdq_checkportable  # noqa: E402
import tdq_devtool_mcp  # noqa: E402
import tdq_lsp  # noqa: E402
import tdq_no  # noqa: E402 — hạ tầng ghi nợ dùng chung với tdq_finish.py
import tdq_setup_state  # noqa: E402
import tdq_ten_lenh  # noqa: E402
import utf8_io  # noqa: E402

_FALLBACK_TREE_SITTER_PACKAGES: tuple[str, ...] = (
    "tree-sitter",
    "tree-sitter-python",
    "tree-sitter-javascript",
    "tree-sitter-typescript",
    "tree-sitter-rust",
)

try:
    import archify_registry
except ImportError:
    archify_registry = None

TREE_SITTER_PACKAGES: tuple[str, ...] = getattr(
    archify_registry, "TREE_SITTER_PACKAGES", _FALLBACK_TREE_SITTER_PACKAGES
)

TIMEOUT_CAI = 300
# Trần cho mỗi phép smoke: chúng chạy sau khi cài xong, và không phép nào được treo lệnh setup.
TIMEOUT_SMOKE = 60
# Đuôi của bản sao lưu để lại trước khi chạm vào file của plugin khác — không có nó thì không lùi được.
DUOI_SAO_LUU = ".truoc-tdq.bak"
# Instruction user-level của Claude Code. Đây là file NGOÀI repo, nên mọi thứ ghi vào đó chỉ được
# nằm trong khối có dấu mốc — phần user tự viết không bao giờ bị đụng tới.
DUONG_INSTRUCTION = "~/.claude/CLAUDE.md"

# Danh sách đã khai: một lệnh chỉ được chạy khi nó bắt đầu bằng đúng một trong các tiền tố này.
# Đây là ranh giới của sự cho phép — user gõ `setup` là đồng ý cài PHỤ THUỘC CỦA WORKFLOW, không
# phải đồng ý cho script chạy mọi chuỗi mà một bậc thang in ra.
TIEN_TO_CAI_DUOC = (
    "uv tool install ",
    "brew install ",
    "npm i -g ",
    "npm install -g ",
    "pipx install ",
)

# Không bao giờ chạm python hệ thống của Apple — ràng buộc đứng của user, nhắc lại ở đây vì
# tiền tố ở trên không chặn được một lệnh `pip install` đi qua đúng bản python đó.
DUONG_PYTHON_CAM = ("/usr/bin/python", "/System/Library/Frameworks/Python")
# Ký tự chỉ có nghĩa với shell. Thấy là từ chối: lệnh cài phải là MỘT lệnh, không phải một đoạn
# script — và `_chay_lenh` không có shell để hiểu chúng.
KY_TU_SHELL = (";", "&", "|", "$", "`", "\n", ">", "<")

def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _log_enabled():
    """Một công tắc duy nhất cho cả hai module: `--khong-log` chỉ việc set đúng biến này."""
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message):
    if _log_enabled():
        print(f"[{_now()}] {message}", file=sys.stderr)


def _chay_lenh(lenh):
    """Chạy một lệnh cài -> (rc, đầu ra). KHÔNG dùng shell.

    Bản đầu chạy `shell=True` rồi tự tách chuỗi bằng regex để kiểm từng vế. Đó là viết lại một
    bộ tách lệnh của shell — thứ không bao giờ đúng: nó không thấy xuống dòng, `$(...)`, dấu
    huyền, hay `;` nằm trong nháy. Mà chuỗi lệnh có phần nội suy từ cấu hình của máy
    (trước 0.58.0: `ollama pull {model}` lấy `model` từ `config.yaml`), nên đó là một đường tiêm
    lệnh thật.

    Nay `shlex` tách, `shell=False` chạy: vế nào không phải lệnh thì không có gì chạy nó.
    """
    _log(f"cài: {lenh}")
    try:
        argv = shlex.split(lenh)
    except ValueError as exc:
        return 1, f"không tách được lệnh: {exc}"
    if not argv:
        return 1, "lệnh rỗng"
    try:
        p = tdq_ten_lenh.chay_subprocess(argv, capture_output=True,
                                         encoding="utf-8", errors="replace", text=True, timeout=TIMEOUT_CAI)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, f"quá {TIMEOUT_CAI}s"
    except OSError as exc:
        return 1, str(exc)


def _duoc_cai(lenh):
    """-> (được chạy?, lý do từ chối). Fail-closed: không khớp danh sách là KHÔNG.

    Bậc 3 nối lệnh của nhiều ngôn ngữ bằng ` ; `, nên một project C + Ruby sinh ra
    `brew install llvm ; gem install solargraph`: chuỗi đó bắt đầu bằng một tiền tố hợp lệ trong
    khi vế sau thì không. Kiểm tiền tố của cả chuỗi là để lọt đúng vế sau.

    Cách xử đúng tầng là TỪ CHỐI cả chuỗi ghép, không phải tự viết lại bộ tách lệnh của shell để
    duyệt từng vế: `_chay_lenh` nay chạy `shell=False`, nên một chuỗi ghép cũng không chạy nổi.
    Người khai lệnh phải khai từng lệnh một.
    """
    if any(cam in lenh for cam in DUONG_PYTHON_CAM):
        return False, "lệnh đi qua python hệ thống của Apple — không bao giờ chạm"
    if any(k in lenh for k in KY_TU_SHELL):
        return False, "lệnh có ký tự của shell — không chạy chuỗi ghép, hãy khai từng lệnh một"
    if not lenh.startswith(TIEN_TO_CAI_DUOC):
        return False, "lệnh nằm ngoài danh sách phụ thuộc đã khai"
    return True, ""


# Set by the test suite for the whole process (tests/helper.py), like TDQ_KHOI_TAO_NEN=0. With it,
# the three functions that touch the REAL machine — download + install agent-lsp, rewrite
# ~/.claude.json, stop processes — do nothing unless the caller injected a fake target. Measured
# 2026-10-08: an older test handing rung 1 to `cai_thieu` downloaded the real release and tried to
# overwrite the running ~/.local/bin/agent-lsp.exe (Windows refused it).
def _khong_cham_may():
    return os.environ.get("TDQ_KHONG_CHAM_MAY") == "1"


REPO_AGENT_LSP = "blackwell-systems/agent-lsp"
URL_PHAT_HANH = f"https://api.github.com/repos/{REPO_AGENT_LSP}/releases/latest"
TIMEOUT_TAI = 120


def _tai_mac_dinh(url):
    """GET -> bytes. GitHub's API refuses a request without a User-Agent."""
    yeu_cau = urllib.request.Request(url, headers={"User-Agent": "tdq-setup"})
    with urllib.request.urlopen(yeu_cau, timeout=TIMEOUT_TAI) as resp:  # noqa: S310 — fixed https URLs
        return resp.read()


def ten_goi_agent_lsp(he=None, kien_truc=None):
    """-> the release asset of this machine, e.g. `agent-lsp_windows_amd64.zip`."""
    he = he or sys.platform
    he = "windows" if he.startswith("win") else ("darwin" if he == "darwin" else "linux")
    kien_truc = (kien_truc or platform.machine()).lower()
    kien_truc = "arm64" if kien_truc in ("arm64", "aarch64") else "amd64"
    return f"agent-lsp_{he}_{kien_truc}.{'zip' if he == 'windows' else 'tar.gz'}"


def _lay_binary(goi, ten_goi, ten_bin):
    """Pull the one binary named `ten_bin` out of the archive bytes -> bytes or None."""
    if ten_goi.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(goi)) as zf:
            ten = next((n for n in zf.namelist() if os.path.basename(n) == ten_bin), None)
            return zf.read(ten) if ten else None
    with tarfile.open(fileobj=io.BytesIO(goi), mode="r:gz") as tf:
        thanh_vien = next((m for m in tf.getmembers() if m.isfile() and os.path.basename(m.name) == ten_bin), None)
        tep = tf.extractfile(thanh_vien) if thanh_vien else None
        return tep.read() if tep else None


def cai_agent_lsp(tai=None, thu_muc=None, ten_goi=None):
    """Install agent-lsp from its latest GitHub release -> (ok, line).

    Upstream's `install.sh | sh` does not run on Windows, and piping a download into a shell is
    exactly what `_chay_lenh` refuses. This path needs no shell: the asset is checked against the
    release's `checksums.txt` (SHA256) before a single byte lands on disk; a mismatch installs
    nothing. Only the binary is extracted — never a path from the archive — into `~/.local/bin`.
    """
    if tai is None and _khong_cham_may():
        return False, "TDQ_KHONG_CHAM_MAY=1 — không cài thật"
    tai = tai or _tai_mac_dinh
    thu_muc = thu_muc or os.path.expanduser(os.path.join("~", ".local", "bin"))
    ten_goi = ten_goi or ten_goi_agent_lsp()
    try:
        phat_hanh = json.loads(tai(URL_PHAT_HANH))
        tag = phat_hanh.get("tag_name", "?")
        tai_san = {a.get("name"): a.get("browser_download_url") for a in phat_hanh.get("assets") or []}
        if ten_goi not in tai_san or "checksums.txt" not in tai_san:
            return False, f"bản {tag} không có {ten_goi} hoặc checksums.txt"
        goi = tai(tai_san[ten_goi])
        tong = tai(tai_san["checksums.txt"]).decode("utf-8", "replace")
    except (OSError, ValueError) as exc:
        return False, f"không tải được bản phát hành: {type(exc).__name__}: {exc}"
    mong = next((d.split()[0].lower() for d in tong.splitlines() if d.split()[-1:] == [ten_goi]), "")
    that = hashlib.sha256(goi).hexdigest()
    if not mong or that != mong:
        return False, f"SHA256 của {ten_goi} không khớp checksums.txt ({that[:12]} ≠ {mong[:12] or 'không có'}) — không cài"
    ten_bin = "agent-lsp.exe" if ten_goi.startswith("agent-lsp_windows") else "agent-lsp"
    try:
        binary = _lay_binary(goi, ten_goi, ten_bin)
    except (OSError, zipfile.BadZipFile, tarfile.TarError) as exc:
        return False, f"không giải nén được {ten_goi}: {exc}"
    if not binary:
        return False, f"{ten_goi} không chứa {ten_bin}"
    os.makedirs(thu_muc, exist_ok=True)
    dich = os.path.join(thu_muc, ten_bin)
    fd, tam = tempfile.mkstemp(dir=thu_muc, prefix=".agent-lsp-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(binary)
        os.chmod(tam, 0o755)
        os.replace(tam, dich)
    except OSError as exc:
        # Windows refuses to replace a running .exe: leave the old binary, never a stray temp file.
        if os.path.exists(tam):
            os.remove(tam)
        return False, f"không ghi được {dich}: {exc}"
    _log(f"cài agent-lsp {tag} → {dich} (sha256 {that[:12]})")
    tren_path = os.path.normcase(thu_muc) in [os.path.normcase(p) for p in os.environ.get("PATH", "").split(os.pathsep)]
    return True, f"agent-lsp {tag} → {dich}" + ("" if tren_path else f" (thêm {thu_muc} vào PATH)")


# A rung whose fix is a workflow command, not an installer: setup handles it itself (MCP entries,
# the module script), so it is neither run as an install nor written down as debt. Both forms:
# `python3 scripts/X.py` in this repo, `python3 "<plugin>/scripts/X.py"` once `lenh_cho_project`
# rewrote it for a project without `scripts/` (diff review 2026-10-08).
_RE_LENH_WORKFLOW = re.compile(r'^python3 "?(?:[^"\s]*/)?scripts/tdq_\w+\.py')


def cai_thieu(bac_list, chay_lenh=None, cai_agent=None):
    """-> (đã cài, nợ). Cài mọi bậc còn thiếu mà lệnh của nó nằm trong danh sách đã khai.

    `chay_lenh` (str -> (rc, output)) defaults to `_chay_lenh`; the background build passes its
    own runner so its deadline also bounds the installs. Rung 1 (agent-lsp itself) goes through
    `cai_agent_lsp` — `cai_agent` replaces it in tests.
    """
    chay_lenh = chay_lenh or _chay_lenh
    cai_agent = cai_agent or cai_agent_lsp
    da_cai, no = [], []
    for bac in bac_list:
        if bac.dat or not bac.lenh_cai:
            continue
        if bac.lenh_cai == tdq_lsp.INSTALL_AGENT_LSP:
            ok, dong = cai_agent()
            (da_cai if ok else no).append(f"bậc 1 ({bac.ten}): {dong}")
            continue
        if _RE_LENH_WORKFLOW.match(bac.lenh_cai):
            continue
        duoc, ly_do = _duoc_cai(bac.lenh_cai)
        if not duoc:
            no.append(f"bậc {bac.so} ({bac.ten}): {ly_do} — `{bac.lenh_cai}`")
            continue
        rc, ra = chay_lenh(bac.lenh_cai)
        if rc == 0:
            da_cai.append(f"bậc {bac.so} ({bac.ten}): `{bac.lenh_cai}`")
        else:
            no.append(f"bậc {bac.so} ({bac.ten}): cài thất bại — `{bac.lenh_cai}` → "
                      f"{ra.splitlines()[0][:80] if ra else f'thoát {rc}'}")
    return da_cai, no


# Language servers that need `--stdio` to speak LSP on stdin/stdout; the rest (gopls,
# rust-analyzer, clangd…) do it by default.
CAN_STDIO = ("typescript-language-server", "pyright-langserver", "vscode-html-language-server",
             "vscode-css-language-server", "vscode-json-language-server", "intelephense",
             "yaml-language-server", "prisma-language-server")


def _ghi_json_nguyen_tu(duong, du_lieu):
    """Atomic JSON write next to the target, after a timestamped backup of the old file."""
    moc = datetime.now().strftime("%Y%m%d%H%M%S")
    shutil.copyfile(duong, f"{duong}.truoc-tdq-{moc}.bak")
    fd, tam = tempfile.mkstemp(dir=os.path.dirname(duong) or ".", prefix=".tdq-mcp-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(du_lieu, fh, ensure_ascii=False, indent=2)
        os.replace(tam, duong)
    except BaseException:
        if os.path.exists(tam):
            os.remove(tam)
        raise


def _duong_ben_vung(binary, duong_which, args):
    """-> a binary path that outlives this shell.

    Measured 2026-10-08: under fnm, `shutil.which` answers `.../fnm_multishells/<pid>_<ts>/x.CMD`,
    a per-shell directory that disappears with the shell — an MCP entry pointing there breaks in
    the next session. First choice: the directory the already-declared servers live in (the user's
    own setup, e.g. `fnm/aliases/default`). Second: fnm's `aliases/default` for a multishell path.
    """
    duoi = os.path.splitext(duong_which)[1]
    for a in args:
        lenh = a.split(":", 1)[1].split(",", 1)[0] if ":" in a else ""
        thu_muc = os.path.dirname(lenh)
        if not thu_muc:
            continue
        for ten in (binary + duoi, binary + duoi.lower(), binary + ".cmd", binary):
            ung_vien = os.path.join(thu_muc, ten)
            if os.path.isfile(ung_vien):
                return ung_vien
    if "fnm_multishells" in duong_which:
        mac_dinh = os.path.join(os.environ.get("APPDATA", ""), "fnm", "aliases", "default",
                                os.path.basename(duong_which))
        if os.path.isfile(mac_dinh):
            return mac_dinh
    return duong_which


def _ghi_args_mcp(duong, duong_cau_hinh, args_moi):
    """Write the new `args` of server `lsp` -> '' or an error line.

    The real ~/.claude.json is rewritten by Claude Code itself all the time, so two writers race
    (code review 2026-10-08). For that file the official CLI does the write — `claude mcp
    remove` + `add-json -s user` — after a timestamped backup. Any other path (tests, a copy) is
    written directly and atomically.
    """
    try:
        with open(duong, encoding="utf-8") as fh:
            du_lieu = json.load(fh)
        server = dict(du_lieu["mcpServers"][tdq_lsp.MCP_SERVER_NAME], args=args_moi)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return f"không đọc được {duong_cau_hinh}: {type(exc).__name__}: {exc}"
    claude = shutil.which("claude")
    if duong_cau_hinh == "~/.claude.json" and claude:
        moc = datetime.now().strftime("%Y%m%d%H%M%S")
        shutil.copyfile(duong, f"{duong}.truoc-tdq-{moc}.bak")
        ten = tdq_lsp.MCP_SERVER_NAME
        for argv in ([claude, "mcp", "remove", ten, "-s", "user"],
                     [claude, "mcp", "add-json", ten, json.dumps(server), "-s", "user"]):
            rc, ra = tdq_lsp._run(argv, timeout=60)
            if rc != 0:
                return f"`claude mcp {argv[2]}` thất bại: {ra.splitlines()[-1][:120] if ra else rc}"
        return ""
    try:
        du_lieu["mcpServers"][tdq_lsp.MCP_SERVER_NAME] = server
        _ghi_json_nguyen_tu(duong, du_lieu)
    except (OSError, ValueError, TypeError) as exc:
        return f"không ghi được {duong_cau_hinh}: {type(exc).__name__}: {exc}"
    return ""


def khai_server_mcp(project, duong_cau_hinh="~/.claude.json", chay_lenh=None, which=None):
    """Declare in the `lsp` MCP server every language of the project it does not serve yet.

    The case it exists for: a project starts as Python, later grows JS + HTML. Per missing
    language: install its server (`LANG_SERVER`, same allow-list as every install), find the real
    binary path, append `<lang>:<path>[,--stdio]` to the `args` of server `lsp`. Only that one array
    changes; the file is backed up with a timestamp first and written atomically.
    -> (lines added, debt). Claude Code reads MCP config at start only — the caller must say so.
    """
    if duong_cau_hinh == "~/.claude.json" and _khong_cham_may():
        return [], []
    chay_lenh = chay_lenh or _chay_lenh
    which = which or shutil.which
    duong = os.path.expanduser(duong_cau_hinh)
    args = tdq_lsp.mcp_args(duong)
    if args is None:
        return [], []
    them, no = [], []
    # TypeScript first: its entry also serves JavaScript, so a JS + TS project gets one tsserver,
    # not two (each costs ~0.5 GB of commit — the very pressure behind 0xc0000409).
    for lang in sorted(tdq_lsp.do_ngon_ngu(project), key=lambda l: (l != "typescript", l)):
        if tdq_lsp.lang_mcp(args + them, lang) or lang not in tdq_lsp.LANG_SERVER:
            continue
        ten, binary, lenh = tdq_lsp.LANG_SERVER[lang]
        if not which(binary):
            duoc, ly_do = _duoc_cai(lenh)
            if duoc:
                chay_lenh(lenh)
            elif ly_do:
                no.append(f"{ten}: {ly_do} — `{lenh}`")
                continue
        duong_bin = which(binary)
        if not duong_bin:
            no.append(f"{ten}: cài `{lenh}` xong vẫn không thấy `{binary}` trên PATH")
            continue
        duong_bin = _duong_ben_vung(binary, duong_bin, args)
        them.append(f"{lang}:{duong_bin}" + (",--stdio" if binary in CAN_STDIO else ""))
    if them:
        loi = _ghi_args_mcp(duong, duong_cau_hinh, args + them)
        if loi:
            return [], no + [loi]
        _log(f"MCP lsp: thêm {len(them)} server → {', '.join(t.split(':', 1)[0] for t in them)}")
    return them, no


def don_may(doc=None, tat=None, trong=None):
    """Stop orphan agent-lsp brokers, then check free commit memory -> (done lines, warnings)."""
    if doc is None and _khong_cham_may():
        return [], []
    xong = [f"tắt broker agent-lsp mồ côi pid={pid}" for pid in lsp_module.don_broker(doc, tat)]
    canh_bao = lsp_module.canh_bao_commit(trong)
    return xong, [canh_bao] if canh_bao else []


# Fallback when language detection finds nothing above its threshold (tiny or brand-new project):
# the common code extensions, so a one-file project still gets a real answer.
DUOI_MAC_DINH = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".java",
                 ".cs", ".c", ".cc", ".cpp", ".h", ".hpp", ".rb", ".php", ".kt", ".swift")

# Line markers that look like a definition, per language key of `tdq_lsp.EXT_LANG`.
# Languages absent here accept any non-empty, non-comment line.
DAU_DINH_NGHIA = {
    "python": ("def ", "class "),
    "typescript": ("function ", "class ", "=>", "export "),
    "javascript": ("function ", "class ", "=>", "export "),
}
DAU_CHU_THICH = ("#", "//", "/*", "*", "--", ";", "<!--")


def _duoi_can_quet(project):
    """Extensions of the languages the project really uses, reusing rung 3/7's detector.

    Measured 2026-10-02: a hard-coded `*.py` made the floor report TRƯỢT on excalidraw
    (TypeScript only) while `git grep` answered instantly — a failure that did not exist.
    """
    ngon_ngu = set(tdq_lsp.do_ngon_ngu(project))
    duoi = tuple(sorted(d for d, l in tdq_lsp.EXT_LANG.items() if l in ngon_ngu))
    return duoi or DUOI_MAC_DINH


def _giong_dinh_nghia(dong, lang):
    """Does this line look like a definition for `lang`?"""
    dau = DAU_DINH_NGHIA.get(lang)
    if dau:
        return any(d in dong for d in dau)
    gon = dong.strip()
    return bool(gon) and not gon.startswith(DAU_CHU_THICH)


def smoke_grep(project):
    """Floor layer: find a definition that CERTAINLY exists in the project's own languages.

    Scans with Python itself instead of calling `grep`: Windows has no `grep` by default, and the
    floor must not depend on anything at all — that is why it is the floor.

    Stops at the FIRST matching file. The question is "can this layer answer", so reading all 505
    files (6.6 MB, 0.1 s warm cache) just to count a number nobody uses is wasted work.
    """
    duoi = _duoi_can_quet(project)
    for goc, thu_muc, tep in os.walk(project):
        thu_muc[:] = [t for t in thu_muc
                      if t not in tdq_lsp.SKIP_DIRS and not t.startswith(tdq_lsp.SKIP_PREFIX)]
        for ten in tep:
            phan_duoi = os.path.splitext(ten)[1]
            if phan_duoi not in duoi:
                continue
            lang = tdq_lsp.EXT_LANG.get(phan_duoi)
            try:
                with io.open(os.path.join(goc, ten), encoding="utf-8", errors="replace") as fh:
                    for dong in fh:
                        if _giong_dinh_nghia(dong, lang):
                            return True, f"tìm ra định nghĩa trong {ten}"
            except OSError:
                continue
    return False, "không quét ra file nào (" + ", ".join(duoi) + ")"


def _smoke(cmd, project, doi_ket_qua=False):
    """Một phép smoke -> (đạt?, mô tả). `doi_ket_qua` bắt công cụ phải trả về NỘI DUNG, không chỉ mã 0."""
    rc, ra = tdq_lsp._run(cmd, cwd=project, timeout=TIMEOUT_SMOKE)
    if rc != 0:
        return False, (ra.splitlines()[0][:80] if ra else f"thoát {rc}")
    if doi_ket_qua and not ra.strip():
        return False, "chạy được nhưng không trả về gì"
    return True, "trả lời được"


def smoke_lsp(project):
    """Tầng quan hệ: `agent-lsp doctor` khởi động thật từng language server đã cấu hình."""
    return _smoke(["agent-lsp", "doctor"], project)


def smoke_graphify(project):
    """Tầng bản đồ: hỏi các hub của đồ thị — rẻ nhất trong mọi câu hỏi graphify trả lời được."""
    return _smoke(["graphify", "god-nodes"], project, doi_ket_qua=True)


def smoke_ba_tang(project):
    """-> [(tên tầng, đạt?, chi tiết)] theo đúng thứ tự của luật tìm kiếm 3 tầng."""
    return [("grep", *smoke_grep(project)),
            ("LSP", *smoke_lsp(project)),
            ("graphify", *smoke_graphify(project))]


def va_hook_xung_dot():
    """-> (đã vá, nợ). Gỡ khối `PreToolUse` nhắm công cụ tìm kiếm khỏi hook của plugin ngoài.

    Vì sao phải sửa file của plugin khác: tài liệu Claude Code nói thẳng *"There is no way to
    disable an individual hook while keeping it in the configuration"* — chỉ có công tắc tổng
    `disableAllHooks`, thứ sẽ tắt luôn hook của chính workflow này. Nên đây là đường duy nhất.

    Ba giới hạn, để quyền này không nở ra: chỉ khối `PreToolUse`, chỉ matcher nhắm công cụ tìm
    kiếm, và luôn để lại một bản sao lưu. Khối `SessionStart` được giữ nguyên vì nó có ích thật.

    Phiên bản plugin nằm trong đường dẫn cache, nên một lần update là hook cũ sống lại ở thư mục
    mới. Đó là lý do lệnh này tồn tại thay vì sửa tay một lần: nó chạy lại được, mỗi lần setup.
    """
    if is_antigravity_host():
        return [], []
    da_va, no = [], []
    for ten, tep, _matcher in tdq_lsp.hook_xung_dot():
        du_lieu = tdq_lsp._doc_json(tep)
        khoi = (du_lieu.get("hooks") or {}).get("PreToolUse") or []
        giu = [m for m in khoi
               if not any(t in str(m.get("matcher", "")) for t in tdq_lsp.TOOL_TIM_KIEM)]
        if len(giu) == len(khoi):
            continue
        try:
            shutil.copyfile(tep, tep + DUOI_SAO_LUU)
            if giu:
                du_lieu["hooks"]["PreToolUse"] = giu
            else:
                du_lieu["hooks"].pop("PreToolUse", None)
            with io.open(tep, "w", encoding="utf-8") as fh:
                json.dump(du_lieu, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
        except OSError as exc:
            no.append(f"không vá được hook của plugin `{ten}` tại {tep}: {exc}")
            continue
        _log(f"vá hook plugin {ten}: gỡ {len(khoi) - len(giu)} khối PreToolUse")
        da_va.append(f"plugin `{ten}`: gỡ {len(khoi) - len(giu)} khối `PreToolUse` tại {tep}")
    return da_va, no


def _ban_cai_user(home):
    """-> (khóa, version) của bản cài `tdq-workflow@*` scope user, hoặc None."""
    duong = os.path.join(home, ".claude", "plugins", "installed_plugins.json")
    du_lieu = tdq_lsp._doc_json(duong)
    plugins = du_lieu.get("plugins") if isinstance(du_lieu, dict) else None
    for khoa, ban_cai in (plugins or {}).items():
        if not khoa.startswith("tdq-workflow@") or not isinstance(ban_cai, list):
            continue
        for ban in ban_cai:
            if isinstance(ban, dict) and ban.get("scope") == "user":
                return khoa, str(ban.get("version") or "")
    return None


def _cai_dat_env_timeout_mcp(duong_settings, cham_may=None):
    """Set default CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT=90000 in env of settings.json."""
    if cham_may is False or (cham_may is None and _khong_cham_may()):
        return False
    try:
        du_lieu = {}
        if os.path.isfile(duong_settings):
            with io.open(duong_settings, "r", encoding="utf-8") as fh:
                noi_dung = fh.read().strip()
                if noi_dung:
                    du_lieu = json.loads(noi_dung)
        if not isinstance(du_lieu, dict):
            return False
        env_khoi = du_lieu.setdefault("env", {})
        if not isinstance(env_khoi, dict):
            return False
        if env_khoi.get("CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT"):
            return False
        env_khoi["CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT"] = "90000"
        os.makedirs(os.path.dirname(os.path.abspath(duong_settings)), exist_ok=True)
        if os.path.isfile(duong_settings):
            shutil.copyfile(duong_settings, duong_settings + ".tdq.bak")
        tam = f"{duong_settings}.{os.getpid()}.tmp"
        with io.open(tam, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(du_lieu, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tam, duong_settings)
        _log(f"đã đặt CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT=90000 tại {duong_settings}")
        return True
    except (OSError, ValueError, TypeError) as exc:
        _log(f"không đặt được env timeout tại {duong_settings}: {exc}")
        return False


def _doc_mcp_servers(duong_cjson):
    if not os.path.isfile(duong_cjson):
        return {}
    try:
        with io.open(duong_cjson, "r", encoding="utf-8") as fh:
            cjson = json.load(fh)
        return (cjson.get("mcpServers") or {}) if isinstance(cjson, dict) else {}
    except Exception as exc:  # noqa: BLE001
        _log(f"không đọc được mcpServers từ {duong_cjson}: {exc}")
        return {}


def _tim_cache_plugin_active(home):
    tep_json = os.path.join(home, ".claude", "plugins", "installed_plugins.json")
    du_lieu = tdq_lsp._doc_json(tep_json)
    target_caches = []
    if isinstance(du_lieu, dict) and "plugins" in du_lieu:
        for k, v in du_lieu["plugins"].items():
            if k.startswith("tdq-workflow@") and isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and item.get("installPath"):
                        ip = item["installPath"]
                        if os.path.isdir(ip) and ip not in target_caches:
                            target_caches.append(ip)
    if target_caches:
        return target_caches
    goc_cache = os.path.join(home, ".claude", "plugins", "cache", "tdq-local", "tdq-workflow")
    if os.path.isdir(goc_cache):
        subs = [os.path.join(goc_cache, s) for s in os.listdir(goc_cache)
                if os.path.isdir(os.path.join(goc_cache, s))]
        if subs:
            subs.sort(key=lambda p: tach_version(os.path.basename(p)), reverse=True)
            return [subs[0]]
    return []


def _cap_nhat_permissions_allow(home):
    duong_settings = os.path.join(home, ".claude", "settings.json")
    st_data = {}
    if os.path.isfile(duong_settings):
        try:
            with io.open(duong_settings, "r", encoding="utf-8") as fh:
                noi_dung = fh.read().strip()
                if noi_dung:
                    st_data = json.loads(noi_dung)
        except Exception:
            return False
    if not isinstance(st_data, dict):
        return False
    allow = st_data.setdefault("permissions", {}).setdefault("allow", [])
    if not isinstance(allow, list):
        return False
    can_them = ("mcp__lsp__*", "mcp__plugin_tdq-workflow_lsp__*", "mcp__plugin_tdq-workflow_chrome-devtools__*")
    doi = False
    for rule in can_them:
        if rule not in allow:
            allow.append(rule)
            doi = True
    if not doi:
        return True
    try:
        os.makedirs(os.path.dirname(os.path.abspath(duong_settings)), exist_ok=True)
        tam = f"{duong_settings}.{os.getpid()}.tmp"
        with io.open(tam, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(st_data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tam, duong_settings)
        return True
    except Exception as exc:  # noqa: BLE001
        _log(f"lỗi cập nhật permissions.allow tại {duong_settings}: {exc}")
        return False


def dong_bo_mcp_plugin_cache(home=None, duong_cau_hinh="~/.claude.json", cham_may=None):
    """Đồng bộ mcpServers từ ~/.claude.json vào <active_plugin_cache>/.mcp.json và cấp quyền allow."""
    if cham_may is False or (cham_may is None and _khong_cham_may()):
        return False
    home = home or os.path.expanduser("~")
    duong_cjson = os.path.expanduser(duong_cau_hinh) if isinstance(duong_cau_hinh, str) else str(duong_cau_hinh)
    servers = _doc_mcp_servers(duong_cjson)
    if not servers:
        return False
    caches = _tim_cache_plugin_active(home)
    ghi_thanh_cong = False
    for cache_dir in caches:
        mcp_file = os.path.join(cache_dir, ".mcp.json")
        try:
            tam = f"{mcp_file}.{os.getpid()}.tmp"
            with io.open(tam, "w", encoding="utf-8", newline="\n") as fh:
                json.dump({"mcpServers": servers}, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            os.replace(tam, mcp_file)
            _log(f"đã đồng bộ {len(servers)} mcpServers vào {mcp_file}")
            ghi_thanh_cong = True
        except Exception as exc:  # noqa: BLE001
            _log(f"lỗi ghi {mcp_file}: {exc}")
    _cap_nhat_permissions_allow(home)
    return ghi_thanh_cong


def _da_bat(duong_settings, khoa):
    du_lieu = tdq_lsp._doc_json(duong_settings)
    bat = du_lieu.get("enabledPlugins") if isinstance(du_lieu, dict) else None
    return isinstance(bat, dict) and bat.get(khoa) is True


def kiem_plugin_user(home=None, goc_plugin=None, cham_may=None):
    """-> (đã cài, cảnh báo, nợ). Plugin phải BẬT ở settings user, không chỉ nằm trên đĩa.

    Instruction được ghim ở `~/.claude/CLAUDE.md` nên áp cho mọi repo; plugin chỉ bật trong
    `.claude/settings.json` của vài project thì ở repo khác skill và hook đều không nạp, model
    gặp `Unknown skill`. Đo 2026-10-11 trên 12 phiên của máy dev. `/plugin install|update` là
    lệnh của harness nên ở đây chỉ in ra, không gọi thay.
    """
    if cham_may is None:
        cham_may = home is not None or not _khong_cham_may()
    home = home or os.path.expanduser("~")
    ban = _ban_cai_user(home)
    if ban is None:
        _log("plugin user: chưa có bản cài tdq-workflow scope user")
        return [], [], ["plugin tdq-workflow chưa cài ở scope user — chạy "
                        "/plugin install tdq-workflow@tdq-local"]
    khoa, v_cai = ban
    da_cai, canh_bao, no = [], [], []
    v_goc = doc_phien_ban_plugin(goc_plugin)
    if v_goc and v_cai != v_goc:
        _log(f"plugin user: {khoa} {v_cai} lệch {v_goc}")
        canh_bao.append(f"bản cài {khoa} {v_cai} lệch instruction {v_goc} — chạy "
                        f"/plugin update {khoa}")
    duong = os.path.join(home, ".claude", "settings.json")
    _cai_dat_env_timeout_mcp(duong, cham_may)
    dong_bo_mcp_plugin_cache(home=home, cham_may=cham_may)
    if _da_bat(duong, khoa):
        return da_cai, canh_bao, no
    if not cham_may:
        no.append(f"plugin {khoa} chưa bật ở scope user ({duong}) — chạy lại setup không đặt "
                  "TDQ_KHONG_CHAM_MAY")
        return da_cai, canh_bao, no
    doi, mo_ta = plugin_tiers.bat_khoa(duong, khoa)
    _log(f"plugin user: {mo_ta}")
    if doi:
        da_cai.append(f"bật plugin {khoa} ở scope user (mở phiên mới để nạp)")
    else:
        no.append(f"không bật được plugin {khoa}: {mo_ta}")
    return da_cai, canh_bao, no


def tach_version(ver_str):
    """-> tuple of ints from version string, e.g. '0.82.0' -> (0, 82, 0)."""
    if not ver_str:
        return (0, 0, 0)
    so = [int(x) for x in re.findall(r"\d+", str(ver_str))]
    return tuple(so) if so else (0, 0, 0)


def la_project_that(cwd):
    """-> True nếu cwd là một thư mục project hợp lệ (có .git hoặc .claude-plugin)."""
    try:
        if not cwd or not os.path.isdir(cwd):
            return False
        cwd = os.path.abspath(cwd)
        if cwd == os.path.abspath(os.path.expanduser("~")) or os.path.dirname(cwd) == cwd:
            return False
        return os.path.exists(os.path.join(cwd, ".git")) or os.path.exists(os.path.join(cwd, ".claude-plugin"))
    except Exception:
        return False


def tu_dong_cap_nhat_plugin_user(home=None, goc_plugin=None, chay_lenh=None, cwd=None):
    """Tự động kiểm tra và nâng cấp plugin scope user khi repo nguồn có version mới hơn."""
    home = home or os.path.expanduser("~")
    ban = _ban_cai_user(home)
    if ban is None:
        return False, ""
    khoa, v_cai = ban

    nguon_list = []
    if goc_plugin:
        v_goc = doc_phien_ban_plugin(goc_plugin)
        if v_goc:
            nguon_list.append((v_goc, goc_plugin))
    cwd = cwd or os.getcwd()
    if la_project_that(cwd):
        v_cwd = doc_phien_ban_plugin(cwd)
        if v_cwd:
            nguon_list.append((v_cwd, cwd))
    mkt_dir = os.path.join(home, ".claude", "plugins", "marketplaces", "tdq-local")
    if os.path.isdir(mkt_dir):
        v_mkt = doc_phien_ban_plugin(mkt_dir)
        if v_mkt:
            nguon_list.append((v_mkt, mkt_dir))
    if not nguon_list and globals().get("GOC_REPO"):
        v_repo = doc_phien_ban_plugin(GOC_REPO)
        if v_repo:
            nguon_list.append((v_repo, GOC_REPO))

    if not nguon_list:
        return False, ""

    nguon_list.sort(key=lambda item: tach_version(item[0]), reverse=True)
    v_nguon, goc_nguon = nguon_list[0]

    if tach_version(v_nguon) <= tach_version(v_cai):
        return False, ""

    _log(f"phát hiện bản cài {khoa} {v_cai} cũ hơn nguồn {v_nguon} — tiến hành tự động cập nhật")
    claude = shutil.which("claude")
    chay = chay_lenh or _chay_lenh
    thanh_cong = False

    # Thử 1: Gọi CLI chính thức nếu có
    if claude and not _khong_cham_may():
        try:
            rc, _ = chay(f'"{claude}" plugin update {khoa} -s user -y')
            ban_moi = _ban_cai_user(home)
            if rc == 0 and ban_moi and tach_version(ban_moi[1]) >= tach_version(v_nguon):
                thanh_cong = True
        except Exception:  # noqa: BLE001
            thanh_cong = False

    # Thử 2: Đồng bộ trực tiếp vào cache nếu CLI không khả dụng hoặc thất bại
    if not thanh_cong and not _khong_cham_may():
        try:
            thu_muc_dich = os.path.join(home, ".claude", "plugins", "cache", "tdq-local", "tdq-workflow", v_nguon)
            os.makedirs(thu_muc_dich, exist_ok=True)
            bo_qua = shutil.ignore_patterns(".git", ".venv", ".venv-tokens", "__pycache__", "graphify-out", ".tdq-worktrees")
            for item in os.listdir(goc_nguon):
                if item in (".git", ".venv", ".venv-tokens", "__pycache__", "graphify-out", ".tdq-worktrees"):
                    continue
                s = os.path.join(goc_nguon, item)
                d = os.path.join(thu_muc_dich, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d, ignore_errors=True)
                    shutil.copytree(s, d, ignore=bo_qua)
                else:
                    shutil.copy2(s, d)

            tep_json = os.path.join(home, ".claude", "plugins", "installed_plugins.json")
            du_lieu = tdq_lsp._doc_json(tep_json)
            if isinstance(du_lieu, dict) and "plugins" in du_lieu and khoa in du_lieu["plugins"]:
                for b in du_lieu["plugins"][khoa]:
                    if b.get("scope") == "user":
                        b["version"] = v_nguon
                        b["installPath"] = thu_muc_dich
                        b["lastUpdated"] = datetime.now().isoformat() + "Z"
                _ghi_json_nguyen_tu(tep_json, du_lieu)
                thanh_cong = True
        except Exception as exc:  # noqa: BLE001
            _log(f"lỗi đồng bộ cache plugin cục bộ: {exc}")

    if thanh_cong:
        _log(f"đã tự động cập nhật {khoa} lên {v_nguon}")
        dong_bo_mcp_plugin_cache(home=home)
        return True, f"[TDQ] Đã tự động cập nhật plugin tdq-workflow lên phiên bản {v_nguon}."
    return False, ""


THU_MUC_PLUGINS_STAMP = os.path.join(".claude", "plugins")
TEP_UPDATE_STAMP = ".tdq-update-stamp.json"
THROTTLE_UPDATE_GIAY = 7200  # 2 giờ


def _duong_update_stamp(home=None):
    home = home or os.path.expanduser("~")
    return os.path.join(home, THU_MUC_PLUGINS_STAMP, TEP_UPDATE_STAMP)


def doc_update_stamp(home=None):
    """-> nội dung file stamp theo dõi update remote, hoặc None."""
    try:
        with io.open(_duong_update_stamp(home), encoding="utf-8") as fh:
            d = json.load(fh)
            return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def ghi_update_stamp(home=None, data=None):
    """Ghi dữ liệu vào stamp theo dõi update remote."""
    duong = _duong_update_stamp(home)
    tam = f"{duong}.{os.getpid()}.tmp"
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with io.open(tam, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data or {}, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tam, duong)
        return True
    except OSError as exc:
        _log(f"không ghi được update stamp {duong}: {exc}")
        try:
            os.remove(tam)
        except OSError:
            pass
        return False


def can_kiem_tra_remote(home=None, throttle_seconds=None):
    """-> True nếu đã qua khoảng thời gian throttle kể từ lần kiểm tra remote gần nhất."""
    if os.environ.get("TDQ_AUTO_UPDATE", "1") == "0":
        return False
    throttle = throttle_seconds if throttle_seconds is not None else int(
        os.environ.get("TDQ_UPDATE_INTERVAL_SECONDS", str(THROTTLE_UPDATE_GIAY)))
    stamp = doc_update_stamp(home)
    if not stamp or not stamp.get("last_check"):
        return True
    try:
        dt = datetime.fromisoformat(str(stamp["last_check"]))
        tuoi = time.time() - dt.timestamp()
        return tuoi > throttle
    except (TypeError, ValueError):
        return True


def thuc_hien_cap_nhat_remote(home=None, chay_lenh=None):
    """Cập nhật marketplace tdq-local và nâng cấp plugin tdq-workflow nếu có bản mới. -> (cap_nhat, msg)"""
    home = home or os.path.expanduser("~")
    chay = chay_lenh or _chay_lenh
    claude = shutil.which("claude")
    stamp = doc_update_stamp(home) or {}
    stamp["last_check"] = _now()
    ghi_update_stamp(home, stamp)

    if not claude or _khong_cham_may():
        return False, "claude CLI không khả dụng hoặc bị cấm chạm máy"

    # 1. Update marketplace
    _log("cập nhật marketplace tdq-local...")
    rc_mkt, out_mkt = chay(f'"{claude}" plugin marketplace update tdq-local')
    if rc_mkt != 0:
        _log(f"cập nhật marketplace thất bại: {out_mkt}")
        stamp["last_error"] = f"marketplace update error: {out_mkt}"
        ghi_update_stamp(home, stamp)
        return False, out_mkt

    # 2. Update plugin
    ban = _ban_cai_user(home)
    if not ban:
        return False, "chưa cài plugin tdq-workflow scope user"
    khoa, v_cai = ban

    mkt_dir = os.path.join(home, ".claude", "plugins", "marketplaces", "tdq-local")
    v_mkt = doc_phien_ban_plugin(mkt_dir)

    if v_mkt and tach_version(v_mkt) > tach_version(v_cai):
        _log(f"phát hiện bản mới {v_mkt} trên marketplace (hiện tại {v_cai}) — cập nhật...")
        rc_up, out_up = chay(f'"{claude}" plugin update {khoa} -s user -y')
        if rc_up == 0:
            stamp["updated_version"] = v_mkt
            stamp["updated_at"] = _now()
            stamp.pop("last_error", None)
            ghi_update_stamp(home, stamp)
            dong_bo_mcp_plugin_cache(home=home)
            return True, f"đã cập nhật {khoa} lên {v_mkt}"
        else:
            stamp["last_error"] = f"plugin update error: {out_up}"
            ghi_update_stamp(home, stamp)
            return False, out_up

    stamp["last_status"] = f"up to date ({v_cai})"
    ghi_update_stamp(home, stamp)
    return False, f"đang ở phiên bản mới nhất ({v_cai})"


def kich_hoat_kiem_tra_remote_nen(home=None):
    """Kích hoạt tiến trình ngầm (detached) kiểm tra & cập nhật plugin từ remote nếu đến hạn."""
    if not can_kiem_tra_remote(home):
        return False
    stamp = doc_update_stamp(home) or {}
    stamp["last_check"] = _now()
    ghi_update_stamp(home, stamp)

    lenh = [sys.executable, os.path.join(SCRIPTS_DIR, "tdq_setup.py"), "--update-plugin", "--khong-log"]
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
          "stderr": subprocess.DEVNULL, "close_fds": True}
    if os.name == "nt":
        c_flags = 0x00000008 | 0x00000200 | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        kw["creationflags"] = c_flags
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen(lenh, **kw)
        _log("đã kích hoạt tiến trình ngầm kiểm tra cập nhật plugin từ remote")
        return True
    except OSError as exc:
        _log(f"không khởi động được tiến trình ngầm kiểm tra cập nhật: {exc}")
        return False


def doc_thong_bao_update_moi(home=None):
    """-> chuỗi thông báo nếu vừa có bản cập nhật mới từ tiến trình nền, và dọn cờ thông báo."""
    stamp = doc_update_stamp(home)
    if not stamp or not stamp.get("updated_version"):
        return ""
    v_moi = stamp.pop("updated_version")
    ghi_update_stamp(home, stamp)
    return f"[TDQ] Plugin tdq-workflow đã được tự động cập nhật lên phiên bản {v_moi}."
    return False, ""


def kiem_va_them_user_scripts_path():
    """Add existing user Scripts dirs with binaries to PATH without installing."""
    if _khong_cham_may():
        return [], [], []
    da_lam, ghi_chu = tdq_checkportable.dam_bao_user_scripts_tren_path()
    return da_lam, ghi_chu, []


def kiem_va_cai_shim_python3(tu_dong_them_path=True):
    """Tự động kiểm tra và cài đặt shim python3 trên Windows nếu thiếu hoặc lỗi. -> (da_cai, canh_bao, no)."""
    if not tdq_ten_lenh.la_windows():
        return [], [], []

    da_path, cb_path, _ = kiem_va_them_user_scripts_path() if tu_dong_them_path else ([], [], [])

    song = False
    try:
        res = tdq_ten_lenh.chay_subprocess("python3 -c \"import sys; sys.exit(0)\"",
                                           shell=True, capture_output=True, timeout=5)
        song = (res.returncode == 0)
    except Exception:  # noqa: BLE001
        song = False

    if song and tdq_ten_lenh.co_shim_python3():
        return ["shim `python3` đã sẵn sàng"] + da_path, cb_path, []

    _log("phát hiện `python3` chưa hoạt động hoặc dính Microsoft Store stub — tiến hành cài shim")
    da_lam, ghi_chu = tdq_checkportable.cai_shim_python3(nen_tang="win32", tu_dong_them_path=tu_dong_them_path)
    if da_lam:
        return [f"shim `python3`: {d}" for d in da_lam] + da_path, ghi_chu + cb_path, []
    # Nếu không có file mới được ghi nhưng ghi_chu cho thấy đã đúng sẵn hoặc song == True
    if any("already correct" in g for g in ghi_chu) or song:
        return ["shim `python3` đã sẵn sàng"] + da_path, ghi_chu + cb_path, []
    return da_path, ghi_chu + cb_path, ["không thể tự cài shim `python3` tự động (cần cấp quyền PATH)"]


def kiem_dryrun_hook(goc_plugin=None):
    """Chạy thử (smoke dry-run) script hook bằng lệnh cấu hình để đảm bảo hook không lỗi. -> (dat, chi_tiet)."""
    goc = goc_plugin or GOC_REPO
    script = os.path.join(goc, "hooks", "scripts", "prompt_context.py")
    if not os.path.isfile(script):
        return True, "không có script hook mẫu để test"

    # Kiểm tra bằng python3 qua shell
    try:
        cmd_str = f'python3 "{script}" --help' if tdq_ten_lenh.la_windows() else ["python3", script, "--help"]
        res = tdq_ten_lenh.chay_subprocess(cmd_str, shell=tdq_ten_lenh.la_windows(), capture_output=True, stdin=subprocess.DEVNULL, timeout=5)
        if res.returncode == 0 or b"prompt_context" in res.stdout or b"usage:" in res.stdout:
            return True, "hook dry-run thành công với `python3`"
        if b"Python was not found" in res.stderr:
            return False, "hook vẫn dính lỗi 'Python was not found' từ Microsoft Store stub"
    except FileNotFoundError:
        pass
    except Exception as exc:  # noqa: BLE001
        return False, f"lỗi chạy hook dry-run: {exc}"

    # Kiểm tra fallback qua py -3 hoặc python
    for cmd in ("py", "python"):
        try:
            if tdq_ten_lenh.la_windows():
                c_str = f'{cmd} -3 "{script}" --help' if cmd == "py" else f'{cmd} "{script}" --help'
                res = tdq_ten_lenh.chay_subprocess(c_str, shell=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=5)
            else:
                args = [cmd, "-3", script, "--help"] if cmd == "py" else [cmd, script, "--help"]
                res = tdq_ten_lenh.chay_subprocess(args, capture_output=True, stdin=subprocess.DEVNULL, timeout=5)
            if res.returncode == 0 or b"usage:" in res.stdout:
                return True, f"hook dry-run thành công qua fallback `{cmd}`"
        except Exception:  # noqa: BLE001
            continue

    return False, "không chạy được hook script bằng cả python3, py và python"


def kiem_tra_archify(project=None):
    """Kiểm tra môi trường chạy cho Archify tái sử dụng archify_delivery.check_environment().

    -> (ok: bool, detail: str)
    """
    env_info = archify_delivery.check_environment()
    node_ok = env_info.get("node_ok", False)
    node_ver = env_info.get("node_version", "")
    root = env_info.get("archify_root", "")
    ready = env_info.get("ready", False)
    err = env_info.get("error")

    if ready:
        archify_bin = archify_delivery.get_archify_bin(root)
        ver_str = f"Node.js {node_ver} (>= 18)" if node_ver else "Node.js (>= 18)"
        return True, f"{ver_str} · Archify tại {archify_bin}"

    if not node_ok:
        return False, err or "không tìm thấy Node.js trong PATH (yêu cầu Node.js >= 18)"

    ver_str = f"Node.js {node_ver} (>= 18)" if node_ver else "Node.js (>= 18)"
    return False, f"{ver_str} · {err or 'không tìm thấy file bin/archify.mjs'}"


def _fallback_tree_sitter_support() -> dict[str, Any]:
    """Fallback probe for tree-sitter packages when archify_registry is unavailable."""
    import importlib
    import importlib.metadata

    installed: list[str] = []
    missing: list[str] = []
    versions: dict[str, str | None] = {}
    for pkg in _FALLBACK_TREE_SITTER_PACKAGES:
        try:
            importlib.import_module(pkg.replace("-", "_"))
        except (ImportError, OSError, RuntimeError, ValueError):
            missing.append(pkg)
            versions[pkg] = None
            continue
        installed.append(pkg)
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except (importlib.metadata.PackageNotFoundError, OSError, ValueError):
            versions[pkg] = None
    lang_pairs = (
        ("tree-sitter-python", ("python",)),
        ("tree-sitter-javascript", ("javascript",)),
        ("tree-sitter-typescript", ("typescript", "tsx")),
        ("tree-sitter-rust", ("rust",)),
    )
    langs = [
        name
        for pkg, names in lang_pairs
        if "tree-sitter" in installed and pkg in installed
        for name in names
    ]
    return {
        "available": len(missing) == 0,
        "missing": missing,
        "installed": installed,
        "languages": langs,
        "version": versions.get("tree-sitter"),
    }


def _probe_tree_sitter_support() -> dict[str, Any]:
    """Probe tree-sitter availability via archify_registry with stdlib fallback."""
    if (
        archify_registry is not None
        and sys.modules.get("archify_registry", archify_registry) is not None
    ):
        return archify_registry.check_tree_sitter_support()
    return _fallback_tree_sitter_support()


def _format_tree_sitter_ok(info: dict[str, Any]) -> str:
    """Format ready status string from check_tree_sitter_support output."""
    ver = info.get("version") or "installed"
    langs = ", ".join(info.get("languages") or [])
    if langs:
        return f"tree-sitter {ver} · 4 grammars ready ({langs})"
    return f"tree-sitter {ver} · 4 grammars ready"


def kiem_tra_tree_sitter() -> tuple[bool, str]:
    """Check tree-sitter core and 4 grammar packages -> (ok, detail)."""
    info = _probe_tree_sitter_support()
    if info.get("available"):
        detail = _format_tree_sitter_ok(info)
        _log(f"kiem_tra_tree_sitter ok: {detail}")
        return True, detail
    missing = info.get("missing") or list(TREE_SITTER_PACKAGES)
    detail = f"missing tree-sitter packages: {', '.join(missing)}"
    _log(f"kiem_tra_tree_sitter missing: {detail}")
    return False, detail


MOC_MO = "<!-- TDQ:TOOLS -->"
MOC_DONG = "<!-- /TDQ:TOOLS -->"

# Bản NGẮN NHẤT mà vẫn đủ để một agent chưa nạp skill nào biết dùng gì khi nào. Luật đầy đủ nằm ở
# `skills/tdq-setup/references/uu-tien-tim-kiem.md`; ở đây chỉ có thứ phải biết TRƯỚC khi nạp.
GOC_REPO = os.path.dirname(SCRIPTS_DIR)
# Chỗ giữ chỗ dùng cho BẢN MẪU trong repo. Bản mẫu là tài liệu chung, không được mang đường dẫn
# của máy người dựng nó; đường tuyệt đối chỉ đi vào file thật trên từng máy.
GOC_MAU = "<đường dẫn thư mục cài TDQ-Workflow>"

KHOI_HUONG_DAN = """## Bộ tìm kiếm 3 tầng

- Bắt đầu phiên/tra cứu code: gọi `mcp__lsp__start_lsp(root_dir, language_id)` trước (TS/JS cần mở 1 file bằng `open_document` để nhận project).
  Tra symbol: `list_symbols` (trong file), `find_symbol` (workspace), `find_references` (nơi gọi). Gọi LSP mở khóa 10 lượt grep.
  Tên chính xác đã biết → grep. Vỡ lan, bản đồ kiến trúc → graphify.
  Khái niệm mơ hồ → `graphify query "<câu hỏi>"` song song grep nhiều từ đồng nghĩa, rồi gộp.
- Mỗi tầng có phụ thuộc riêng và chết trong im lặng; tầng nào chết thì rơi xuống grep.
- Kiểm các bậc bằng `python {goc}/scripts/tdq_lsp.py check`; thiếu công cụ thì research nguồn chính thức và đề xuất cài user-level, chờ user duyệt. Chỉ chạy `python {goc}/scripts/tdq_setup.py` khi phạm vi setup đã được duyệt (Windows có thể dùng `py -3`).
  Luật đầy đủ kèm số đo: `{goc}/skills/tdq-setup/references/uu-tien-tim-kiem.md`.
- Khảo sát code 3 chiều (Triangulation Code Exploration) trong phase analyze/quick_analyze: Quét rộng bằng Grep tự do không giới hạn quota. Đào sâu cấu trúc bằng LSP (find_references, go_to_definition) và quét vỡ lan bằng Graphify (affected 2 bước). Lập bảng đối chiếu vùng chạm để không bỏ sót mã nguồn khi refactor hoặc mở rộng.
- Tự quyết xử lý LSP: áp dụng `--bo-qua-lsp "<lý do rõ ràng>"` cho tài liệu/nghiên cứu/cài MCP hoặc tham chiếu nội tệp khi phù hợp. Phục hồi công cụ đã cài trong quyền hiện có; thiếu Language Server/dependency thì tìm nguồn chính thức, đề xuất cài user-level và chờ user duyệt, không tự cài hoặc nới quyền.

## Nguyên tắc TDQ Workflow bắt buộc

- Mọi yêu cầu mới từ người dùng BẮT BUỘC phải mở bằng skill `tdq-workflow:tdq-intake` (hoặc `tdq-intake` nếu cài cục bộ) và chạy theo pipeline của TDQ Workflow (quick hoặc full). Tuyệt đối KHÔNG tự ý chuyển sang plan mode của harness (`EnterPlanMode`) khi nhận yêu cầu.
- Yêu cầu chứa '_tdq_direct' → tự động phân tích & tìm kiếm mã nguồn, lập mini-plan và chỉ dừng ở 1 cổng duyệt mini-plan (không hỏi chọn pipeline, không phỏng vấn).
- Ngoại lệ Refactor & Kiến trúc sạch (Rung 1): Khi người dùng yêu cầu Refactor, tái cấu trúc hoặc Clean Architecture/SOLID, cấu trúc sạch và tính mở rộng module đứng TRÊN luật phẫu thuật 1 dòng tối thiểu. Cấm tự ý ép gộp các tầng/lớp hợp lý thành hàm phẳng nếu làm vỡ chủ đích thiết kế.
- Tự phục hồi môi trường (Self-healing): lỗi 'Python was not found' thì dùng Python đã cài (`python` hoặc `py -3`). Công cụ đã cài sẵn ở thư mục Scripts/bin mức người dùng nhưng thiếu trong `PATH` thì được phép tự thêm vào User `PATH`. Không chạy setup toàn phần nếu sẽ cài mới hoặc đổi permission/host ngoài phạm vi.
- Skill báo `Unknown skill` → plugin chưa bật ở project này: đọc `{goc}/skills/tdq-intake/SKILL.md`, thay `{bien_plugin}` bằng `{goc}`, làm theo; nhắc người dùng chạy lệnh setup ở trên để bật plugin.
- Không được tự ý đổi mode làm việc hiện tại (`EnterPlanMode`, `ExitPlanMode`...).
- Mọi câu hỏi, lựa chọn option và duyệt gate PHẢI trao đổi trực tiếp trong chat (dạng `1a 2b 3c`, "duyệt spec", "duyệt plan", "duyệt nhanh" hoặc câu tự nhiên). Tuyệt đối CẤM mở popup question UI (`AskUserQuestion`) của agent code.

## Nguyên tắc Ưu tiên MCP & Bộ kỹ năng MCP (MCP-First)

- Luôn ưu tiên dùng MCP và bộ skill của MCP (nếu có); ưu tiên lập phương án dùng MCP trong spec/plan để giải quyết trọn vẹn yêu cầu người dùng.
- Kiểm tra kết nối trước (Pre-flight check): kiểm inventory, schema và endpoint cấu hình thực trước thao tác MCP. Nếu chưa kết nối, tự phục hồi công cụ đã cài trong quyền hiện có rồi probe lại; cần thao tác ngoài quyền thì hướng dẫn user. Không suy trạng thái runtime từ cấu hình.
- Ví dụ: Khi phát triển mã nguồn Roblox hoặc Unity, luôn kiểm tra sự hiện diện của MCP và bộ skill/tool của MCP tương ứng để thực hiện và kiểm chứng thay vì thao tác mù mờ.
Chi tiết cẩm nang: `{goc}/skills/tdq-setup/references/mcp-first-guide.md`.

## Tự chủ phối hợp công cụ có kiểm chứng

- Mọi task: xác định mục tiêu, input, đích và quyền; lập bước nội bộ ngắn với tool, output và điều kiện xong. Không yêu cầu xuất suy luận kín. Chỉ hỏi thông tin thiếu làm đổi kết quả; giữ gate TDQ.
- Khám phá tool/skill thực trong phiên. Web ưu tiên Chrome MCP; native app/dialog dùng agent-desktop khi cần; file/CLI dùng tool chuyên biệt. Một tool đủ thì không ép phối hợp nhiều tool; chọn đường ít bước nhất vẫn đúng và có quyền.
- Ưu tiên upload_file trực tiếp nếu schema có và browser host đọc được file. Khi chuyển browser/native: kiểm trang, process/window, file và đích bằng quan sát/ref mới; xác minh attachment trước gửi. handle_dialog không mặc định điều khiển Windows picker.
- Download/Save As phải kiểm file cuối tồn tại, loại và nội dung phù hợp; click thành công chưa phải hoàn tất. Chờ event/tool wait nếu có, không poll dồn dập.
- Delivery gửi/upload chưa rõ: quan sát đích trước, không lặp thao tác khi chưa biết kết quả. Retry chỉ khi có dữ kiện mới/điều kiện đổi; không tiến triển thì đổi phương án hợp lệ hoặc báo blocker. Không đổi tool để vượt hành động đã bị từ chối.
- Thiếu tool: research nguồn chính thức, kiểm OS/quyền, đề xuất lệnh cài user-level kèm kiểm chứng và gỡ; chờ user duyệt. Không tự cài mới, đổi permission, OAuth hoặc nới phạm vi file/dịch vụ/người nhận.
- Tự kiểm từng bước và output cuối; báo rõ hoàn tất/partial/blocker bằng bằng chứng. Chất lượng > runtime > context cost. ĐÚNG: upload trực tiếp, kiểm attachment, gửi một lần, kiểm file tải. SAI: gửi lại khi timeout chưa rõ hoặc báo xong chỉ từ click.

## Quy tắc Git và Attribution bắt buộc

- Tuyệt đối KHÔNG thêm dòng `Co-Authored-By: Claude Code...` hoặc bất kỳ attribution trailer nào vào git commit message hoặc PR body. Mọi commit và PR chỉ chứa nội dung kỹ thuật thuần túy do người dùng và agent trao đổi.
- Vùng tự động mang theo khi đổi/hợp nhất nhánh: Khi mở nhánh request hoặc khi merge về nhánh gốc, nếu working tree dirty nhưng CHỈ thuộc `docs/**`, `*.md`, `logs/**`, `*.log`, `graphify-out/**` thì TỰ ĐỘNG mang theo, commit hoặc merge. Không cần dừng lại hỏi người dùng. Chỉ dừng hỏi khi có thay đổi dirty ở mã nguồn (`scripts/`, `src/`, `hooks/`, `tests/`...).

## Chuẩn Trình bày & Báo cáo (Soul & Report)

- Luôn trình bày đơn giản, dễ hiểu, ngắn gọn nhưng trực quan, đầy đủ thông tin theo chuẩn 2 lớp (`user-facing-block.md`). Lớp 1 cho người đọc ở chat (8–16 dòng, không bọc backtick số thường) và ô `> **Tóm tắt dễ hiểu:**` đầu file `.md` (<= 120 từ, <= 6 backtick/100 từ, không nhồi tường `·`). Lớp 2 lưu đầy đủ bằng chứng bên dưới.
- Mặc định cho cả `spec`, `plan` và `report`: kể theo mạch Trước → Sau → Kết quả với ô `Tóm tắt dễ hiểu` ở đầu file `.md` để ai đọc 10–15 giây cũng hiểu ngay.
- Phase `report` luôn xuất cặp `docs/tdq/reports/<slug>.md` và `Archify HTML` (`docs/tdq/reports/<slug>.html`) với đủ 4 mục: Trước request, Sau request, Đã test gì, Kết quả test."""


def khoi_huong_dan(goc=None):
    """Khối ghim, với đường dẫn TUYỆT ĐỐI của bản cài trên máy này.

    Hai bản trước đều sai: đường dẫn tương đối repo không mở được từ project khác, còn
    `${CLAUDE_PLUGIN_ROOT}` là biến của tầng hook/plugin và KHÔNG được expand trong `CLAUDE.md`
    — agent đọc được một chuỗi không trỏ tới đâu cả. Instruction user-level áp cho mọi repo trên
    máy, nên thứ duy nhất luôn đúng ở đó là đường dẫn tuyệt đối.
    """
    # Biến plugin đi qua tham số, không viết `${{...}}` trong hằng số: bản build portable chỉ thay
    # được chuỗi literal, một tên biến kẹp trong ngoặc kép làm nó báo còn sót biến.
    return KHOI_HUONG_DAN.format(goc=(goc or GOC_REPO).replace("\\", "/"),
                                 bien_plugin="${CLAUDE_PLUGIN_ROOT}")


ARCHIFY_REPO_URL = "https://github.com/tt-a1i/archify.git"
GEMINI_PIN_MAX_BYTES = 24000

KHOI_HUONG_DAN_AGY = """## Bộ tìm kiếm 3 tầng

- Bắt đầu phiên/tra cứu code: gọi `start_lsp(root_dir, language_id)` trước (TS/JS cần mở 1 file bằng `open_document` để nhận project).
  Tra symbol: `list_symbols` (trong file), `find_symbol` (workspace), `find_references` (nơi gọi). Gọi LSP mở khóa 10 lượt grep.
  Tên chính xác đã biết → grep. Vỡ lan, bản đồ kiến trúc → graphify.
  Khái niệm mơ hồ → `graphify query "<câu hỏi>"` song song grep nhiều từ đồng nghĩa, rồi gộp.
- Mỗi tầng có phụ thuộc riêng và chết trong im lặng; tầng nào chết thì rơi xuống grep.
- Kiểm các bậc bằng `python {goc}/scripts/tdq_lsp.py check`; thiếu công cụ thì research nguồn chính thức và đề xuất cài user-level, chờ user duyệt. Chỉ chạy `python {goc}/scripts/tdq_setup.py` khi phạm vi setup đã được duyệt (Windows có thể dùng `py -3`).
  Luật đầy đủ kèm số đo: `{goc}/skills/tdq-setup/references/uu-tien-tim-kiem.md`.
- Khảo sát code 3 chiều (Triangulation Code Exploration) trong phase analyze/quick_analyze: Quét rộng bằng Grep tự do không giới hạn quota. Đào sâu cấu trúc bằng LSP (find_references, go_to_definition) và quét vỡ lan bằng Graphify (affected 2 bước). Lập bảng đối chiếu vùng chạm để không bỏ sót mã nguồn khi refactor hoặc mở rộng.
- Tự quyết xử lý LSP: áp dụng `--bo-qua-lsp "<lý do rõ ràng>"` cho tài liệu/nghiên cứu/cài MCP hoặc tham chiếu nội tệp khi phù hợp. Phục hồi công cụ đã cài trong quyền hiện có; thiếu Language Server/dependency thì tìm nguồn chính thức, đề xuất cài user-level và chờ user duyệt, không tự cài hoặc nới quyền.

## Nguyên tắc TDQ Workflow bắt buộc

- Mọi yêu cầu mới từ người dùng BẮT BUỘC phải mở bằng skill `tdq-intake` và chạy theo pipeline của TDQ Workflow (quick hoặc full). Tuyệt đối KHÔNG tự ý chuyển sang plan mode của harness (`/plan`) khi nhận yêu cầu.
- Yêu cầu chứa '_tdq_direct' → tự động phân tích & tìm kiếm mã nguồn, lập mini-plan và chỉ dừng ở 1 cổng duyệt mini-plan (không hỏi chọn pipeline, không phỏng vấn).
- Ngoại lệ Refactor & Kiến trúc sạch (Rung 1): Khi người dùng yêu cầu Refactor, tái cấu trúc hoặc Clean Architecture/SOLID, cấu trúc sạch và tính mở rộng module đứng TRÊN luật phẫu thuật 1 dòng tối thiểu. Cấm tự ý ép gộp các tầng/lớp hợp lý thành hàm phẳng nếu làm vỡ chủ đích thiết kế.
- Tự phục hồi môi trường (Self-healing): lỗi 'Python was not found' thì dùng Python đã cài (`python` hoặc `py -3`). Chẩn đoán trước; chỉ sửa kết nối/shim trong quyền đã cấp. Không chạy setup toàn phần nếu sẽ cài mới hoặc đổi permission/host ngoài phạm vi.
- Skill báo `Unknown skill` → plugin chưa bật ở project này: đọc `{goc}/skills/tdq-intake/SKILL.md`, thay `{bien_plugin}` bằng `{goc}`, làm theo; nhắc người dùng chạy lệnh setup ở trên để bật plugin.
- Không được tự ý đổi mode làm việc hiện tại (`/plan`...).
- Mọi câu hỏi, lựa chọn option và duyệt gate PHẢI trao đổi trực tiếp trong chat (dạng `1a 2b 3c`, "duyệt spec", "duyệt plan", "duyệt nhanh" hoặc câu tự nhiên). Tuyệt đối CẤM mở popup question UI (`ask_question`) của agent code.

## Nguyên tắc Ưu tiên MCP & Bộ kỹ năng MCP (MCP-First)

- Luôn ưu tiên dùng MCP và bộ skill của MCP (nếu có); ưu tiên lập phương án dùng MCP trong spec/plan để giải quyết trọn vẹn yêu cầu người dùng.
- Kiểm tra kết nối trước (Pre-flight check): kiểm inventory, schema và endpoint cấu hình thực trước thao tác MCP. Nếu chưa kết nối, tự phục hồi công cụ đã cài trong quyền hiện có rồi probe lại; cần thao tác ngoài quyền thì hướng dẫn user. Không suy trạng thái runtime từ cấu hình.
- Ví dụ: Khi phát triển mã nguồn Roblox hoặc Unity, luôn kiểm tra sự hiện diện của MCP và bộ skill/tool của MCP tương ứng để thực hiện và kiểm chứng thay vì thao tác mù mờ.
Chi tiết cẩm nang: `{goc}/skills/tdq-setup/references/mcp-first-guide.md`.

## Tự chủ phối hợp công cụ có kiểm chứng

- Mọi task: xác định mục tiêu, input, đích và quyền; lập bước nội bộ ngắn với tool, output và điều kiện xong. Không yêu cầu xuất suy luận kín. Chỉ hỏi thông tin thiếu làm đổi kết quả; giữ gate TDQ.
- Khám phá tool/skill thực trong phiên. Web ưu tiên Chrome MCP; native app/dialog dùng agent-desktop khi cần; file/CLI dùng tool chuyên biệt. Một tool đủ thì không ép phối hợp nhiều tool; chọn đường ít bước nhất vẫn đúng và có quyền.
- Ưu tiên upload_file trực tiếp nếu schema có và browser host đọc được file. Khi chuyển browser/native: kiểm trang, process/window, file và đích bằng quan sát/ref mới; xác minh attachment trước gửi. handle_dialog không mặc định điều khiển Windows picker.
- Download/Save As phải kiểm file cuối tồn tại, loại và nội dung phù hợp; click thành công chưa phải hoàn tất. Chờ event/tool wait nếu có, không poll dồn dập.
- Delivery gửi/upload chưa rõ: quan sát đích trước, không lặp thao tác khi chưa biết kết quả. Retry chỉ khi có dữ kiện mới/điều kiện đổi; không tiến triển thì đổi phương án hợp lệ hoặc báo blocker. Không đổi tool để vượt hành động đã bị từ chối.
- Thiếu tool: research nguồn chính thức, kiểm OS/quyền, đề xuất lệnh cài user-level kèm kiểm chứng và gỡ; chờ user duyệt. Không tự cài mới, đổi permission, OAuth hoặc nới phạm vi file/dịch vụ/người nhận.
- Tự kiểm từng bước và output cuối; báo rõ hoàn tất/partial/blocker bằng bằng chứng. Chất lượng > runtime > context cost. ĐÚNG: upload trực tiếp, kiểm attachment, gửi một lần, kiểm file tải. SAI: gửi lại khi timeout chưa rõ hoặc báo xong chỉ từ click.

## Quy tắc Git và Attribution bắt buộc

- Tuyệt đối KHÔNG thêm dòng `Co-Authored-By: Claude Code...` hoặc bất kỳ attribution trailer nào vào git commit message hoặc PR body. Mọi commit và PR chỉ chứa nội dung kỹ thuật thuần túy do người dùng và agent trao đổi.
- Vùng tự động mang theo khi đổi/hợp nhất nhánh: Khi mở nhánh request hoặc khi merge về nhánh gốc, nếu working tree dirty nhưng CHỈ thuộc `docs/**`, `*.md`, `logs/**`, `*.log`, `graphify-out/**` thì TỰ ĐỘNG mang theo, commit hoặc merge. Không cần dừng lại hỏi người dùng. Chỉ dừng hỏi khi có thay đổi dirty ở mã nguồn (`scripts/`, `src/`, `hooks/`, `tests/`...).

## Chuẩn Trình bày & Báo cáo (Soul & Report)

- Luôn trình bày đơn giản, dễ hiểu, ngắn gọn nhưng trực quan, đầy đủ thông tin để mọi người đọc đều nắm được bản chất và bằng chứng.
- Mặc định cho cả `spec`, `plan` và `report`: kể theo mạch Trước → Sau → Kết quả với ô `Tóm tắt dễ hiểu` ở đầu file `.md`. Viết ngắn gọn, tự nhiên để ai đọc 10–15 giây cũng hiểu ngay, không nhồi tường `·`.
- Phase `report` luôn xuất cặp `docs/tdq/reports/<slug>.md` và `Archify HTML` (`docs/tdq/reports/<slug>.html`); khi có cập nhật bắt buộc nêu rõ 4 phần: (1) Trước request trạng thái/flow thế nào, (2) Sau request thế nào, (3) Đã test gì, và (4) Kết quả test ra được cái gì."""


def khoi_huong_dan_agy(goc=None):
    """Build Antigravity-native <!-- TDQ:TOOLS --> block for ~/.gemini/GEMINI.md."""
    resolved = (goc or GOC_REPO).replace("\\", "/")
    return KHOI_HUONG_DAN_AGY.format(goc=resolved, bien_plugin="${PLUGIN_ROOT}")


def _doc_instruction(duong):
    """Snapshot byte + metadata; không theo symlink/reparse point hoặc đọc FIFO."""
    try:
        info = os.lstat(duong)
    except FileNotFoundError:
        return b"", None
    if (not stat.S_ISREG(info.st_mode) or
            getattr(info, "st_file_attributes", 0) & 0x400):
        raise ValueError("instruction không phải file thường")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(duong, flags)
    with os.fdopen(fd, "rb") as fh:
        opened = os.fstat(fh.fileno())
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise OSError("instruction đổi trong lúc mở")
        data = fh.read()
        if (_dau_instruction(os.fstat(fh.fileno())) != _dau_instruction(opened) or
                _dau_instruction(os.lstat(duong)) != _dau_instruction(info)):
            raise OSError("instruction đổi trong lúc đọc")
    return data, info


def _dau_instruction(info):
    return None if info is None else (info.st_dev, info.st_ino, info.st_size,
                                      info.st_mtime_ns, info.st_ctime_ns, info.st_mode)


def _noi_instruction(cu, goc, khoi_fn=None):
    text = cu.decode("utf-8")
    counts = text.count(MOC_MO), text.count(MOC_DONG)
    if counts not in ((0, 0), (1, 1)):
        raise ValueError("marker TDQ:TOOLS thiếu hoặc lặp")
    if counts == (1, 1) and text.index(MOC_MO) > text.index(MOC_DONG):
        raise ValueError("marker TDQ:TOOLS đảo thứ tự")
    match = re.search(rb"\r\n|\r|\n", cu)
    newline = match.group() if match else b"\n"
    builder = khoi_fn or khoi_huong_dan
    khoi = f"{MOC_MO}\n{builder(goc)}\n{MOC_DONG}".encode().replace(b"\n", newline)
    if counts == (1, 1):
        start, end = cu.index(MOC_MO.encode()), cu.index(MOC_DONG.encode()) + len(MOC_DONG)
        return cu[:start] + khoi + cu[end:]
    separator = b"" if cu in (b"", b"\xef\xbb\xbf") else newline * 2
    return cu + separator + khoi + newline


def _mien_acl(data, offset, size):
    if offset < 20 or offset % 4 or size < 0 or offset + size > len(data):
        raise OSError("ACL descriptor vượt biên")
    return data[offset:offset + size]


def _sid_acl(data, offset):
    if not offset:
        return None
    header = _mien_acl(data, offset, 8)
    if header[0] != 1 or header[1] > 15:
        raise OSError("ACL SID không hợp lệ")
    return _mien_acl(data, offset, 8 + 4 * header[1])


def _danh_sach_acl(data, offset):
    if not offset:
        return None
    revision, _, size, count, _ = struct.unpack("<BBHHH", _mien_acl(data, offset, 8))
    if revision not in (2, 4) or size < 8:
        raise OSError("ACL header không hợp lệ")
    acl = _mien_acl(data, offset, size)
    aces, cursor = [], 8
    for _ in range(count):
        if cursor + 4 > size:
            raise OSError("ACL ACE thiếu header")
        ace_size = int.from_bytes(acl[cursor + 2:cursor + 4], "little")
        if ace_size < 4 or ace_size % 4 or cursor + ace_size > size:
            raise OSError("ACL ACE vượt biên")
        aces.append(acl[cursor:cursor + ace_size])
        cursor += ace_size
    if os.name == "nt":
        valid = ctypes.WinDLL("advapi32", use_last_error=True).IsValidAcl
        valid.argtypes, valid.restype = [ctypes.c_void_p], ctypes.c_int
        if not valid(ctypes.create_string_buffer(acl)):
            raise OSError("ACL không hợp lệ trên Windows")
    return revision, tuple(aces)


def _nghia_acl_instruction(data):
    if data is None:
        return None
    if not isinstance(data, bytes) or len(data) < 20:
        raise OSError("ACL descriptor thiếu header")
    revision, resource, control, owner, group, sacl, dacl = struct.unpack("<BBHIIII", data[:20])
    if revision != 1 or not control & 0x8000:
        raise OSError("ACL descriptor không self-relative")
    if (sacl and not control & 0x10) or (dacl and not control & 4):
        raise OSError("ACL offset không khớp cờ present")
    result = (revision, resource if control & 0x4000 else 0, control,
              _sid_acl(data, owner), _sid_acl(data, group),
              _danh_sach_acl(data, sacl), _danh_sach_acl(data, dacl))
    if os.name == "nt":
        valid = ctypes.WinDLL("advapi32", use_last_error=True).IsValidSecurityDescriptor
        valid.argtypes, valid.restype = [ctypes.c_void_p], ctypes.c_int
        if not valid(ctypes.create_string_buffer(data)):
            raise OSError("ACL descriptor không hợp lệ trên Windows")
    return result


def _acl_instruction_bang_nhau(trai, phai):
    """So semantics; giữ control, SID, thứ tự/flags ACE; bỏ offset và vùng dư."""
    return _nghia_acl_instruction(trai) == _nghia_acl_instruction(phai)


def _acl_instruction(duong, descriptor=None):
    """Windows owner/group/DACL, gồm cờ protected; không cần package ngoài."""
    if os.name != "nt":
        return None
    from ctypes import wintypes
    api = ctypes.WinDLL("advapi32", use_last_error=True)
    get = api.GetFileSecurityW
    get.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p,
                    wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    get.restype = wintypes.BOOL
    if descriptor is None:
        size = wintypes.DWORD()
        get(duong, 7, None, 0, ctypes.byref(size))
        if not size.value:
            raise ctypes.WinError(ctypes.get_last_error())
        buf = ctypes.create_string_buffer(size.value)
        if not get(duong, 7, buf, size.value, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return buf.raw
    _nghia_acl_instruction(descriptor)
    control = int.from_bytes(descriptor[2:4], "little")
    # SetFileSecurityW giữ AUTO_INHERITED chỉ khi kèm AUTO_INHERIT_REQ.
    # Cờ request chỉ dành cho lời gọi; descriptor gốc vẫn dùng để kiểm readback.
    requested = control | (0x100 if control & 0x400 else 0)
    buf = ctypes.create_string_buffer(descriptor[:2] + requested.to_bytes(2, "little") + descriptor[4:])
    set_security = api.SetFileSecurityW
    set_security.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    set_security.restype = wintypes.BOOL
    flags = 7 | (0x80000000 if control & 0x1000 else 0x20000000)
    if not set_security(duong, flags, buf):
        raise ctypes.WinError(ctypes.get_last_error())


def _tam_instruction(duong, data, info, acl, suffix):
    fd, tam = tempfile.mkstemp(prefix=os.path.basename(duong) + suffix,
                               dir=os.path.dirname(duong))
    try:
        with os.fdopen(fd, "wb") as fh:
            if info is not None:
                _acl_instruction(tam, acl)
                if os.name != "nt":
                    os.fchown(fh.fileno(), info.st_uid, info.st_gid)
                    os.fchmod(fh.fileno(), stat.S_IMODE(info.st_mode))
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if info is not None and os.name == "nt":
            os.chmod(tam, stat.S_IMODE(info.st_mode))
        with io.open(tam, "rb") as fh:
            if fh.read() != data:
                raise OSError("file tạm không khớp dữ liệu")
        if info is not None and not _acl_instruction_bang_nhau(_acl_instruction(tam), acl):
            raise OSError("ACL file tạm không khớp instruction")
        return tam
    except BaseException:
        os.unlink(tam)
        raise


def _khoi_phuc_instruction(duong, cu, info, acl, staged, backup):
    restore = None
    try:
        current = os.lstat(duong)
        if ((current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) !=
                (staged.st_dev, staged.st_ino, staged.st_size, staged.st_mtime_ns)):
            raise OSError("instruction đổi sau replace")
        if info is None:
            os.unlink(duong)
        else:
            restore = _tam_instruction(duong, cu, info, acl, ".tmp.")
            os.replace(restore, duong)
            with io.open(duong, "rb") as fh:
                if fh.read() != cu:
                    raise OSError("khôi phục không khớp")
            if not _acl_instruction_bang_nhau(_acl_instruction(duong), acl):
                raise OSError("ACL khôi phục không khớp")
    except OSError as exc:
        raise OSError(f"{exc}; backup: {backup}") from exc
    finally:
        if restore is not None and os.path.lexists(restore):
            try:
                os.unlink(restore)
            except OSError as exc:
                raise OSError(f"{exc}; backup: {backup}") from exc


def _thay_instruction(duong, cu, moi, info, acl):
    backup = _tam_instruction(duong, cu, info, acl, ".bak.") if info else None
    tam = _tam_instruction(duong, moi, info, acl, ".tmp.")
    try:
        observed, current = _doc_instruction(duong)
        if observed != cu or _dau_instruction(current) != _dau_instruction(info):
            raise OSError("instruction đổi đồng thời; không ghi đè")
        if info is not None and not _acl_instruction_bang_nhau(_acl_instruction(duong), acl):
            raise OSError("ACL instruction đổi đồng thời; không ghi đè")
        staged = os.lstat(tam)
        os.replace(tam, duong)
        try:
            with io.open(duong, "rb") as fh:
                if fh.read() != moi:
                    raise OSError("đọc lại instruction không khớp")
            if info is not None and not _acl_instruction_bang_nhau(_acl_instruction(duong), acl):
                raise OSError("ACL đọc lại instruction không khớp")
        except OSError:
            _khoi_phuc_instruction(duong, cu, info, acl, staged, backup)
            raise
    finally:
        if os.path.lexists(tam):
            os.unlink(tam)


def ghim_huong_dan_tool(duong, goc=None, khoi_fn=None):
    """Ghim nguyên tử; True khi đổi, False khi no-op, lỗi không tiến stamp."""
    duong = os.path.abspath(duong)
    try:
        cu, info = _doc_instruction(duong)
        moi = _noi_instruction(cu, goc, khoi_fn=khoi_fn)
        if moi == cu:
            return False
        acl = _acl_instruction(duong) if info else None
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        _thay_instruction(duong, cu, moi, info, acl)
    except UnicodeError as exc:
        _log(f"lỗi ghim hướng dẫn tại {duong}: UTF-8 không hợp lệ")
        raise ValueError(f"{duong}: UTF-8 không hợp lệ") from exc
    except (OSError, ValueError) as exc:
        _log(f"lỗi ghim hướng dẫn tại {duong}: {type(exc).__name__}")
        raise type(exc)(f"{duong}: {exc}") from exc
    _log(f"ghim hướng dẫn 3 tầng vào {duong}")
    return True


def no_skill_khong_ton_tai(project):
    """-> nợ cho mỗi skill mà bản mẫu instruction bảo dùng nhưng máy này không có.

    Một dòng luật trỏ vào một skill không tồn tại thì tệ hơn là không có dòng nào: agent đọc nó,
    đi tìm, không thấy, rồi tự bịa ra cách làm. Đo được 2026-09-28: §9 của bản mẫu bảo dùng skill
    `mem0-memory`, thứ không có trên máy này.
    """
    ban_mau = os.path.join(project, "docs", "claude-md-mau.md")
    if not os.path.isfile(ban_mau):
        return []
    with io.open(ban_mau, encoding="utf-8", errors="replace") as fh:
        noi_dung = fh.read()
    goc = [os.path.join(project, "skills"), os.path.expanduser("~/.claude/skills")]
    no = []
    for ten in sorted(set(re.findall(r"skill `([a-z0-9][a-z0-9-]{2,})`", noi_dung))):
        if not any(os.path.isdir(os.path.join(g, ten)) for g in goc):
            no.append(f"bản mẫu instruction trỏ tới skill `{ten}` — máy này không có nó")
    return no


# --------------------------------------------------------------------------------------------
# Background bootstrap (`--nen`)
#
# A SessionStart hook cannot build the expensive layers itself: measured, a semantic index of
# excalidraw took 11m5s (843 files, 29,796 chunks; lumen, removed in 0.58.0) and `graphify
# extract` takes minutes on a big repo. So the hook only reads the readiness stamp
# and, when the project is not ready, spawns `tdq_setup.py --nen` detached. This block is that
# detached side. Contract shared with the hook and the search gate — do not rename:
#   stamp  docs/tdq/.tdq-san-sang.json  {"cap_nhat", "dang_dung", "pid", "tang": {layer: {...}}}
#   lock   docs/tdq/.tdq-khoi-tao.lock  the builder's pid as text
# --------------------------------------------------------------------------------------------

MOC_SAN_SANG = search_rules.MOC_SAN_SANG
KHOA_KHOI_TAO = os.path.join("docs", "tdq", ".tdq-khoi-tao.lock")
# Overall cap of one background build. Sized when the build still held an 11-minute lumen index
# of excalidraw; kept at 30 minutes for installs + graphify on a slower machine, and is also the
# age after which a lock is stale even if its pid looks alive (pids get recycled).
TRAN_GIAY = 30 * 60
# How long an EMPTY lock file is believed to be a builder still writing its pid. Writing a pid
# takes microseconds; ten seconds is generous and still frees a lock a crash left empty.
KHOA_RONG_GIAY = 10
# Per-step caps, each further bounded by what is left of TRAN_GIAY.
TIMEOUT_GRAPHIFY_NEN = 10 * 60
TANG_SAN_SANG = ("grep", "lsp", "graphify")


def _tim_cong_cu(ten):
    """Path of an external tool on PATH, or None. One seam so tests never find real tools."""
    return shutil.which(ten)


def _duong_moc(project):
    return os.path.join(project, MOC_SAN_SANG)


def _duong_phat_hanh(project):
    return os.path.join(project, search_rules.MOC_PHAT_HANH)


def doc_phat_hanh(project):
    """-> mốc phiên bản đã setup của project, hoặc None nếu chưa có/lỗi."""
    try:
        with io.open(_duong_phat_hanh(project), encoding="utf-8") as fh:
            du_lieu = json.load(fh)
    except (OSError, ValueError):
        return None
    return du_lieu if isinstance(du_lieu, dict) else None


def ghi_phat_hanh(project, phien_ban):
    """Ghi mốc phiên bản đã setup cho project (không ghi đè nếu phiên bản hiện có cao hơn)."""
    da_ghi = doc_phat_hanh(project)
    if da_ghi and da_ghi.get("phien_ban"):
        if tach_version(phien_ban) < tach_version(da_ghi.get("phien_ban")):
            _log(f"bỏ qua hạ cấp mốc phiên bản {project}: {da_ghi.get('phien_ban')} > {phien_ban}")
            return False
    duong = _duong_phat_hanh(project)
    tam = f"{duong}.{os.getpid()}.tmp"
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with io.open(tam, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"phien_ban": str(phien_ban), "cap_nhat": _now()}, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tam, duong)
        return True
    except OSError as exc:
        _log(f"không ghi được mốc phiên bản {duong}: {exc}")
        try:
            os.remove(tam)
        except OSError:
            pass
        return False


def doc_phien_ban_plugin(goc_plugin=None):
    """Đọc version hiện hành từ plugin.json."""
    goc = goc_plugin or GOC_REPO
    for man in (os.path.join(goc, ".claude-plugin", "plugin.json"),
                os.path.join(goc, ".codex-plugin", "plugin.json")):
        try:
            with io.open(man, encoding="utf-8") as fh:
                d = json.load(fh)
                if d.get("version"):
                    return str(d["version"])
        except (OSError, ValueError):
            continue
    return None


def can_cap_nhat_phien_ban(project, goc_plugin=None):
    """-> True nếu phiên bản plugin hiện hành mới hơn mốc phiên bản đã setup trong project."""
    hien_tai = doc_phien_ban_plugin(goc_plugin)
    if not hien_tai:
        return False
    da_ghi = doc_phat_hanh(project)
    if not da_ghi or not da_ghi.get("phien_ban"):
        return True
    return tach_version(hien_tai) > tach_version(da_ghi.get("phien_ban"))


def thuc_hien_setup_bu(project, v_cu, v_moi, goc_plugin=None):
    """Chạy kiểm thử và thiết lập bù các thành phần mới từ version cũ lên version mới."""
    _log(f"thực hiện setup bù từ {v_cu} lên {v_moi} tại {project}")
    ket_qua = []
    # 1. Cài đặt / kiểm tra shim python3 trên Windows
    try:
        da_cai, _, _ = kiem_va_cai_shim_python3()
        if da_cai:
            ket_qua.extend(da_cai)
    except Exception as exc:  # noqa: BLE001
        _log(f"lỗi kiểm tra shim khi setup bù: {exc}")

    # Required sync: propagate failure so the version stamp remains retryable.
    ghim_huong_dan_tool(os.path.expanduser(DUONG_INSTRUCTION), goc=goc_plugin)
    dong_bo_mcp_plugin_cache()
    ket_qua.append("ghim instruction mới")

    # 3. Đồng bộ Codex MCP & hook nếu có
    if _tim_cong_cu("codex"):
        try:
            import tdq_codex_mcp
            tdq_codex_mcp.khai_mcp_codex()
            tdq_codex_mcp.khai_hook_codex(project)
            ket_qua.append("đồng bộ cấu hình codex")
        except Exception as exc:  # noqa: BLE001
            _log(f"lỗi khai codex khi setup bù: {exc}")

    # 4. Kiểm tra Chrome DevTools MCP
    try:
        tdq_devtool_mcp.check_session_start(cwd=project)
    except Exception:  # noqa: BLE001
        pass

    # 5. Kiểm thử dry-run hook
    try:
        ok, chi_tiet = kiem_dryrun_hook(goc_plugin=goc_plugin)
        if ok:
            ket_qua.append(f"dry-run hook ĐẠT ({chi_tiet})")
    except Exception as exc:  # noqa: BLE001
        _log(f"lỗi dry-run hook khi setup bù: {exc}")

    # 6. Dọn tiến trình broker cũ
    try:
        don_may()
    except Exception:  # noqa: BLE001
        pass

    return ket_qua


def tu_dong_cap_nhat_khi_doi_phien_ban(project, goc_plugin=None):
    """Chạy đồng bộ instruction, cấu hình Codex, setup bù và ghim version mới vào mốc."""
    hien_tai = doc_phien_ban_plugin(goc_plugin)
    da_ghi = doc_phat_hanh(project)
    v_cu = da_ghi.get("phien_ban") if da_ghi else "0.0.0"
    if da_ghi and da_ghi.get("phien_ban") and tach_version(hien_tai) <= tach_version(v_cu):
        return False
    _log(f"tự động cập nhật cho phiên bản {hien_tai} (từ {v_cu}) tại {project}")
    thuc_hien_setup_bu(project, v_cu, hien_tai, goc_plugin=goc_plugin)
    if not hien_tai or not ghi_phat_hanh(project, hien_tai):
        raise OSError("Setup version stamp was not written; update remains retryable")
    return True


def _duong_khoa(project):
    return os.path.join(project, KHOA_KHOI_TAO)


def doc_san_sang(project):
    """-> the readiness stamp as a dict, or None when it is missing, unreadable or corrupt."""
    try:
        with io.open(_duong_moc(project), encoding="utf-8") as fh:
            du_lieu = json.load(fh)
    except (OSError, ValueError):
        return None
    return du_lieu if isinstance(du_lieu, dict) else None


def ghi_san_sang(project, data):
    """Write the stamp atomically (temp file + os.replace) -> True when written.

    Atomic because the hook may read it at any moment while the builder rewrites it; a reader
    must see the old stamp or the new one, never half of one. Never raises: a stamp that cannot
    be written is logged, and the build goes on.
    """
    duong = _duong_moc(project)
    tam = f"{duong}.{os.getpid()}.tmp"
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with io.open(tam, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tam, duong)
        return True
    except OSError as exc:
        _log(f"nền: không ghi được mốc sẵn sàng {duong}: {exc}")
        try:
            os.remove(tam)
        except OSError:
            pass
        return False


def _pid_con_song(pid):
    """Is process `pid` alive? Cross-platform, never raises; unsure counts as alive.

    "Unsure -> alive" is the safe side: a wrongly kept lock still expires after TRAN_GIAY,
    while a wrongly stolen one means two builders indexing the same project.
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        return _pid_con_song_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, OverflowError):
        return False
    return True


def _pid_con_song_windows(pid):
    """Windows liveness via OpenProcess + GetExitCodeProcess (os.kill(pid, 0) would KILL it)."""
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        k32.CloseHandle.argtypes = (wintypes.HANDLE,)
        if pid > 0xFFFFFFFF:
            return False
        process_query_limited_information = 0x1000
        still_active = 259
        handle = k32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            # Access denied means the process exists but belongs to someone else.
            return ctypes.get_last_error() == 5
        try:
            ma = wintypes.DWORD()
            if not k32.GetExitCodeProcess(handle, ctypes.byref(ma)):
                return True
            return ma.value == still_active
        finally:
            k32.CloseHandle(handle)
    except Exception:  # noqa: BLE001 — a liveness probe must never take the builder down
        return True


def _khoa_cu(duong):
    """Is the lock at `duong` stale: unreadable pid, dead pid, or older than TRAN_GIAY?"""
    try:
        with io.open(duong, encoding="utf-8", errors="replace") as fh:
            noi_dung = fh.read().strip()
        tuoi = datetime.now().timestamp() - os.path.getmtime(duong)
    except OSError:
        return True
    if tuoi > TRAN_GIAY:
        return True
    if not noi_dung:
        # The lock is created with O_EXCL and the pid is written right after: an EMPTY lock this
        # young is a builder mid-write, not a dead one. Reading it as stale let a second builder
        # delete a live lock (POSIX), found by review 2026-10-03.
        return tuoi > KHOA_RONG_GIAY
    return not _pid_con_song(noi_dung)


def giu_khoa(project):
    """Take the build lock -> True when this process holds it now.

    O_CREAT|O_EXCL makes the take atomic: of two builders started together exactly one creates
    the file. A stale lock is removed and the take is retried once.
    """
    duong = _duong_khoa(project)
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
    except OSError as exc:
        _log(f"nền: không tạo được thư mục khoá: {exc}")
        return False
    for lan in range(2):
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if lan == 0 and _khoa_cu(duong):
                _log(f"nền: khoá cũ tại {duong} — lấy lại")
                try:
                    os.remove(duong)
                except OSError:
                    return False
                continue
            return False
        except OSError as exc:
            _log(f"nền: không tạo được khoá {duong}: {exc}")
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
        return True
    return False


def nha_khoa(project):
    """Release the build lock — only if it is still ours. Never raises."""
    duong = _duong_khoa(project)
    try:
        with io.open(duong, encoding="utf-8", errors="replace") as fh:
            if fh.read().strip() != str(os.getpid()):
                return
        os.remove(duong)
    except OSError:
        pass


def _chay_mac_dinh(argv, cwd=None, timeout=None):
    """Default command runner of the background build: no shell, bounded, never raises."""
    return tdq_lsp._run(argv, cwd=cwd, timeout=timeout or TIMEOUT_CAI)


def _tang_tu_smoke(smoke):
    """[(layer, passed, detail)] -> the stamp's `tang` dict, always with the three keys."""
    tang = {ten: {"san_sang": False, "chi_tiet": "chưa kiểm"} for ten in TANG_SAN_SANG}
    for ten, dat, chi_tiet in smoke:
        khoa = str(ten).lower()
        if khoa in tang:
            tang[khoa] = {"san_sang": bool(dat), "chi_tiet": str(chi_tiet)}
    return tang


def khoi_tao_nen(project, chay=None, *, cache_mode="off", request=None):
    """The `--nen` body: build the expensive layers in the background, then write the stamp.

    Steps, each bounded and none able to stop the others: declared installs (`cai_thieu`),
    the Codex MCP declaration, `graphify extract`, then the three-layer smoke.
    `chay(argv, cwd=None, timeout=None) -> (rc, output)` is the injectable runner.
    -> 0 always: a background process has nobody to report an exit code to; the stamp is the report.
    """
    chay = chay or _chay_mac_dinh
    if not giu_khoa(project):
        _log(f"nền: một tiến trình khác đang dựng {project} — thoát")
        return 0
    bat_dau = datetime.now().timestamp()

    def con_lai():
        return TRAN_GIAY - (datetime.now().timestamp() - bat_dau)

    def chay_an_toan(argv, cwd, tran):
        thoi_gian = min(tran, con_lai())
        if thoi_gian <= 0:
            _log(f"nền: hết trần {TRAN_GIAY}s — bỏ {argv[0]}")
            return 1, "hết trần thời gian"
        _log(f"nền: chạy {' '.join(str(a) for a in argv)}")
        try:
            return chay(argv, cwd=cwd, timeout=thoi_gian)
        except Exception as exc:  # noqa: BLE001 — one step must never stop the next
            return 1, f"{type(exc).__name__}: {exc}"

    def buoc(ten, ham):
        if con_lai() <= 0:
            _log(f"nền: hết trần {TRAN_GIAY}s — bỏ bước {ten}")
            return
        try:
            ham()
        except Exception as exc:  # noqa: BLE001 — same contract as chay_an_toan
            _log(f"nền: bước {ten} lỗi: {type(exc).__name__}: {exc}")

    try:
        try:
            grep = [("grep", *smoke_grep(project))]
        except Exception as exc:  # noqa: BLE001
            grep = [("grep", False, f"{type(exc).__name__}: {exc}")]
        tang = _tang_tu_smoke(grep)
        for ten in TANG_SAN_SANG[1:]:
            tang[ten]["chi_tiet"] = "đang dựng nền"
        ghi_san_sang(project, {"cap_nhat": _now(), "dang_dung": True, "pid": os.getpid(),
                               "tang": tang})
        if os.path.isfile(lsp_module.duong_bang(project)):
            lsp_module.ghi_ngon_ngu(project)

        def cai():
            def chay_lenh(lenh):
                try:
                    argv = shlex.split(lenh)
                except ValueError as exc:
                    return 1, f"không tách được lệnh: {exc}"
                return chay_an_toan(argv, None, TIMEOUT_CAI)
            da_shim, _, no_shim = kiem_va_cai_shim_python3()
            for d in da_shim:
                _log(f"nền: {d}")
            if no_shim:
                tdq_no.ghi_no(no_shim, project)
            options = {"cache_mode": cache_mode, "request": request} if cache_mode != "off" else {}
            da_cai, no = cai_thieu(tdq_lsp.chay_kiem(project, **options), chay_lenh=chay_lenh)
            them, no_mcp = khai_server_mcp(project, chay_lenh=chay_lenh)
            for dong in da_cai + [f"MCP lsp + {t}" for t in them]:
                _log(f"nền: đã cài · {dong}")
            if no + no_mcp:
                tdq_no.ghi_no(no + no_mcp, project)

        def don():
            xong, canh_bao = don_may()
            for dong in xong + canh_bao:
                _log(f"nền: {dong}")

        def codex():
            if not _tim_cong_cu("codex"):
                _log("nền: không thấy codex — bỏ khai MCP cho Codex")
                return
            import tdq_codex_mcp
            for dong in tdq_codex_mcp.khai_mcp_codex() + tdq_codex_mcp.khai_hook_codex(project):
                _log(f"nền: codex · {dong}")

        def graphify():
            if not _tim_cong_cu("graphify"):
                _log("nền: không thấy graphify — bỏ dựng đồ thị")
                return
            rc, ra = chay_an_toan(["graphify", "extract", ".", "--code-only"], project,
                                  TIMEOUT_GRAPHIFY_NEN)
            _log(f"nền: graphify → {'xong' if rc == 0 else 'hỏng: ' + ra[-120:]}")

        def instruction():
            ghim_huong_dan_tool(os.path.expanduser(DUONG_INSTRUCTION), goc=GOC_REPO)
            dong_bo_mcp_plugin_cache()
            phien_ban = doc_phien_ban_plugin(GOC_REPO)
            if phien_ban:
                ghi_phat_hanh(project, phien_ban)

        for ten, ham in (("instruction", instruction), ("cài", cai), ("dọn", don),
                         ("codex", codex), ("graphify", graphify)):
            buoc(ten, ham)

        smoke = []

        def kiem():
            smoke.extend(tdq_lsp.chay_smoke(project))

        buoc("smoke", kiem)
        if smoke:
            tang = _tang_tu_smoke(smoke)
        else:
            for ten in TANG_SAN_SANG[1:]:
                tang[ten] = {"san_sang": False, "chi_tiet": "không chạy được smoke"}
        ghi_san_sang(project, {"cap_nhat": _now(), "dang_dung": False, "pid": None,
                               "tang": tang})
        _log("nền: xong · " + ", ".join(
            f"{t}={'ĐẠT' if tang[t]['san_sang'] else 'TRƯỢT'}" for t in TANG_SAN_SANG))
    finally:
        nha_khoa(project)
    return 0


def parse_args(argv):
    ap = argparse.ArgumentParser(
        description="Install and verify 3-tier search and Antigravity setup dependencies.")
    ap.add_argument("--khong-log", action="store_true", help="tắt log ra stderr")
    ap.add_argument("--readiness-cache", choices=("off", "auto"), default="off")
    ap.add_argument("--request", help="Request cache namespace (defaults to active state)")
    ap.add_argument("--nen", action="store_true",
                    help="dựng nền phần đắt (cài, graphify) rồi ghi mốc sẵn sàng")
    ap.add_argument("--kiem-archify", action="store_true",
                    help="chỉ kiểm tra môi trường Node.js >= 18 và gói Archify")
    ap.add_argument("--update-plugin", action="store_true",
                    help="kiểm tra và cập nhật plugin tdq-workflow từ remote marketplace")
    ap.add_argument("--with-rtk", action="store_true",
                    help="tải và cài user-level rtk + rg kiểm SHA256 (cần sự đồng ý của user)")
    ap.add_argument("--check-rtk", action="store_true",
                    help="kiểm tra trạng thái rtk + rg (Collision Guard) không chạm máy")
    ap.add_argument("--mute-rtk-prompt", action="store_true",
                    help="tắt dòng nhắc [TDQ:SETUP] thiếu rtk/rg lúc SessionStart")
    ap.add_argument("--unmute-rtk-prompt", action="store_true",
                    help="bật lại dòng nhắc [TDQ:SETUP] thiếu rtk/rg lúc SessionStart")
    ap.add_argument("--with-caveman", action="store_true",
                    help="bật Caveman opt-in và bọc MCP proxy với sự đồng ý của user")
    ap.add_argument("--without-caveman", action="store_true",
                    help="tắt Caveman và khôi phục mcp_config.json gốc")
    ap.add_argument("--check-caveman", action="store_true",
                    help="kiểm tra trạng thái Caveman opt-in không chạm máy")
    ap.add_argument("--mute-caveman-prompt", action="store_true",
                    help="tắt dòng nhắc [TDQ:SETUP] Caveman lúc SessionStart")
    ap.add_argument("--unmute-caveman-prompt", action="store_true",
                    help="bật lại dòng nhắc [TDQ:SETUP] Caveman lúc SessionStart")
    ap.add_argument("--setupfully", action="store_true",
                    help="Run automated one-shot Antigravity setup (Phase 1) and persist restart state")
    ap.add_argument("--scan-json", action="store_true",
                    help="Scan Antigravity toolchain and emit structured JSON manifest")
    ap.add_argument("--apply-manifest", action="store_true",
                    help="Apply Antigravity Phase-1 setup manifest without restarting")
    ap.add_argument("--post-restart-verify", action="store_true",
                    help="Run 6-layer post-restart verification and clear pending flag on Core Gate PASS")
    ap.add_argument("--confirm-restarted", action="store_true",
                    help="Explicitly confirm IDE restart when process fingerprint cannot change")
    ap.add_argument("--set-tavily-key", default="",
                    help="Save TAVILY_API_KEY in private secrets.env without echoing the secret")
    ap.add_argument("--state-dir", default="",
                    help="Override TDQ_SETUP_STATE_DIR for isolated state operations")
    ap.add_argument("--json", action="store_true", help="Emit JSON summary when supported")
    return ap.parse_args(argv)


def _in_rtk_check(rtk_mod, project):
    st = rtk_mod.probe_rtk(cwd=project)
    rg = rtk_mod.locate_rg_binary()
    lbl = "trùng tên Rust Type Kit" if st.get("collision") else (
        st.get("version") if st.get("valid") else st.get("reason")
    )
    ok = bool(st.get("valid"))
    _log(f"rtk check · valid={ok} label={lbl} rg={rg or 'missing'}")
    print(f"rtk · valid={ok} ({lbl}) | rg={rg or 'thiếu'} | muted={rtk_mod.is_prompt_muted()}")
    return 0 if (ok and rg) else 1


def _xu_ly_rtk_flags(args, project):
    """Handle RTK CLI flags; return int exit code or None to continue."""
    flags = (args.mute_rtk_prompt, args.unmute_rtk_prompt, args.check_rtk, args.with_rtk)
    if not any(flags):
        return None
    if getattr(args, "khong_log", False):
        os.environ["TDQ_LOG"] = "0"
    import rtk_integration
    if args.mute_rtk_prompt or args.unmute_rtk_prompt:
        muted = bool(args.mute_rtk_prompt)
        path = rtk_integration.set_prompt_muted(muted)
        _log(f"rtk prompt · {'muted' if muted else 'unmuted'} ({path})")
        print(f"rtk prompt · {'đã tắt' if muted else 'đã bật lại'} ({path})")
        return 0
    if args.check_rtk:
        return _in_rtk_check(rtk_integration, project)
    res = rtk_integration.install_rtk_and_rg(approve=True)
    if res.get("ok"):
        _log(f"rtk install · ĐẠT rtk={res.get('rtk_version')} rg={res.get('rg_version')}")
        print(f"rtk · ĐẠT rtk={res.get('rtk_version')} ({res.get('rtk_path')}), rg={res.get('rg_version')} ({res.get('rg_path')}), cfg={res.get('config_path')}")
        return 0
    _log(f"rtk install · THẤT BẠI: {res.get('reason')}")
    print(f"rtk · THẤT BẠI: {res.get('reason')}")
    return 1


def _caveman_targets(plugin_root):
    """Return existing mcp_config.json paths and active plugin root for Caveman wrapping."""
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or os.path.expanduser("~")
    installed_root = os.path.join(home, ".gemini", "config", "plugins", "tdq-workflow-agy")
    candidates = [os.path.join(plugin_root, "mcp_config.json"),
                  os.path.join(installed_root, "mcp_config.json")]
    seen = []
    for path in candidates:
        norm = os.path.abspath(path)
        if os.path.isfile(norm) and norm not in seen:
            seen.append(norm)
    probe_root = installed_root if os.path.isfile(os.path.join(installed_root, "mcp_config.json")) else plugin_root
    return seen, probe_root


def _in_caveman_check(cfg_mod, plugin_root):
    _, probe_root = _caveman_targets(plugin_root)
    st = cfg_mod.probe_caveman(plugin_root=probe_root)
    _log(f"caveman check · enabled={st.get('enabled')} active={st.get('active')} wrapped={st.get('mcp_wrapped_servers')}")
    print(
        f"caveman · enabled={st.get('enabled')} | active={st.get('active')} "
        f"| wrapped={st.get('mcp_wrapped_servers')} | muted={st.get('prompt_muted')} "
        f"| cfg={st.get('config_path')}"
    )
    return 0


def _xu_ly_caveman_flags(args, project):
    """Handle Caveman CLI flags; return int exit code or None to continue."""
    flags = (args.mute_caveman_prompt, args.unmute_caveman_prompt,
             args.check_caveman, args.with_caveman, args.without_caveman)
    if not any(flags):
        return None
    if getattr(args, "khong_log", False):
        os.environ["TDQ_LOG"] = "0"
    import caveman_config
    plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if args.mute_caveman_prompt or args.unmute_caveman_prompt:
        muted = bool(args.mute_caveman_prompt)
        path = caveman_config.set_prompt_muted(muted)
        _log(f"caveman prompt · {'muted' if muted else 'unmuted'} ({path})")
        print(f"caveman prompt · {'đã tắt' if muted else 'đã bật lại'} ({path})")
        return 0
    if args.check_caveman:
        return _in_caveman_check(caveman_config, plugin_root)
    targets, _ = _caveman_targets(plugin_root)
    if args.without_caveman:
        unwrapped = []
        for mcp_path in targets:
            unwrapped.extend(caveman_config.unwrap_mcp_config(Path(mcp_path)))
        res = caveman_config.disable_caveman()
        _log(f"caveman disabled · unwrapped={unwrapped}")
        print(f"caveman · ĐÃ TẮT (unwrapped={unwrapped}, cfg={res.get('config_path')})")
        return 0
    proxy_script = Path(plugin_root) / "scripts" / "tdq_mcp_shrink.py"
    wrapped = []
    for mcp_path in targets:
        wrapped.extend(caveman_config.wrap_mcp_config(Path(mcp_path), proxy_script))
    res = caveman_config.enable_caveman(approve=True, wrapped_servers=wrapped or list(caveman_config.CAVEMAN_MCP_SERVERS))
    _log(f"caveman enabled · wrapped={res.get('wrapped_servers')}")
    print(f"caveman · ĐẠT enabled=True | wrapped={res.get('wrapped_servers')} | cfg={res.get('config_path')}")
    return 0


def _khai_codex_mac_dinh():
    """The CLI's Codex step: the lsp MCP server, then the search gate in the project's
    `.codex/hooks.json` (Codex no longer takes hooks from a plugin). -> result lines."""
    import tdq_codex_mcp
    if not shutil.which("codex"):
        return tdq_codex_mcp.khai_mcp_codex()
    return tdq_codex_mcp.khai_mcp_codex() + tdq_codex_mcp.khai_hook_codex(tdq_lsp._project_dir())


def chay_cli(argv):
    """The command line entry: `main` WITH the Codex MCP declaration turned on.

    Why `main` does not do it by default: `codex mcp add` writes the user's real
    `~/.codex/config.toml`, and in-process callers of `main` (the existing tests) must never do
    that. Typing the command is the consent, exactly as for the installs.
    """
    return main(argv, khai_codex=_khai_codex_mac_dinh)


@contextmanager
def _scoped_state_dir(state_dir: Optional[str]):
    """Temporarily scope TDQ_SETUP_STATE_DIR around one CLI invocation."""
    cleaned = (state_dir or "").strip()
    if not cleaned:
        yield None
        return
    resolved = Path(cleaned).expanduser()
    prev = os.environ.get("TDQ_SETUP_STATE_DIR")
    os.environ["TDQ_SETUP_STATE_DIR"] = str(resolved)
    try:
        yield resolved
    finally:
        if prev is None:
            os.environ.pop("TDQ_SETUP_STATE_DIR", None)
        else:
            os.environ["TDQ_SETUP_STATE_DIR"] = prev


def _xu_ly_legacy_mode_flags(args, project) -> Optional[int]:
    """Handle legacy standalone flags (--kiem-archify, --update-plugin, --nen)."""
    if args.kiem_archify:
        ok, chi_tiet = kiem_tra_archify(project)
        print(f"archify · ĐẠT ({chi_tiet})" if ok else f"cảnh báo · archify chưa sẵn sàng ({chi_tiet})")
        return 0
    if args.update_plugin:
        ok, msg = thuc_hien_cap_nhat_remote()
        print(f"cập nhật plugin · {'ĐẠT' if ok else 'THÔNG TIN'}: {msg}")
        return 0
    if args.nen:
        options = {"cache_mode": args.readiness_cache, "request": args.request}
        khoi_tao_nen(project) if args.readiness_cache == "off" else khoi_tao_nen(project, **options)
        return 0
    return None


def main(argv, khai_codex=None):
    args = parse_args(argv)
    if args.khong_log:
        os.environ["TDQ_LOG"] = "0"
    project = tdq_lsp._project_dir()
    with _scoped_state_dir(getattr(args, "state_dir", "")) as state_dir_override:
        for handler in (
            lambda: _xu_ly_rtk_flags(args, project),
            lambda: _xu_ly_caveman_flags(args, project),
            lambda: _xu_ly_legacy_mode_flags(args, project),
            lambda: _handle_antigravity_cli(args, project, state_dir_override),
        ):
            rc = handler()
            if rc is not None:
                return rc
        return _run_legacy_claude_setup(args, project, khai_codex)


def _record_tree_sitter_status(da_cai: list[str], canh_bao: list[str]) -> None:
    """Probe or install tree-sitter dependencies and record status in setup output."""
    try:
        dat_ts, chi_tiet_ts = ensure_tree_sitter_installed()
        if dat_ts:
            da_cai.append(f"tree-sitter AST: {chi_tiet_ts}")
        else:
            canh_bao.append(f"tree-sitter AST: {chi_tiet_ts}")
    except (
        OSError,
        RuntimeError,
        ValueError,
        ImportError,
        subprocess.SubprocessError,
    ) as exc:
        canh_bao.append(f"tree-sitter AST check error: {exc}")


def _run_legacy_claude_setup(args, project, khai_codex=None):
    """Run legacy Claude Code setup flow unchanged when host is not Antigravity."""
    _log(f"setup · project={project} · máy={platform.node()}")

    # Handoff contains only static probe receipts; each reuse hashes its inputs again.
    options = ({"cache_mode": args.readiness_cache, "request": args.request, "handoff": {}}
               if args.readiness_cache != "off" else {})
    bac = tdq_lsp.chay_kiem(project, **options)
    da_cai, no = cai_thieu(bac)
    da_shim, cb_shim, no_shim = kiem_va_cai_shim_python3()
    da_cai += da_shim
    canh_bao_shim = cb_shim
    no += no_shim
    them, no_mcp = khai_server_mcp(project)
    da_cai += [f"MCP `lsp` + {t}" for t in them]
    no += no_mcp
    xong, canh_bao = don_may()
    canh_bao += canh_bao_shim
    da_cai += xong
    da_va, no_hook = va_hook_xung_dot()
    da_cai += da_va
    bat_plugin, lech_plugin, no_plugin = kiem_plugin_user()
    da_cai += bat_plugin
    canh_bao += lech_plugin
    no += no_hook + no_plugin + no_skill_khong_ton_tai(project)
    dat_dryrun, chi_tiet_dryrun = kiem_dryrun_hook(GOC_REPO)
    if dat_dryrun:
        da_cai.append(f"hook dry-run: {chi_tiet_dryrun}")
    else:
        no.append(f"hook dry-run thất bại: {chi_tiet_dryrun}")
    if ghim_huong_dan_tool(os.path.expanduser(DUONG_INSTRUCTION)):
        da_cai.append(f"ghim hướng dẫn 3 tầng vào {DUONG_INSTRUCTION}")
    if dong_bo_mcp_plugin_cache():
        da_cai.append("đồng bộ .mcp.json vào cache plugin và mở permissions.allow")
    if tdq_devtool_mcp.is_enabled(cwd=project):
        st = tdq_devtool_mcp.check_devtool_setup()
        if not st["all_ready"]:
            if tdq_devtool_mcp.setup_devtool_mcp():
                da_cai.append("cấu hình Chrome DevTools MCP (~/.claude.json, permissions.allow, profile)")
            else:
                no.append("lỗi tự động cài đặt Chrome DevTools MCP")
        else:
            da_cai.append("Chrome DevTools MCP đã sẵn sàng")
    try:
        dat_archify, chi_tiet_archify = kiem_tra_archify(project)
        if dat_archify:
            da_cai.append(f"tiện ích Archify: {chi_tiet_archify}")
        else:
            canh_bao.append(f"tiện ích Archify: {chi_tiet_archify}")
    except Exception as exc:  # noqa: BLE001
        canh_bao.append(f"lỗi kiểm tra tiện ích Archify: {exc}")
    _record_tree_sitter_status(da_cai, canh_bao)
    phien_ban_moi = doc_phien_ban_plugin(GOC_REPO)
    if phien_ban_moi:
        ghi_phat_hanh(project, phien_ban_moi)

    for dong in da_cai:
        print(f"đã cài · {dong}")
    for dong in canh_bao:
        print(f"cảnh báo · {dong}")
    if them:
        print("→ Claude Code chỉ đọc cấu hình MCP lúc khởi động: gõ /mcp và kết nối lại `lsp` "
              "(hoặc mở phiên mới) rồi chạy kịch bản của bậc 8.")
    if khai_codex:
        try:
            for dong in khai_codex():
                print(f"codex · {dong}")
        except Exception as exc:  # noqa: BLE001 — Codex is optional; setup goes on without it
            no.append(f"không khai được MCP cho Codex: {type(exc).__name__}: {exc}")
    print("")

    # The very same check `tdq_lsp.py check` runs — re-run after installing, so the ladder and
    # the smoke report the machine as it is now, under one total line.
    rc, _, smoke = tdq_lsp.kiem_mot_lenh(project, **options)
    no += [f"tầng {ten} không trả lời được: {chi_tiet}" for ten, dat, chi_tiet in smoke if not dat]

    for dong in no:
        print(f"nợ · {dong}")
    so = tdq_no.ghi_no(no, project)
    print("")
    print(f"Nợ: {len(no)} món ({so} dòng mới) → {tdq_no.FILE_NO}")
    return rc


_ORIG_GHIM_HUONG_DAN = ghim_huong_dan_tool


def is_antigravity_host():
    """Return True when running inside Antigravity plugin/agent context."""
    return tdq_lsp._is_antigravity_host(caller_file=__file__)


def _sync_agy_guard_ghim(duong, goc=None, khoi_fn=None):
    """Skip mutating ~/.claude/CLAUDE.md when running natively under Antigravity."""
    if is_antigravity_host() and ".claude" in os.path.expanduser(str(duong)).lower():
        _log("antigravity host: skipped ~/.claude/CLAUDE.md mutation")
        return False
    return _ORIG_GHIM_HUONG_DAN(duong, goc=goc, khoi_fn=khoi_fn)


ghim_huong_dan_tool = _sync_agy_guard_ghim


def _resolve_home(home: Optional[str] = None) -> Path:
    """Resolve user home from explicit arg, HOME, USERPROFILE, or Path.home."""
    if home is not None and str(home).strip():
        return Path(str(home)).expanduser()
    env_home = os.environ.get("HOME", "").strip() or os.environ.get("USERPROFILE", "").strip()
    return Path(env_home).expanduser() if env_home else Path.home()


def _is_temp_path(path: Path) -> bool:
    """Return True when `path` resides inside system temp or active test job root."""
    try:
        resolved = Path(path).resolve()
        roots = [Path(tempfile.gettempdir()).resolve()]
        job_root = os.environ.get("TDQ_TEST_JOB_ROOT", "").strip()
        if job_root:
            roots.append(Path(job_root).resolve())
        return any(resolved == root or root in resolved.parents for root in roots)
    except OSError:
        return False


def _can_write_home(home: Path) -> bool:
    """Allow home writes in live runs or inside isolated temp test homes."""
    return (not _khong_cham_may()) or _is_temp_path(home)


def _can_write_state(state_dir: Path) -> bool:
    """Allow state writes in live runs or inside isolated TDQ_SETUP_STATE_DIR/temp dirs."""
    has_override = bool(os.environ.get("TDQ_SETUP_STATE_DIR", "").strip())
    return (not _khong_cham_may()) or has_override or _is_temp_path(state_dir)


def _write_setup_log(state_dir: Path, message: str) -> None:
    """Append an ISO-timestamped log line to `${PLUGIN_DATA}/logs/setup.log`."""
    if not _log_enabled() or not _can_write_state(state_dir):
        return
    try:
        log_path = state_dir / "logs" / "setup.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with io.open(log_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(f"[{_now()}] {message}\n")
    except OSError:
        pass


@contextmanager
def _antigravity_host_context():
    """Temporarily ensure TDQ_HOST=antigravity during Antigravity manifest ops."""
    prev = os.environ.get("TDQ_HOST")
    if prev and prev.strip().lower() in ("antigravity", "agy"):
        yield
        return
    os.environ["TDQ_HOST"] = "antigravity"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop("TDQ_HOST", None)
        else:
            os.environ["TDQ_HOST"] = prev


def _active_agy_plugin_root(home: Optional[Path] = None) -> str:
    """Resolve installed Antigravity plugin root, falling back to repo/plugin dir."""
    resolved_home = home or _resolve_home()
    installed = resolved_home / ".gemini" / "config" / "plugins" / "tdq-workflow-agy"
    if (installed / "skills").is_dir() or (installed / "mcp_config.json").is_file():
        return str(installed)
    bundled = Path(GOC_REPO) / "plugins" / "tdq-workflow-agy"
    if (bundled / "skills").is_dir() or (bundled / "mcp_config.json").is_file():
        return str(bundled)
    return GOC_REPO


def pin_agy_gemini_md(
    gemini_md_path: Optional[str] = None, plugin_root: Optional[str] = None
) -> bool:
    """Pin the Antigravity <!-- TDQ:TOOLS --> block atomically into ~/.gemini/GEMINI.md."""
    home = _resolve_home()
    target = Path(gemini_md_path).expanduser() if gemini_md_path else (home / ".gemini" / "GEMINI.md")
    root = plugin_root or _active_agy_plugin_root(home)
    block = f"{MOC_MO}\n{khoi_huong_dan_agy(root)}\n{MOC_DONG}"
    if len(block.encode("utf-8")) >= GEMINI_PIN_MAX_BYTES:
        raise ValueError(f"Antigravity GEMINI pin exceeds {GEMINI_PIN_MAX_BYTES} bytes")
    return _ORIG_GHIM_HUONG_DAN(str(target), goc=root, khoi_fn=khoi_huong_dan_agy)


def _find_archify_for_home(home: Path) -> Optional[Path]:
    """Locate Archify installation honoring ARCHIFY_ROOT, ~/.local/share/archify, and ~/Documents/archify."""
    env_set, env_path = archify_delivery._check_env_archify_root()
    if env_set:
        return Path(env_path) if env_path else None
    candidates = [
        home / ".local" / "share" / "archify",
        home / "Documents" / "archify",
    ]
    if not _is_temp_path(home):
        found = archify_delivery.find_archify_root()
        if found:
            candidates.insert(0, Path(found))
    for cand in candidates:
        if archify_delivery.get_archify_bin(cand) is not None:
            return cand
    return None


def _run_git_cmd(args: list[str], timeout: int = 120) -> tuple[int, str]:
    """Run git command without shell or console window on Windows."""
    try:
        proc = tdq_ten_lenh.chay_subprocess(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        return proc.returncode, out
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)


def _validate_archify_origin(repo_dir: Path) -> tuple[bool, str]:
    """Verify existing Archify git checkout points strictly at upstream tt-a1i/archify."""
    rc, url_out = _run_git_cmd(["git", "-C", str(repo_dir), "remote", "get-url", "origin"])
    if rc != 0:
        return False, "unable to verify archify git origin remote"
    norm = url_out.strip().rstrip("/")
    if norm.lower().endswith(".git"):
        norm = norm[:-4]
    expected = ARCHIFY_REPO_URL[:-4] if ARCHIFY_REPO_URL.lower().endswith(".git") else ARCHIFY_REPO_URL
    if norm.lower() != expected.lower():
        return False, f"unexpected archify git origin: {url_out.strip()[:80]}"
    return True, "ok"


def _clone_or_update_archify(existing: Optional[Path], install_dir: Path) -> tuple[bool, str]:
    """Clone or fast-forward pull Archify via git after verifying official origin."""
    git_bin = shutil.which("git")
    if existing is not None:
        if (existing / ".git").is_dir() and git_bin:
            ok_orig, msg_orig = _validate_archify_origin(existing)
            if not ok_orig:
                return False, msg_orig
            rc, out = _run_git_cmd([git_bin, "-C", str(existing), "pull", "--ff-only"])
            if rc != 0:
                _log(f"WARN archify git pull failed: {out[:120]}")
        return True, str(existing)
    if not git_bin:
        return False, "git executable not found in PATH"
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    rc, out = _run_git_cmd(
        [git_bin, "clone", "--branch", "main", "--depth", "1", "--", ARCHIFY_REPO_URL, str(install_dir)]
    )
    if rc != 0:
        detail = out.splitlines()[0][:120] if out else str(rc)
        return False, f"git clone archify failed: {detail}"
    return True, str(install_dir)


def _local_archify_result(existing: Optional[Path]) -> tuple[bool, str]:
    """Return local-only Archify status without touching network."""
    if existing is not None:
        _log(f"archify ready at {existing} (local-only)")
        return True, str(existing)
    reason = "TDQ_KHONG_CHAM_MAY=1" if _khong_cham_may() else "opt_in_required"
    _log(f"archify missing; skipped network clone because {reason}")
    return False, f"skipped: {reason}"


def ensure_archify_installed(
    home: Optional[str] = None, allow_network: bool = True
) -> tuple[bool, str]:
    """Ensure Archify is installed at ~/.local/share/archify; respect TDQ_KHONG_CHAM_MAY=1."""
    env_root = os.environ.get("ARCHIFY_ROOT", "").strip()
    target_home = _resolve_home(home)
    existing = _find_archify_for_home(target_home)
    if env_root and existing is None:
        return False, f"ARCHIFY_ROOT is invalid: {env_root}"
    if _khong_cham_may() or not allow_network:
        return _local_archify_result(existing)
    ok_git, target_or_err = _clone_or_update_archify(existing, target_home / ".local" / "share" / "archify")
    if not ok_git:
        return False, target_or_err
    target_dir = Path(target_or_err)
    if archify_delivery.get_archify_bin(target_dir) is None:
        return False, f"archify.mjs missing under {target_dir}"
    node_ok, _, node_errs = archify_delivery._check_node_environment()
    if not node_ok:
        return False, "; ".join(node_errs) or "Node.js >= 18 required for Archify"
    _log(f"archify ready at {target_dir}")
    return True, str(target_dir)


def _run_tree_sitter_pip(missing: list[str]) -> tuple[bool, str]:
    """Install allowlisted missing tree-sitter packages via pip --user without shell."""
    cmd = [sys.executable, "-m", "pip", "install", "--user", *missing]
    try:
        proc = tdq_ten_lenh.chay_subprocess(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_CAI,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _log(f"ensure_tree_sitter_installed subprocess error: {exc}")
        return False, f"pip install failed for {', '.join(missing)}: {exc}"
    if proc.returncode != 0:
        out = ((proc.stderr or "") or (proc.stdout or "")).strip()
        snippet = out.splitlines()[-1][:160] if out else f"exit={proc.returncode}"
        _log(f"ensure_tree_sitter_installed pip rc={proc.returncode}: {snippet}")
        return False, (
            f"pip install failed ({proc.returncode}) "
            f"for {', '.join(missing)}: {snippet}"
        )
    import importlib

    importlib.invalidate_caches()
    after = _probe_tree_sitter_support()
    if after.get("available"):
        detail = _format_tree_sitter_ok(after)
        _log(f"ensure_tree_sitter_installed installed {missing}: {detail}")
        return True, detail
    still_missing = after.get("missing") or missing
    _log(f"ensure_tree_sitter_installed incomplete after pip: {still_missing}")
    return False, f"tree-sitter still missing after install: {', '.join(still_missing)}"


def ensure_tree_sitter_installed(allow_network: bool = True) -> tuple[bool, str]:
    """Ensure tree-sitter core and 4 grammars exist; honor TDQ_KHONG_CHAM_MAY=1."""
    info = _probe_tree_sitter_support()
    allowlist = set(TREE_SITTER_PACKAGES)
    missing = [pkg for pkg in (info.get("missing") or []) if pkg in allowlist]
    if info.get("available") and not missing:
        detail = _format_tree_sitter_ok(info)
        _log(f"ensure_tree_sitter_installed ready: {detail}")
        return True, detail
    if not missing:
        return False, "tree-sitter check failed: no installable packages in allowlist"
    if _khong_cham_may() or not allow_network:
        reason = "TDQ_KHONG_CHAM_MAY=1" if _khong_cham_may() else "allow_network=False"
        pkg_list = ", ".join(missing)
        hint = f"pip install --user {' '.join(missing)}"
        _log(f"ensure_tree_sitter_installed skipped ({reason}): {pkg_list}")
        return False, (
            f"missing tree-sitter packages ({reason}): "
            f"{pkg_list}; install via: {hint}"
        )
    return _run_tree_sitter_pip(missing)


def _agy_cli_env(home: Path) -> dict[str, str]:
    """Build environment for `agy` subprocess aligned with `home`."""
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["GEMINI_CONFIG_DIR"] = str(home / ".gemini" / "config")
    env["ANTIGRAVITY_GEMINI_DIR"] = str(home / ".gemini")
    return env


def _probe_agy_cli_plugins(resolved_home: Path) -> Optional[list[dict[str, Any]]]:
    """Query `agy plugin list --json`; return None when CLI absent or failed."""
    agy_bin = shutil.which("agy")
    if not agy_bin:
        return None
    try:
        proc = tdq_ten_lenh.chay_subprocess(
            [agy_bin, "plugin", "list", "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=_agy_cli_env(resolved_home), timeout=10,
        )
        parsed = json.loads(proc.stdout or "[]") if proc.returncode == 0 else None
        if isinstance(parsed, list):
            return [p for p in parsed if isinstance(p, dict)]
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        _log(f"agy plugin list failed: {type(exc).__name__}")
    return None


def _scan_agy_plugin_dirs(plugins_dir: Path) -> list[dict[str, Any]]:
    """Collect installed plugin metadata directly from ~/.gemini/config/plugins."""
    if not plugins_dir.is_dir():
        return []
    disk: list[dict[str, Any]] = []
    for pdir in sorted(plugins_dir.iterdir()):
        manifest = pdir / "plugin.json"
        if not manifest.is_file():
            continue
        try:
            meta = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        disk.append({
            "name": str(meta.get("name") or pdir.name),
            "enabled": True,
            "version": str(meta.get("version") or ""),
            "path": str(pdir),
        })
    return disk


def _probe_agy_plugins(home: Optional[str] = None) -> list[dict[str, Any]]:
    """Probe installed Antigravity plugins via `agy plugin list --json` with disk fallback."""
    resolved_home = _resolve_home(home)
    cli_plugins = _probe_agy_cli_plugins(resolved_home)
    if cli_plugins is not None:
        return cli_plugins
    return _scan_agy_plugin_dirs(resolved_home / ".gemini" / "config" / "plugins")


def _run_agy_plugin_cmd(args: list[str], home: Path) -> tuple[bool, str]:
    """Run an `agy plugin ...` subcommand safely."""
    agy_bin = shutil.which("agy")
    if not agy_bin:
        return False, "agy CLI not found"
    try:
        proc = tdq_ten_lenh.chay_subprocess(
            [agy_bin, "plugin", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_agy_cli_env(home),
            timeout=30,
        )
        out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        return proc.returncode == 0, out[:160]
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)


def _inspect_gemini_md(home: Path) -> dict[str, Any]:
    """Inspect ~/.gemini/GEMINI.md presence, markers, byte size, and Antigravity compliance."""
    path = home / ".gemini" / "GEMINI.md"
    if not path.is_file():
        return {
            "path": str(path), "exists": False, "pinned": False,
            "bytes": 0, "under_budget": True, "valid_agy_pin": False,
        }
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    pinned = (MOC_MO in text) and (MOC_DONG in text)
    forbidden = ("mcp__lsp__", "CLAUDE_" + "PLUGIN_ROOT", "EnterPlanMode", "AskUserQuestion")
    required = ("start_lsp", "tdq-intake", "/plan", "ask_question")
    valid_pin = (
        pinned
        and len(raw) < GEMINI_PIN_MAX_BYTES
        and all(tok in text for tok in required)
        and not any(tok in text for tok in forbidden)
    )
    return {
        "path": str(path),
        "exists": True,
        "pinned": pinned,
        "bytes": len(raw),
        "under_budget": len(raw) < GEMINI_PIN_MAX_BYTES,
        "valid_agy_pin": valid_pin,
    }


def _inspect_archify_for_home(home: Path) -> dict[str, Any]:
    """Inspect Node.js >= 18 and Archify location scoped to `home`."""
    node_ok, node_ver, node_errs = archify_delivery._check_node_environment()
    root = _find_archify_for_home(home)
    bin_path = archify_delivery.get_archify_bin(root) if root else None
    ready = bool(node_ok and root and bin_path)
    return {
        "ready": ready,
        "node_ok": node_ok,
        "node_version": node_ver,
        "root": str(root) if root else "",
        "bin": str(bin_path) if bin_path else "",
        "error": "; ".join(node_errs) if not node_ok else ("" if bin_path else "archify_not_found"),
    }


def _inspect_tree_sitter() -> dict[str, Any]:
    """Inspect tree-sitter core and 4 grammar packages for Antigravity manifest."""
    info = _probe_tree_sitter_support()
    missing = list(info.get("missing") or [])
    installed = bool(info.get("available")) and len(missing) == 0
    return {
        "installed": installed,
        "missing": missing,
        "languages": list(info.get("languages") or []),
        "version": str(info.get("version") or ""),
        "packages": list(TREE_SITTER_PACKAGES),
    }


def _inspect_lsp_core_agy(project: str) -> dict[str, Any]:
    """Collect Antigravity-safe Rungs 1-7 status without mutating project state."""
    rungs = [
        tdq_lsp.bac1_binary(),
        tdq_lsp.bac2_mcp(),
        tdq_lsp.bac3_language_server(project),
        tdq_lsp.bac4_quyen_tool(),
        tdq_lsp.bac5_hook_xung_dot(project),
        tdq_lsp.bac6_cau_hinh_goc_import(project),
        tdq_lsp.bac7_graphify(project),
    ]
    rows = [
        {
            "rung": b.so,
            "name": b.ten,
            "ok": bool(b.dat),
            "warn_only": bool(b.chi_canh_bao),
            "detail": b.chi_tiet,
            "fix": b.lenh_cai,
        }
        for b in rungs
    ]
    blocking = [r for r in rows if not r["ok"] and not r["warn_only"]]
    return {"ok": len(blocking) == 0, "blocking_count": len(blocking), "rungs": rows}


def _find_plugin_entry(plugins: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """Return installed plugin status summary from `_probe_agy_plugins` output."""
    match = next((p for p in plugins if p.get("name") == name), None)
    if not match:
        return {"installed": False, "enabled": False, "version": "", "path": ""}
    return {
        "installed": True,
        "enabled": bool(match.get("enabled")),
        "version": str(match.get("version") or ""),
        "path": str(match.get("path") or ""),
    }


def _build_manifest_actions(
    lsp_core: dict[str, Any],
    gemini_info: dict[str, Any],
    rtk_ok: bool,
    caveman_info: dict[str, Any],
    archify_info: dict[str, Any],
    cdp_plugin: dict[str, Any],
    tree_sitter_info: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build ordered list of setup actions needed for Antigravity."""
    actions: list[dict[str, Any]] = []
    if not lsp_core["ok"]:
        actions.append({"id": "fix_core_lsp", "category": "core", "blocking": True})
    if not gemini_info["valid_agy_pin"]:
        actions.append({"id": "pin_gemini_md", "category": "core", "blocking": True})
    if not rtk_ok:
        actions.append({"id": "install_rtk_rg", "category": "addon", "blocking": False})
    if not caveman_info.get("active"):
        actions.append({"id": "wrap_caveman_mcp", "category": "addon", "blocking": False})
    if not archify_info["ready"]:
        actions.append({"id": "install_archify", "category": "addon", "blocking": False})
    if tree_sitter_info is not None and not tree_sitter_info.get("installed"):
        actions.append(
            {"id": "install_tree_sitter", "category": "addon", "blocking": False}
        )
    if not cdp_plugin["enabled"]:
        actions.append({
            "id": "enable_chrome_devtools_plugin",
            "category": "optional_companion",
            "blocking": False,
        })
    return actions


def _inspect_tavily_and_chrome(
    state_dir: Path, devtool_status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Inspect optional Tavily key presence (never returning secret) and Chrome readiness."""
    secrets = tdq_setup_state.load_secrets_env(data_dir=state_dir)
    env_tavily = bool(os.environ.get("TAVILY_API_KEY", "").strip())
    file_tavily = bool(secrets.get("TAVILY_API_KEY"))
    tavily_info = {
        "key_configured": env_tavily or file_tavily,
        "source": "env" if env_tavily else ("secrets_env" if file_tavily else "none"),
        "optional": True,
    }
    chrome_info = {
        "available": bool(devtool_status.get("chrome_available")),
        "chrome_path_env": bool(os.environ.get("CHROME_PATH", "").strip()),
        "mcp_registered": bool(devtool_status.get("mcp_registered")),
        "optional": True,
    }
    return tavily_info, chrome_info


def scan_setup_manifest(project: str) -> dict[str, Any]:
    """Scan Antigravity toolchain and return structured JSON manifest with 0 Claude debt."""
    import caveman_config
    import rtk_integration

    home, state_dir = _resolve_home(), tdq_setup_state.resolve_plugin_data_dir()
    with _antigravity_host_context():
        lsp_core = _inspect_lsp_core_agy(project)
        plugins = _probe_agy_plugins(home=str(home))
        caveman_info = caveman_config.probe_caveman(
            plugin_root=_active_agy_plugin_root(home), home=str(home)
        )
        rtk_probe = rtk_integration.probe_rtk(cwd=project)
        rg_path = rtk_integration.locate_rg_binary() or ""
        rtk_ok = bool(rtk_probe.get("valid")) and bool(rg_path)
        archify_info = _inspect_archify_for_home(home)
        tree_sitter_info = _inspect_tree_sitter()
        gemini_info = _inspect_gemini_md(home)
        devtool_status = tdq_devtool_mcp.check_devtool_setup(agy_plugins_probe=lambda: plugins)

    cdp_plugin = {**_find_plugin_entry(plugins, "chrome-devtools-plugin"), "optional": True}
    tavily_info, chrome_info = _inspect_tavily_and_chrome(state_dir, devtool_status)
    actions = _build_manifest_actions(
        lsp_core,
        gemini_info,
        rtk_ok,
        caveman_info,
        archify_info,
        cdp_plugin,
        tree_sitter_info=tree_sitter_info,
    )
    _log(f"scan_setup_manifest host=antigravity actions={len(actions)} claude_debt=0")
    rtk_summary = {
        "valid": bool(rtk_probe.get("valid")), "collision": bool(rtk_probe.get("collision")),
        "version": str(rtk_probe.get("version") or ""), "rg_path": rg_path, "ok": rtk_ok,
    }
    return {
        "schema_version": 1, "host": "antigravity", "project": str(project),
        "claude_debt_count": 0, "state_dir": str(state_dir),
        "setup_state": tdq_setup_state.load_setup_state(data_dir=state_dir),
        "core": {
            "tdq_lsp": lsp_core, "gemini_md": gemini_info,
            "tdq_workflow_agy": _find_plugin_entry(plugins, "tdq-workflow-agy"),
        },
        "addons": {
            "rtk": rtk_summary,
            "caveman": caveman_info,
            "archify": archify_info,
            "tree_sitter": tree_sitter_info,
        },
        "optional_companions": {
            "chrome_devtools_plugin": cdp_plugin, "chrome_browser": chrome_info, "tavily": tavily_info,
        },
        "actions": actions,
    }


def _apply_core_agy_tools(
    project: str, dry_run: bool, applied: list[str], skipped: list[str]
) -> dict[str, Any]:
    """Install/verify core 3-tier LSP tools for Antigravity without touching ~/.claude*."""
    bac = [
        tdq_lsp.bac1_binary(),
        tdq_lsp.bac2_mcp(),
        tdq_lsp.bac3_language_server(project),
        tdq_lsp.bac4_quyen_tool(),
        tdq_lsp.bac5_hook_xung_dot(project),
        tdq_lsp.bac7_graphify(project),
    ]
    missing = [b.ten for b in bac if not b.dat and not b.chi_canh_bao]
    if dry_run:
        if missing:
            skipped.append(f"core_install_dry_run:{','.join(missing)}")
        return {"dry_run": True, "missing": missing, "installed": [], "debt": []}
    da_cai, no = cai_thieu(bac)
    da_shim, _, no_shim = kiem_va_cai_shim_python3()
    don_may()
    applied.extend(da_cai + da_shim)
    return {"dry_run": False, "missing": missing, "installed": da_cai + da_shim, "debt": no + no_shim}


def _apply_rtk_addon(
    project: str, setupfully: bool, dry_run: bool, applied: list[str], skipped: list[str]
) -> dict[str, Any]:
    """Probe and optionally install RTK + ripgrep."""
    import rtk_integration

    rtk_probe = rtk_integration.probe_rtk(cwd=project)
    rg_bin = rtk_integration.locate_rg_binary()
    if bool(rtk_probe.get("valid") and rg_bin):
        if not dry_run:
            rtk_integration.ensure_rtk_config()
        return {"ok": True, "installed": False}
    if setupfully and not dry_run:
        res = rtk_integration.install_rtk_and_rg(approve=True)
        ok = bool(res.get("ok"))
        if ok:
            applied.append("rtk_and_rg")
        return {"ok": ok, "installed": ok}
    skipped.append("rtk_and_rg:dry_mode_or_opt_in")
    return {"ok": False, "installed": False}


def _apply_caveman_addon(
    home: Path, setupfully: bool, applied: list[str], skipped: list[str]
) -> dict[str, Any]:
    """Wrap installed Antigravity mcp_config.json via Node launcher and enable Caveman."""
    import caveman_config

    installed_plugin = home / ".gemini" / "config" / "plugins" / "tdq-workflow-agy"
    installed_mcp = installed_plugin / "mcp_config.json"
    if not (setupfully and installed_mcp.is_file() and _can_write_home(home)):
        skipped.append("caveman_node_wrap:no_installed_mcp_or_dry")
        return {"wrapped": [], "enabled": False}
    proxy = installed_plugin / "scripts" / caveman_config.PROXY_SCRIPT_NAME
    wrapped = caveman_config.wrap_mcp_config(installed_mcp, proxy)
    cav_res = caveman_config.enable_caveman(
        approve=True,
        wrapped_servers=wrapped or list(caveman_config.CAVEMAN_MCP_SERVERS),
        home=str(home),
    )
    if wrapped:
        applied.append("caveman_node_wrap")
    return {"wrapped": wrapped, "enabled": bool(cav_res.get("enabled"))}


def _apply_addons_agy(
    project: str,
    home: Path,
    setupfully: bool,
    dry_run: bool,
    applied: list[str],
    skipped: list[str],
) -> dict[str, Any]:
    """Apply RTK, Caveman Node launcher, Archify, and tree-sitter installation."""
    rtk_status = _apply_rtk_addon(project, setupfully, dry_run, applied, skipped)
    caveman_status = _apply_caveman_addon(home, setupfully, applied, skipped)
    allow_net = bool(setupfully and not dry_run)
    archify_ok, archify_detail = ensure_archify_installed(
        home=str(home), allow_network=allow_net
    )
    if archify_ok:
        applied.append(f"archify:{archify_detail}")
    else:
        skipped.append(f"archify:{archify_detail}")
    ts_ok, ts_detail = ensure_tree_sitter_installed(allow_network=allow_net)
    if ts_ok:
        applied.append(f"tree_sitter:{ts_detail}")
    else:
        skipped.append(f"tree_sitter:{ts_detail}")
    return {
        "rtk": rtk_status,
        "caveman": caveman_status,
        "archify": {"ok": archify_ok, "detail": archify_detail},
        "tree_sitter": {"ok": ts_ok, "detail": ts_detail},
    }


def _apply_optional_companions_agy(
    home: Path,
    setupfully: bool,
    dry_run: bool,
    applied: list[str],
    skipped: list[str],
) -> dict[str, Any]:
    """Enable/check optional Antigravity companion plugins without blocking core gate."""
    plugins = _probe_agy_plugins(home=str(home))
    tdq_p = _find_plugin_entry(plugins, "tdq-workflow-agy")
    cdp_p = _find_plugin_entry(plugins, "chrome-devtools-plugin")
    if not dry_run:
        if tdq_p["installed"] and not tdq_p["enabled"]:
            ok, _ = _run_agy_plugin_cmd(["enable", "tdq-workflow-agy"], home)
            if ok:
                tdq_p["enabled"] = True
                applied.append("enable:tdq-workflow-agy")
        if setupfully and not cdp_p["enabled"]:
            cmd = ["enable", "chrome-devtools-plugin"] if cdp_p["installed"] else ["install", "chrome-devtools-plugin"]
            ok, _ = _run_agy_plugin_cmd(cmd, home)
            if ok:
                cdp_p["installed"] = True
                cdp_p["enabled"] = True
                applied.append(f"{cmd[0]}:chrome-devtools-plugin")
            else:
                skipped.append("chrome-devtools-plugin:optional_unavailable")
    elif not cdp_p["enabled"]:
        skipped.append("chrome-devtools-plugin:optional_dry_run")
    devtool_info = tdq_devtool_mcp.check_devtool_setup(agy_plugins_probe=lambda: plugins)
    return {
        "tdq_workflow_agy": tdq_p,
        "chrome_devtools_plugin": {**cdp_p, "blocking_core": False},
        "chrome_browser": {
            "available": bool(devtool_info.get("chrome_available")),
            "blocking_core": False,
        },
    }


def _persist_awaiting_restart_state(
    project: str, setupfully: bool, state_dir: Path
) -> tuple[str, bool]:
    """Compute host fingerprint and persist awaiting_restart + setup-pending.flag."""
    fp_info = tdq_setup_state.compute_host_session_fingerprint()
    fingerprint = str(fp_info.get("fingerprint", ""))
    payload = {
        "version": 2, "status": "awaiting_restart", "host": "antigravity",
        "setupfully": bool(setupfully), "project": str(project),
        "host_fingerprint": fingerprint,
        "host_root_pid": fp_info.get("root_pid"), "host_root_name": fp_info.get("root_name"),
    }
    if not _can_write_state(state_dir):
        return fingerprint, False
    tdq_setup_state.save_setup_state(payload, pending=True, data_dir=state_dir)
    return fingerprint, True


def apply_setup_manifest(
    project: str, setupfully: bool = False, tavily_key: str = ""
) -> dict[str, Any]:
    """Execute Antigravity Phase-1 setup and persist awaiting_restart + pending flag."""
    home, state_dir = _resolve_home(), tdq_setup_state.resolve_plugin_data_dir()
    dry_run = _khong_cham_may()
    applied, skipped = [], []
    resolved_tavily = _read_secret_arg(tavily_key) if tavily_key else ""
    if resolved_tavily and resolved_tavily.strip() and _can_write_state(state_dir):
        tdq_setup_state.save_tavily_secret(resolved_tavily, data_dir=state_dir)
        applied.append("tavily_secret_saved")
    with _antigravity_host_context():
        core_res = _apply_core_agy_tools(project, dry_run, applied, skipped)
        addons_res = _apply_addons_agy(project, home, setupfully, dry_run, applied, skipped)
        optional_res = _apply_optional_companions_agy(home, setupfully, dry_run, applied, skipped)
    if _can_write_home(home):
        if pin_agy_gemini_md(str(home / ".gemini" / "GEMINI.md"), _active_agy_plugin_root(home)):
            applied.append("gemini_md_pinned")
    else:
        skipped.append("gemini_md_pin:dry_mode")
    fp, persisted = _persist_awaiting_restart_state(project, setupfully, state_dir)
    _write_setup_log(state_dir, f"apply_setup_manifest setupfully={setupfully} dry_run={dry_run}")
    _log(f"apply_setup_manifest status=awaiting_restart pending=True dry_run={dry_run}")
    return {
        "ok": True, "dry_run": dry_run, "host": "antigravity", "claude_debt_count": 0,
        "setupfully": bool(setupfully), "status": "awaiting_restart", "pending": True,
        "state_persisted": persisted, "state_dir": str(state_dir), "host_fingerprint": fp,
        "core": core_res, "addons": addons_res, "optional_companions": optional_res,
        "gemini_md": _inspect_gemini_md(home),
        "actions_applied": applied, "actions_skipped": skipped,
    }


def _read_secret_arg(raw_arg: str) -> str:
    """Resolve API key from stdin when '-' is passed so secrets avoid process argv."""
    if raw_arg == "-":
        return sys.stdin.read().strip()
    return raw_arg


def _handle_set_tavily_key(
    api_key: str, state_dir: Optional[Path], as_json: bool
) -> int:
    """Validate and save TAVILY_API_KEY into secrets.env without echoing the key."""
    target_dir = state_dir or tdq_setup_state.resolve_plugin_data_dir()
    resolved_key = _read_secret_arg(api_key)
    try:
        saved_path = tdq_setup_state.save_tavily_secret(resolved_key, data_dir=target_dir)
    except (ValueError, PermissionError) as exc:
        print(f"tavily-key error: {exc}", file=sys.stderr)
        return 1
    _write_setup_log(target_dir, "saved TAVILY_API_KEY via --set-tavily-key (redacted)")
    if as_json:
        print(json.dumps({"ok": True, "secrets_path": str(saved_path)}))
    else:
        print(f"tavily-key · saved (redacted) -> {saved_path}")
    return 0


def _handle_post_restart_verify(
    confirm_restarted: bool, state_dir: Optional[Path], as_json: bool
) -> int:
    """Lazy-import tdq_simulate_verify, run 6-layer verification, and finalize state."""
    target_dir = state_dir or tdq_setup_state.resolve_plugin_data_dir()
    if confirm_restarted:
        tdq_setup_state.evaluate_restart_resume(
            is_new_turn=True, confirm_manual=True, data_dir=target_dir
        )
    # Lazy import required: scripts/tdq_simulate_verify.py is delivered in Wave 4 (T2.3).
    import tdq_simulate_verify

    plugin_root = Path(_active_agy_plugin_root())
    verify_res = tdq_simulate_verify.run_simulate_verify(
        plugin_root=plugin_root, data_dir=target_dir
    )
    core_pass = str(verify_res.get("core_gate", "")).upper() == "PASS"
    state = tdq_setup_state.load_setup_state(data_dir=target_dir)
    state["status"] = "verified" if core_pass else "verify_failed"
    state["verify_result"] = verify_res
    tdq_setup_state.save_setup_state(state, pending=not core_pass, data_dir=target_dir)
    _write_setup_log(target_dir, f"post-restart-verify core_gate={verify_res.get('core_gate')}")
    if as_json:
        print(json.dumps({"status": state["status"], "verify": verify_res}, ensure_ascii=False))
    else:
        print(
            f"post-restart-verify · core_gate={verify_res.get('core_gate')} "
            f"| optional_gate={verify_res.get('optional_gate')} | status={state['status']}"
        )
    return 0 if core_pass else 1


def _run_antigravity_apply_cli(args: argparse.Namespace, project: str) -> int:
    """Apply Phase-1 setup manifest and format either JSON or summary output."""
    receipt = apply_setup_manifest(
        project, setupfully=bool(args.setupfully), tavily_key=args.set_tavily_key
    )
    if args.json:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0
    print(
        f"setupfully · host=antigravity status={receipt['status']} "
        f"pending={receipt['pending']} claude_debt={receipt['claude_debt_count']} "
        f"state_dir={receipt['state_dir']}"
    )
    print("Phase 1 complete. Please restart Antigravity IDE, then send any message to run --post-restart-verify.")
    return 0


def _print_confirm_restarted(state_dir: Optional[Path]) -> int:
    """Confirm manual IDE restart transition and print resulting resume JSON."""
    target_dir = state_dir or tdq_setup_state.resolve_plugin_data_dir()
    res = tdq_setup_state.evaluate_restart_resume(
        is_new_turn=True, confirm_manual=True, data_dir=target_dir
    )
    print(json.dumps(res, ensure_ascii=False))
    return 0


def _handle_antigravity_cli(
    args: argparse.Namespace, project: str, state_dir: Optional[Path]
) -> Optional[int]:
    """Dispatch Antigravity Setupfully / Manifest / Verify CLI flags or default AGY host flow."""
    if args.set_tavily_key and not (args.setupfully or args.apply_manifest):
        return _handle_set_tavily_key(args.set_tavily_key, state_dir, args.json)
    if args.scan_json:
        print(json.dumps(scan_setup_manifest(project), indent=2, ensure_ascii=False))
        return 0
    if args.post_restart_verify:
        return _handle_post_restart_verify(args.confirm_restarted, state_dir, args.json)
    if args.confirm_restarted:
        return _print_confirm_restarted(state_dir)
    if args.setupfully or args.apply_manifest or is_antigravity_host():
        return _run_antigravity_apply_cli(args, project)
    return None


if __name__ == "__main__":
    sys.exit(chay_cli(sys.argv[1:]))
