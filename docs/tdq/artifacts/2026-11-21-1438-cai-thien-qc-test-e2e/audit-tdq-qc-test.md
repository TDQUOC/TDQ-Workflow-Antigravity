# Kiểm toán 3 Lớp QC & Kiểm thử Nội bộ TDQ (`T1.1`)

Ngày: 2026-11-21 · Request: `2026-11-21-1438-cai-thien-qc-test-e2e` · Phạm vi: `Zero-Code-Touch` (chỉ đọc mã nguồn, biên bản QC, log thời gian và sổ test)

> **Tóm tắt kiểm toán:** Qua đọc trực tiếp 3 lớp (quy trình/template, 8 biên bản `docs/tdq/qc/*.md` + `timing.jsonl` + `.tdq-test.jsonl`, và runner `scripts/tdq_test.py` + `doc_lint.py`), giả thuyết **H1**, **H2** và **H4** được xác nhận **Đúng** (riêng **H2** thực tế còn chậm gấp ~4 lần giả định ban đầu: mặc định `--workers 1` tốn trung vị **`1,190.1s` / ~19.8 phút** mỗi lượt `tron-bo`, không phải ~5 phút), còn **H3** **Đúng một phần** vì TDQ đã có sẵn mảnh ghép `Given-When-Then` (`vision-test-loop.md`) và 5 lớp `tdq-browser-test`, nhưng đang bị giấu sau điều kiện phụ và viết theo khuôn máy đọc thay vì kịch bản cho dev. Đồng thời, TDQ sở hữu 5 nhóm chốt bảo vệ lõi có giá trị cao (`TDQ_LOG=1/0`, khóa toàn vẹn receipt `tron-bo`, guard `[TDQ:GIT]`/`[TDQ:STATE]`/`[TDQ:READONLY]`, parity/latency Rust `tdq-dispatch`, và bán kính AST `vung-cham`) cần **giữ lại dưới dạng tự động hóa ngầm**, không xóa bỏ.

---

## 1. Định lượng 3 lớp TDQ QC & Test

### 1.1. Lớp 1 — Quy trình, Template & Agent QC

| Thành phần (`path:line`) | Cơ chế hiện hành | Tác động tới độ đọc & E2E |
|---|---|---|
| `skills/tdq-build/references/qc.md:36-40,55-58` | Bảng `muc_qc` (`lite`/`full`/`ultra`); mặc định fail-closed là `full` (`scripts/tdq_state.py:215-231`). Cả `lite` và `full` đều đặt **`smoke test = KHÔNG`** và **`runtime test = KHÔNG`** (chỉ bật ở `ultra` với trần 120s tại `qc.md:125-141`). | Mọi request `full` mặc định bỏ qua smoke/runtime E2E để tránh check bị treo (`qc.md:56-58`), tạo vùng mù tích hợp sống. |
| `skills/tdq-build/references/qc.md:67-68,93-123` | Số mục QC = số dòng DoD + 4 mục cố định (`QC-F1..F4`) + kiểm tra `§3b` (`doc_lint.py --pair`). **`qc.md:99` ép cứng lệnh `tdq_test.py tron-bo --workers 1 --fresh --reuse off`**. | Ép chạy tuần tự 1 worker cho toàn bộ suite (~4.600+ tests), kéo thời gian chờ QC lên ~20–22 phút. |
| `skills/tdq-build/references/qc.md:148-171` | Khuôn `docs/tdq/qc/<slug>.md` gồm bảng `| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |`, trích log thô và mục `Lệch spec chờ duyệt`. | Không có khung "kịch bản người dùng → thao tác → kết quả mong đợi" bằng ngôn ngữ tự nhiên cho dev. |
| `skills/tdq-build/references/qc-vong-fix.md:5-25` | Tối đa 3 vòng sửa (`QC1.x`..`QC3.x`), ép ghi task sửa bằng khung `R15-Compact` 5 trường (`Chạm`, `Sinh ra`, `Neo & Công cụ`, `Trước → Sau`, `Tiêu chí & Assert`) vào `plan.md`. | Phù hợp cho điều phối agent, nhưng không tạo bảng lỗi/tái hiện theo luồng sử dụng thực tế. |
| `skills/tdq-build/references/report-template.md:112-154` | Trộn tóm tắt dev với telemetry V2 (`treo_tuong_giay`, `api_request_seconds`, `tool_call_seconds`, `observed_union`, `unattributed`, `model_giay=null`), `Agent Role Telemetry`, `tdq-archify-binding`, `lech list`, `lsp_bo_qua`. | Trên Antigravity 2.0 (`docs/tdq/reports/2026-11-21-1253-fix-subagent-tools-bump.md:96-114`), cả 5 cột quan sát V2 đều in `— [unavailable]` / `no_usable_source`, gây nhiễu mắt người đọc. |
| `skills/tdq-browser-test/SKILL.md:19-75` & `skills/tdq-build/references/vision-test-loop.md:29-77` | Có đủ quy trình 5 lớp Chrome DevTools MCP (`Layer 1..5`), khung 3 tầng `Given - When - Then`, 6 anti-pattern `ANTI-1..ANTI-6`, và vòng so ảnh `tdq_vision_diff.py`. | `qc.md:115` chỉ gọi `vision-test-loop.md` khi *"the DoD reaches them"*; `0/8` biên bản QC gần nhất kích hoạt kiểm tra này. |
| `agents/tdq-qc-tester.md:1-31` | Subagent kiểm độc lập (`tools: Bash, Read, Grep, Glob`), tự chạy lại DoD, probe edge case, kiểm `TDQ_LOG=0`, trả bảng digest `<= 1,500` ký tự. | Chỉ chạy mặc định ở mức `ultra` (`qc.md:36-40,71-73`); ở `full` thường chỉ dùng cho release/nhánh rủi ro hoặc bỏ qua. |

### 1.2. Lớp 2 — Đo đạc trên 8 biên bản `docs/tdq/qc/*.md`, `timing.jsonl` & `.tdq-test.jsonl`

#### A. Phân loại `82` mục kiểm trong `8` biên bản QC gần nhất (`2026-11-20` – `2026-11-21`)

Tiêu chí phân loại áp dụng thống nhất cho toàn bộ mục đỉnh (`Q*`, `QC-F*`, `T*`, không đếm trùng mục con lặp lại ở phần `## Bằng chứng`):
- `meta-compliance/doc`: kiểm tra quy trình/tài liệu nội bộ (`doc_lint`, `token_budget`, `i18n_check`, `doc_index`, `EV-xxx`/`path:line`, `Zero-Code-Touch`, `CHANGELOG <= 500`, `QC-F3` kiến trúc `docs/kien-truc.md`, `QC-F4` 5 câu SOLID trong `skills/tdq-conventions/references/clean-code.md:112-121`, hoặc `QC-F1` khi request `docs` miễn chạy `tron-bo`).
- `unit/integration`: chạy `pytest`/`unittest`/`cargo test`/`clippy`/`py_compile`, hồi quy `Chạm:` (`QC-F2`), `tron-bo` (`QC-F1`), đóng gói tĩnh (`build_portable`, `agy plugin validate --strict`), và test E2E mô phỏng trong `TemporaryDirectory`.
- `true E2E/runtime behavior`: thực thi/probe trực tiếp trên tiến trình thật, môi trường OS thật hoặc host sống ngoài fixture pytest (SSH `ubuntu-100-95`/`mbair`, probe nhị phân `tdq-dispatch.exe` sống với payload đối kháng / `TDQ_LOG=0/1` / `sidA-sidB`, hoặc gọi thật `invoke_subagent` trong Antigravity).

| Biên bản (`docs/tdq/qc/...`) | Dòng | Ký tự (~Tok) | Tổng mục | `meta-compliance/doc` | `unit/integration` | `true E2E/runtime` | Ghi chú thực tế |
|---|---|---|---|---|---|---|---|
| `2026-11-20-0015-trien-khai-plan-v2-planner-spec.md` | 41 | 6,364 (~1,818) | 10 | 4 | 6 | 0 | `tron-bo` `4,525` cases mất `1,370.06s` |
| `2026-11-20-1056-phan-tich-nang-cap-agent.md` | 74 | 3,377 (~965) | 9 | 8 | 1 | 0 | Request `docs` vẫn chạy `tron-bo` **`1,227.94s`** (`L13`) |
| `2026-11-20-1230-trien-khai-4-de-xuat-agent.md` | 43 | 8,826 (~2,522) | 10 | 3 | 5 | 2 | Mức `ultra`: 17 probe `tdq-dispatch.exe`; chạy `tron-bo` 3 lần |
| `2026-11-20-2355-toi-uu-research-phan-tich.md` | 82 | 8,054 (~2,301) | 10 | 10 | 0 | 0 | `100%` kiểm tra hồ sơ `EV-xxx`, `ND-*`, `doc_lint`, `git diff` |
| `2026-11-21-0217-trien-khai-investigate-v2.md` | 119 | 15,890 (~4,540) | 10 | 3 | 4 | 3 | Vượt ngưỡng `3,500` tok; có `qc_probe.py`, `sidA/B`, `TDQ_LOG` |
| `2026-11-21-0917-mac-dinh-trinh-bay-ngan.md` | 76 | 6,900 (~1,971) | 9 | 6 | 3 | 0 | Sửa template UX nhưng `0` check render người dùng; `tron-bo` `1,327.59s` |
| `2026-11-21-1034-bump-version-release-local.md` | 61 | 10,686 (~3,053) | 11 | 3 | 6 | 2 | **`v0.103.0`**: `4,603 passed` (`1,332.27s`), vẫn vỡ `8/8` subagent (`L56`) |
| `2026-11-21-1253-fix-subagent-tools-bump.md` | 163 | 17,029 (~4,865) | 13 | 3 | 7 | 3 | **`v0.103.1`**: `--workers 6` tốn `325.82s` + `314.31s`; có live `invoke_subagent` |
| **Tổng cộng 8 biên bản** | **659** (TB 82.4) | **77,126** (TB 9,641 / ~2,754) | **82** | **40 (`48.8%`)** | **32 (`39.0%`)** | **10 (`12.2%`)** | `0/8` dùng `tdq-browser-test` hay `tdq_vision_diff.py`; `4/8` có `0` E2E/runtime |

#### B. Đo thời lượng từ `docs/tdq/timing.jsonl` (`179` bản ghi) & `docs/tdq/.tdq-test.jsonl` (`38` bản ghi)

- **`docs/tdq/timing.jsonl` (`179` dòng: `140` v1, `39` v2):**
  - Toàn bộ `20` request gần nhất (`17` `full` + `3` `quick`): `total_wall` trung vị `12,335.1s` (P90 `51,928.6s`, đã gồm thời gian chờ user duyệt theo `report-template.md:149`); `implement` trung vị **`2,693.0s`** (`44.9` phút, n=15); `qc` trung vị **`1,518.0s`** (`25.3` phút, n=16, mean `2,279.5s`, P90 `5,389.0s`); `report` trung vị `1,753.5s` (n=20).
  - Riêng `17` request lane `full` trong 20 lượt gần nhất: `implement` trung vị **`2,998.5s`** (mean `3,772.8s`, P90 `7,349.0s`, n=14); `qc` trung vị **`1,518.0s`** (mean `2,279.5s`, P90 `5,389.0s`, n=16); tỷ trọng pha `qc / total_wall` có trung vị `9.0%` (dao động `1.1%` ở `1034` và `6.8%` ở `1253` nơi `tron-bo` được chạy ngay trong pha `implement`, tới `39.6%` ở `0917` với `qc=1,635s / total=4,133s`).
  - Riêng `10` request gần nhất: `implement` trung vị `2,624.5s` (mean `3,209.5s`, P90 `7,349.0s`, n=8); `qc` trung vị `1,518.0s` (mean `2,303.9s`, P90 `5,432.0s`, n=10); `report` trung vị `2,355.2s` (n=10).
- **`docs/tdq/.tdq-test.jsonl` (`38` dòng: `28` `tron-bo`, `10` `vung-cham`, `0` `bo-sot`):**
  - **`tron-bo` (`28` lượt thực chạy):** trung vị **`1,190.1s` (`19.8` phút)**, trung bình `988.9s`, P90 `1,340.7s`, max `1,370.1s`. Trong `10` lượt gần nhất, trung vị tăng lên **`1,241.4s` (`20.7` phút)**!
  - **Tỷ lệ `tron-bo` bị đánh dấu `INCOMPLETE`:** **`6 / 28` (`21.4%`)**. Đặc biệt ở `2026-11-20-1230`, `tron-bo` chạy 3 lần (`1,243.21s` FAIL + `1,215.05s` INCOMPLETE + `1,239.60s` PASS = **`3,697.86s` > 61 phút**); ở `2026-11-21-1253` (`v0.103.1`), dù dùng `--workers 6`, lượt 1 chạy đủ `4,641` cases trong **`325.82s`** vẫn bị hủy thành `INCOMPLETE`, buộc chạy lại lượt 2 mất thêm **`314.31s`** (tổng **`640.13s`**).
  - **`vung-cham` (`10` lượt non-skip):** `7/10` lượt trúng bán kính chỉ mất **`5.47s`–`64.73s`** (trung vị nhóm trúng `13.09s`; trung vị chung cả 10 lượt là `38.9s`), nhưng **`3/10` lượt bị ép rơi về `scope=full` (`121.7s`, `1,152.96s`, `1,386.3s`)**.

### 1.3. Lớp 3 — Hạ tầng Test Runner & Guards (`scripts/tdq_test.py`, `scripts/tdq_test_receipt.py`, `scripts/doc_lint.py`)

| Vị trí (`path:line`) | Cơ chế cài đặt | Lỗ hổng / Ma sát đo được |
|---|---|---|
| `scripts/tdq_test.py:967,1480-1488` | `_worker_count` mặc định **`1`** (khi không truyền `--workers`), `--timeout` mặc định **`1800`** giây (30 phút), `--reuse` mặc định **`"off"`**. | Kết hợp với `qc.md:99` (`--workers 1 --fresh --reuse off`), mọi đợt QC `full` đều chạy tuần tự mất ~20–22 phút dù máy hỗ trợ `--workers 6` (`314.31s`, nhanh gấp **4.28x**). |
| `scripts/tdq_test.py:104-105,382-395` | `DATA_EXTS` chỉ liệt kê `{".md", ".json", ".jsonl", ".txt", ".yml", ".yaml", ".toml", ".csv", ".png", ".svg"}` — **thiếu `.html` / `.htm`**. | Mọi file preview HTML trong `docs/tdq/spec/*-preview.html` bị `_ly_do_ngoai` coi là code/file lạ ngoài `TOP_DIRS`, ép `vung-cham` chạy full `220` module (`1,386.3s` ở lượt `[22]` của `.tdq-test.jsonl` ngày `2026-11-20`!). |
| `scripts/tdq_test.py:1175-1178` & `scripts/tdq_test_receipt.py:29-34,146-156` | `_finish_run` đánh dấu `INCOMPLETE` nếu `source_before != source_after`. Hàm `_source_files` bỏ qua `EXCLUDED_DIRS = {".git", ".venv", ".venv-tokens", "node_modules", "__pycache__", ".pytest_cache", ".tdq-worktrees"}` — **thiếu `.ruff_cache`**. | Khi `ruff check` chạy trong lúc `tron-bo` đang chạy (`2026-11-21-1253`), file dưới `.ruff_cache/0.17.3/*` thay đổi làm toàn bộ `4,605` bài test PASS bị đánh dấu `INCOMPLETE` sau **`325.82s`**. |
| `tests/` (`222` file `test_*.py`) | Quét `pytest.mark` trên toàn `222` file: chỉ `15` file có marker (`parametrize`, `skip`, `skipif`, `xfail`), **`0` file phân tầng `@pytest.mark.unit` / `smoke` / `e2e` / `slow`**. `tests/test_devtool_mcp_integration.py:42-88` chỉ mock `.claude.json` và kiểm chuỗi `SKILL.md`. | `tdq_test.py` không có đường dẫn chạy riêng nhóm `Changed-Flow E2E Smoke` nhanh; `tron-bo` trộn tất cả vào một lệnh khổng lồ. |
| `scripts/doc_lint.py:202-327,533-624,1279-1304` | Kiểm tra `R1..R15` (câu `> 40` từ `R5`, cap dòng skill `R6`, SHA-256 `token-budget.json` `R13`, ngưỡng số `R14`, cấu trúc Plan V2+ & `ANTI2_PATTERNS` `R15`). | Hữu ích như lint tĩnh, nhưng nhiều QC report đưa kết quả lint/token/i18n thành hàng loạt hạng mục DoD chính (`48.8%` tổng số mục kiểm). |

---

## 2. Đối chiếu chi tiết Giả thuyết H1–H4

### H1 (Hàn lâm hóa & nặng nghi thức) — **Đúng**
- **Bằng chứng định lượng:**
  - `40 / 82` mục kiểm (**`48.8%`**) trong `8` biên bản `docs/tdq/qc/*.md` gần nhất là kiểm tra tuân thủ quy trình/tài liệu/kiến trúc/SOLID (`meta-compliance/doc`), trong khi chỉ `10 / 82` (**`12.2%`**) kiểm hành vi runtime/E2E sống. Ở 2 request `investigate` gần đây (`1056` và `2355`), tỷ lệ này là `8/9` (`88.9%`) và `10/10` (`100%`); ở request chỉnh template UX (`0917`), tỷ lệ meta/doc là `6/9` (`66.7%`) và `0/9` E2E người dùng.
  - Biên bản QC trung bình dài **`82.4` dòng / `9,641` ký tự (~`2,754` token)**, 2 biên bản lên tới `15,890` ký tự (~`4,540` token) và `17,029` ký tự (~`4,865` token). Cấu trúc lặp 3–4 tầng (bảng `Q1..Qn` + `QC-F1..F4` + mục `## Bằng chứng` chép lại đúng thông tin trên + phần `report` chép lại lần nữa kèm 5 cột V2 `— [unavailable]`).
- **Điểm giới hạn công bằng:** Ở các request có chạm runtime/Rust/agent (`1230`, `0217`, `1034`, `1253`), đội ngũ vẫn chèn các probe CLI/SSH thực sự (`10/82` mục), nên không thể nói TDQ *chỉ* làm giấy tờ — nhưng tỷ lệ nghi thức dày đặc khiến dev khó nhìn ra "tính năng chạy đúng hay gãy ở luồng nào".

### H2 (Unit-heavy, E2E-light, chậm và dễ lọt lỗi tích hợp thật) — **Đúng (thậm chí nghiêm trọng hơn giả định `~5` phút)**
- **Bằng chứng định lượng:**
  - `skills/tdq-build/references/qc.md:38-40,55-58` tắt mặc định cả `smoke test` lẫn `runtime test` ở mức mặc định `full`, và `qc.md:99` ép `--workers 1 --fresh --reuse off`. Vì vậy `tron-bo` không tốn `~5` phút như brief ước tính mà tốn trung vị **`1,190.1s` (~19.8 phút)** trên toàn bộ 28 lần chạy (và **`1,241.4s` / ~20.7 phút** trong 10 lần gần nhất). Chỉ khi user xin chạy nhiều worker (`--workers 6`) ở `v0.103.1`, thời gian mới giảm còn **`314.31s`** (~5.24 phút — vẫn lãng phí thêm **`325.82s`** vì lỗi `.ruff_cache` gây `INCOMPLETE`).
- **Đối chứng sự cố thực tế `v0.103.0` vs `v0.103.1`:**
  - **`v0.103.0` (`docs/tdq/qc/2026-11-21-1034-bump-version-release-local.md:11,12,15,56`, `docs/tdq/reports/2026-11-21-1253-fix-subagent-tools-bump.md:4,14`, `docs/tdq/brief/2026-11-21-1253-fix-subagent-tools-bump.md:20`):**
    - `tron-bo --workers 1` chạy **`4,603 passed, 36 skipped, 2,892 subtests passed` trong `1,332.27s`** (`1,345.26s` trong `.tdq-test.jsonl`), `agy.EXE plugin validate --strict` trả `"findings": []`, và `tdq-qc-tester` chốt `VERDICT: PASS everything`.
    - Tuy nhiên, **`8/8` subagent của gói phát hành `plugins/tdq-workflow-agy/agents/` vỡ ngay lúc dựng executor khi gọi live `invoke_subagent`** (`unknown component: tool "call_mcp_tool" not found in registry`, kèm `grep_search`, `find_by_name`, `list_dir` do `tools/patches/skills_and_agents.py:28-47` đưa vào). Lý do lọt: (1) unit test `tests/test_agent_frontmatter.py:34` tự khóa sai danh sách tool; (2) `tdq-qc-tester` ở `1034` chỉ chạy trên `.agents/agents/` đã cache trước (`qc/1034:56`); (3) mức `full` không yêu cầu bài kiểm smoke gọi live `invoke_subagent` trên plugin vừa build.
  - **`v0.103.1` (`docs/tdq/qc/2026-11-21-1253-fix-subagent-tools-bump.md:9,15,95-97,132`):**
    - Sửa lỗi bằng test âm tính mới **và** bổ sung `Q6` gọi live `invoke_subagent(tdq-explorer)` (`4b121235`) ngay trong Antigravity để chứng minh runtime thật chạy được (`read_file` + `send_message` trả kết quả tức thì). Đồng thời phát hiện thêm điểm ma sát lớn của runner: lần chạy `tron-bo --workers 6` đầu (`task-12326`) đạt `4,605/4,605` pass nhưng bị hủy `INCOMPLETE` sau **`325.82s`** chỉ vì `.ruff_cache` đổi file khi `ruff check` chạy song song.

### H3 (Thiếu tầng kịch bản người dùng plain-language & triage lặp lại) — **Đúng một phần**
- **Bằng chứng trên đĩa:**
  - **Phần TDQ đã có (không thiếu trắng):** `skills/tdq-build/references/vision-test-loop.md:38-77` đã định nghĩa 3 tầng kịch bản `Given - When - Then` (Happy Path, Boundary/Edge, Failure/Recovery) và 6 anti-pattern `ANTI-1..ANTI-6`; `skills/tdq-browser-test/SKILL.md:27-60` có kiểm thử 5 lớp qua Chrome DevTools MCP; `skills/tdq-build/references/qc-vong-fix.md:5-25` có quy trình vòng sửa 3 lượt `QC1.x..QC3.x`.
  - **Phần còn thiếu/lệch (xác nhận vấn đề dev phản ánh):** Các kịch bản này chỉ nằm trong `references/` và được gọi *"only when the DoD reaches them"* (`qc.md:115`); `0/8` biên bản gần nhất chạy `tdq-browser-test`; `tests/test_devtool_mcp_integration.py` chỉ mock config; định dạng báo cáo QC (`qc.md:151-171`) và vòng sửa (`qc-vong-fix.md:12-19`) vẫn là bảng CLI thô + cú pháp `R15-Compact` thay vì kịch bản người dùng plain-language và Bug Board tái hiện từng bước cho dev.

### H4 (Thiếu phân tầng tốc độ theo rủi ro / `Changed-Flow E2E Smoke`) — **Đúng**
- **Bằng chứng trên đĩa:**
  - TDQ đã có `scripts/tdq_test.py vung-cham` (`ban_kinh()` tại `tdq_test.py:448-462`) giúp rút ngắn kiểm thử từ ~20 phút xuống `5.47s`–`64.73s` (`7/10` lượt không fallback). **Tuy nhiên**, `vung-cham` chỉ là bộ lọc *file test đơn vị theo AST tĩnh*, **không phải tầng `Changed-Flow E2E Smoke` theo luồng rủi ro hành vi**:
    1. Toàn kho `tests/` (`222` file) có **`0` file gắn marker `@pytest.mark.smoke` hoặc `@pytest.mark.e2e`**.
    2. `qc.md:38-39` đặt `smoke test = KHÔNG` cho cả `lite` và `full`.
    3. `vung-cham` bị gọi ít (`10` lượt so với `28` lượt `tron-bo` trong `.tdq-test.jsonl`) và dễ rơi vào fallback toàn bộ suite (`3/10` lượt tốn `121.7s`–`1,386.3s`), thậm chí vì thiếu `.html` trong `DATA_EXTS` (`tdq_test.py:104-105`).
    4. Khi chạm vùng rủi ro cao (frontmatter subagent, hooks, compiler plugin, UI/HTML), chưa có cơ chế tự kích hoạt 1 gói E2E smoke <60 giây nhắm đúng luồng vừa sửa trước khi chạy hồi quy nặng.

---

## 3. Phần lõi tốt của TDQ BẮT BUỘC GIỮ LẠI (chuyển sang tự động hóa ngầm)

Các cơ chế dưới đây đã chứng minh hiệu quả chặn lỗi thật và chống gian lận trong kho mã nguồn — **tuyệt đối không xóa**, chỉ rút khỏi báo cáo tay/bảng kiểm rườm rà của dev để chạy ngầm bằng script/CI/hook:

1. **`TDQ_LOG=1/0` (dịch vụ log ISO mặc định trên `stderr`):**
   - Tồn tại nhất quán trên `tdq_test.py:477-480`, `doc_lint.py:26-34`, `token_budget.py:52-55`, `tdq_finish.py:43-50` và `tdq-dispatch`.
   - **Cách giữ ngầm:** Kiểm tự động trong 1 test parity/CLI nhẹ thay vì bắt dev đọc 50 dòng dump `TDQ_LOG` trong biên bản QC (`qc/1253:26-82`).
2. **Cơ chế chống gian lận & toàn vẹn receipt của `tdq_test.py` (`tdq_test_receipt.py`, `details_complete`, `bo_sot`, `source_before/after`):**
   - Khóa chặt bằng chứng thực thi thật (`_phase_result` tại `tdq_test.py:1063-1084`, `_persist_result` tại `tdq_test.py:996-1003`, `module_bo_sot` tại `tdq_test.py:1295-1312`), ngăn chặn tuyệt đối việc báo PASS giả khi test treo/đổi mã nguồn giữa chừng.
   - **Cách giữ & vá ngay:** Giữ toàn bộ xác thực SHA-256 ở tầng runner, nhưng **vá 2 lỗi ma sát**: thêm `.ruff_cache` vào `EXCLUDED_DIRS` (`scripts/tdq_test_receipt.py:29-30`) và thêm `.html`/`.htm` vào `DATA_EXTS` (`scripts/tdq_test.py:104-105`), đồng thời nâng `--workers` mặc định lên mức đa luồng an toàn thay vì ép `--workers 1` trong `qc.md:99`.
3. **Chốt bảo vệ runtime `[TDQ:GIT]`, `[TDQ:STATE]`, `[TDQ:READONLY]` / `[TDQ:SCOPED-WRITE]`:**
   - Thực thi trực tiếp tại `hooks/scripts/bash_gate.py:32-53`, `hooks/scripts/edit_gate.py:78-100`, `hooks/scripts/stop_gate.py:48-52` và `scripts/tdq_state.py:4-10`. Ngăn sửa tay `state.json`, ngăn `Co-Authored-By`, và khóa subagent đọc lén ghi đè code.
   - **Cách giữ ngầm:** Để hook/Rust binary tiếp tục chặn tự động ở runtime; chỉ báo vào báo cáo khi vi phạm, không liệt kê làm mục đọc tay ở mọi biên bản QC.
4. **Rust `tdq-dispatch` hiệu năng cao & đối soát parity Python↔Rust 1-1:**
   - Đạt median **`14.76 ms`** (direct) / **`22.57 ms`** (`cmd /c`) ở `docs/tdq/qc/2026-11-21-0217-trien-khai-investigate-v2.md:52-57` (trong ngưỡng `<= 25 ms` / `<= 32 ms` của `tests/test_rust_latency_benchmark.py:214-218`) và khóa hành vi 22 mã AGY × 6 sự kiện tại `tests/test_rust_dispatch_parity.py:1-50`.
   - **Cách giữ ngầm:** Tự động kích hoạt trong gói smoke/regression chỉ khi diff chạm `hooks/` hoặc `tools/patches/`.
5. **Bán kính ảnh hưởng AST (`ban_kinh` / `vung-cham`), `ANTI-1..6`, & lint tĩnh (`doc_lint.py` R15, `token_budget.py`, `tdq_finish.py`):**
   - `vung-cham` chạy mất **`5.47s`–`20.28s`** ở các thay đổi cục bộ (`tdq_test.py:448-462`), còn `tdq_finish.py` gom lint + workinglog + state + graphify vào 1 lệnh.
   - **Cách giữ ngầm:** Đẩy toàn bộ `doc_lint` / `token_budget` / `i18n_check` / `doc_index` / 5 câu SOLID thành bước **Auto Meta-Gate** trả 1 dòng `PASS/FAIL` tự động (ẩn chi tiết khi xanh), nhường không gian biên bản QC và thời gian chạy chính cho kiểm thử hành vi E2E.
