# Báo cáo Research & Đề xuất Kiến trúc Hook giữ đúng Behavior và Hiệu năng

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

- **Mã yêu cầu (Request Slug):** `2026-11-19-1612-research-behavior-va-hieu-nang`
- **Nhánh làm việc:** `docs/research-behavior-va-hieu-nang` (tách từ `dev`)
- **Tài liệu Brief:** [2026-11-19-1612-research-behavior-va-hieu-nang.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/brief/2026-11-19-1612-research-behavior-va-hieu-nang.md)
- **Kế hoạch triển khai (Mini-Plan):** [2026-11-19-1612-research-behavior-va-hieu-nang.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/plan/2026-11-19-1612-research-behavior-va-hieu-nang.md)
- **Báo cáo Audit nền trước đó:** [2026-11-19-1457-audit-sai-sot-noi-hook.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-19-1457-audit-sai-sot-noi-hook.md)
- **Báo cáo trực quan (Archify HTML cục bộ):** [2026-11-19-1612-research-behavior-va-hieu-nang.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-19-1612-research-behavior-va-hieu-nang.html)
- **Đường dẫn xem trực tiếp qua Tailscale Serve:** https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-19-1612-research-behavior-va-hieu-nang.html

---

## 1. Trước request: Bài toán đánh đổi thực tế & Số liệu nền (Baseline)

Kết quả khảo sát từ hai báo cáo trước (`2026-11-18-1346-scan-hook-anh-huong-runtime` trên `120` transcript trong `4` ngày, và `2026-11-19-1457-audit-sai-sot-noi-hook`) cùng hợp đồng chính thức Antigravity 2.0 (`agy-customizations/docs/hooks.md`) cho thấy bài toán tối ưu tầng hook đang đối mặt với ba ràng buộc cốt lõi:

- **Giới hạn vật lý của nền tảng Antigravity (`hooks.md:127-131, 428-429`):** Host chỉ hỗ trợ `"type": "command"` chạy đồng bộ (*"Hooks run synchronously and block the agent loop"*), mỗi lần gọi đều phải spawn qua vỏ `cmd /c` (Windows) hoặc `sh -c` (Unix). Antigravity chưa hỗ trợ HTTP hook hay async hook. Phí cố định riêng cho việc mở vỏ `cmd /c` đã chiếm ~`8–10 ms`/lần.
- **Độ trễ thực tế đã đo giữa các engine (`tests/test_rust_latency_benchmark.py` N=30 & `bench_dispatch.py`):**
  - Rust `tdq-dispatch.exe` gọi trực tiếp đạt **`19,90 ms`** (qua vỏ `cmd /c` đạt **`28,37 ms`**).
  - Python `dispatch.py` R1–R3 đạt **`69,5–126,1 ms`** (trong đó bản CPython lạnh không cache đạt **`190,21–199,36 ms`**, riêng launcher `py -3` tốn thêm **`+17,62 ms`/spawn** so với gọi thẳng `python.exe`).
- **Tỷ trọng thật của Hook trong tổng thời gian chạy phiên dài:**
  - Trên `120` transcript / `4` ngày (`11.241` lần gọi model, `17.429` bước tool, `105` `SessionStart`, `60` `Stop` block), chi phí hook ước tính chỉ chiếm **`2,67%`** tổng thời lượng 60 lượt dài (`63,55` phút / `2.377,38` phút) cộng `0,14%` chờ deny (`3,27` phút), trong khi **`~74%`** thời lượng nằm ở model sinh (`46,42%`), chờ subagent (`20,00%`) và chờ lỗi/timeout API (`15,20%`).
  - Yếu tố làm chậm agent nặng nhất liên quan đến hook **không chỉ là millisecond spawn**, mà là **bơm lặp text làm phình ngữ cảnh** (`0–50k` token model sinh median **`6,0 s`**, lên `>= 400k` nhảy tới **`53,0 s`**, `p90 = 217,0 s`) và **vòng lặp chặn nhầm** (`34,12` phút chờ agent xử lý `196` deny, phần lớn do `SEARCH malformed` và `TICK streak=3`).
- **Khoảng cách codebase & nguyên nhân rơi behavior:**
  - Toàn bộ tầng hook Python AGY (`plugins/tdq-workflow-agy/hooks/scripts/`) gồm **`5.634` dòng** qua 17 module; trong khi crate Rust hiện tại (`hooks/rust/tdq-dispatch/src/`) mới có **`1.502` dòng** (13 file, phủ ~25% logic và đang lệch schema `PreInvocation`/`PostInvocation`/`injectSteps`/`reason`).
  - Đợt `v0.100.0` (R1–R3) hạ cấp cứng thành nhắc mềm quá tay để né chặn nhầm, còn đợt `v0.101.0` (Rust) chuyển cả 6 sự kiện sang binary thiếu cổng mà không có fallback chọn lọc và Parity Test đầy đủ.

---

## 2. Sau request: Phân tách `Hot-path` vs `Cold-path` & Phân loại 22 mã cổng

Để đạt cả hai mục tiêu (**giữ tốc độ `<= 25–30 ms` ở mọi bước lặp dày** và **bảo toàn 100% kỷ luật trên 22 mã cổng**), dữ liệu thực tế cho phép tách toàn bộ lưu lượng `~39.966` lời gọi hook / 4 ngày (sau khi thu hẹp `PostToolUse` chỉ còn tìm kiếm + MCP) thành hai đường chạy rõ rệt:

### 2.1. Phân bổ lưu lượng theo `Hot-path` và `Cold-path`

| Đường chạy | Sự kiện & Điều kiện kích hoạt | Tần suất / 4 ngày (ước tính) | Tỷ trọng | Phụ thuộc kỹ thuật | Engine tối ưu |
|---|---|---|---|---|---|
| **`Hot-path`** | `PreInvocation` giữa lượt (user signature & `turn_closed` không đổi) | ~`10.000` | ~25,0% | Đọc `turn-meta-<sid>.json` + đuôi `64 KB` `transcriptPath` + xả hàng đợi | **Rust thuần** (`~22–28 ms`) |
| **`Hot-path`** | `PostInvocation` | `11.241` | ~28,1% | `stat` nhanh `pending-reminders-<sid>.jsonl` (rỗng trả `{}` ngay) | **Rust thuần** (`~20–26 ms`) |
| **`Hot-path`** | `PreToolUse` phổ thông (`read_file`, `edit_file` inline, `ask_question`, `start_lsp` O(1), `invoke_subagent`, `run_command` an toàn/shell mutator) | ~`15.500` | ~38,8% | Đọc `state.json`, file plan (`_TASK_LINE`), regex shell, sidecar lock | **Rust thuần** (`~22–28 ms`) |
| **`Hot-path`** | `PostToolUse` thu hẹp (chỉ tìm kiếm, `mcp_*`, `call_mcp_tool` & `graphify`) | ~`4.000` | ~10,0% | Ghi `.tdq-search.jsonl`, `turns-<sid>.jsonl`, lưu CCR `> 32 KB` | **Rust thuần** (`~22–28 ms`) |
| **`Hot-path`** | `Stop` khi `phase=idle` hoặc không có `active_request` | (phần lớn lượt rỗi) | — | Đọc `state.json` → trả `{"decision":"allow"}` ngay | **Rust thuần** (`~20 ms`) |
| **`Cold-path`** | `SessionStart` (mở phiên mới) | `105` | <0,3% | Đọc luật `chung.md`, lọc `muc_gat`, probe setup/anchor/background | **Python `dispatch.py`** (`~120–160 ms`) |
| **`Cold-path`** | `PreInvocation` **đầu lượt user mới** (`last_user_sig` đổi hoặc `turn_closed=True`) | ~`1.241` | ~3,1% | NLP `looks_like_approval`, `render_next`, `turn_snapshot` (cache `.git/index`), worktree | **Python `dispatch.py`** (`~95–126 ms`) |
| **`Cold-path`** | `Stop` khi có `active_request` đang mở (không phải `TERMINAL_STOP_REASONS`) | ~`1.241` | ~3,1% | `git status` đối chiếu `turn_start`, kiểm `docs/workinglog/`, `dod_tick_state`, `plan_sha` | **Python `dispatch.py`** (`~77–95 ms`) |
| **`Cold-path`** | `PreToolUse` ca phức tạp (`run_command` cần `rtk rewrite`/`search_rules` sâu; `edit_file` khi `implement_mode=subagent`) | ~`1.929` | ~4,8% | `tdq_team` phân công chi tiết hoặc `rtk rewrite` cache | **Python `dispatch.py`** (`~85–110 ms`) |

*Tổng hợp theo lưu lượng thực tế (không tính các bước `PostToolUse` thường đã loại bỏ ở R1): **~91% lời gọi rơi vào `Hot-path` (Rust)** và **chỉ ~9% lời gọi hiếm rơi vào `Cold-path` (Python)**.*

### 2.2. Bảng phân loại toàn bộ 22/22 mã cổng theo Kiến trúc Smart Hardening

| # | Mã cổng | Sự kiện | Nhóm thực thi đề xuất | Đường chạy | Cơ chế thực thi chính xác |
|---|---|---|---|---|---|
| 1 | `APPROVE` | `PreInv`, `PreTool` | **Hard Deny** | `Cold` (Inv) / `Hot` (Edit) | Chặn cứng mọi sửa file ngoài `docs/` và shell mutator khi `cong_dang_cho(state)` còn mở |
| 2 | `GIT` | `PreTool` (`run_command`) | **Hard Deny** | `Hot` | Chặn cứng `git push`, `git reset --hard`, `git clean -f`, nhánh prefix AI, trailer `Co-Authored-By` |
| 3 | `TEAM` | `PreTool` (`edit`, `cmd`) | **Hard Deny** | `Cold` (team) / `Hot` (sub) | Chặn cứng subagent sửa ngoài `docs/` trước `implement`, leader làm thay task giao, hoặc ghi ngoài `Chạm:` |
| 4 | `STATE` | `PreTool` (`edit`, `cmd`) | **Hard Deny** | `Hot` | Chặn cứng mọi tool ghi trực tiếp `docs/tdq/state.json` / `STATE.md` ngoài CLI `tdq_state.py` |
| 5 | `READONLY` | `PreTool` (`edit`, `cmd`) | **Hard Deny** | `Hot` | Chặn cứng `reviewer`, `browser`, **và `qc-tester`** dùng cả `edit_file` lẫn shell mutator (`>`, `Out-File`...) |
| 6 | `VUNG` | `PreTool` (`edit`, `cmd`) | **Hard Deny** | `Hot` | Chặn cứng sửa ngoài `TDQ_CODEX_VUNG` hoặc chạm vùng khóa `TDQ_CODEX_KHOA` |
| 7 | `ZERO-POPUP` | `PreTool` (`ask_question`) | **Hard Deny** | `Hot` | Chặn cứng popup `ask_question`/`ask_user_question` khi đang có `active_request` |
| 8 | `UNFINISHED` | `Stop` | **Hard Deny (Trần 2)** | `Cold` | Chặn dừng khi còn task `[ ]`/`[~]` ở `implement`; chỉ nhả sau `MAX_STREAK=2` giữ nguyên `plan_sha` hoặc có `[>]`/`pause` |
| 9 | `TICK` | `PreTool` (`edit`), `Stop` | **Smart-Hard Deny** | `Hot` (Edit) / `Cold` (Stop) | Chặn cứng khi `0` hoặc `>1` `[~]`; nhắc ở edit 4, chặn ở edit **8** (thay `3`); **chặn cứng `Stop`** nếu sửa code mà `plan_sha` đứng yên |
| 10 | `LOG` | `PreTool`, `Stop` | **Smart-Hard Deny** | `Hot` (Remind) / `Cold` (Stop) | **Chặn cứng `Stop`** nếu repo sửa mã nguồn mà `docs/workinglog/` chưa cập nhật; trừ sạch `docs/.staging*`, `docs/tdq/`, `graphify-out/` |
| 11 | `SEARCH` | `PreTool`, `PostTool` | **Smart-Hard Deny** | `Hot`/`Cold` | Giữ Hướng A (ân xá lần 1, chặn cứng lần 2 liên tiếp); không cho shell chứa `rg`/`grep`/`Select-String` lọt `malformed_allow`; bắt `graphify` qua `run_command` |
| 12 | `LSP` | `PreTool` (`lsp`/`mcp`) | **Auto-Overwrite + Guard** | `Hot` | Tự điền `language_id` O(1) từ `.tdq-lsp-module.json`/mốc gốc (bọc đúng `Arguments`); chặn cứng `blast_radius > 3` hoặc `scope='all'` |
| 13 | `SUBAGENT` | `PreTool` (`subagent`) | **Auto-Overwrite + Guard** | `Hot` | Tự đặt `Workspace='inherit'` khi có `WORKTREE:`; chặn `swarm` sai mode; nhắc nếu thiếu 5 trường bắt buộc |
| 14 | `DOC` | `PreTool` (`read_file`) | **Context / Soft** | `Hot` | Nhắc `StartLine`/`EndLine` khi đọc lặp file `>= 2 KB` chưa đổi; nhắc `tdq_ccr.py` cho file dữ liệu `> 32 KB` |
| 15 | `OUTPUT` | `PreTool` (`run_command`) | **Context / Soft** | `Cold` (`rtk`) | Ưu tiên `overwrite` qua `rtk rewrite`; nhắc giới hạn dòng nếu lệnh đổ output thô không nén được |
| 16 | `GON` | `SS`, `PreInv` (đầu pha) | **Context / Soft** | `Cold` | Không lặp giữa lượt; bơm 1 dòng neo `<= 160` ký tự ở đầu pha `implement` và ngay sau khi phát hiện compaction |
| 17 | `NEXT` | `SS`, `PreInv` (đổi pha) | **Context / Soft** | `Cold` | Chỉ bơm khi mở lượt mới hoặc khi `phase`/`slug` đổi (không bơm `"same as last turn"`) |
| 18 | `DOD` | `Stop` (`report`/`idle`) | **Context / Soft** | `Cold` | Nhắc rõ ngay trong lượt (hoặc cảnh báo user) khi QC PASS mà checkbox DoD trong plan vẫn chưa tick `[x]` |
| 19 | `INTAKE` | `PreInv` (khi `idle`) | **Context / Soft** | `Cold` | Nhắc mở `tdq-intake` hoặc quy trình `_tdq_direct` ở lượt mở đầu |
| 20 | `SETUP` | `SessionStart` | **Context / Soft** | `Cold` | Nhắc thiếu `rtk`/`rg`/LSP trong 1 thẻ `user_markdown` gọn khi mở phiên |
| 21 | `WORKTREE` | `SessionStart`, `PreInv` | **Context / Soft** | `Cold` | Nhắc dọn `.tdq-worktrees/` chỉ khi sổ worktree còn dòng mở và đã qua đợt chạy |
| 22 | `ANCHOR` | `SessionStart` | **Context / Soft** | `Cold` | Bơm 1 dòng neo `request`, `phase`, `doing` khi phục hồi phiên sau compact/resume |

---

## 3. Đã test / phân tích định lượng những gì?

Quá trình nghiên cứu thực hiện tổng hợp và đối chiếu trên 5 tập dữ liệu và mã nguồn thực tế trong workspace:

1. **Hợp đồng kỹ thuật Antigravity 2.0:** Phân tích toàn văn `C:\Users\admin\.gemini\antigravity\builtin\skills\agy-customizations\docs\hooks.md` (429 dòng) xác định rõ giới hạn chỉ hỗ trợ `type: "command"` đồng bộ, cấu trúc payload 6 sự kiện, cơ chế shallow `overwrite`, `metadata.user_markdown` và cờ `continuationActive`.
2. **Dữ liệu vận hành thực tế 120 transcript (`4` ngày):** Đối chiếu số đo từ `docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md` (`11.241` lời gọi model, `17.429` bước tool, `105` `SessionStart`, `60` `Stop` block, `196` deny thô và `60` lượt dài `>= 10` phút).
3. **Benchmark độ trễ thực nghiệm giữa 2 engine:** Đối chiếu kết quả đo N=30 tại `tests/test_rust_latency_benchmark.py` (Rust direct `19,90 ms`, Rust qua `cmd /c` `28,37 ms`, Python direct `190,21 ms`, Python qua `cmd /c` `199,36 ms`) và `docs/tdq/bench/2026-11-18-1814-toi-uu-hook-huong-dan/bench_dispatch.py` (`PreInvocation` `126,1 ms`, `PreToolUse` `69,5–93,4 ms`, `Stop` `77,3 ms`).
4. **Kiểm đếm độ phức tạp mã nguồn:** Đo trực tiếp `5.634` dòng across 17 file Python AGY vs `1.502` dòng across 13 file Rust trong `hooks/rust/tdq-dispatch/src/`.
5. **Mô hình hóa độ trễ có trọng số (Weighted Latency):** Tính tổng chi phí dự kiến trên `~39.966` lời gọi hook / 4 ngày (loại bỏ `PostToolUse` thừa trên `run_command`/`read_file`) cho từng phương án kiến trúc.

---

## 4. Kết quả test định lượng & Đề xuất phương án kiến trúc (`Hybrid` 2 tầng + `Smart Hardening`)

### 4.1. Bảng so sánh định lượng 3 phương án kiến trúc thực thi

| Tiêu chí đánh giá | Phương án 1 — **`Hybrid` 2 tầng** (Rust Router + Python Cold-Path) **[KHUYẾN NGHỊ]** | Phương án 2 — **`Full-Rust` 100% Parity** (Port toàn bộ sang Rust) | Phương án 3 — **Persistent `Sidecar` / Daemon** (Python thường trú + client mỏng) |
|---|---|---|---|
| **Cơ chế định tuyến** | Rust xử lý chuẩn AGY 2.0 trên ~91% `Hot-path` (chỉ I/O + regex); tự spawn/delegate sang `dispatch.py` cho ~9% `Cold-path` | Rust xử lý 100% logic của cả 17 script Python, `tdq_state`, `tdq_team`, `rtk_integration`, `search_rules` | Client Rust/C mỏng qua `cmd /c` gửi payload vào daemon Python qua Named Pipe / localhost TCP |
| **Độ trễ `Hot-path` (~91% call)** | **`20–28 ms`** (qua `cmd /c`) | **`20–29 ms`** | ~`22–30 ms` (`cmd /c` `8–10ms` + IPC `5–10ms` + xử lý `5–10ms`) |
| **Độ trễ `Cold-path` (~9% call)** | `80–126 ms` (chỉ ~3.500 lần hiếm / 4 ngày) | **`22–32 ms`** | ~`25–35 ms` (vẫn tốn subprocess khi gọi `git status` / `rtk`) |
| **Độ trễ TB có trọng số** | **`~35,4 ms/event`** (`0,91×28 + 0,09×110`) | **`~29,0 ms/event`** | **`~26,0 ms/event`** |
| **Tổng thời gian hook / 4 ngày** | **`~23,6 phút`** (~`5,9 phút/ngày`, nhanh hơn **2,7×** Python R1–R3) | **`~19,3 phút`** (~`4,8 phút/ngày`, chỉ tiết kiệm thêm **~1 phút/ngày** so với `Hybrid`) | **`~17,3 phút`** |
| **Độ phủ kỷ luật `22` cổng** | **100% (22/22 mã)** ngay lập tức vì không ca nào bị bỏ rơi | 100% *sau khi port xong* `4.100+` dòng mới | **100%** (tái dùng trực tiếp Python hiện tại) |
| **Chi phí bảo trì & Rủi ro Drift** | **Thấp:** giữ `~2.000` dòng Rust cho Hot-path ổn định; giữ **1 nguồn chân lý** cho `tdq_state`/`tdq_team`/NLP duyệt | **Rất cao:** nhân đôi toàn bộ nghiệp vụ sang 2 ngôn ngữ (Claude Python vs AGY Rust) → dễ tái phát Behavior Drift | **Cao (hạ tầng):** quản lý daemon/zombie, tường lửa localhost/Named Pipe Windows, và **stale code** khi user chạy `install.py` |
| **Phụ thuộc nền tảng AGY** | Tuân thủ 100% `type: "command"` (`hooks.md:428`), không chạy tiến trình nền bất thường | Tuân thủ 100% | Vi phạm tinh thần stateless `command` hook, khó dọn sạch cross-OS |

**Kết luận lựa chọn kiến trúc:** Chọn **Phương án 1 (`Hybrid` 2 tầng)**. Đánh đổi vỏn vẹn **~1 phút/ngày** (so với `Full-Rust`) ở ~9% ca lạnh đổi lấy **100% độ chính xác 22/22 cổng ngay từ Chặng 1**, loại bỏ gánh nặng nhân đôi 5.634 dòng Python sang Rust và tránh hoàn toàn rủi ro zombie daemon của `Sidecar`.

### 4.2. Chính sách `Smart Hardening` (Siết Cổng Thông Minh — Không đánh đổi kỷ luật vì false-positive)

Nguyên nhân sâu xa khiến R1–R3 phải "nới" hàng loạt là vì trước đây nhiều cổng chọn **nhầm ngưỡng** (ví dụ `STREAK_NGUONG = 3` khi 1 task có thể sửa 4–5 file hợp lệ, hoặc `Stop TDQ:LOG` bắt nhầm file nháp `docs/.staging*`). Bộ 6 quy tắc `Smart Hardening` khôi phục toàn bộ kỷ luật gốc bằng cách chỉnh đúng điều kiện kích hoạt thay vì xóa cổng:

1. **`TDQ:TICK` hai tầng không gây nhiễu:**
   - Giữ **chặn cứng (`deny`)** ở `PreToolUse` (`edit_file`/`write_to_file`/`replace_file_content` ngoài `tests/**`, `docs/**`, `.tdq-worktrees/**`) khi plan có `0` hoặc `> 1` task đang `[~]` (tính chính xác 100%, không bao giờ có false-positive).
   - Nâng trần sửa liên tiếp cùng `plan_sha` từ `STREAK_NGUONG = 3` lên **`8`**: từ lần sửa thứ **4–7** chỉ phát nhắc nhẹ, đến lần thứ **8** mới `deny` buộc cập nhật plan → triệt tiêu `30` ca `tick_loop` vô ích nhưng vẫn khóa chặt chống làm lụi quên plan.
   - Giữ **chặn cứng ở `Stop`** (`decision: "continue"`) nếu lượt vừa rồi có sửa mã nguồn thật mà `plan_sha` không đổi chút nào (loại bỏ hoàn toàn lỗi sót `[ ]` như request `2026-11-19-0046`).
2. **`TDQ:LOG` sạch false-positive:**
   - Khôi phục **chặn cứng ở `Stop`** khi repo có file mã nguồn/kịch bản/cấu hình thay đổi so với `turn_start` nhưng `docs/workinglog/YYYY-MM-DD.md` chưa được cập nhật.
   - Loại trừ sạch toàn bộ bookkeeping & nháp trong cả `edit` lẫn `_shell_change_check`: `docs/.staging*`, `docs/tdq/`, `graphify-out/`, `*.tmp`.
3. **`TDQ:UNFINISHED` sửa bẫy thoát sớm `continuationActive`:**
   - Bỏ dòng `return` mù tại `stop_gate.py:299-302`. Thay vào đó, khi `continuationActive=True`: kiểm tra `plan_sha` hiện tại so với `stop_streak.json`. Nếu agent vừa tích cực hoàn thành thêm task (`plan_sha` đổi), **reset bộ đếm streak và tiếp tục giữ gate**; chỉ cho dừng (`allow` + nhắc `[TDQ:UNFINISHED]`) khi `plan_sha` đứng yên quá `MAX_STREAK = 2` lần liên tiếp, hoặc khi có task `[>]` (`dispatched_count > 0`) hay `implement_pause` hợp lệ.
4. **`TDQ:SEARCH` giữ Hướng A nhưng bịt lỗ hổng lách luật:**
   - Giữ ân xá lần 1 + chặn cứng lần 2 liên tiếp ở pha `implement`/`qc`.
   - Khi lệnh shell không parse hết (`unknown`) nhưng chứa mẫu tìm kiếm rõ ràng (`\brg\b`, `\bgrep\b`, `Select-String`, `findstr`), **không** cho rơi vào nhánh `agy_malformed_allow` miễn kiểm tra.
   - Khôi phục ghi nhận từ khóa `graphify` từ `run_command` (bắt sớm ở `PreToolUse` khi lệnh hợp lệ hoặc giữ matcher tối giản cho `run_command` chỉ khi pattern khớp `graphify` để không tăng chi phí `PostToolUse`).
5. **Bịt lỗ hổng Shell Mutator & `READONLY`:**
   - Bổ sung `"qc-tester"` vào `bash_gate.py:173` (hiện mới chỉ chặn `reviewer` và `browser`).
   - Tại `PreToolUse` (`run_command`), kiểm tra nhanh bằng regex các mẫu ghi file qua shell (`Set-Content`, `Out-File`, `Add-Content`, `tee `, `sed -i`, `>`, `python.*open\(.*['"](w|a|x)`): nếu đang có khóa `APPROVE` (chưa duyệt spec/plan/quick) hoặc subagent ghi ngoài `docs/` trước `implement` → **`deny` ngay** (ngăn tái diễn lỗi như `step 1803` dùng `py -3 -c` lọt `edit_gate`).
6. **Chống phình ngữ cảnh & giữ nhắc Clean Code sau compaction:**
   - Tuyệt đối không khôi phục `"same as last turn — unchanged"` hay bơm lặp nguyên văn `chung.md` 7 KB ở mỗi lượt (bảo vệ mục tiêu giữ ngữ cảnh `< 200k` token để model sinh ở `~6–18 s` thay vì `53 s`).
   - Chỉ bơm đúng **1 dòng** `[TDQ:GON]` (đầu pha `implement` & ngay sau compaction/resume) và 1 dòng `[TDQ:QC]` (đầu pha `qc`), kèm 1 dòng `TDQ:RULE` ngắn lần đầu chạm mỗi ngôn ngữ mới; đồng thời sửa `session_start.rs` dùng `char_indices()` để cắt an toàn chuỗi UTF-8 tiếng Việt.

### 4.3. Bản đồ khắc phục `10/10` hạn chế từ Audit `2026-11-19-1457`

| # | Hạn chế từ Audit trước | Giải pháp trực tiếp trong `Hybrid` + `Smart Hardening` | Ảnh hưởng độ trễ |
|---|---|---|---|
| 1 | Mất phanh `TDQ:TICK` trên AGY & Rust | Khôi phục `deny` 0/>1 `[~]`, ngưỡng `STREAK=8`, chặn cứng `Stop` nếu `plan_sha` đứng yên (cả Hot-path Rust & Python) | `+1–2 ms` đọc file plan tại Hot-path |
| 2 | Rust bỏ rơi `PreInvocation` & `PostInvocation` | Match đủ 6 sự kiện trong `main.rs`; mid-turn chạy Rust (~22ms), đầu lượt mới gọi `dispatch.py` | `+0 ms` (nhanh hơn Python toàn phần `4×`) |
| 3 | Lệch schema JSON AGY 2.0 (Input/Output) trên Rust | Đồng bộ `protocol.rs` xuất `injectSteps`/`reason` + nhận `toolCall`, `workspacePaths`, `write_to_file`/`replace_file_content` | `+0 ms` |
| 4 | Thiếu 14/22 cổng & điểm mù Parity Test | Mọi cổng chưa port trên Rust tự động chuyển về `dispatch.py` (`Cold-path` fallback); mở rộng Parity Test `22/22` mã × `6` sự kiện | Chỉ áp dụng cho ~9% `Cold-path` |
| 5 | Mềm hóa `TDQ:LOG` & `TDQ:DOD` ở `Stop` | Bật lại chặn cứng `TDQ:LOG` ở `Stop` (trừ `docs/.staging*`, `docs/tdq/`, `graphify-out/`); giữ nhắc `DOD` trước khi cho phép `idle` | Chỉ chạy tại `Stop` có active request |
| 6 | Lỗ hổng `continuationActive` & `stop_streak` Rust | Dùng `MAX_STREAK=2` gắn `plan_sha` thay cho `return` sớm; fix `dispatched_count` `[>]` & mã `"UNFINISHED"` trong `stop_streak.rs` | `+0 ms` |
| 7 | Độ trễ `queue_remind` & phân mảnh 2 `.tdq-runtime` | Thống nhất **duy nhất** `docs/tdq/.tdq-runtime/` cho cả Rust và Python; nhắc khẩn phát trực tiếp qua `reason`/`injectSteps` | `-1 ms` (bỏ đọc/ghi nhầm dir) |
| 8 | Nới `TDQ:SEARCH` + sót `graphify` ở `PostToolUse` | Bít lỗ hổng `rg`/`grep`/`Select-String` khỏi `malformed_allow`; ghi nhận `graphify` từ `run_command` vào `.tdq-search.jsonl` | `+0 ms` |
| 9 | Tắt `TDQ:RULE`/`GON`/`QC` & lỗi cắt byte UTF-8 Rust | Bơm 1 dòng neo đầu pha & sau compaction; fix `session_start.rs` dùng `char_indices()` và phân giải đường dẫn từ `PLUGIN_ROOT` | `+0 ms` |
| 10 | Lách cổng qua Shell, sót `qc-tester` & `Arguments` | Thêm `"qc-tester"` vào `bash_gate.py`; chặn shell mutator khi khóa `APPROVE`/`TEAM`; bọc `Arguments` trong `pre_tool_use.rs` | `+0,5 ms` regex trên `run_command` |

### 4.4. Lộ trình triển khai 3 chặng đề xuất (cho request implement kế tiếp)

| Chặng | Phạm vi công việc cụ thể | Tiêu chí kiểm chứng hoàn tất |
|---|---|---|
| **Chặng 1 (P0 — Khôi phục 100% Behavior & Schema AGY 2.0)** | Sửa `main.rs` nhận đủ `PreInvocation`/`PostInvocation`; chuẩn hóa `protocol.rs` xuất `injectSteps`/`reason` và parse đủ field AGY 2.0; thống nhất `docs/tdq/.tdq-runtime/`; cài cơ chế **delegate tự động về `dispatch.py`** cho các sự kiện/cổng Rust chưa xử lý (`Cold-path` fallback theo routing table thay vì âm thầm `allow`). | `tdq-dispatch` trả đúng JSON `injectSteps` & `reason`; không còn sự kiện nào bị silent no-op; `100%` cổng hoạt động ngay từ bản P0. |
| **Chặng 2 (P1 — `Smart Hardening` & Di chuyển Hot-path sang Rust)** | Áp dụng 6 quy tắc `Smart Hardening` (bật lại cứng `TDQ:TICK` ngưỡng 8, `TDQ:LOG` trừ staging, `continuationActive` theo `plan_sha`, thêm `qc-tester`, shell mutator guard, fix UTF-8 `session_start.rs`); hoàn thiện xử lý `Hot-path` thuần Rust cho `PreInvocation` mid-turn, `PostInvocation`, `edit_gate` core, `read_gate`, `ask_gate`, `lsp_gate` O(1) (kèm bọc `Arguments`). Biên dịch lại đủ 3 binary (Windows, Linux musl, macOS arm64). | Đo lại `bench_dispatch.py`: `Hot-path` (`~91%`) giữ `<= 28 ms` qua `cmd /c`, độ trễ trung bình có trọng số `<= 36 ms`; mô phỏng bắt buộc `TDQ:TICK` (thiếu `[~]`) & `TDQ:LOG` đều chặn 100%. |
| **Chặng 3 (P2 — Golden Parity Test Suite `22/22` mã × `6` sự kiện)** | Mở rộng `tests/test_rust_dispatch_parity.py` từ `9` ca lên **bộ Golden Parity phủ đủ `22` mã cổng × `6` sự kiện**, so khớp toàn bộ cấu trúc (`decision`, `reason`, `injectSteps`, `overwrite`, `metadata.user_markdown`) giữa `tdq-dispatch` và `dispatch.py` chạy trực tiếp. | `pytest tests/test_rust_dispatch_parity.py` 100% PASS cả trên Windows, Linux và macOS; zero Behavior Drift khi bật/tắt `TDQ_HOOK_ENGINE=python`. |
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-19-1612-research-behavior-va-hieu-nang.manifest.json -->
<!-- manifest_digest: a4517ae9dd4a4219dd41a4bd1e45a98369a3a917c12e065f0dae5db8e9c947aa -->
<!-- tdq-archify-binding:end -->