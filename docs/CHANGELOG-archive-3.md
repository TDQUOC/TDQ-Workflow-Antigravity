# Changelog — bản lưu trữ 3

Bản 0.59.0 đến 0.57.0, tách khỏi `CHANGELOG.md` để giữ file chính dưới trần R6 500 dòng (`docs/CHANGELOG-archive-2.md` đã chạm 496 dòng). Mới nhất trên cùng, chữ nghĩa copy nguyên văn.

## 0.59.0 — 2026-10-08

Mỗi project chỉ mở được request khi LSP đã được CHỨNG MINH trả lời đúng cho từng module (ngôn ngữ,
gốc), qua đúng đường MCP agent dùng. Ca gốc (bench 2026-10-07): `start_lsp` thiếu `language_id`
trên repo Python → agent-lsp bật hết server, TypeScript thành server hiện hành → crash
`0xc0000409` / "No Project", trong khi `agent-lsp doctor` vẫn báo khoẻ.
Báo cáo: `docs/tdq/reports/2026-10-07-2225-tu-dong-setup-lsp.md`.

- **Module LSP** (`scripts/lsp_module.py`, mới). Dò (ngôn ngữ, gốc) theo file mốc sâu nhất —
  repo một ngôn ngữ là một dòng, claudecodeui là `typescript:.` + `typescript:server`. Lệnh mới
  `tdq_lsp.py module | kich-ban | ghi-kiem`: script chọn symbol và in sẵn ba lời gọi MCP, agent gửi,
  script chấm (tham chiếu LSP > số lần trong file định nghĩa). Kết quả hạn 24 giờ hoặc tới khi file
  mốc / dòng MCP đổi.
- **Bậc 8 "LSP theo module"** trong `tdq_lsp.py check`; bậc 3 thêm cổng: mỗi ngôn ngữ của project
  phải có dòng trong `args` của MCP `lsp`.
- **Cổng `init`.** `tdq_state.py init` từ chối khi còn module chưa ĐẠT; lối thoát
  `--bo-qua-lsp "<lý do>"` ghi vào `lsp_bo_qua`, report đọc ra.
- **Hook `lsp_gate.py` (`TDQ:LSP`, chặn).** `start_lsp` thiếu `language_id` hoặc sai cặp
  (gốc, ngôn ngữ) bị từ chối, lời chặn liệt kê lời gọi đúng.
- **Tự cài không hỏi.** `tdq_setup.py` cài agent-lsp từ bản phát hành GitHub (kiểm SHA256 theo
  `checksums.txt`, chạy được trên Windows — `install.sh` upstream thì không); ngôn ngữ mới xuất hiện
  trong project (vd. Python rồi thêm JS + HTML) được cài server và khai vào MCP `lsp` (sao lưu
  `~/.claude.json` trước khi ghi, rồi nhắc `/mcp` kết nối lại); SessionStart dựng nền lại khi tập
  ngôn ngữ đổi. Tắt `agent-lsp daemon-broker` mồ côi, cảnh báo bộ nhớ commit < 4 GB.
- **Luật chữ.** Intake 1b tự chạy setup → check → kịch bản; `kiem-lsp-hieu-ung.md` viết lại theo
  module; `uu-tien-tim-kiem.md` thêm luật gọi `start_lsp` theo module (TS mở file trước, ưu tiên
  tool theo file, `find_symbol` chỉ hỏi server hiện hành — issue #55 upstream).
- **Test không chạm máy.** `TDQ_KHONG_CHAM_MAY=1` (đặt cho cả tiến trình test) khoá ba việc chạm
  máy thật: tải/cài agent-lsp, ghi `~/.claude.json`, tắt tiến trình.

## 0.58.0 — 2026-10-07

Gỡ lumen, luật tìm kiếm còn ba tầng (LSP · grep · graphify), cổng tìm kiếm dẫn tới tầng đang
sống. Đo trước khi gỡ (request `2026-10-07-1843-phan-tich-bo-lumen`): 12 câu khái niệm trên
TDQ-Workflow và claudecodeui, không lumen vẫn trúng 11/12 và 10/12 (trượt 0), token 0,88× và
1,06× — không giảm đáng kể. Báo cáo: `docs/tdq/reports/2026-10-07-2041-go-lumen-toi-uu-tim-kiem.md`.

- **lumen ra khỏi mã.** Thang `tdq_lsp.py check` còn 7 bậc đánh số liền (bậc lumen cũ là 5;
  hook xung đột 6→5, cấu hình gốc import 7→6, graphify 8→7), smoke còn 3 tầng — máy không cài
  lumen không còn "CHƯA ĐẠT, exit 4" vĩnh viễn. Bỏ `wake`/`release` của ollama, bước `reindex`
  của `tdq_finish.py`, phần lumen của `tdq_setup.py` (cấu hình, dựng nền, khối ghim CLAUDE.md),
  `setup_status`, khai MCP lumen cho Codex; xoá `skills/tdq-setup/references/lumen.md`,
  `.lumenignore`.
- **Cổng `TDQ:SEARCH` bớt lượt thừa.** Lời chặn chỉ nêu tầng mà dấu mốc sẵn sàng ghi là sống,
  kèm lệnh dùng ngay (`start_lsp` khi LSP báo chưa khởi động). Lời gọi `mcp__lsp__*` được ghi sổ
  ngay ở PreToolUse, nên lời gọi lỗi vẫn tính là đã hỏi. Mốc cũ còn khoá `lumen` không còn làm
  dựng lại nền mỗi 6 giờ.
- **Luật chữ 3 tầng.** Bốn câu từng chấm agent oan khi lumen vắng (`analyze-full.md`,
  `quick-lane.md`, `tdq-build/SKILL.md`, `PHASE_TABLE`) nay đòi LSP rồi graphify; câu chuẩn và
  bảng loại câu hỏi trong `uu-tien-tim-kiem.md` mang số đo mới kèm tên repo.
- **Codex.** `tdq_codex_mcp.khai_hook_codex` không còn ghi đè `.codex/hooks.json` viết tay của
  chính repo plugin (đã xảy ra 2026-10-03 và 2026-10-07). Mỗi lần ghi hook, nó nói rõ hai điều
  kiện để hook chạy. Một: hook phải được duyệt ở `/hooks`, hook chưa duyệt bị bỏ qua lặng lẽ. Hai:
  trên Windows, sandbox `read-only`/`workspace-write` chặn mọi tiến trình, kể cả tiến trình hook
  (`docs/tdq/research/2026-10-07-2041-hook-codex.md`).

## 0.57.0 — 2026-10-05

Một luật chạy test, một nguồn. Bước trung gian chỉ chạy test trong vùng chạm, trọn bộ dồn về
hai cổng. Trước bản này `tdq-build` ("EXACTLY ONCE"), khuôn plan ("sau mỗi phase chạy toàn bộ")
và `qc.md` (mỗi vòng sửa) nói ba kiểu khác nhau. Báo cáo:
`docs/tdq/reports/2026-10-03-1907-test-vung-cham-buoc-trung-gian.md`.

- **Bước trung gian chạy `scripts/tdq_test.py vung-cham`.** Nó chọn vùng chạm cộng bán kính ảnh
  hưởng: test nhắc đường dẫn/tên file, import bắc cầu đọc bằng AST, test quét thư mục cha. Trọn
  bộ chỉ ở 2 cổng: QC-F1 (thay lần "xong implement") và sau vòng sửa QC cuối nếu có sửa.
- **Không chắc thì chạy hết.** Bán kính ≥ 60% số module, hoặc file mã/loại không rõ ngoài
  `scripts/ hooks/ skills/ tests/ agents/` → trọn bộ trong một tiến trình. File dữ liệu (.md,
  .json…) chỉ kéo theo test nhắc đường dẫn của nó.
- **Đo trên repo này.** Sửa `stop_gate.py` → 16/129 module, 51,6 s (trọn bộ ~420 s). Sửa hub
  `tdq_state.py` → 98/129 module → trọn bộ.
- **Sổ sách.** `tdq_test.py tron-bo` ghi sổ, và có sổ bán kính bỏ sót (QC-F1 đỏ ở module bán kính
  chưa chọn); report in số lần, xem bằng `tdq_test.py so`. `next` nhắc khi số lần trọn bộ vượt
  ngân sách 2 (3 sau một lần trọn bộ đỏ) — chỉ nhắc, không chặn.
- **Test chạy được từ PowerShell.** Bỏ lệnh shell `true` khỏi 5 module test (trước: 26 fail +
  1 error).
- **Trung thực về tiết kiệm.** Nền cũ trung bình 7,4 lần trọn bộ/request (59 lần/8 request). Hai
  request gần nhất đã chỉ 2–3 lần, nên lợi chính là khoá luật cho khỏi trôi ngược.
