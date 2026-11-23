# BÁO CÁO — Nghiên cứu tính khả thi hook kiểm tra bản mới từ Git remote

Ngày: 2026-11-23 · Mã yêu cầu: `2026-11-23-0027-research-hook-remote-update` (4 task tick đủ)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Làm hook kiểm tra phiên bản mới từ Git remote rồi nhắc trong chat xin quyền cập nhật và chạy nối tiếp `setupfully` là hoàn toàn khả thi. Mã nguồn Antigravity đã sẵn kênh gửi thẻ nhắc trực tiếp ra chat, bộ lọc xác nhận chặt và chuỗi nối tiếp sau khởi động lại. Tuy nhiên, ta cần thay lệnh cài qua đường dẫn URL bằng bước tải về thư mục tạm rồi đồng bộ an toàn để tránh lỗi khóa file thực thi trên Windows.

**Trước request (trạng thái/flow):** Trên Google Antigravity, luồng kiểm tra bản mới từ xa bị khóa riêng cho Claude (`if not is_agy():` tại `hooks/scripts/session_start.py:242`), không có file cache trạng thái cập nhật ở `${PLUGIN_DATA}`, và `README-Antigravity.md:16` xác nhận IDE không tự kiểm tra hay tự cập nhật plugin cài từ GitHub.
**Sau request (trạng thái/flow):** Kết luận **Khả thi có điều kiện kỹ thuật rõ ràng** (`4/4` giả thuyết `H1`–`H4` đã kiểm chứng, `0` file mã nguồn bị sửa) với kiến trúc 2 chặng không chặn luồng chính:
- **Chặng kiểm tra nền (0 ms độ trễ lượt chat):** `SessionStart` lạnh gọi tiến trình nền tách biệt theo TTL (`6–24` giờ), chạy `git ls-remote --heads` (`696.1 ms`) rồi chỉ tải `plugin.json` tại gốc nhánh `release/antigravity` (`426.0 ms`) khi mã commit thay đổi, lưu vào `${PLUGIN_DATA}/update-stamp.json`.
- **Chặng nhắc, xin quyền và cập nhật nối `setupfully`:** `PreInvocation` phát thẻ `user_markdown` ngắn kèm nút từ chối/hoãn theo phiên bản; khi người dùng đồng ý rõ ràng, hệ thống sao lưu ra `${PLUGIN_DATA}/backups/`, tải nhánh mới vào thư mục tạm rồi đồng bộ tại chỗ kèm thay thế nguyên tử file `.exe` và gọi nối `tdq_setup.py --setupfully` → khởi động lại → `--post-restart-verify`.
**Đã test gì:** Khảo sát đối chiếu `13` bằng chứng nguồn trên `hooks/`, `scripts/`, `tools/`, `tests/`, đo thời gian trực tiếp `git ls-remote --heads`, kiểm tra HTTP `raw.githubusercontent.com`, rà soát `agy plugin --help` / `list --json`, kiểm tra tiến trình Windows và chạy kiểm chứng `QC-I1..I4`.
**Kết quả test:** `13/13` bằng chứng đạt độ tin cậy xác nhận (`9` high, `4` medium) trong `evidence.jsonl`, `QC-I1..I4` đạt `PASS` (`4/4` dòng DoD đạt), `0` thay đổi ngoài phạm vi `docs/tdq/`, bác bỏ được `2` giả định sai (vị trí `plugin.json` trên `release/antigravity` và hành vi `agy plugin install <url>`).
**Đầu ra:** `docs/tdq/reports/2026-11-23-0027-research-hook-remote-update.md` · **Archify HTML:** `docs/tdq/reports/2026-11-23-0027-research-hook-remote-update.html`
**Giới hạn:** Chỉ là nghiên cứu thuần (`work_kind=investigate`); chưa chạy thử `agy plugin install <url>` hoặc ghi đè thực trên `~/.gemini/config/plugins/` để giữ nguyên môi trường live theo đúng phạm vi đã duyệt.
**Lệch spec chờ duyệt:** không có
**Git:** chưa commit (đang trên nhánh `docs/research-hook-remote-update`)

---

## Phân tích kỹ thuật chi tiết (`H1`–`H4`)

### 1. Kết luận tổng quát theo từng giả thuyết

| Giả thuyết | Kết luận | Độ tin cậy | Bằng chứng chính |
|---|---|---|---|
| **H1:** Hook nền + kênh nhắc trực tiếp trong chat không làm chậm hot-path | **Xác nhận (Verified)** | Cao (`Verified`) | `[60cecd885103]`, `[4460616dff10]`, `[70f424dec3be]`, `[9f9ccab26d84]`, `[c2abe962c021]`, `[2cc5916f83b9]` |
| **H2:** So sánh bản mới từ Git remote không clone cả repo và không dính 60 req/h | **Xác nhận (Verified)** | Cao (`Verified`) | `[e8f84942db63]`, `[e97a0a48851b]`, `[a5470d07b891]`, `[af3482c08ee7]` |
| **H3:** Xin quyền chặt trong chat → cài bản mới → nối `setupfully` + restart | **Xác nhận có điều kiện (Conditional)** | Cao (`Verified` chuỗi / `Inferred` phần staging) | `[09a244c0d12f]`, `[4c663a1ce64b]` |
| **H4:** Ghi đè plugin trên Windows khi IDE đang mở, giữ state + `caveman` + 23 mã | **Xác nhận có điều kiện (Conditional)** | Cao (`Verified` rủi ro khóa / state) | `[a8281e46df21]`, `[c2abe962c021]` |

### 2. Phân tích từng nút thắt và phát hiện thực tế (`T1`–`T3`)

#### T1 — Điểm gắn hook và kênh hiển thị cho người dùng (`H1`)
- **Đường chạy thật của `SessionStart` (`[60cecd885103]`):** Dù `hooks/rust/tdq-dispatch/src/events/session_start.rs:10-62` tồn tại, bộ định tuyến `route_event()` tại `hooks/rust/tdq-dispatch/src/main.rs:330` định tuyến `"SessionStart"` qua nhánh `RouteOutcome::DelegatePython`. Vì thế, mỗi đầu phiên Antigravity đều chạy `node scripts/tdq_hook_launcher.mjs` → `tdq-dispatch.exe` → Python `session_start.py` (`plugins/tdq-workflow-agy/hooks.json:4-8`).
- **Bảo toàn `< 50 ms` hot-path (`[4460616dff10]`):** `PreInvocation` trong `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs:189-239` chỉ chạy hot-path Rust cho subagent và giữa lượt (`<= 25 ms`), còn lượt hỏi mới của người dùng trả về `DelegatePython` tới `prompt_context.py`. Gọi tiến trình nền tách biệt (`detached Popen`) từ `session_start.py` hoàn toàn không ảnh hưởng hot-path.
- **Lỗ hổng hiện tại (`[70f424dec3be]`):** `hooks/scripts/session_start.py:237-246` khóa `kich_hoat_kiem_tra_remote_nen()` trong `if not is_agy():` (`:242`), nhưng lại để `doc_thong_bao_update_moi()` chạy không khóa (`:239`). Hệ quả là Antigravity đọc thông báo cập nhật nhưng không bao giờ có tiến trình nền tạo dữ liệu cho nó.
- **Kênh hai chiều (`[9f9ccab26d84]`, `[2cc5916f83b9]`):** `hooks/rust/tdq-dispatch/src/protocol.rs:75-108,150-178` và `tools/patches/agy_hooks.py:495-505,755-774` cung cấp sẵn cặp `injectSteps[].systemMessage.systemMessage` (nhắc AI) và `metadata.user_markdown` tối đa 1200 ký tự (thẻ hiển thị trực tiếp cho người dùng trong chat). Trong bản biên dịch `plugins/tdq-workflow-agy/hooks/scripts/prompt_context.py:625`, `_emit_setup_hooks` đã truyền sẵn `user_md_fn=emit_user_markdown` (đã test xanh ở `tests/test_hook_setup_resume.py:233-285`), còn `session_start.py` hiện chưa gọi `emit_user_markdown`.
- **Hợp đồng 23 mã `[TDQ:*]` (`[c2abe962c021]`):** `tools/patches/agy_hooks.py:36-61`, `tests/test_rust_dispatch_parity.py:50,697-701` và `tests/test_hooks_dual_protocol.py:72-76` khóa cứng đúng 23 mã. Không nên thêm `[TDQ:UPDATE]` hay `[TDQ:REMIND]`; dùng lại `[TDQ:SETUP]` (hoặc tiền tố không nằm trong bộ mã như `[TDQ]`) vừa giữ nguyên parity vừa tận dụng thẻ 4 phần sẵn có.

#### T2 — Cơ chế dò bản mới từ nhánh Git remote (`H2`)
- **Bác bỏ giả định đường dẫn `plugin.json` (`[a5470d07b891]`):** Đo HTTP trực tiếp trên GitHub cho thấy nhánh phát hành `release/antigravity` đặt `plugin.json` ở **gốc nhánh** (`.../release/antigravity/plugin.json` → HTTP 200 trong `426.0 ms`, `v0.105.0`), còn đường dẫn `.../release/antigravity/plugins/tdq-workflow-agy/plugin.json` trả **HTTP 404** (`511.6 ms`). Ngược lại, nhánh nguồn `main`/`dev` đặt file ở `plugins/tdq-workflow-agy/plugin.json` (`HTTP 200` trong `364.5 ms`, `v0.98.0`). Vì thế hàm `doc_phien_ban_plugin` ở `scripts/tdq_setup.py:1573-1585` (chỉ đọc `.claude-plugin/` và `.codex-plugin/`) và mọi URL cố định đều sẽ đọc trượt nếu không thử fallback gốc → thư mục con.
- **Đo thực tế trên repo (`[e97a0a48851b]`):**
  - Thư mục cài live `~/.gemini/config/plugins/tdq-workflow-agy/` chứa `plugin.json` (`v0.105.0`) nhưng **không có `.git`** và **không có file `.tdq-update-stamp*`**.
  - Lệnh `git ls-remote --heads https://github.com/TDQUOC/TDQ-Workflow-Antigravity` chạy hết `696.1 ms` (`rc=0`), trả đủ 5 nhánh (`release/antigravity` tại `441435ce`), không dùng GitHub REST API nên không dính giới hạn 60 request/giờ cho IP chưa đăng nhập.
- **So sánh 3 phương án dò bản mới:**

| Tiêu chí | A: Chỉ `git ls-remote` SHA | B: Raw URL / GitHub API | C: Hai bước Hybrid + Nền TTL (Khuyến nghị) |
|---|---|---|---|
| **Độ trễ lượt chat** | ~700 ms nếu chạy đồng bộ | ~426 ms nếu chạy đồng bộ | **< 1 ms** (đọc JSON cục bộ; mạng chạy `Popen` nền) |
| **Giới hạn API** | Không có | API 60 req/giờ; raw ~5 phút cache CDN | `git ls-remote` trước; chỉ tải `plugin.json` khi đổi SHA |
| **Repo private** | Dùng credential helper/SSH (cần `GIT_TERMINAL_PROMPT=0` + timeout 4s) | Raw 404 nếu thiếu token | Tận dụng git auth sẵn có, không treo prompt |
| **Commit không tăng version** | Báo nhầm khi commit doc | So đúng semver nhưng tốn request định kỳ | So SHA xong mới đọc `plugin.json` + so `tach_version` |
| **Offline / mất mạng** | Phải ghi `last_error` + TTL tránh thử lại | Tương tự | Ghi `last_check` + `last_error`, im lặng hết TTL |

#### T3 — Sai lệch CLI `agy plugin install`, khóa file Windows và nối `setupfully` (`H3`, `H4`)
- **Phát hiện sai lệch quan trọng về `agy plugin install` (`[09a244c0d12f]`, `[af3482c08ee7]`):** Trong `README-Antigravity.md:10,16` ghi cài bằng `agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity/tree/release/antigravity`. Nhưng kiểm tra thực tế trên máy: `agy.exe plugin --help` liệt kê `install <target> (supports plugin[@marketplace])`, và `agy plugin install --help` trả lỗi `Error: install target must be a directory: --help`; `agy plugin list --json` cũng xác nhận plugin `tdq-workflow-agy` đang nằm tại `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` không có trường `"source"` marketplace. Vì vậy bộ tự cập nhật **không được phụ thuộc mù quáng vào `agy plugin install <url>`**, mà nên tải bản mới về thư mục staging cục bộ (`git clone --depth 1 --branch <nhánh>` hoặc tải zip từ GitHub) rồi dùng `install_agy_plugin.py` / `agy plugin install <thư_mục_tạm>`.
- **Cô lập state & bảo toàn `caveman` (`[a8281e46df21]`, `[4c663a1ce64b]`):**
  - Toàn bộ trạng thái sống (`setup-state.json`, `secrets.env`, `setup-pending.flag`) và `backups/` nằm tại `${PLUGIN_DATA}` (`~/.gemini/antigravity/plugin_data/tdq-workflow-agy/`), tách biệt hoàn toàn với thư mục plugin tại `~/.gemini/config/plugins/tdq-workflow-agy/`, nên ghi đè plugin không làm mất key hay trạng thái.
  - `tools/install_agy_plugin.py:164-189,374` đã có sẵn sao lưu sang `${PLUGIN_DATA}/backups/<timestamp>/` và tự giữ bọc `caveman` (`preserved_opt_in`) nếu người dùng đã bật trước đó.
- **Rủi ro khóa file thực thi trên Windows (`[a8281e46df21]`):** `tools/patches/common_utils.py:45-82` (`sync_tree_inplace`) dùng `shutil.copy2` ghi đè tại chỗ. Khi Antigravity đang chạy, `tdq-dispatch.exe` chạy ngắn theo từng hook (tại thời điểm đo có 0 tiến trình thường trú), nhưng `agent-lsp.exe` hoặc chính hook đang mở vẫn có thể gây `PermissionError` (`WinError 5`/`32`, như cảnh báo sẵn ở `scripts/tdq_setup.py:162`). Cách xử lý an toàn: bỏ qua file `.exe` trùng hash SHA256, với file đổi hash thì ghi file `.tmp` cạnh bên + `os.replace` (hoặc đổi tên file cũ sang `.old` để dọn ở lần `SessionStart` sau).
- **Cổng xin quyền & nối tiếp `setupfully` (`[4c663a1ce64b]`):** Bộ lọc `extract_setupfully_trigger` tại `hooks/scripts/prompt_context.py:180-231` đã chặn câu hỏi, trích dẫn, phủ định và lượt không phải người dùng thật (`source` là `compact`/`resume`/`system`). Sau khi cập nhật file plugin xong, chỉ cần chạy `tdq_setup.py --setupfully` để đồng bộ MCP, rule, `GEMINI.md`, đặt `status="awaiting_restart"` + `Host Session Fingerprint`, để lượt mở lại IDE tự nối vào `--post-restart-verify`.

### 3. Kiến trúc khuyến nghị nếu triển khai ở request tiếp theo

1. **Dò bản mới (`scripts/tdq_setup.py` + `hooks/scripts/session_start.py`):** Tách hàm kiểm tra nền dùng riêng cho Antigravity (không đi chung đường `claude plugin`), lưu cache tại `${PLUGIN_DATA}/update-stamp.json` (TTL mặc định `21600`–`86400` giây, tắt bằng `TDQ_AUTO_UPDATE=0`, cho phép chọn nhánh mục tiêu mặc định `release/antigravity`). Dùng `git ls-remote --heads` với `GIT_TERMINAL_PROMPT=0` + timeout 4s; chỉ tải `plugin.json` khi commit SHA đổi, so `tach_version` + lưu `available_version`, `available_sha`, `checked_at`.
2. **Nhắc trong chat + chống spam (`hooks/scripts/prompt_context.py`):** Trên lượt chat mới của người dùng (`is_new_turn=True`), nếu `available_version > installed_version` và chưa nằm trong `dismissed_version` / chưa hết `snooze_until`, phát 1 thẻ `[TDQ:SETUP]` ngắn qua cả `emit_context` và `emit_user_markdown` nêu rõ: bản đang cài → bản mới trên nhánh nào, kèm lựa chọn đồng ý cập nhật (`"cập nhật và setupfully tdq-workflow"`) hoặc bỏ qua bản này (`"bỏ qua bản vX.Y.Z"`).
3. **Thực thi có xin quyền (`scripts/tdq_setup.py --update-and-setupfully`):** Chỉ kích hoạt sau xác nhận tường minh từ người dùng: sao lưu sang `${PLUGIN_DATA}/backups/` → clone nông nhánh đích vào thư mục tạm (`--depth 1`, khóa đúng URL `https://github.com/TDQUOC/TDQ-Workflow-Antigravity`) → kiểm tra hợp lệ `plugin.json` → đồng bộ tại chỗ an toàn trên Windows (skip `.exe` trùng SHA256, atomic replace / `.old` fallback khi `.exe` đang khóa) → giữ `caveman` opt-in → gọi nối `--setupfully` để pin `awaiting_restart` và tự `--post-restart-verify` sau khi khởi động lại IDE.

### 4. Danh sách rủi ro cần khóa trước khi viết code

- **An ninh nguồn tải:** Khóa cứng URL repository cho phép (allowlist từ `plugin.json` / config tin cậy) và verify schema `plugin.json` trước khi đồng bộ; cấm tự chạy lệnh từ nội dung remote khi người dùng chưa xác nhận.
- **Kích hoạt nhầm & vòng lặp nhắc:** Mượn nguyên bộ lọc của `extract_setupfully_trigger`, cộng thêm trạng thái `dismissed_version` và cooldown trong `${PLUGIN_DATA}/update-stamp.json` để từ chối 1 lần là im đến phiên bản kế tiếp.
- **Khóa file Windows & mất kết nối giữa chừng:** Sao lưu trước, tải xong toàn bộ vào temp mới ghi đè; nếu `.exe` bị khóa hoàn toàn thì đổi tên `.old` hoặc báo người dùng chạy ngoài IDE / sau thoát IDE.
- **Giữ hợp đồng test hiện tại:** Không thêm mã `[TDQ:*]` thứ 24 để không làm vỡ 4 bộ test parity (`test_rust_dispatch_parity.py`, `test_hooks_dual_protocol.py`, `test_gate_guidance.py`, `test_investigate_workflow.py`).

---

## Thời gian

```text
Request `2026-11-23-0027-research-hook-remote-update` · lane quick · opened at 2026-11-23T00:29:20+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 1 min | 1 |
| analyze | 7 min | 1 |
| implement | 4 min | 1 |
| Total | 12 min |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
Host metrics unavailable (5 hidden: api_request_seconds, tool_call_seconds, background_job_seconds, observed_union_seconds, unattributed_seconds): no_usable_source, no_usable_observations, wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |
```

## Thân PR (soạn sẵn)

**Tóm tắt:** Nghiên cứu khả thi kỹ thuật (chỉ đọc mã nguồn, không sửa code) xác nhận có thể xây dựng cơ chế hook nền dò phiên bản mới trên nhánh Git remote, nhắc xin quyền qua `user_markdown` và đồng bộ nối tiếp `setupfully` trên Google Antigravity.
**Trước/Sau:** [docs/tdq/reports/2026-11-23-0027-research-hook-remote-update.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/reports/2026-11-23-0027-research-hook-remote-update.html)
**Đã kiểm:**
- Thu thập và hợp nhất `13` bằng chứng nguồn + đo đạc thực tế vào `docs/tdq/artifacts/2026-11-23-0027-research-hook-remote-update/evidence.jsonl`
- Kiểm chứng `QC-I1..I4`, `doc_lint.py`, và `git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` (`0` file mã nguồn thay đổi)
**Rủi ro hồi quy:** Không có (request `work_kind=investigate`, chỉ thêm báo cáo và shard nghiên cứu trong `docs/tdq/`).
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-23-0027-research-hook-remote-update.manifest.json -->
<!-- manifest_digest: 2f60838de83174e6742f59dc1164a77d38b00513effc3d8279edbf30603765eb -->
<!-- tdq-archify-binding:end -->