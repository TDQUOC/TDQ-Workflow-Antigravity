#!/usr/bin/env python3
"""4-part Antigravity guidance dictionary and dual-channel formatters.

Provides the canonical 22 retained AGY gate codes, 7 removed lean codes,
Vietnamese 4-part user cards (What / Why / Next / Bypass), and concise English
model hints. Pure stdlib so build scripts can copy it straight to hooks/.

Env: TDQ_LOG=0 silences ISO-timestamped stderr debug logs.
"""
import os
import sys
from datetime import datetime

HARD_DENY_CODES: tuple[str, ...] = (
    "APPROVE",
    "GIT",
    "TEAM",
    "STATE",
    "READONLY",
    "VUNG",
    "ZERO-POPUP",
    "SUBAGENT",
    "UNFINISHED",
)

OVERWRITE_CODES: tuple[str, ...] = ("LSP", "SUBAGENT")

GUIDANCE_CODES: tuple[str, ...] = (
    "SEARCH",
    "TICK",
    "DOC",
    "LOG",
    "OUTPUT",
    "SETUP",
    "GON",
    "NEXT",
    "WORKTREE",
    "ANCHOR",
    "DOD",
    "INTAKE",
)

ALL_AGY_CODES: tuple[str, ...] = tuple(
    dict.fromkeys(HARD_DENY_CODES + OVERWRITE_CODES + GUIDANCE_CODES)
)

LEAN_REMOVED_CODES: tuple[str, ...] = (
    "ASK",
    "DEVTOOL",
    "FEEDBACK",
    "GATE",
    "QC",
    "RULE",
    "STUCK",
)

MAX_MODEL_HINT_CHARS = 160
MAX_MODEL_SUMMARY_CHARS = 200
MAX_USER_MARKDOWN_CHARS = 1200
MAX_DETAIL_CHARS = 320

_FOUR_PART_LABELS = (
    ("chuyen_gi", "Chuyện gì"),  # i18n-allow
    ("vi_sao", "Vì sao"),  # i18n-allow
    ("lam_gi", "Làm gì"),  # i18n-allow
    ("bo_qua", "Bỏ qua"),  # i18n-allow
)

GUIDANCE_TABLE: dict[str, dict[str, str]] = {
    "APPROVE": {
        "chuyen_gi": "Đang chờ người dùng duyệt bước hiện tại trước khi chuyển pha.",  # i18n-allow
        "vi_sao": "Duyệt rõ trong chat giúp chốt phạm vi và tránh suy đoán sai ý.",  # i18n-allow
        "lam_gi": "In lại khối lựa chọn trong chat rồi chạy `tdq_state.py approve` sau khi chốt.",  # i18n-allow
        "bo_qua": "Chỉ mở khi người dùng đã đồng ý rõ và cờ `*_approved` đã bật.",  # i18n-allow
        "model_hint": (
            "Wait for explicit user approval in chat, then record via tdq_state.py approve; "
            "never guess ambiguous replies."
        ),
    },
    "GIT": {
        "chuyen_gi": "Tên nhánh/worktree mở đầu bằng tên AI hoặc commit mang trailer AI.",  # i18n-allow
        "vi_sao": "Lịch sử Git phải thuần kỹ thuật và theo quy ước `<loại>/<mô-tả>`.",  # i18n-allow
        "lam_gi": "Đổi tên nhánh theo công việc và bỏ `Co-Authored-By:` khỏi commit.",  # i18n-allow
        "bo_qua": "Không có ngoại lệ cho tiền tố AI ở đầu nhánh hoặc trailer AI.",  # i18n-allow
        "model_hint": (
            "Rename branch/worktree away from AI prefixes (claude/antigravity/gemini/codex) "
            "and strip AI trailers from commits."
        ),
    },
    "TEAM": {
        "chuyen_gi": "Thao tác sửa file sai vùng phân công nhóm hoặc trước pha `implement`.",  # i18n-allow
        "vi_sao": "Khóa vùng ngăn các subagent ghi đè nhau và giữ đúng vai trò điều phối.",  # i18n-allow
        "lam_gi": "Chỉ sửa file trong vùng được giao hoặc mở task qua `tdq_team.py open`.",  # i18n-allow
        "bo_qua": "Subagent được ghi báo cáo vào `docs/tdq/artifacts/` hoặc khi leader đặt `tu_lam`.",  # i18n-allow
        "model_hint": (
            "Respect team assignment map and worktree bounds; do not edit delegated areas "
            "or source outside implement phase."
        ),
    },
    "STATE": {
        "chuyen_gi": "Thao tác định ghi tay trực tiếp vào `docs/tdq/state.json` hoặc `STATE.md`.",  # i18n-allow
        "vi_sao": "Sửa tay dễ lệch checksum, hỏng bản chiếu chỉ-đọc và gãy luồng pha.",  # i18n-allow
        "lam_gi": "Dùng CLI `py -3 scripts/tdq_state.py <set|approve|init|reset|pause>`.",  # i18n-allow
        "bo_qua": "Chỉ được đọc file state; không có ngoại lệ ghi trực tiếp ngoài CLI.",  # i18n-allow
        "model_hint": (
            "Never hand-edit docs/tdq/state.json or STATE.md; mutate workflow state "
            "exclusively via tdq_state.py CLI."
        ),
    },
    "READONLY": {
        "chuyen_gi": "Subagent vai trò chỉ đọc vừa gọi công cụ hoặc lệnh làm đổi file.",  # i18n-allow
        "vi_sao": "Vai trò kiểm tra phải độc lập với người viết code để đánh giá khách quan.",  # i18n-allow
        "lam_gi": "Dừng ghi file; chỉ đọc/chạy kiểm thử và trả kết quả về cho leader.",  # i18n-allow
        "bo_qua": "Không có ngoại lệ ghi file cho vai trò reviewer, qc-tester hay browser.",  # i18n-allow
        "model_hint": (
            "Read-only subagent cannot modify files; run diagnostics only and return "
            "structured findings to the leader."
        ),
    },
    "VUNG": {
        "chuyen_gi": "Đường dẫn ghi nằm ngoài `VÙNG FILE` được cấp hoặc vào vùng khóa.",  # i18n-allow
        "vi_sao": "Ranh giới vùng bảo vệ các nhánh song song không đè nhau và khóa file test.",  # i18n-allow
        "lam_gi": "Chỉ sửa file trong `VÙNG FILE`; nếu cần thêm file hãy báo leader nới vùng.",  # i18n-allow
        "bo_qua": "Chỉ mở sau khi leader cập nhật `VÙNG FILE` trong kế hoạch và giao lại.",  # i18n-allow
        "model_hint": (
            "Target path is outside allowed VUNG FILE or inside locked zone; edit only "
            "assigned paths or ask leader to widen scope."
        ),
    },
    "ZERO-POPUP": {
        "chuyen_gi": "Hệ thống vừa gọi popup hỏi người dùng trong lúc yêu cầu TDQ đang mở.",  # i18n-allow
        "vi_sao": "Mọi câu hỏi `1a 2b 3c` và dấu duyệt phải nằm trực tiếp trong luồng chat.",  # i18n-allow
        "lam_gi": "Bỏ công cụ popup; viết câu hỏi đánh số kèm phương án và dòng `➤` trong chat.",  # i18n-allow
        "bo_qua": "Chỉ dùng công cụ hỏi popup khi chưa có yêu cầu TDQ nào đang mở.",  # i18n-allow
        "model_hint": (
            "Popup question tools are banned during an active TDQ request; ask numbered "
            "options (1a 2b) directly in chat."
        ),
    },
    "SUBAGENT": {
        "chuyen_gi": "Lệnh subagent sai chế độ `swarm` hoặc lệch `Workspace` khi có `WORKTREE:`.",  # i18n-allow
        "vi_sao": "`WORKTREE:` đã tách nhánh sẵn nên cần `inherit`, còn `swarm` cần mode `subagent`.",  # i18n-allow
        "lam_gi": "Dùng `Workspace='inherit'`, điền đủ trường giao việc và chỉ `swarm` ở mode `subagent`.",  # i18n-allow
        "bo_qua": "Hook tự sửa `Workspace='inherit'` nếu chỉ sai tham số; `swarm` chỉ chạy khi đã duyệt.",  # i18n-allow
        "model_hint": (
            "Use Workspace='inherit' when WORKTREE: is provided, include all task fields, "
            "and use swarm only in subagent mode."
        ),
    },
    "UNFINISHED": {
        "chuyen_gi": "Định kết thúc lượt trong khi pha `implement` vẫn còn task mở `[ ]`/`[~]`.",  # i18n-allow
        "vi_sao": "Không được bỏ dở giữa chừng khi vẫn còn task chưa hoàn tất theo kế hoạch.",  # i18n-allow
        "lam_gi": "Làm tiếp task mở theo red → green và tick `[x]` trước khi dừng lượt.",  # i18n-allow
        "bo_qua": "Chỉ dừng khi đã chạy `pause --loai ...` hoặc `continuationActive=True`.",  # i18n-allow
        "model_hint": (
            "Open tasks remain in implement phase; finish them and tick [x] before "
            "stopping, or declare pause --loai."
        ),
    },
    "LSP": {
        "chuyen_gi": "Lời gọi LSP thiếu `language_id`, sai `(root, lang)`, hoặc `blast_radius` quá rộng.",  # i18n-allow
        "vi_sao": "Thiếu `language_id` dễ treo server sai ngôn ngữ; `blast_radius` rộng dễ timeout.",  # i18n-allow
        "lam_gi": "Truyền đúng `language_id`, giữ `blast_radius <= 3` file, `scope='exported'`.",  # i18n-allow
        "bo_qua": "Hook tự điền cho repo đơn ngữ; dùng `--bo-qua-lsp` chỉ cho doc hoặc nội tệp.",  # i18n-allow
        "model_hint": (
            "Pass explicit language_id (or rely on auto-overwrite), keep blast_radius "
            "<=3 files, scope='exported', include_transitive=False."
        ),
    },
    "SEARCH": {
        "chuyen_gi": "Tìm kiếm code bằng Grep/shell mà chưa hỏi tầng khái niệm LSP hoặc Graphify.",  # i18n-allow
        "vi_sao": "Đi qua LSP/Graphify trước giúp khoanh đúng symbol và giảm grep mò tốn token.",  # i18n-allow
        "lam_gi": "Gọi `find_symbol`, `find_references` hoặc `graphify query` trước khi grep tiếp.",  # i18n-allow
        "bo_qua": "Ân xá lần 1; pha `analyze`/`spec`, từ trong prompt hoặc lọc tên file được phép.",  # i18n-allow
        "model_hint": (
            "Query concept layer first (LSP find_symbol/find_references or graphify query) "
            "before consecutive grep; 1st miss is warned."
        ),
    },
    "TICK": {
        "chuyen_gi": "Code đã sửa nhưng ô kiểm `[~]`/`[x]` trong file kế hoạch chưa cập nhật.",  # i18n-allow
        "vi_sao": "Đánh dấu từng task giữ tiến độ khớp thực tế và hỗ trợ khôi phục khi gián đoạn.",  # i18n-allow
        "lam_gi": "Mở plan đánh dấu `[~]` khi đang làm và đổi `[x]` ngay sau khi test xanh.",  # i18n-allow
        "bo_qua": "Miễn khi sửa trong `tests/**`, worktree cô lập hoặc chưa có file kế hoạch.",  # i18n-allow
        "model_hint": (
            "Keep plan checkboxes synced: mark active task [~] and tick [x] "
            "immediately once its test passes."
        ),
    },
    "DOC": {
        "chuyen_gi": "Đọc lại toàn bộ một file chưa thay đổi trong cùng phiên (hoặc file dữ liệu lớn).",  # i18n-allow
        "vi_sao": "Đọc lặp nguyên file làm phình ngữ cảnh và tốn chi phí ở mọi lượt gọi sau.",  # i18n-allow
        "lam_gi": "Dùng `StartLine`/`EndLine` đúng đoạn cần xem hoặc `tdq_ccr.py` cho file > 32 KB.",  # i18n-allow
        "bo_qua": "Bỏ qua khi đọc lần đầu, đọc dải dòng mới, hoặc file vừa đổi nội dung.",  # i18n-allow
        "model_hint": (
            "Avoid whole-file re-reads of unchanged files; use StartLine/EndLine "
            "(or tdq_ccr.py summarize for >32KB data)."
        ),
    },
    "LOG": {
        "chuyen_gi": "Kho mã nguồn có thay đổi nhưng nhật ký `docs/workinglog/` hôm nay chưa cập nhật.",  # i18n-allow
        "vi_sao": "Nhật ký ghi lại file sửa, lý do và kết quả test để đối chiếu giữa các phiên.",  # i18n-allow
        "lam_gi": "Chạy `tdq_finish.py --files ... --log \"...\"`; không sửa tay file workinglog.",  # i18n-allow
        "bo_qua": "Bỏ qua ở lượt chỉ đọc hoặc khi chỉ sửa nháp trong `docs/.staging*`.",  # i18n-allow
        "model_hint": (
            "Repo changed without working log entry; run tdq_finish.py --files ... "
            "--log '...' (never hand-edit docs/workinglog)."
        ),
    },
    "OUTPUT": {
        "chuyen_gi": "Lệnh shell có nguy cơ xuất toàn bộ file hoặc log dài không giới hạn dòng.",  # i18n-allow
        "vi_sao": "Đầu ra dài chưa lọc chiếm đầy ngữ cảnh và lặp lại chi phí đọc ở bước sau.",  # i18n-allow
        "lam_gi": "Giới hạn bằng `head`/`tail`/`Select-Object`/`-n` hoặc dùng `read_file` theo dòng.",  # i18n-allow
        "bo_qua": "Bỏ qua khi `rtk` đã nén hợp lệ hoặc khi cần toàn bộ đầu ra để chẩn đoán.",  # i18n-allow
        "model_hint": (
            "Limit unbounded shell output with head/tail/Select-Object/-n or use "
            "read_file with line range (or rtk compression)."
        ),
    },
    "SETUP": {
        "chuyen_gi": "Thiếu công cụ hỗ trợ (`rtk`, `rg`, `caveman`, hoặc stub Python) hay chưa cài xong.",  # i18n-allow
        "vi_sao": "Đủ công cụ giúp tiết kiệm token, chạy đúng UTF-8 và bật đủ tìm kiếm 3 tầng.",  # i18n-allow
        "lam_gi": "Chạy `tdq_setup.py` / `tdq_lsp.py check`; đề xuất người dùng duyệt nếu cần cài thêm.",  # i18n-allow
        "bo_qua": "Bỏ qua khi đã tắt nhắc qua cờ mute hoặc không dùng công cụ tùy chọn đó.",  # i18n-allow
        "model_hint": (
            "Environment tool missing or setup incomplete; verify with tdq_setup.py / "
            "tdq_lsp.py check and ask user before installing."
        ),
    },
    "GON": {
        "chuyen_gi": "Nhắc kiểm tra thang gọn 7 bậc (`build-less-than-asked`) trước khi thêm cấu trúc mới.",  # i18n-allow
        "vi_sao": "Ưu tiên tái dùng mã sẵn có và stdlib giúp tránh đẻ thừa lớp hoặc wrapper.",  # i18n-allow
        "lam_gi": "Xét từ bậc 1 (không thêm mới → repo → stdlib → tối giản) và giữ cyclomatic <= 10.",  # i18n-allow
        "bo_qua": "Tắt khi `muc_gat=off` hoặc yêu cầu chỉ định rõ Refactor/Clean Architecture.",  # i18n-allow
        "model_hint": (
            "Apply the 7-rung lean ladder before creating new files/abstractions "
            "(reuse repo/stdlib first; keep cyclomatic <= 10)."
        ),
    },
    "NEXT": {
        "chuyen_gi": "Chỉ dẫn pha TDQ hiện tại và bước chuyển tiếp kế tiếp được nạp đầu lượt.",  # i18n-allow
        "vi_sao": "Giữ agent làm đúng việc của pha hiện hành, không nhảy cóc sang pha sau.",  # i18n-allow
        "lam_gi": "Theo đúng chỉ dẫn `[TDQ:NEXT]` đã có sẵn mà không cần chạy lại `next`.",  # i18n-allow
        "bo_qua": "Chỉ chạy `tdq_state.py next` khi ngữ cảnh chưa có dòng `[TDQ:NEXT]`.",  # i18n-allow
        "model_hint": (
            "Follow injected [TDQ:NEXT] phase guidance directly without re-running "
            "next unless phase changed or missing."
        ),
    },
    "WORKTREE": {
        "chuyen_gi": "Sổ đăng ký vẫn còn worktree đang mở từ nhiệm vụ hoặc đợt song song trước.",  # i18n-allow
        "vi_sao": "Worktree tồn đọng chiếm đĩa, giữ khóa nhánh cũ và dễ gây nhầm đường dẫn.",  # i18n-allow
        "lam_gi": "Chạy `py -3 scripts/tdq_team.py sweep` sau khi merge xong để dọn sạch.",  # i18n-allow
        "bo_qua": "Bỏ qua khi các subagent trong đợt hiện tại vẫn đang làm việc trên đó.",  # i18n-allow
        "model_hint": (
            "Open worktrees remain in ledger; run tdq_team.py sweep after merging "
            "completed parallel tasks."
        ),
    },
    "ANCHOR": {
        "chuyen_gi": "Phiên vừa nén hoặc khôi phục từ điểm neo (`compact`/`resume`) của yêu cầu đang chạy.",  # i18n-allow
        "vi_sao": "Thẻ neo giữ tên request, pha, task mở và quy tắc cấm để không mất mạch làm việc.",  # i18n-allow
        "lam_gi": "Đọc kỹ `request`, `phase`, `doing`, `next` trong thẻ neo và đối chiếu lại file đĩa.",  # i18n-allow
        "bo_qua": "Không phát ở phiên mới bình thường khi chưa qua nhánh `compact`/`resume`.",  # i18n-allow
        "model_hint": (
            "Session resumed/compacted; re-anchor on active request, phase, doing "
            "task, and verify disk state before acting."
        ),
    },
    "DOD": {
        "chuyen_gi": "Đang đóng gói `report`/`idle` sau khi QC PASS nhưng ô kiểm DoD vẫn còn trống.",  # i18n-allow
        "vi_sao": "Checkbox DoD trong plan là bằng chứng nghiệm thu khớp với kết quả QC đã chạy.",  # i18n-allow
        "lam_gi": "Mở plan kiểm lại từng mục DoD đã đạt và đánh dấu `[x]` trước khi kết thúc.",  # i18n-allow
        "bo_qua": "Bỏ qua nếu mục chưa đạt đã được ghi độ lệch (`lech add`) trong báo cáo.",  # i18n-allow
        "model_hint": (
            "QC passed but DoD checkboxes in the plan remain unchecked; verify and "
            "tick [x] before closing out."
        ),
    },
    "INTAKE": {
        "chuyen_gi": "Chưa có yêu cầu TDQ nào đang mở (hoặc phát hiện cờ `_tdq_direct` trong prompt).",  # i18n-allow
        "vi_sao": "Mọi yêu cầu mới phải đi qua `tdq-intake` để mở nhánh và theo dõi đúng quy trình.",  # i18n-allow
        "lam_gi": "Mở skill `tdq-intake` (với `_tdq_direct`: phân tích, lập mini-plan và chốt 1 cổng duyệt).",  # i18n-allow
        "bo_qua": "Bỏ qua nếu lượt hiện tại đang trả lời tiếp cuộc phỏng vấn `tdq-intake` đã mở.",  # i18n-allow
        "model_hint": (
            "No active TDQ request open; start with tdq-intake (for _tdq_direct, "
            "analyze and stop once at mini-plan gate)."
        ),
    },
}


def _log(message: str) -> None:
    """Emit one ISO-timestamped stderr log line unless TDQ_LOG=0."""
    if os.environ.get("TDQ_LOG", "1") != "0":
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{stamp}] gate_guidance: {message}", file=sys.stderr)


def normalize_code(code: str) -> str:
    """Normalize a TDQ gate code by stripping brackets, 'TDQ:' prefix, and case."""
    raw = str(code or "").strip()
    if raw.startswith("[") and raw.endswith("]") and len(raw) >= 2:
        raw = raw[1:-1].strip()
    else:
        raw = raw.strip("[]").strip()
    upper = raw.upper()
    if upper.startswith("TDQ:"):
        upper = upper[4:].strip()
    return upper


def _balance_backticks(cut: str, limit: int) -> str:
    """Close or strip an unclosed inline code span before appending ellipsis."""
    if cut.count("`") % 2 == 0:
        return cut
    if cut.endswith("`"):
        return cut[:-1].rstrip()
    trimmed = cut[: limit - 2].rstrip()
    if trimmed.endswith("`"):
        return trimmed[:-1].rstrip()
    return trimmed + "`"


def _cap_text(text: str, limit: int) -> str:
    """Truncate text cleanly to <= limit characters on a word boundary."""
    cleaned = str(text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    if limit <= 1:
        return cleaned[:limit]
    cut = cleaned[: limit - 1].rstrip()
    space_idx = cut.rfind(" ")
    if space_idx > limit // 2:
        cut = cut[:space_idx].rstrip()
    return _balance_backticks(cut, limit) + "…"


def _fallback_entry(norm_code: str, emit_log: bool = True) -> dict[str, str]:
    """Return a safe 4-part fallback entry when norm_code is absent from GUIDANCE_TABLE."""
    if emit_log:
        _log(f"unknown gate code fallback code={norm_code}")
    return {
        "chuyen_gi": f"Cổng kiểm soát `[TDQ:{norm_code}]` vừa kích hoạt trên thao tác này.",  # i18n-allow
        "vi_sao": "Quy tắc TDQ giữ an toàn quy trình, chất lượng mã và kỷ luật ngữ cảnh.",  # i18n-allow
        "lam_gi": f"Kiểm tra điều kiện của `[TDQ:{norm_code}]` và điều chỉnh thao tác trước khi thử lại.",  # i18n-allow
        "bo_qua": "Chỉ bỏ qua khi điều kiện hợp lệ của cổng hoặc ngoại lệ quy trình được đáp ứng.",  # i18n-allow
        "model_hint": (
            f"Gate {norm_code} triggered; inspect policy requirement and adjust action "
            "before retrying."
        ),
    }


def _lookup_entry(code: str, emit_log: bool = True) -> tuple[str, dict[str, str]]:
    """Resolve normalized code and guidance dictionary entry."""
    norm = normalize_code(code) or "UNKNOWN"
    entry = GUIDANCE_TABLE.get(norm)
    if entry is None:
        return norm, _fallback_entry(norm, emit_log=emit_log)
    return norm, entry


def _format_4part_card(norm_code: str, entry: dict[str, str], detail: str = "") -> str:
    """Format one 4-part Vietnamese Markdown block capped at <= 1,200 characters."""
    clean_detail = _cap_text(" ".join(str(detail or "").split()), MAX_DETAIL_CHARS)
    what = f"{entry['chuyen_gi']} ({clean_detail})" if clean_detail else entry["chuyen_gi"]
    lines = [f"**[TDQ:{norm_code}]**"]
    for key, label in _FOUR_PART_LABELS:
        val = what if key == "chuyen_gi" else entry[key]
        lines.append(f"- **{label}:** {val}")
    return _cap_text("\n".join(lines), MAX_USER_MARKDOWN_CHARS)


def format_deny_4part(code: str, detail: str = "") -> str:
    """Format a 4-part Vietnamese block/deny message tagged with [TDQ:<CODE>] (<= 1,200 chars)."""
    norm_code, entry = _lookup_entry(code)
    return _format_4part_card(norm_code, entry, detail=detail)


def build_reminder_entry(code: str, detail: str = "") -> dict:
    """Build a dual-channel reminder payload with model_line (<= 160) and user_card (<= 1,200)."""
    norm_code, entry = _lookup_entry(code)
    prefix = f"[TDQ:{norm_code}] "
    clean_detail = " ".join(str(detail or "").split())
    base_line = f"{prefix}{entry['model_hint']}"
    if clean_detail and len(base_line) < MAX_MODEL_HINT_CHARS - 8:
        model_line = _cap_text(f"{base_line} ({clean_detail})", MAX_MODEL_HINT_CHARS)
    else:
        model_line = _cap_text(base_line, MAX_MODEL_HINT_CHARS)
    return {
        "code": norm_code,
        "model_line": model_line,
        "user_card": _format_4part_card(norm_code, entry, detail=detail),
    }


def _dedupe_entries(entries: list[dict]) -> list[dict]:
    """Normalize and deduplicate reminder entries by code while preserving first-seen order."""
    if not isinstance(entries, list):
        return []
    seen: set[str] = set()
    unique: list[dict] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        raw_code = str(item.get("code") or "").strip()
        norm_code = normalize_code(raw_code)
        if not norm_code:
            if not item.get("user_card") and not item.get("model_line"):
                continue
            norm_code = "UNKNOWN"
        if norm_code in seen:
            continue
        seen.add(norm_code)
        detail = str(item.get("detail") or "")
        built = build_reminder_entry(norm_code, detail=detail)
        unique.append({
            "code": norm_code,
            "detail": detail,
            "model_line": str(item.get("model_line") or built["model_line"]),
            "user_card": str(item.get("user_card") or built["user_card"]),
        })
    return unique


def _table_cell(text: str, limit: int = 44) -> str:
    """Sanitize and shorten one Markdown table cell without breaking table delimiters."""
    single = " ".join(str(text or "").split()).replace("|", "/")
    return _cap_text(single, limit)


def _extract_card_fields(item: dict) -> tuple[str, str, str, str]:
    """Extract the 4 guidance text fields for compact table rendering."""
    norm_code = item["code"]
    card = str(item.get("user_card") or "")
    parsed: dict[str, str] = {}
    for line in card.splitlines():
        stripped = line.strip()
        for key, label in _FOUR_PART_LABELS:
            prefix = f"- **{label}:**"
            if stripped.startswith(prefix):
                parsed[key] = stripped[len(prefix) :].strip()
    if len(parsed) == len(_FOUR_PART_LABELS):
        return (
            parsed["chuyen_gi"],
            parsed["vi_sao"],
            parsed["lam_gi"],
            parsed["bo_qua"],
        )
    _, entry = _lookup_entry(norm_code, emit_log=False)
    detail = " ".join(str(item.get("detail") or "").split())
    what = f"{entry['chuyen_gi']} ({detail})" if detail else entry["chuyen_gi"]
    return what, entry["vi_sao"], entry["lam_gi"], entry["bo_qua"]


def _entry_table_row(item: dict) -> str:
    """Render one reminder entry as a complete 5-column 4-part Markdown table row."""
    what, why, do_next, skip = _extract_card_fields(item)
    cells = [
        f"`[TDQ:{item['code']}]`",
        _table_cell(what, 48),
        _table_cell(why, 44),
        _table_cell(do_next, 48),
        _table_cell(skip, 44),
    ]
    return "| " + " | ".join(cells) + " |"


def _format_remaining_footer(codes: list[str], budget: int) -> str:
    """Render remaining skipped codes on one complete line inside budget."""
    if not codes or budget < 18:
        return ""
    prefix = f"_Còn {len(codes)} mục:_ "  # i18n-allow
    if len(prefix) >= budget:
        return ""
    chosen: list[str] = []
    for idx, code in enumerate(codes):
        tag = f"`[TDQ:{code}]`"
        rem_count = len(codes) - idx - 1
        tail = f" (+{rem_count})" if rem_count > 0 else ""
        candidate = prefix + ", ".join([*chosen, tag]) + tail
        if len(candidate) > budget:
            break
        chosen.append(tag)
    if not chosen:
        return _cap_text(f"_+{len(codes)} mục TDQ khác_", budget)  # i18n-allow
    leftover = len(codes) - len(chosen)
    suffix = f" (+{leftover})" if leftover > 0 else ""
    return prefix + ", ".join(chosen) + suffix


def _format_compact_table(entries: list[dict], limit: int = MAX_USER_MARKDOWN_CHARS) -> str:
    """Compact overflowing user cards into a clean 4-part Markdown table within limit."""
    cols = " | ".join(["Mã", *(label for _, label in _FOUR_PART_LABELS)])  # i18n-allow
    header = f"| {cols} |\n|---|---|---|---|---|"
    rows: list[str] = []
    used = len(header)
    for idx, item in enumerate(entries):
        row = _entry_table_row(item)
        remaining_after = len(entries) - idx - 1
        footer_reserve = 96 if remaining_after > 0 else 0
        if rows and used + 1 + len(row) + footer_reserve > limit:
            break
        if not rows and used + 1 + len(row) > limit:
            break
        rows.append(row)
        used += 1 + len(row)
    table_text = "\n".join([header, *rows])
    remaining_codes = [item["code"] for item in entries[len(rows) :]]
    if not remaining_codes:
        return table_text
    footer = _format_remaining_footer(remaining_codes, limit - len(table_text) - 2)
    _log(f"compacted user_markdown table kept={len(rows)}/{len(entries)}")
    return f"{table_text}\n\n{footer}" if footer else table_text


def format_user_markdown(entries: list[dict]) -> str:
    """Deduplicate and render user-facing 4-part Markdown guidance capped at <= 1,200 chars."""
    unique = _dedupe_entries(entries)
    if not unique:
        return ""
    joined = "\n\n".join(item["user_card"] for item in unique)
    if len(joined) <= MAX_USER_MARKDOWN_CHARS:
        return joined
    if len(unique) == 1:
        return _cap_text(joined, MAX_USER_MARKDOWN_CHARS)
    return _format_compact_table(unique, MAX_USER_MARKDOWN_CHARS)


def _format_code_overflow(codes: list[str], budget: int) -> str:
    """Format leftover model reminder codes cleanly inside remaining character budget."""
    if not codes or budget < 12:
        return ""
    prefix = "More: "
    chosen: list[str] = []
    for idx, code in enumerate(codes):
        tag = f"[TDQ:{code}]"
        rem = len(codes) - idx - 1
        tail = f" (+{rem})" if rem > 0 else ""
        candidate = prefix + ", ".join([*chosen, tag]) + tail
        if len(candidate) > budget:
            break
        chosen.append(tag)
    if not chosen:
        return _cap_text(f"(+{len(codes)} more)", budget)
    rem = len(codes) - len(chosen)
    tail = f" (+{rem})" if rem > 0 else ""
    return prefix + ", ".join(chosen) + tail


def _compact_model_lines(unique: list[dict], lines: list[str], limit: int) -> str:
    """Pack deduplicated model_line strings into <= limit chars preserving full tags."""
    if len(unique) == 1:
        return _cap_text(lines[0], limit)
    kept: list[str] = []
    used = 0
    for idx, line in enumerate(lines):
        remaining = len(lines) - idx - 1
        reserve = min(64, 15 * remaining) if remaining > 0 else 0
        if not kept:
            kept.append(_cap_text(line, limit - reserve))
            used = len(kept[0])
            continue
        if used + 1 + len(line) + reserve <= limit:
            kept.append(line)
            used += 1 + len(line)
        else:
            break
    leftover_codes = [item["code"] for item in unique[len(kept) :]]
    if not leftover_codes:
        return "\n".join(kept)
    budget = limit - used - 1
    if len(leftover_codes) == 1 and budget >= 40:
        kept.append(_cap_text(lines[len(kept)], budget))
        return "\n".join(kept)
    overflow = _format_code_overflow(leftover_codes, budget)
    return "\n".join([*kept, overflow]) if overflow else "\n".join(kept)


def format_model_summary(entries: list[dict]) -> str:
    """Deduplicate and join concise model reminder lines within <= 200 chars."""
    unique = _dedupe_entries(entries)
    lines = [item["model_line"] for item in unique if item.get("model_line")]
    if not lines:
        return ""
    joined = "\n".join(lines)
    if len(joined) <= MAX_MODEL_SUMMARY_CHARS:
        return joined
    return _compact_model_lines(unique, lines, MAX_MODEL_SUMMARY_CHARS)
