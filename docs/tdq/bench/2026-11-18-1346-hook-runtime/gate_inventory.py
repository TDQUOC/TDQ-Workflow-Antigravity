#!/usr/bin/env python3
"""Inventory all [TDQ:*] gate/reminder codes from hook scripts and runtime metrics.

Scans `hooks/scripts/*.py` (plus `plugins/tdq-workflow-agy/hooks/scripts/*.py` and
delegated rules in `scripts/`) via AST + regex, cross-references `hook_impact.json`
and `false_positive_repro.json`, applies `tdq-lean` classification, and outputs
`gate_inventory.json` with 4-part instructional message proposals.

Env: TDQ_LOG=0 mutes stderr logging.
"""
import argparse
import ast
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys

SCHEMA_VERSION = "tdq-gate-inventory/v1"
TDQ_TAG_RE = re.compile(r"\[?(TDQ:[A-Z0-9_-]+)\]?")
MA_NAME_RE = re.compile(r"^(?:MA(?:_[A-Z]+)?|ma_[a-z]+)$")
GATE_CALLS = frozenset({
    "block",
    "remind",
    "remind_force",
    "stop_block",
    "already_reminded",
    "echo_line",
    "queue_remind",
})
VALID_CLASSIFICATIONS = frozenset({"chan_cung", "tu_sua", "huong_dan", "xoa"})
VALID_PROPOSAL_KEYS = ("chuyen_gi", "vi_sao", "lam_gi", "bo_qua")

# Internal ledger/dedupe keys mapped back to the canonical tag they emit.
ALIAS_TO_CANONICAL = {
    "TDQ:READ": "TDQ:DOC",
    "TDQ:SETUP-RTK": "TDQ:SETUP",
    "TDQ:SETUP-CAVEMAN": "TDQ:SETUP",
}

# Identifiers found in AST that are NOT standalone emitted [TDQ:*] gates.
NON_EMITTER_FILTER = {
    "TDQ:STOP": (
        "Internal default `code` argument for `stop_block`/`queue_remind` in "
        "`_common.py` and `stop_gate.py`; actual emitted tags are `[TDQ:STUCK]`, "
        "`[TDQ:UNFINISHED]`, `[TDQ:LOG]`, `[TDQ:TICK]`, `[TDQ:DOD]`, `[TDQ:NEXT]`."
    ),
    "TDQ:EDIT": "Reserved entry in `_common.AGY_CODES`; no active emitter in hooks/scripts.",
    "TDQ:TEST": "Reserved entry in `_common.AGY_CODES`; emitted only by scripts/tdq_test.py CLI.",
    "TDQ:DIRTY": "Reserved entry in `_common.AGY_CODES`; no active emitter in hooks/scripts.",
    "TDQ:NO-PLAN-MODE": "Reserved entry in `_common.AGY_CODES`; no active emitter in hooks/scripts.",
    "TDQ:LSP-WAIT": "Reserved entry in `_common.AGY_CODES`; no active emitter in hooks/scripts.",
    "TDQ:COMPACT": "Reserved entry in `_common.AGY_CODES`; no active emitter in hooks/scripts.",
    "TDQ:PAUSE": "Reserved entry in `_common.AGY_CODES`; no active emitter in hooks/scripts.",
    "TDQ:LECH": "Reserved entry in `_common.AGY_CODES`; no active emitter in hooks/scripts.",
    "TDQ:SCOPE": "Reserved entry in `_common.AGY_CODES`; no active emitter in hooks/scripts.",
}

UNWIRED_LEGACY_SCRIPTS = {
    "doc_file_gate.py": (
        "Standalone script emitting `[TDQ DOC-GATE REJECTION]`, not wired in hooks.json "
        "(tdq-lean: delete/yagni candidate)."
    ),
    "strategic_compact_gate.py": (
        "Standalone script emitting `[TDQ Strategic Compaction Advisory]`, not wired in "
        "hooks.json (tdq-lean: delete/yagni candidate)."
    ),
    "stop_batch_checker.py": (
        "Standalone script emitting `[TDQ Stop-Batch: ...]`, not wired in hooks.json "
        "(tdq-lean: delete/yagni candidate)."
    ),
}

# Raw tag quirks measured in hook_impact.py (scanned from index 0 of step text).
HOOK_IMPACT_NOTES = {
    "TDQ:LOG": (
        "hook_impact.json reports 2 PreToolUse hits under tag LOG, but the sample is an "
        "agent quote containing 'denied by pre-tool hook:'; edit_gate never blocks TDQ:LOG."
    ),
    "TDQ:NEXT": (
        "hook_impact.json reports 2 PreToolUse hits under tag NEXT whose sample is actually "
        "[TDQ:SEARCH] (hook_impact.py matched the earliest [TDQ:*] tag in step text)."
    ),
    "TDQ:WORKTREE": (
        "hook_impact.json reports 1 PreToolUse hit under tag WORKTREE whose sample is "
        "actually [TDQ:TEAM] (hook_impact.py matched the earliest [TDQ:*] tag in step text)."
    ),
}

# Exact catalog of all active [TDQ:*] gates/reminders across hooks/scripts/*.py,
# plugins/tdq-workflow-agy/hooks/scripts/*.py, and delegated scripts/.
GATE_CATALOG = {
    "TDQ:ANCHOR": {
        "file": "hooks/scripts/session_start.py",
        "events": ["SessionStart"],
        "dieu_kien": "SessionStart khi có active_request và source là 'compact' hoặc 'resume'.",  # i18n-allow
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Giữ neo trạng thái ngắn 1 dòng khi compact/resume; cắt dòng lặp "  # i18n-allow
            "MCP-First/ANTI-1..6 vì đã nằm trong user rules."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:ANCHOR] Compact recovery: request=<req> phase=<pha> source=<src> "
            "owner=<owner> plan=<plan_f> doing=<doing_str> ..."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Phiên vừa được compact hoặc mở lại nên ngữ cảnh cũ đã bị nén.",  # i18n-allow
            "vi_sao": "Giữ neo đúng request, phase, task đang làm [~] và worktree để không làm trùng hoặc lệch task.",  # i18n-allow
            "lam_gi": "Đọc `plan` và kiểm tra biên nhận/file hiện có rồi chạy `py -3 scripts/tdq_state.py next` trước khi gọi tool sửa.",  # i18n-allow
            "bo_qua": "Chỉ bỏ qua khi đã chuyển sang request mới (`tdq_state.py init`) hoặc phase đã là `idle`.",  # i18n-allow
        },
    },
    "TDQ:APPROVE": {
        "file": (
            "hooks/scripts/bash_gate.py, hooks/scripts/edit_gate.py, "
            "hooks/scripts/prompt_context.py, hooks/scripts/stop_gate.py"
        ),
        "events": ["PreInvocation", "PreToolUse", "Stop"],
        "dieu_kien": (
            "Chạy `tdq_state.py approve` / `set phase=` không khớp tín hiệu user trong lượt, "  # i18n-allow
            "hoặc sửa code ngoài `docs/` khi spec/plan/quick/mode chưa được duyệt, hoặc spec lệch sha256."  # i18n-allow
        ),
        "phan_loai": "chan_cung",
        "tdq_lean_note": (
            "shrink: Giữ chặn cứng ở PreToolUse (cổng an toàn/duyệt); bỏ lặp lại dòng nhắc dài "  # i18n-allow
            "trong PreInvocation khi trạng thái chưa đổi, dùng thẻ `metadata.user_markdown`."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:APPROVE] The user's prompt this turn did not approve <target> (or the mode differs) "
            "— STOP, do not run this command."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Lệnh duyệt hoặc thao tác sửa mã bị chặn vì lượt hiện tại chưa có xác nhận rõ ràng của người dùng.",  # i18n-allow
            "vi_sao": "Mọi cổng duyệt (spec, plan, quick, mode) phải do chính người dùng quyết định, cấm model tự suy diễn.",  # i18n-allow
            "lam_gi": "Trình bày bản cần duyệt trong chat, kết thúc lượt chờ user trả lời; khi user đã duyệt rõ mới chạy `py -3 scripts/tdq_state.py approve <target> --by \"<lời user>\"`.",  # i18n-allow
            "bo_qua": "Không có ngoại lệ (chỉ mở tự động ở vòng sửa QC khi cổng trước đó đã `*_approved = true`).",  # i18n-allow
        },
    },
    "TDQ:ASK": {
        "file": "hooks/scripts/ask_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": "Gọi tool `AskUserQuestion` trong phase `implement` hoặc `qc` khi chưa đặt `implement_pause`.",  # i18n-allow
        "phan_loai": "xoa",
        "tdq_lean_note": (
            "delete: Trên Antigravity, `TDQ:ZERO-POPUP` trong chính `ask_gate.py` đã chặn mọi popup hỏi; "  # i18n-allow
            "0 deny/4 ngày và nội dung trùng quy tắc `lech add` trong skill `tdq-build`."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:ASK] An unmet spec threshold is no reason to ask: apply the §6 fallback, "
            "`lech add`, carry on."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Hệ thống nhắc không tự ý dừng giữa `implement`/`qc` để hỏi khi ngưỡng spec không đạt.",  # i18n-allow
            "vi_sao": "Tránh đứt mạch thực thi tự động vì các ngưỡng có thể xử lý bằng phương án dự phòng §6.",  # i18n-allow
            "lam_gi": "Áp dụng dự phòng trong spec §6 và chạy `py -3 scripts/tdq_state.py lech add \"<chi tiết>\"` rồi làm tiếp.",  # i18n-allow
            "bo_qua": "Hợp lệ khi gặp ca bất khả kháng (`mat-truy-cap`, `pha-huy`, `dau-vao-user`, `tran-qc`) sau khi chạy `tdq_state.py pause --loai <loại>`.",  # i18n-allow
        },
    },
    "TDQ:DEVTOOL": {
        "file": "hooks/scripts/session_start.py -> scripts/tdq_devtool_mcp.py",
        "events": ["SessionStart"],
        "dieu_kien": "SessionStart khi Chrome DevTools MCP được bật trong cấu hình project/plugin.",  # i18n-allow
        "phan_loai": "xoa",
        "tdq_lean_note": (
            "delete: Bơm trạng thái `[TDQ:DEVTOOL] ready/active` ở mọi phiên kể cả khi không mở trình duyệt "  # i18n-allow
            "và tốn thêm kiểm tra socket TCP 9222; chỉ báo lỗi cấu hình trong `TDQ:SETUP` nếu cần."  # i18n-allow
        ),
        "loi_hien_tai": "[TDQ:DEVTOOL] Chrome DevTools MCP: active (9222) / ready (auto-launch on call)",
        "loi_de_xuat": {
            "chuyen_gi": "Thông báo trạng thái kết nối Chrome DevTools MCP lúc mở phiên.",  # i18n-allow
            "vi_sao": "Giúp nhận biết Chrome DevTools MCP đã sẵn sàng hay thiếu cấu hình trước khi test UI.",  # i18n-allow
            "lam_gi": "Nếu dùng test trình duyệt mà báo thiếu, chạy `py -3 scripts/tdq_setup.py`; đề xuất xóa dòng báo khi đã sẵn sàng.",  # i18n-allow
            "bo_qua": "Bỏ qua hoàn toàn với các request không liên quan đến trình duyệt/web UI.",  # i18n-allow
        },
    },
    "TDQ:DOC": {
        "file": "hooks/scripts/read_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": (
            "Đọc lại toàn bộ file (>= 2 KB) không đổi size/mtime trong cùng phiên, "  # i18n-allow
            "đọc dải dòng trùng >= 70% từ 2 lần, hoặc đọc file dữ liệu > 32 KB."  # i18n-allow
        ),
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Gộp mã nội bộ `'READ'` về đúng `'TDQ:DOC'`; bỏ nhánh tính overlap 70% phức tạp, "  # i18n-allow
            "chỉ giữ nhắc 1 dòng ngắn qua hàng đợi lượt khi đọc lại nguyên file >= 2 KB hoặc file dữ liệu > 32 KB."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:DOC] <file> (<kb> KB) is already in context from an earlier read, unchanged. "
            "Need another part? Read it with offset/limit."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Tệp này chưa thay đổi nhưng vừa được đọc lại toàn bộ (hoặc file dữ liệu lớn > 32 KB).",  # i18n-allow
            "vi_sao": "Nội dung đọc vào ngữ cảnh sẽ bị model đọc lại ở mọi API call kế tiếp, làm tăng chi phí và độ trễ.",  # i18n-allow
            "lam_gi": "Dùng `read_file` kèm `StartLine`/`EndLine` cho phần mới, hoặc tóm tắt file dữ liệu bằng `py -3 scripts/tdq_ccr.py summarize \"<path>\"`.",  # i18n-allow
            "bo_qua": "Hợp lệ khi tệp vừa bị chỉnh sửa ngoài hoặc ngữ cảnh vừa bị compact nên cần đọc lại đúng vùng cần sửa.",  # i18n-allow
        },
    },
    "TDQ:DOD": {
        "file": "hooks/scripts/stop_gate.py",
        "events": ["Stop"],
        "dieu_kien": "Stop ở phase `report` hoặc `idle` khi QC đã PASS hết nhưng còn checkbox task/DoD chưa tick `[x]`.",  # i18n-allow
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Giữ nhắc 1 dòng không chặn ở cuối lượt đóng sổ; tận dụng cache trạng thái lượt "  # i18n-allow
            "thay vì đọc lặp plan/qc nhiều lần."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:DOD] Closing the books with boxes still open: <n> task(s), <m> DoD line(s). "
            "QC passed — tick them in the plan."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Phiên sắp kết thúc ở pha đóng báo cáo (QC đã PASS) nhưng trong plan vẫn còn ô `[ ]` chưa đánh dấu.",  # i18n-allow
            "vi_sao": "Tránh lệch sổ sách giữa kết quả QC đã đạt và trạng thái checkbox của plan.",  # i18n-allow
            "lam_gi": "Mở file plan và cập nhật `[x]` cho các task/mục DoD đã nghiệm thu trước khi xuất báo cáo cuối.",  # i18n-allow
            "bo_qua": "Hợp lệ khi có mục lệch đã ghi `lech add` và chờ người dùng chốt ở phase `report`.",  # i18n-allow
        },
    },
    "TDQ:FEEDBACK": {
        "file": "hooks/scripts/prompt_context.py",
        "events": ["PreInvocation"],
        "dieu_kien": "PreInvocation khi prompt chứa từ khóa `lỗi|bug|sửa lại|broken|fail|không chạy|sai rồi`.",  # i18n-allow
        "phan_loai": "xoa",
        "tdq_lean_note": (
            "delete: Khớp từ khóa thô trên mọi prompt gây báo nhầm cả khi đang chạy test đỏ hoặc bàn về lỗi; "  # i18n-allow
            "luồng `tdq-intake` đã phân loại bug/hotfix ngay lúc mở request."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:FEEDBACK] User reported bug/feedback: run `py -3 scripts/tdq_state.py hotfix <slug>` "
            "or open express fix cycle before editing."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Prompt có chứa từ khóa liên quan tới lỗi/hỏng nên hook gợi ý mở luồng hotfix.",  # i18n-allow
            "vi_sao": "Nhắc mở chu trình sửa lỗi thay vì sửa tay ngoài quy trình TDQ.",  # i18n-allow
            "lam_gi": "Nếu đúng là phản hồi lỗi mới từ user, chạy `py -3 scripts/tdq_state.py hotfix <slug>`; đề xuất xóa trigger từ khóa này.",  # i18n-allow
            "bo_qua": "Bỏ qua khi đang trong quá trình TDD đỏ-xanh hoặc thảo luận phân tích lỗi.",  # i18n-allow
        },
    },
    "TDQ:GATE": {
        "file": "hooks/scripts/bash_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": "Lệnh shell PowerShell (`Set-Content|Add-Content|Out-File|...`) chạm vào `docs/tdq/state.json|STATE.md`.",  # i18n-allow
        "phan_loai": "xoa",
        "tdq_lean_note": (
            "delete: Trùng 100% với `TDQ:STATE` (thậm chí `agy_pretooluse_gate.py` đã chặn cùng mẫu "  # i18n-allow
            "bằng mã `TDQ:STATE`); xóa mã `GATE` và gom vào `TDQ:STATE`."  # i18n-allow
        ),
        "loi_hien_tai": "[TDQ:GATE] Do not mutate TDQ state via PowerShell; use tdq_state.py CLI.",
        "loi_de_xuat": {
            "chuyen_gi": "Lệnh PowerShell định ghi trực tiếp vào tệp trạng thái TDQ.",  # i18n-allow
            "vi_sao": "Ghi tay làm hỏng schema hoặc mất đồng bộ giữa `state.json` và `STATE.md`.",  # i18n-allow
            "lam_gi": "Dùng CLI chuẩn `py -3 scripts/tdq_state.py set <k>=<v>` (hoặc `approve`/`init`); hợp nhất cảnh báo này về mã `TDQ:STATE`.",  # i18n-allow
            "bo_qua": "Không có ngoại lệ cho việc ghi trực tiếp file state.",  # i18n-allow
        },
    },
    "TDQ:GIT": {
        "file": (
            "hooks/scripts/bash_gate.py, hooks/scripts/agy_pretooluse_gate.py, "
            "hooks/scripts/stop_gate.py"
        ),
        "events": ["PreToolUse", "Stop"],
        "dieu_kien": (
            "Tạo branch/worktree bắt đầu bằng `claude|antigravity|gemini|codex` (chặn cứng), "  # i18n-allow
            "hoặc commit message chứa `Co-Authored-By` / `generated with` AI (nhắc/chặn)."  # i18n-allow
        ),
        "phan_loai": "chan_cung",
        "tdq_lean_note": (
            "shrink: Gộp logic kiểm tra trùng lặp giữa `bash_gate.py` và `agy_pretooluse_gate.py` "  # i18n-allow
            "vào một hàm thuần dùng chung; giữ chặn cứng vì lịch sử git khó đảo ngược."  # i18n-allow
        ),
        "loi_hien_tai": "[TDQ:GIT] AI-prefixed branch names are banned; name the branch after the work.",
        "loi_de_xuat": {
            "chuyen_gi": "Tên nhánh/worktree có tiền tố tên AI hoặc nội dung commit mang dấu attribution AI.",  # i18n-allow
            "vi_sao": "Quy tắc git của dự án cấm tên nhánh theo AI và cấm mọi dòng `Co-Authored-By` trong lịch sử commit.",  # i18n-allow
            "lam_gi": "Đổi tên nhánh theo công việc (vd `git switch -c fix/<mo-ta>`) và bỏ hoàn toàn dòng attribution AI khỏi commit message.",  # i18n-allow
            "bo_qua": "Không có ngoại lệ (nhánh thuộc worktree TDQ hợp lệ có tiền tố `tdq/...` được phép).",  # i18n-allow
        },
    },
    "TDQ:GON": {
        "file": (
            "hooks/scripts/session_start.py, hooks/scripts/subagent_start.py, "
            "hooks/scripts/prompt_context.py"
        ),
        "events": ["SessionStart", "SubagentStart", "PreInvocation"],
        "dieu_kien": (
            "SessionStart / SubagentStart nạp luật tinh gọn từ `chung.md` theo `muc_gat`; "  # i18n-allow
            "PreInvocation lặp 1 dòng nhắc ở phase `implement`."  # i18n-allow
        ),
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Giữ nạp 1 lần ở `SessionStart`/`SubagentStart`; XÓA kênh lặp `[TDQ:GON]` "  # i18n-allow
            "ở `prompt_context.py` (PreInvocation) để giảm ký tự bơm lặp trên 9.744 lượt gọi model."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:GON] muc_gat=full · build less than asked: climb the ladder from rung 1 "
            "(nothing new) before adding a file, class or layer."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Hệ thống nạp nhắc luật code tinh gọn (ít file mới, ít lớp trừu tượng đơn dụng) theo mức `muc_gat`.",  # i18n-allow
            "vi_sao": "Giữ code gọn, tránh over-engineering trước khi cân nhắc sửa trên file/hàm sẵn có.",  # i18n-allow
            "lam_gi": "Kiểm tra bậc thang từ bậc 1 (không thêm file/class mới) và chỉ ghi marker `ponytail:` nếu cần nợ kỹ thuật có ngưỡng.",  # i18n-allow
            "bo_qua": "Tắt qua cấu hình `muc_gat=off` trong state, hoặc bỏ qua khi đang ở ngoại lệ Refactor/Clean Architecture (Rung 1).",  # i18n-allow
        },
    },
    "TDQ:INTAKE": {
        "file": "hooks/scripts/prompt_context.py",
        "events": ["PreInvocation"],
        "dieu_kien": "PreInvocation khi chưa có `active_request` hoặc `phase == 'idle'` (phát hiện thêm `_tdq_direct`).",  # i18n-allow
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Quy tắc mở `tdq-intake` đã có trong user rule `TDQ:TOOLS`; chỉ phát ở lượt đầu "  # i18n-allow
            "khi mở phiên hoặc khi phát hiện `_tdq_direct`, không lặp lại ở mọi model call."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:INTAKE] No request is open — unless this prompt belongs to an intake round "
            "already running, open tdq-workflow:tdq-intake (or tdq-intake)."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Chưa có request TDQ đang mở (hoặc phiên đang ở trạng thái `idle`).",  # i18n-allow
            "vi_sao": "Đảm bảo mọi yêu cầu mới đi qua bước tiếp nhận `tdq-intake` để phân làn `quick`/`full` hoặc `_tdq_direct`.",  # i18n-allow
            "lam_gi": "Mở skill `tdq-intake` (hoặc chạy `py -3 scripts/tdq_state.py init <slug> <quick|full>` sau khi phân tích nếu là `_tdq_direct`).",  # i18n-allow
            "bo_qua": "Hợp lệ khi người dùng chỉ hỏi đáp nhanh không sửa đổi mã/tài liệu dự án.",  # i18n-allow
        },
    },
    "TDQ:LOG": {
        "file": "hooks/scripts/edit_gate.py, hooks/scripts/stop_gate.py, hooks/scripts/agy_stop_gate.py",
        "events": ["PreToolUse", "Stop"],
        "dieu_kien": (
            "PreToolUse nhắc khi file `docs/workinglog/YYYY-MM-DD.md` chưa tồn tại; "  # i18n-allow
            "Stop chặn (`stop_block`) khi repo có thay đổi ngoài bookkeeping nhưng workinglog không đổi."  # i18n-allow
        ),
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Bỏ chặn Stop bắt buộc gây 7 lượt quay đầu/4 ngày (gồm cả ca chặn nhầm file `docs/.staging*`); "  # i18n-allow
            "chuyển sang nhắc không chặn cuối lượt và bổ sung `docs/.staging` vào danh sách loại trừ."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:LOG] Repo changed (<culprit>), docs/workinglog/YYYY-MM-DD.md not appended. "
            "Run `tdq_finish.py --files <file> --log \"<summary>\"`, no hand Edit."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Kho mã nguồn có thay đổi trong lượt nhưng nhật ký làm việc hôm nay chưa được ghi thêm.",  # i18n-allow
            "vi_sao": "Lưu dấu vết ngắn gọn những file đã đổi và việc đã làm theo ngày để phục vụ tra cứu/handoff.",  # i18n-allow
            "lam_gi": "Chạy `py -3 scripts/tdq_finish.py --files <file> --log \"<tóm tắt>\"` hoặc ghi thêm 1 mục `## HH:MM — ...` vào `docs/workinglog/YYYY-MM-DD.md`.",  # i18n-allow
            "bo_qua": "Hợp lệ khi thay đổi chỉ nằm trong vùng nháp/bookkeeping (`docs/.staging*`, `docs/tdq/`, `graphify-out/`).",  # i18n-allow
        },
    },
    "TDQ:LSP": {
        "file": "hooks/scripts/lsp_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": (
            "`start_lsp` thiếu `language_id` hoặc sai `(root_dir, language_id)` trong `.tdq-lsp-module.json`; "  # i18n-allow
            "`blast_radius` > 3 file, `scope != 'exported'`, `include_transitive=True`, hoặc circuit breaker mở."  # i18n-allow
        ),
        "phan_loai": "tu_sua",
        "tdq_lean_note": (
            "shrink: Dùng `overwrite` của Antigravity để tự điền `language_id` từ `do_ngon_ngu_du_an` / "  # i18n-allow
            "`.tdq-lsp-module.json` và tự chuẩn hóa `scope='exported'` thay vì deny lặp 16 lần (48 deny/4 ngày)."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:LSP] start_lsp without language_id: agent-lsp starts every server and makes "
            "TypeScript current (crash 0xc0000409 / No Project on 2026-10-07)."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Lệnh `start_lsp` thiếu `language_id` (hoặc `blast_radius` yêu cầu phạm vi quá rộng gây treo server).",  # i18n-allow
            "vi_sao": "Thiếu `language_id` làm agent-lsp khởi động toàn bộ server và dễ sập tsserver; `blast_radius` rộng gây timeout 1800s.",  # i18n-allow
            "lam_gi": "Truyền rõ `language_id` (vd `\"language_id\": \"python\"`) khi gọi `start_lsp`, hoặc thu hẹp `blast_radius` còn <= 3 file với `scope=\"exported\"` (đề xuất tự sửa qua `overwrite`).",  # i18n-allow
            "bo_qua": "Hợp lệ khi dự án không dùng server ngôn ngữ nào hoặc đã có `.tdq-lsp-module.json` khớp sẵn để hook tự điền.",  # i18n-allow
        },
    },
    "TDQ:NEXT": {
        "file": (
            "hooks/scripts/session_start.py, hooks/scripts/prompt_context.py, "
            "hooks/scripts/stop_gate.py -> scripts/tdq_state.py"
        ),
        "events": ["SessionStart", "PreInvocation", "Stop"],
        "dieu_kien": "SessionStart và mọi lượt PreInvocation in 1 dòng tóm tắt trạng thái/lệnh kế tiếp; Stop nhắc nếu chưa thấy `next_run`.",  # i18n-allow
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Bỏ hoàn toàn dòng `[TDQ:NEXT] (same as last turn — unchanged)` khi hash không đổi "  # i18n-allow
            "trong `prompt_context.py` và bỏ lặp lại ở `stop_gate.py` (EFFECTS) để giảm 2,33M ký tự PreInvocation."  # i18n-allow
        ),
        "loi_hien_tai": "[TDQ:NEXT] <slug> · lane <lane> · phase <phase> · run: python3 scripts/tdq_state.py next",
        "loi_de_xuat": {
            "chuyen_gi": "Hiển thị nhanh request đang chạy, pha hiện tại và bước tiếp theo của quy trình TDQ.",  # i18n-allow
            "vi_sao": "Giúp agent đồng bộ trạng thái thật từ `state.json` thay vì đoán theo trí nhớ hội thoại.",  # i18n-allow
            "lam_gi": "Khi trạng thái vừa chuyển pha hoặc chưa rõ bước kế, chạy `py -3 scripts/tdq_state.py next`.",  # i18n-allow
            "bo_qua": "Bỏ qua việc bơm lại nếu pha và trạng thái giống hệt lượt trước (không in dòng `same as last turn`).",  # i18n-allow
        },
    },
    "TDQ:OUTPUT": {
        "file": "hooks/scripts/bash_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": (
            "Lệnh shell chạy `cat|git log|git diff|git show|ls -R` không giới hạn dòng "  # i18n-allow
            "(`head`/`tail`/`--stat`/`--oneline`...) và RTK không nén được."  # i18n-allow
        ),
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Khi RTK hoạt động đã tự nén qua `overwrite`; chỉ đẩy nhắc vào hàng đợi lượt "  # i18n-allow
            "(không ngắt tool) nếu RTK không hỗ trợ lệnh."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:OUTPUT] This command dumps its whole content into context — every output is "
            "re-read on every API call after it."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Lệnh shell sắp chạy có thể đổ toàn bộ nội dung dài vào ngữ cảnh hội thoại.",  # i18n-allow
            "vi_sao": "Output quá dài làm phình input token ở mọi lượt gọi model sau đó và dễ gây chạm ngưỡng timeout.",  # i18n-allow
            "lam_gi": "Thêm giới hạn ngay trong lệnh (vd `--stat`, `--oneline -n 20`, `| Select-Object -First 40`) hoặc đọc bằng `read_file` có `StartLine`/`EndLine`.",  # i18n-allow
            "bo_qua": "Hợp lệ khi thực sự cần đọc trọn vẹn toàn bộ đầu ra để đảm bảo chất lượng kiểm tra.",  # i18n-allow
        },
    },
    "TDQ:QC": {
        "file": "hooks/scripts/prompt_context.py",
        "events": ["PreInvocation"],
        "dieu_kien": "PreInvocation ở phase `qc` khi prompt có từ khóa `qc|kiểm tra|dod`.",  # i18n-allow
        "phan_loai": "xoa",
        "tdq_lean_note": (
            "delete: Checklist DoD, 5 câu hỏi SOLID và anti-fake-red đã được quy định trong skill "  # i18n-allow
            "`tdq-qc` và spec §6; nhắc thêm ở PreInvocation theo từ khóa là thừa (`yagni`/`delete`)."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:QC] Quality Control checklist: verify DoD items with evidence; "
            "check 5 SOLID questions (clean-code.md); ensure zero false red tests."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Đang ở pha QC nên hook nhắc kiểm tra DoD, 5 câu hỏi SOLID và bằng chứng test thật.",  # i18n-allow
            "vi_sao": "Đảm bảo nghiệm thu dựa trên kết quả chạy thật, không có test giả đỏ hoặc bỏ sót hạng mục DoD.",  # i18n-allow
            "lam_gi": "Chạy kiểm chứng theo bảng DoD ở spec §6 và ghi kết quả vào biên bản QC; đề xuất xóa nhắc lặp ở PreInvocation.",  # i18n-allow
            "bo_qua": "Bỏ qua khi đang ở phase ngoài `qc` hoặc đã thực hiện đầy đủ theo skill `tdq-qc`.",  # i18n-allow
        },
    },
    "TDQ:READONLY": {
        "file": "hooks/scripts/bash_gate.py, hooks/scripts/edit_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": "Subagent mang role chỉ đọc (`reviewer`, `qc-tester`, `browser`) gọi tool sửa file hoặc lệnh shell ghi file.",  # i18n-allow
        "phan_loai": "chan_cung",
        "tdq_lean_note": (
            "shrink: Hợp nhất danh sách role chỉ đọc giữa `bash_gate.py` và `edit_gate.py` "  # i18n-allow
            "(hiện `bash_gate.py` thiếu `qc-tester`) thành một hằng số chung trong `_common.py`."  # i18n-allow
        ),
        "loi_hien_tai": "[TDQ:READONLY] Subagent role `<role>` is strictly read-only and cannot modify files.",
        "loi_de_xuat": {
            "chuyen_gi": "Subagent chỉ có quyền đọc (`reviewer`/`qc-tester`/`browser`) đang cố sửa tệp hoặc ghi qua shell.",  # i18n-allow
            "vi_sao": "Giữ nguyên tắc tách biệt vai trò: agent review/QC chỉ kiểm chứng và báo cáo, không tự ý sửa mã nguồn.",  # i18n-allow
            "lam_gi": "Trả kết quả kiểm tra/lỗi phát hiện về cho leader qua `send_message` để leader giao `tdq-implementer` sửa.",  # i18n-allow
            "bo_qua": "Không có ngoại lệ (nếu cần sửa file hãy dispatch bằng role `tdq-implementer`).",  # i18n-allow
        },
    },
    "TDQ:RULE": {
        "file": "hooks/scripts/edit_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": (
            "Lần sửa mã nguồn đầu tiên theo đuôi `.py/.ts/.tsx/.js/.jsx` trên main (ngoài `tests/` "  # i18n-allow
            "và ngoài `.tdq-worktrees/`) khi có task `[~]`, phát `TDQ:RULE:PY|TS|JS`."  # i18n-allow
        ),
        "phan_loai": "xoa",
        "tdq_lean_note": (
            "delete: Quy chuẩn cyclomatic <= 10, cognitive <= 15 và lint đã nạp sẵn trong `tdq-build` / "  # i18n-allow
            "`tdq-implementer`, lại bỏ qua worktree đội; xóa giúp giảm nhánh I/O và nhiễu trên `edit_gate.py`."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:RULE:PY] Python: cyclomatic <= 10, cognitive <= 15; surgical edits only; "
            "no single-use abstraction."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Nhắc chuẩn độ phức tạp và lệnh lint ngôn ngữ ngay lần đầu chỉnh sửa tệp mã nguồn.",  # i18n-allow
            "vi_sao": "Giữ hàm gọn, dễ đọc và nhắc chạy `ruff`/`eslint` trước khi chốt task.",  # i18n-allow
            "lam_gi": "Chạy linter tương ứng sau khi sửa (vd `ruff check <file>`); đề xuất xóa reminder này ở `edit_gate.py` vì đã có trong skill.",  # i18n-allow
            "bo_qua": "Bỏ qua khi đang chạy trong worktree subagent hoặc với file ngoài `.py/.ts/.js`.",  # i18n-allow
        },
    },
    "TDQ:SEARCH": {
        "file": (
            "hooks/scripts/search_gate.py, hooks/scripts/command_gate.py -> scripts/search_rules.py, "
            "hooks/scripts/session_start.py"
        ),
        "events": ["PreToolUse", "SessionStart"],
        "dieu_kien": (
            "Chặn lệnh tìm kiếm code thô (Bash/Grep) trước khi hỏi tầng khái niệm LSP/graphify, "  # i18n-allow
            "lệnh có >1 nhánh đoán, hoặc chuỗi lệnh không parse được (`malformed`); SessionStart báo nền."  # i18n-allow
        ),
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Nguyên nhân deny #1 (85/196 ca, 7/8 ca tái hiện chặn nhầm `py -c`, PowerShell `@'...'@`, "  # i18n-allow
            "`curl -split \"`n\"`). Bỏ chặn nhánh `malformed` và chuyển toàn bộ sang ghi sổ + nhắc hướng dẫn không chặn."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:SEARCH] Command could not be parsed safely (malformed). "
            "Ask first: mcp__lsp__start_lsp ... / Code search before any concept query."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Lệnh tìm kiếm hoặc lệnh shell chứa ký tự trích dẫn phức tạp kích hoạt kiểm tra tầng tìm kiếm.",  # i18n-allow
            "vi_sao": "Ưu tiên hỏi LSP/Graphify trước khi grep mò giúp định vị đúng symbol và giảm bước tìm thử.",  # i18n-allow
            "lam_gi": "Nếu đang dò symbol/caller, gọi `start_lsp` -> `find_symbol` hoặc `graphify query \"<câu hỏi>\"`; nếu chạy script `py -3`/PowerShell thông thường thì cho phép chạy thẳng (chỉ nhắc, không chặn).",  # i18n-allow
            "bo_qua": "Hợp lệ khi tên symbol đã có trong prompt người dùng, đang ở phase `analyze`/`spec`, hoặc đang chạy lệnh không phải tìm kiếm code.",  # i18n-allow
        },
    },
    "TDQ:SETUP": {
        "file": "hooks/scripts/session_start.py",
        "events": ["SessionStart"],
        "dieu_kien": (
            "SessionStart phát hiện lỗi auto-update phiên bản, chưa cài đặt lần đầu, "  # i18n-allow
            "thiếu `rtk`/`rg`, hoặc tắt `caveman`."  # i18n-allow
        ),
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Gộp 4 dòng nhắc `nhac_setup`/`nhac_rtk`/`nhac_caveman`/`loi_cap_nhat` thành 1 dòng gọn "  # i18n-allow
            "hoặc đẩy ra thẻ `metadata.user_markdown` để không đội `SessionStart` lên ~4.000 ký tự."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:SETUP] Missing rtk/rg for token savings — ask user permission to run "
            "py -3 scripts/tdq_setup.py --with-rtk (or --mute-rtk-prompt to hide)."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Môi trường hiện thiếu công cụ hỗ trợ (như `rtk`/`rg`) hoặc chưa chạy setup TDQ cho repo.",  # i18n-allow
            "vi_sao": "Các công cụ như `rtk`/`rg` giúp nén output lệnh shell và tăng tốc tìm kiếm mà vẫn giữ kết quả.",  # i18n-allow
            "lam_gi": "Xin phép người dùng rồi chạy `py -3 scripts/tdq_setup.py --with-rtk`, hoặc tắt nhắc bằng `py -3 scripts/tdq_setup.py --mute-rtk-prompt`.",  # i18n-allow
            "bo_qua": "Hợp lệ khi người dùng không muốn cài công cụ bổ sung và đã tắt nhắc bằng cờ `--mute-*-prompt`.",  # i18n-allow
        },
    },
    "TDQ:STATE": {
        "file": (
            "hooks/scripts/bash_gate.py, hooks/scripts/agy_pretooluse_gate.py, "
            "hooks/scripts/edit_gate.py, hooks/scripts/stop_gate.py"
        ),
        "events": ["PreToolUse", "Stop"],
        "dieu_kien": (
            "Ghi trực tiếp `docs/tdq/state.json` hoặc `docs/tdq/STATE.md` qua shell (chặn cứng trên AGY, "  # i18n-allow
            "chặn subagent ở `edit_gate`, nhắc ở `bash_gate`/`edit_gate` main)."  # i18n-allow
        ),
        "phan_loai": "chan_cung",
        "tdq_lean_note": (
            "shrink: Gom logic phát hiện ghi file state từ `bash_gate`, `agy_pretooluse_gate`, `edit_gate` "  # i18n-allow
            "vào 1 hàm dùng chung (và xóa mã trùng `TDQ:GATE`)."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:STATE] writing docs/tdq/state.json or STATE.md straight through the shell "
            "is not allowed — use python3 scripts/tdq_state.py set|approve|init|reset."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Thao tác định sửa trực tiếp `docs/tdq/state.json` hoặc `docs/tdq/STATE.md` không qua CLI.",  # i18n-allow
            "vi_sao": "Tránh sai định dạng JSON, mất sha256 kiểm soát duyệt và làm lệch gương `STATE.md`.",  # i18n-allow
            "lam_gi": "Cập nhật trạng thái bằng CLI: `py -3 scripts/tdq_state.py set <key>=<value>` hoặc `approve <spec|plan|quick>`.",  # i18n-allow
            "bo_qua": "Không có ngoại lệ (subagent càng không được phép ghi state, phải báo về leader).",  # i18n-allow
        },
    },
    "TDQ:STUCK": {
        "file": "hooks/scripts/stop_gate.py",
        "events": ["Stop"],
        "dieu_kien": "Stop hook đã chặn `TDQ:UNFINISHED` liên tiếp quá `MAX_STREAK` (= 3) lần mà checkbox plan không đổi.",  # i18n-allow
        "phan_loai": "xoa",
        "tdq_lean_note": (
            "delete: Khi `TDQ:UNFINISHED` đã giới hạn ép tiếp tối đa 1 lần/lượt dựa vào `continuationActive`, "  # i18n-allow
            "cơ chế đếm `stop_streak.json` và mã hạ cấp `[TDQ:STUCK]` không còn cần thiết (`delete`/`yagni`)."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:STUCK] <n> open task(s). Finish plan or declare a genuine blocker with "
            "`tdq_state.py pause --loai <kind> --ly-do \"<why>\"`."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Vòng Stop đã chặn lặp quá 3 lần mà tiến độ checkbox không nhúc nhích nên hạ cấp thành cảnh báo kẹt.",  # i18n-allow
            "vi_sao": "Ngăn vòng lặp Stop vô hạn khi agent thực sự bị kẹt hoặc thiếu quyền.",  # i18n-allow
            "lam_gi": "Ghi rõ điểm tắc cho người dùng và chạy `py -3 scripts/tdq_state.py pause --loai <loại> --ly-do \"<lý do>\"`; đề xuất xóa mã này khi giới hạn Stop còn 1 lần/lượt.",  # i18n-allow
            "bo_qua": "Không áp dụng khi các task đã hoàn tất hoặc đã bật tạm dừng `pause`.",  # i18n-allow
        },
    },
    "TDQ:SUBAGENT": {
        "file": "plugins/tdq-workflow-agy/hooks/scripts/subagent_dispatch_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": (
            "Chặn `swarm action=add` khi `implement_mode != 'subagent'`; chặn `Workspace='branch'|'share'` "  # i18n-allow
            "khi prompt có `WORKTREE:`; nhắc nếu thiếu 5 trường bắt buộc của implementer."  # i18n-allow
        ),
        "phan_loai": "chan_cung",
        "tdq_lean_note": (
            "shrink: Giữ chặn `swarm` sai mode (`chan_cung`); riêng phần `Workspace` khi có `WORKTREE:` "  # i18n-allow
            "có thể nâng cấp thành tự sửa `overwrite` thành `Workspace='inherit'`."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:SUBAGENT] TDQ already isolated a git worktree (WORKTREE:); pass Workspace='inherit' "
            "to invoke_subagent."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Lệnh gọi subagent/swarm chưa khớp mode thực thi hoặc chọn sai `Workspace` khi đã cấp worktree riêng.",  # i18n-allow
            "vi_sao": "Tránh tách thêm nhánh chồng chéo lên worktree TDQ hoặc chạy song song khi plan chưa duyệt chế độ `subagent`.",  # i18n-allow
            "lam_gi": "Đặt `Workspace=\"inherit\"` nếu prompt đã có `WORKTREE:`, truyền đủ `TASK:/WORKTREE:/VÙNG FILE:/TEST:/TRẢ VỀ:`, và đảm bảo `implement_mode=subagent`.",  # i18n-allow
            "bo_qua": "Không có ngoại lệ cho `swarm`/`Workspace` sai; nhắc thiếu trường chỉ mang tính hướng dẫn.",  # i18n-allow
        },
    },
    "TDQ:TEAM": {
        "file": "hooks/scripts/edit_gate.py, hooks/scripts/bash_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": (
            "Subagent sửa project trước pha `implement`; hoặc ở mode `subagent` leader sửa vào vùng file "  # i18n-allow
            "đã giao cho subagent / thiếu bản đồ phân công; hoặc subagent ghi ra ngoài `VÙNG FILE`."  # i18n-allow
        ),
        "phan_loai": "chan_cung",
        "tdq_lean_note": (
            "shrink: Cổng an toàn đội (16 deny/4 ngày), giữ chặn cứng để tránh xung đột merge; "  # i18n-allow
            "rút gọn thông báo nhánh lỗi và gộp phần kiểm tra từ `bash_gate` + `edit_gate`."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:TEAM] Team mode with no assignment map — you may not edit code on main first. "
            "Run: python3 scripts/tdq_team.py assign (then audit, then wave)."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Thao tác sửa file vi phạm ranh giới phân công giữa leader và subagent (hoặc sửa code trước pha `implement`).",  # i18n-allow
            "vi_sao": "Ngăn 2 agent ghi đè cùng 1 file và đảm bảo leader không âm thầm làm thay phần việc đã giao qua đội.",  # i18n-allow
            "lam_gi": "Leader chạy `py -3 scripts/tdq_team.py assign` -> `audit` -> `open <TASK>`; subagent chỉ sửa đúng file trong `VÙNG FILE` hoặc báo leader nới vùng.",  # i18n-allow
            "bo_qua": "Không có ngoại lệ cho việc ghi ngoài `VÙNG FILE`; leader chỉ sửa trực tiếp khi task được ghi `tu_lam` trong bản đồ.",  # i18n-allow
        },
    },
    "TDQ:TICK": {
        "file": "hooks/scripts/edit_gate.py, hooks/scripts/stop_gate.py, hooks/scripts/agy_stop_gate.py",
        "events": ["PreToolUse", "Stop"],
        "dieu_kien": (
            "PreToolUse chặn khi phase `implement`/`qc` không có task `[~]`, có >1 task `[~]`, "  # i18n-allow
            "hoặc sửa 3 lần liên tiếp chưa đổi sha256 plan; Stop chặn khi repo đổi nhưng plan không đổi."  # i18n-allow
        ),
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Nguyên nhân deny #3 (30 deny/4 ngày, streak_repeat=16, tái hiện 2/2 ca vòng lặp ở "  # i18n-allow
            "`false_positive_repro.json`). Bỏ bộ đếm `STREAK_NGUONG=3` chặn giữa lúc edit, chuyển sang nhắc nhẹ."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:TICK] 3 edits in a row with no tick in the plan — close the task before editing on. "
            "Task still in progress → update notes or tasks in the plan file to reset the streak."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Đang sửa mã nguồn ở pha `implement`/`qc` nhưng chưa cập nhật dấu `[~]` / `[x]` trong file plan.",  # i18n-allow
            "vi_sao": "Giúp tiến độ plan phản ánh đúng việc đang làm và đo ETA từng task chính xác.",  # i18n-allow
            "lam_gi": "Mở file plan, giữ đúng 1 task đang làm ở trạng thái `[~]` và đổi sang `[x]` ngay khi test task đó xanh.",  # i18n-allow
            "bo_qua": "Hợp lệ khi sửa file dưới `tests/` (TDD red-first), file dưới `docs/`, hoặc khi subagent làm việc trong `.tdq-worktrees/`.",  # i18n-allow
        },
    },
    "TDQ:UNFINISHED": {
        "file": "hooks/scripts/stop_gate.py, hooks/scripts/agy_stop_gate.py",
        "events": ["Stop"],
        "dieu_kien": (
            "Stop khi phase là `implement`, plan vẫn còn task chưa `[x]`, không có task `[>]` "  # i18n-allow
            "đang chạy qua subagent, và chưa khai báo `implement_pause`."  # i18n-allow
        ),
        "phan_loai": "chan_cung",
        "tdq_lean_note": (
            "shrink: Tác nhân Stop lớn nhất (53/60 ca trong 4 ngày). Giữ chặn mềm bằng `decision: continue` "  # i18n-allow
            "nhưng giới hạn tối đa 1 lần/lượt qua cờ `continuationActive` của Antigravity (thay cho `MAX_STREAK=3`)."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:UNFINISHED] <n> open task(s). Keep working to the approved spec: mark [~], test, "
            "mark [x]. Small drift → `lech add`, continue; only true blockers → `tdq_state.py pause`."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Lượt trả lời sắp dừng lại trong khi plan vẫn còn task chưa hoàn thành ở pha `implement`.",  # i18n-allow
            "vi_sao": "Tránh agent dừng nửa chừng bỏ dở task khi chưa gặp blocker thật sự.",  # i18n-allow
            "lam_gi": "Đọc task mở kế tiếp trong plan, đánh dấu `[~]`, triển khai, chạy lệnh `Test:` đến khi xanh rồi tick `[x]`.",  # i18n-allow
            "bo_qua": "Hợp lệ khi đang chờ subagent (`[>]`), khi đã dừng có lý do qua `tdq_state.py pause --loai <loại> --ly-do \"<lý do>\"`, hoặc khi `continuationActive=true` đã ép tiếp 1 lần trong lượt.",  # i18n-allow
        },
    },
    "TDQ:VUNG": {
        "file": "hooks/scripts/codex_edit_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": (
            "Chạy trong sandbox Codex (`TDQ_CODEX_TASK` được đặt) và lệnh `apply_patch`/shell ghi "  # i18n-allow
            "trúng `TDQ_CODEX_KHOA` hoặc nằm ngoài `TDQ_CODEX_VUNG`."  # i18n-allow
        ),
        "phan_loai": "chan_cung",
        "tdq_lean_note": (
            "yagni: Chỉ dùng riêng cho chế độ Codex CLI; giữ chặn cứng để bảo vệ `VÙNG KHÓA` (test) "  # i18n-allow
            "nhưng có thể hợp nhất logic kiểm tra vùng với `TDQ:TEAM` nếu không dùng tách riêng."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:VUNG] `<duong>` nằm ngoài VÙNG FILE đã khai cho task — "
            "sửa đúng file trong vùng, hoặc báo leader nới vùng."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Phiên Codex định ghi vào tệp nằm ngoài `VÙNG FILE` hoặc chạm vào `VÙNG KHÓA` của task.",  # i18n-allow
            "vi_sao": "Ngăn task tự sửa file ngoài phạm vi hoặc sửa file test khóa trước khi đạt tiêu chuẩn.",  # i18n-allow
            "lam_gi": "Chỉ sửa các đường dẫn thuộc `VÙNG FILE` được giao; nếu thiếu file cần sửa thì dừng và báo leader mở rộng vùng.",  # i18n-allow
            "bo_qua": "Không có ngoại lệ trong phiên `TDQ_CODEX_TASK` (khi không có biến môi trường này hook tự đứng im).",  # i18n-allow
        },
    },
    "TDQ:WORKTREE": {
        "file": "hooks/scripts/prompt_context.py",
        "events": ["PreInvocation"],
        "dieu_kien": "PreInvocation khi sổ worktree (`tdq_worktree_registry.dong_mo`) còn dòng chưa đóng.",  # i18n-allow
        "phan_loai": "huong_dan",
        "tdq_lean_note": (
            "shrink: Chỉ hiện 1 lần ở `SessionStart` hoặc qua `user_markdown` khi chuyển sang `report`/`idle`, "  # i18n-allow
            "không chèn vào mỗi lượt gọi model ở `PreInvocation`."  # i18n-allow
        ),
        "loi_hien_tai": "[TDQ:WORKTREE] <n> worktree(s) still open — run: python3 scripts/tdq_team.py sweep",
        "loi_de_xuat": {
            "chuyen_gi": "Vẫn còn các git worktree tạm của đội chưa được dọn sau khi chạy task.",  # i18n-allow
            "vi_sao": "Tránh tích tụ worktree rác chiếm dung lượng đĩa và gây nhầm lẫn nhánh ở phiên sau.",  # i18n-allow
            "lam_gi": "Khi các task đã merge xong, chạy `py -3 scripts/tdq_team.py sweep` để dọn worktree mở.",  # i18n-allow
            "bo_qua": "Hợp lệ trong lúc các subagent của đợt song song vẫn đang làm việc trên worktree đó.",  # i18n-allow
        },
    },
    "TDQ:ZERO-POPUP": {
        "file": "hooks/scripts/ask_gate.py",
        "events": ["PreToolUse"],
        "dieu_kien": "Gọi tool `ask_question`, `ask_user_question` hoặc `AskUserQuestion` (trên AGY) khi có `active_request`.",  # i18n-allow
        "phan_loai": "chan_cung",
        "tdq_lean_note": (
            "shrink: Giữ chặn cứng theo quy tắc người dùng cấm mở popup hỏi; hợp nhất danh sách tên tool "  # i18n-allow
            "vào hằng số dùng chung và bỏ phần `TDQ:ASK` phía sau trên AGY."  # i18n-allow
        ),
        "loi_hien_tai": (
            "[TDQ:ZERO-POPUP] Popup question UI is banned during an active TDQ request. "
            "Ask numbered options (1a 2b 3c) directly in chat instead."
        ),
        "loi_de_xuat": {
            "chuyen_gi": "Agent vừa gọi công cụ popup hỏi người dùng trong khi có request TDQ đang mở.",  # i18n-allow
            "vi_sao": "Quy tắc bắt buộc yêu cầu mọi câu hỏi và cổng duyệt phải trao đổi trực tiếp trong chat để lưu lịch sử rõ ràng.",  # i18n-allow
            "lam_gi": "In trực tiếp các lựa chọn đánh số (`1a 2b 3c`) hoặc câu hỏi ra nội dung chat rồi kết thúc lượt chờ người dùng trả lời.",  # i18n-allow
            "bo_qua": "Không có ngoại lệ khi `active_request` đang mở.",  # i18n-allow
        },
    },
}


def _log_enabled() -> bool:
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message: str) -> None:
    """Emit one ISO-timestamped log line to stderr unless TDQ_LOG=0."""
    if _log_enabled():
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"[{stamp}] gate_inventory: {message}", file=sys.stderr)


def _collect_docstring_ids(tree: ast.AST) -> set[int]:
    """Return object ids of module, class, and function docstring AST nodes."""
    doc_ids: set[int] = set()
    body_holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if isinstance(node, body_holders) and node.body:
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                doc_ids.add(id(first.value))
    return doc_ids


def _normalize_code(raw: str) -> str:
    """Normalize a raw code token into canonical `TDQ:<CODE>` form."""
    token = raw.strip()
    return token if token.startswith("TDQ:") else f"TDQ:{token}"


def _extract_call_code(node: ast.Call) -> str | None:
    """Extract code string from a block/remind/stop_block/echo_line call AST node."""
    func = node.func
    fname = getattr(func, "id", None) or getattr(func, "attr", "")
    if fname not in GATE_CALLS:
        return None
    arg_idx = 0 if fname == "echo_line" else 2
    code_node = next((kw.value for kw in node.keywords if kw.arg == "code"), None)
    if code_node is None and fname != "stop_block" and len(node.args) > arg_idx:
        code_node = node.args[arg_idx]
    if not isinstance(code_node, ast.Constant) or not isinstance(code_node.value, str):
        return None
    val = code_node.value.strip()
    return _normalize_code(val) if re.match(r"^[A-Z0-9:_-]+$", val) else None


def _extract_assign_code(node: ast.Assign) -> str | None:
    """Extract `MA = "..."` / `MA_* = "..."` / `ma_* = "..."` constant assignments."""
    if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
        return None
    for target in node.targets:
        if isinstance(target, ast.Name) and MA_NAME_RE.match(target.id):
            val = node.value.value.strip()
            if val.startswith("TDQ:"):
                return val
    return None


def _scan_node_codes(node: ast.AST, doc_ids: set[int]) -> list[str]:
    """Return any TDQ codes emitted or referenced by a single AST node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
        return [
            m.group(1)
            for m in TDQ_TAG_RE.finditer(node.value)
            if m.group(1) == "TDQ:RULE" or not m.group(1).startswith("TDQ:RULE:")
        ]
    if isinstance(node, ast.Call):
        code = _extract_call_code(node)
        return [code] if code else []
    if isinstance(node, ast.Assign):
        code = _extract_assign_code(node)
        return [code] if code else []
    return []


def _scan_python_file(path: Path, rel_label: str) -> dict[str, list[str]]:
    """AST-scan one Python file for active TDQ gate/reminder codes (ignoring docstrings/comments)."""
    hits: dict[str, list[str]] = {}
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_label)
    doc_ids = _collect_docstring_ids(tree)
    for node in ast.walk(tree):
        for code in _scan_node_codes(node, doc_ids):
            hits.setdefault(code, []).append(f"{rel_label}:{node.lineno}")
    return hits


def _merge_hits(target: dict[str, list[str]], source: dict[str, list[str]]) -> None:
    """Merge sorted unique source locations into target."""
    for code, locs in source.items():
        existing = target.setdefault(code, [])
        for loc in locs:
            if loc not in existing:
                existing.append(loc)


def scan_hook_codes(root: Path) -> dict:
    """Scan hooks/scripts/*.py, plugin extra hooks, and delegated scripts for TDQ codes."""
    raw_hits: dict[str, list[str]] = {}
    hooks_dir = root / "hooks" / "scripts"
    scanned_files = sorted(hooks_dir.glob("*.py"))
    plugin_dir = root / "plugins" / "tdq-workflow-agy" / "hooks" / "scripts"
    extra_plugin_files = [
        plugin_dir / "subagent_dispatch_gate.py",
        plugin_dir / "post_invocation.py",
    ]
    for path in scanned_files + [p for p in extra_plugin_files if p.is_file()]:
        rel = path.relative_to(root).as_posix()
        _merge_hits(raw_hits, _scan_python_file(path, rel))

    # Delegated emitters invoked by search_gate / command_gate / session_start / prompt_context.
    delegated_specs = (
        ("scripts/search_rules.py", "TDQ:SEARCH"),
        ("scripts/tdq_devtool_mcp.py", "TDQ:DEVTOOL"),
        ("scripts/tdq_state.py", "TDQ:NEXT"),
    )
    for rel, expected_code in delegated_specs:
        dpath = root / rel
        if dpath.is_file():
            file_hits = _scan_python_file(dpath, rel)
            if expected_code in file_hits:
                _merge_hits(raw_hits, {expected_code: file_hits[expected_code]})

    filtered_out: dict[str, dict] = {}
    merged_aliases: dict[str, dict] = {}
    active_hits: dict[str, list[str]] = {}

    for code, locs in sorted(raw_hits.items()):
        if code in ALIAS_TO_CANONICAL:
            canon = ALIAS_TO_CANONICAL[code]
            merged_aliases[code] = {"merged_into": canon, "locations": locs[:5]}
            _merge_hits(active_hits, {canon: locs})
        elif code in NON_EMITTER_FILTER:
            filtered_out[code] = {"reason": NON_EMITTER_FILTER[code], "locations": locs[:5]}
        else:
            _merge_hits(active_hits, {code: locs})

    grepped_codes = sorted(active_hits.keys())
    return {
        "scanned_hooks_count": len(scanned_files),
        "scanned_plugin_extras": [p.relative_to(root).as_posix() for p in extra_plugin_files if p.is_file()],
        "scanned_delegated_scripts": [rel for rel, _ in delegated_specs],
        "grepped_codes": grepped_codes,
        "grepped_count": len(grepped_codes),
        "raw_hit_count": len(raw_hits),
        "active_locations": {k: active_hits[k][:8] for k in grepped_codes},
        "filter_metadata": {
            "method": "Python AST scan skipping comments and docstrings + delegated emitter cross-check",
            "merged_internal_keys": merged_aliases,
            "excluded_non_emitters": filtered_out,
            "unwired_legacy_scripts": UNWIRED_LEGACY_SCRIPTS,
        },
    }


def _tag_counts(rows: list[dict]) -> dict[str, int]:
    """Convert `[{tag, count}, ...]` rows into `{TDQ:TAG: count}`."""
    counts: dict[str, int] = {}
    for row in rows:
        tag = str(row.get("tag") or "")
        if tag and tag != "?":
            counts[_normalize_code(tag)] = int(row.get("count") or 0)
    return counts


def _load_repro_by_code(repro_path: Path) -> dict[str, dict]:
    """Aggregate false-positive reproduction cases grouped by canonical TDQ code."""
    if not repro_path.is_file():
        return {}
    group_to_code = {
        "search_malformed": "TDQ:SEARCH",
        "lsp_non_lsp": "TDQ:LSP",
        "tick_loop": "TDQ:TICK",
    }
    repro = json.loads(repro_path.read_text(encoding="utf-8"))
    by_code: dict[str, dict] = {}
    for case in repro.get("cases", []):
        code = group_to_code.get(str(case.get("group") or ""))
        if not code:
            continue
        bucket = by_code.setdefault(code, {"total_cases": 0, "reproduced": 0, "case_ids": []})
        bucket["total_cases"] += 1
        bucket["reproduced"] += int(bool(case.get("reproduced")))
        bucket["case_ids"].append(case.get("id"))
    return by_code


def _load_impact_metrics(bench_dir: Path) -> tuple[dict[str, int], dict[str, int], dict[str, dict]]:
    """Load 4-day deny/stop counts from hook_impact.json and cases from false_positive_repro.json."""
    impact_path = bench_dir / "hook_impact.json"
    impact = json.loads(impact_path.read_text(encoding="utf-8")) if impact_path.is_file() else {}
    deny_by_code = _tag_counts(impact.get("pretool_deny_by_tag", []))
    stop_by_code = _tag_counts(impact.get("stop_block_by_tag", []))
    repro_by_code = _load_repro_by_code(bench_dir / "false_positive_repro.json")
    return deny_by_code, stop_by_code, repro_by_code


def _validate_catalog_alignment(grepped_codes: list[str]) -> None:
    """Fail fast if AST-scanned codes diverge from GATE_CATALOG or any proposal field is invalid."""
    scanned_set = set(grepped_codes)
    catalog_set = set(GATE_CATALOG.keys())
    missing = sorted(scanned_set - catalog_set)
    extra = sorted(catalog_set - scanned_set)
    if missing or extra:
        raise ValueError(f"Catalog mismatch: missing={missing}, extra={extra}")
    for code, entry in GATE_CATALOG.items():
        if entry["phan_loai"] not in VALID_CLASSIFICATIONS:
            raise ValueError(f"{code}: invalid phan_loai {entry['phan_loai']!r}")
        proposal = entry["loi_de_xuat"]
        for key in VALID_PROPOSAL_KEYS:
            if not str(proposal.get(key) or "").strip():
                raise ValueError(f"{code}: empty loi_de_xuat.{key}")


def build_inventory(root: Path, bench_dir: Path) -> dict:
    """Build the complete gate inventory JSON payload."""
    scan = scan_hook_codes(root)
    _validate_catalog_alignment(scan["grepped_codes"])
    deny_by_code, stop_by_code, repro_by_code = _load_impact_metrics(bench_dir)

    cong = []
    by_phan_loai: dict[str, int] = {k: 0 for k in sorted(VALID_CLASSIFICATIONS)}
    for code in scan["grepped_codes"]:
        meta = GATE_CATALOG[code]
        phan_loai = meta["phan_loai"]
        by_phan_loai[phan_loai] += 1
        row = {
            "ma": code,
            "file": meta["file"],
            "events": meta["events"],
            "dieu_kien": meta["dieu_kien"],
            "deny_count_4d": deny_by_code.get(code, 0),
            "stop_count_4d": stop_by_code.get(code, 0),
            "phan_loai": phan_loai,
            "tdq_lean_note": meta["tdq_lean_note"],
            "loi_hien_tai": meta["loi_hien_tai"],
            "loi_de_xuat": meta["loi_de_xuat"],
            "source_locations": scan["active_locations"][code],
        }
        if code in HOOK_IMPACT_NOTES:
            row["hook_impact_note"] = HOOK_IMPACT_NOTES[code]
        if code in repro_by_code:
            row["false_positive_repro"] = repro_by_code[code]
        cong.append(row)

    return {
        "schema": SCHEMA_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "grepped_codes": scan["grepped_codes"],
        "grepped_count": scan["grepped_count"],
        "cong_count": len(cong),
        "sources": {
            "hooks_scripts_dir": "hooks/scripts/*.py",
            "hooks_scripts_files": scan["scanned_hooks_count"],
            "plugin_extra_files": scan["scanned_plugin_extras"],
            "delegated_scripts": scan["scanned_delegated_scripts"],
            "hook_impact_json": "docs/tdq/bench/2026-11-18-1346-hook-runtime/hook_impact.json",
            "false_positive_repro_json": "docs/tdq/bench/2026-11-18-1346-hook-runtime/false_positive_repro.json",
        },
        "filter_metadata": scan["filter_metadata"],
        "summary": {
            "by_phan_loai": by_phan_loai,
            "deny_count_4d_in_catalog": sum(r["deny_count_4d"] for r in cong),
            "stop_count_4d_in_catalog": sum(r["stop_count_4d"] for r in cong),
            "raw_hook_impact_notes": HOOK_IMPACT_NOTES,
        },
        "cong": cong,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint to generate gate_inventory.json."""
    default_root = Path(__file__).resolve().parents[4]
    default_bench = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Generate TDQ [TDQ:*] gate inventory JSON.")
    parser.add_argument("--root", default=str(default_root), help="Repository root directory.")
    parser.add_argument("--bench-dir", default=str(default_bench), help="Bench evidence directory.")
    parser.add_argument(
        "--json",
        dest="json_out",
        default=str(default_bench / "gate_inventory.json"),
        help="Output JSON file path.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    bench_dir = Path(args.bench_dir).resolve()
    payload = build_inventory(root, bench_dir)
    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = payload["summary"]["by_phan_loai"]
    _log(
        f"wrote {out_path} (grepped_count={payload['grepped_count']}, "
        f"summary={summary})"
    )
    print(
        f"gate_inventory: {payload['grepped_count']} codes -> {out_path} | "
        f"chan_cung={summary['chan_cung']} tu_sua={summary['tu_sua']} "
        f"huong_dan={summary['huong_dan']} xoa={summary['xoa']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
