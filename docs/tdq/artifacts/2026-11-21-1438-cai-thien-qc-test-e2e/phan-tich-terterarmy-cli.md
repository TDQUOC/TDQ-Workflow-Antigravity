# Phân tích kiến trúc & quy trình E2E/QA của `terterarmy-cli`

> **Tóm tắt nhanh**: `terterarmy-cli` (`C:\Users\admin\Documents\terterarmy-cli`, 33 file ngoài `.git/`, MIT license tại `LICENSE:1-21`) không chứa mã nguồn CLI runner thực thi cục bộ mà đóng vai trò **bộ phân phối Control Plane** gồm 4 lớp: tài liệu điều khiển CLI `ta` (`SKILL.md`), máy chủ Hosted MCP qua OAuth (`https://tester.army/mcp`), bộ manifest plugin đồng bộ đa nền tảng agent, và thư viện kịch bản mẫu plain-language (`examples/`) kèm chuẩn triage lỗi (`reporting-template.md`, `BUG_BOARD.md`). Điểm đáng học nhất cho TDQ-Workflow là cách viết kịch bản người dùng **đọc hiểu trong 10 giây**, kỷ luật phân tách hành động (`act`) với khẳng định (`assert`), và chuỗi bằng chứng tái hiện 4 tầng (`run` → `messages` → `telemetry` → `recording`/JUnit). Điểm giới hạn cốt lõi là phụ thuộc hoàn toàn vào cloud `tester.army`, đòi hỏi API key/OAuth + preview/tunnel URL mở ra internet, và thiếu kiểm định nội tại offline (unit suite, Golden Parity Python↔Rust, Pixel-diff Vision Loop, chống test giả `ANTI-*`).

---

## 1. Kiến trúc tổng quan & triết lý *"Agents that test your app like real users"*

### 1.1. Bản chất 33 file trong kho `terterarmy-cli`
Kho mã là gói phân phối công cụ agent của TesterArmy (`github.com/e2e-inc/cli`), phát hành song song cho nhiều hệ sinh thái agent (`README.md:45-136`):

| Thành phần | Tệp tiêu biểu (`path:line`) | Vai trò trong kiến trúc |
|---|---|---|
| **CLI Control Plane docs** | `README.md:23-78`, `skills/testerarmy-cli/SKILL.md:12-17` | Quản trị project, environment, credential, test/group, lịch chạy và đẩy job kiểm thử lên **TesterArmy cloud** qua `ta` / `testerarmy` (gói npm `testerarmy`, `README.md:48`). |
| **Hosted MCP Server** | `mcp.json:1-9`, `.mcp.json:1-8`, `server.json:1-18`, `glama.json:1-4` | Cung cấp endpoint duy nhất `https://tester.army/mcp` (`streamable-http` cho Agent Plugins/Registry, `http` cho Claude Code) dùng **OAuth** thay cho API key (`README.md:90`), phủ ngang tính năng với CLI. |
| **Multi-Platform Plugin & CI Sync** | `plugin.json:1-49`, `.claude-plugin/plugin.json:1-25`, `.claude-plugin/marketplace.json:1-44`, `.codex-plugin/plugin.json:1-46`, `.agents/plugins/marketplace.json:1-20`, `.cursor-plugin/plugin.json:1-24`, `scripts/check-plugin-manifests.sh:1-47`, `.github/workflows/validate-plugin.yml:1-37`, `.github/workflows/publish-mcp-registry.yml:1-99` | Đóng gói `skills/testerarmy-cli/` cùng `.mcp.json` thành plugin cài một lệnh cho Claude Code, Codex, Cursor; kiểm khớp chéo 9 file JSON bằng `jq` + `ajv-cli` + `claude plugin validate --strict`, và tự động xuất bản lên Official MCP Registry qua OIDC. |
| **Skill & Reporting Contract** | `skills/testerarmy-cli/SKILL.md:1-396`, `skills/testerarmy-cli/agents/openai.yaml:1-4`, `skills/testerarmy-cli/references/reporting-template.md:1-26` | Dạy coding agent quy tắc viết step, tách chạy ad-hoc vs lưu test bền vững, chuỗi debug run fail, và khuôn báo cáo PASS/FAILED bắt buộc kèm `runId`. |
| **Examples & Bug Triage** | `examples/README.md:1-49`, `examples/TESTER.md:1-19`, `examples/prompts/ad-hoc-regression.md:1-7`, `examples/tests/01-landing-page.md`–`03-project-create.md`, `docs/BUG_BOARD.md:1-42`, `.github/ISSUE_TEMPLATE/bug_report.yml:1-66`, `.github/ISSUE_TEMPLATE/regression_report.yml:1-47`, `feature_request.yml:1-26`, `config.yml:1-5` | Cung cấp mẫu test plain-language để chuyển đổi thành payload `ta tests create` (`examples/README.md:3-5`) và quy trình báo lỗi/hồi quy có bằng chứng CLI bắt buộc. |

### 1.2. Triết lý *"Agents that test your app like real users"*
Triết lý này được khẳng định trực diện tại `README.md:21` và mô tả mở rộng trong `plugin.json:28`:
1. **Không viết và bảo trì script selector truyền thống**: *"There are no test scripts to write or maintain"* (`plugin.json:28`); agent cloud mở trình duyệt/ứng dụng mobile thật, đọc các bước bằng ngôn ngữ tự nhiên như bàn giao cho đồng nghiệp (`SKILL.md:152`) và tự tìm phần tử qua ngữ cảnh hiển thị.
2. **Tích hợp tri thức ứng dụng (`memories`) để ổn định flow dài**: CLI lưu bền tri thức nền về cấu trúc route, thói quen test, và tùy chọn người dùng theo 3 danh mục `site_structure`, `test_insights`, `user_preferences` (`SKILL.md:98-106`), giúp agent test không phải đoán mò lặp lại.
3. **Vòng lặp khép kín với coding agent trong editor**: thay vì tách QA thành nhóm rời rạc, coding agent tự tạo coverage từ acceptance criteria (`SKILL.md:21-22`), chờ cloud chạy (`--wait --json`), đọc transcript/console/network để tự sửa lỗi mà không rời khỏi editor (`README.md:28-30`, `plugin.json:5,28`).

---

## 2. Cách viết kịch bản E2E plain-language & lý do dev đọc hiểu trong 10 giây

### 2.1. Giải phẫu 5 tài liệu kịch bản mẫu
Các ví dụ trong `examples/` cố tình cực ngắn (chỉ **7 đến 19 dòng**) và dùng chung một khung tư duy nhất:

- **`examples/TESTER.md:1-19` (`19` dòng) — Bối cảnh dùng chung**:
  - Tham số hóa điểm đích bằng `<target_url>` (`TESTER.md:3`).
  - `## Scope` (`TESTER.md:5-8`): ưu tiên phát hiện regression chức năng, chủ động bỏ qua nhiễu thẩm mỹ nhỏ trừ phi chặn core flow.
  - `## Authentication` (`TESTER.md:10-14`): 3 bước tuần tự có chốt điều kiện chuyển tiếp (*"Continue only after dashboard/home is visible"*).
  - `## Reporting` (`TESTER.md:16-19`): nhị phân `PASS` (khi mọi check đạt) / `FAILED` kèm lý do ngắn gọn, cụ thể.
- **`examples/tests/01-landing-page.md:1-10` (`10` dòng) — Khói trang chủ**:
  - `Goal:` 1 dòng duy nhất (*"verify landing page is reachable and primary CTA is visible"*, `01-landing-page.md:3`).
  - `Steps:` 4 bước đánh số (`01-landing-page.md:7-10`): mở `<target_url>/` → kiểm tiêu đề/hero nhắc `TesterArmy` → kiểm nút CTA chính như `Get Started` hoặc `Sign in` hiển thị → trả `pass` nếu mọi bước đạt.
- **`examples/tests/02-auth-smoke.md:1-11` (`11` dòng) — Khói đăng nhập**:
  - `Goal:` 1 dòng xác minh route sign-in và vào app shell (`02-auth-smoke.md:3`).
  - `Steps:` 5 bước đánh số (`02-auth-smoke.md:7-11`): tới `/sign-in` → hoàn tất luồng đăng nhập hợp lệ → kiểm redirect về `/dashboard` (hoặc tương đương) → kiểm user menu/avatar hiển thị → chốt *"Return failed with exact first broken step if any check fails"*.
- **`examples/tests/03-project-create.md:1-12` (`12` dòng) — Luồng nghiệp vụ CRUD**:
  - `Goal:` 1 dòng tạo project mới từ dashboard (`03-project-create.md:3`).
  - `Steps:` 6 bước đánh số (`03-project-create.md:7-12`): mở `/projects` → bấm đúng nhãn nút nhìn thấy (`New Project`) → điền giá trị test duy nhất (*unique test values*) → submit form → kiểm dự án xuất hiện trong danh sách và trang chi tiết mở được → trả `pass/fail` kèm lý do cụ thể.
- **`examples/prompts/ad-hoc-regression.md:1-7` (`7` dòng) — Prompt tái kiểm nhanh**:
  - 4 yêu cầu đánh số (`ad-hoc-regression.md:4-7`): chạy lại happy path E2E cho luồng vừa đổi → xác thực key CTA và key success state → nếu gãy phải ghi lại **exact step + visible error text** → trả verdict `PASS`/`FAILED` nghiêm ngặt với lập luận ngắn.

### 2.2. Vì sao dev đọc hiểu ngay được trong 10 giây?
Kết hợp 5 file mẫu trên với quy chuẩn biên soạn trong `SKILL.md:134-189`, có 6 cơ chế thiết kế trực tiếp tạo tốc độ đọc 10 giây:
1. **Đóng khung 1 Goal + 3–10 bước trên 1 hành trình (`SKILL.md:181-182`)**: Mỗi file đại diện đúng một user journey, đọc lướt từ dòng `Goal:` xuống bước `1..N` mất dưới nửa màn hình (tối đa `50` bước ở tầng engine, `SKILL.md:189`).
2. **Cấm rào cản kỹ thuật DOM/CSS/Timing (`SKILL.md:153,165`)**: Bảng `Avoid | Write` (`SKILL.md:163-168`) cấm viết `.nav-item:nth-child(3)` hay `wait 500ms`; thay bằng nhãn UI người thật nhìn thấy (`Pricing`, `New Project`, `Invite teammate`, `Get Started`, `Sign in`, `SKILL.md:156`, `01-landing-page.md:9`, `03-project-create.md:8`). Dev không phải mở mã frontend mới hiểu test đang bấm chỗ nào.
3. **Tách đôi Hành động và Khẳng định (`SKILL.md:154-155,167,183-184`)**: Mỗi bước làm đúng một việc có điểm dừng rõ (`"Add the Pro plan to the cart."` rồi mới tới `"Verify the cart shows the Pro plan with the correct monthly price."`). Cấm nhét ngầm login, upload hay assertion vào một câu gộp (`SKILL.md:188`).
4. **Chuẩn hóa 5 kiểu bước tường minh trong JSON thực thi (`SKILL.md:139-146`)**: `act` (thao tác), `assert` (trạng thái/URL/email nhìn thấy), `login` (gắn `credentialId` hoặc `temporaryEmail: true`, cấm nhét mật khẩu vào tiêu đề bước `SKILL.md:185`), `files` (tải file mẫu lên tới 50 MB `SKILL.md:76`), và `screenshot` (chỉ đặt tại điểm kiểm thị giác quan trọng `SKILL.md:187`).
5. **Chống assertion mơ hồ kiểu "looks good" (`SKILL.md:158,168`)**: Mọi kiểm tra phải nêu vật chứng cụ thể có thể phán quyết đúng/sai dứt khoát (ví dụ: *"shows a Projects card, a Recent Runs card, and no visible error banner"*).
6. **Tách lớp người đọc vs lớp máy chạy (`examples/README.md:3-5,26`)**: Tệp `.md` dùng để người và agent đọc nhanh và review ý định; khi đăng ký vào dashboard mới chuyển thành JSON đưa vào `ta tests create` (`SKILL.md:123,129`).

---

## 3. Cấu trúc báo lỗi & vòng tái hiện cho dev

### 3.1. Khuôn báo cáo sau kiểm thử (`reporting-template.md` & `SKILL.md:378-388`)
Mọi báo cáo kết thúc tác vụ bắt buộc tuân theo khuôn 6–7 dòng tại `skills/testerarmy-cli/references/reporting-template.md:5-26`:
- Ghi rõ `Project: <Name> (<projectId>)`, test vừa `Created`/`Updated` (`<title> (<testId>)`), `Group`, câu lệnh xác thực thực tế (`ta tests run ... --wait --json`), `Result` (`PASS` hoặc `FAILED`), `Run: <runId>`, và nếu lỗi thì thêm dòng `Failure: "<thông báo/triệu chứng cụ thể>"` (`reporting-template.md:17-26`).
- **Chốt chặn chống báo cáo ảo**:
  1. Cấm tuyên bố có coverage bền vững nếu chưa chạy `ta tests create` hoặc `ta tests update` (`SKILL.md:388`).
  2. Không có `--wait`, mã thoát `0` chỉ chứng nhận *đã xếp hàng đợi chạy trên cloud*, không chứng nhận app pass (`README.md:75-76`, `SKILL.md:259-260`).

### 3.2. Chuỗi truy vết 4 tầng & xuất artifact CI (`SKILL.md:295-332,344-355`)
Khi `--wait` trả kết quả không phải pass (exit code `1` cho cả `FAILED`, `blocked`, lẫn `cancelled` — agent/dev phải đọc JSON verdict để phân biệt, `SKILL.md:329-332`), dev tái hiện lỗi theo đúng 4 bước từ thô đến chi tiết (`SKILL.md:295-308`):
1. **`ta runs get <runId> --json`** (`SKILL.md:297,305`): lấy verdict cuối, trạng thái run và metadata môi trường.
2. **`ta runs messages <runId> --json`** (`SKILL.md:299,305-306`): đọc full transcript từng bước agent đã thực thi và điểm vấp đầu tiên.
3. **`ta runs telemetry <runId> --json`** (`SKILL.md:300,306`, `plugin.json:28`): trích xuất log console trình duyệt và lỗi network request.
4. **`ta runs recording <runId> --output ./recordings/`** (`SKILL.md:302,307-308`): tải video MP4 quay màn hình phiên lỗi (hoặc lấy link MP4 ngắn hạn nếu không truyền `--output`).

Ngoài ra, hệ thống hỗ trợ:
- Lưu JSON kết quả cục bộ bằng `> result.json` (`SKILL.md:290`, `examples/README.md:48`).
- Xuất **JUnit XML** cho CI (`ta runs junit <runId> --output report.xml`, `ta batches junit <batchId> --output report.xml`), mặc định fail nếu run/batch chưa xong trừ phi truyền `--allow-incomplete` (`SKILL.md:318-324`).
- **Triage & khử trùng lặp issue tự động** (`SKILL.md:344-355`): các bug từ `ta discover` tự gom vào `ta issues`, được **deduplicate qua nhiều lần chạy**, gắn theo từng environment (`staging`, v.v.) với 3 trạng thái `open`, `resolved`, `false_positive`; `ta issues get <issueId>` trả ngược danh sách `runId` đã làm bộc lộ lỗi để dev xem lại recording/messages và chuyển bug tái diễn thành saved regression test.

### 3.3. Quy trình Bug Board & Issue Templates (`.github/ISSUE_TEMPLATE/` & `docs/BUG_BOARD.md`)
- `docs/BUG_BOARD.md:7-31` chuẩn hóa 3 loại issue (`bug`, `regression`, `feature`) và 5 trạng thái triage (`needs-info` → `confirmed` → `in-progress` → `blocked` → `shipped`).
- `.github/ISSUE_TEMPLATE/bug_report.yml:10-61` khóa 7 trường bắt buộc: lệnh chạy chính xác (`ta ...`), URL/môi trường đích, kết quả (`FAILED` / `PASS (unexpected)` / `CLI/runtime error`), `Exit code`, `Run ID` hoặc file `result.json`, `Expected behavior`, `Actual behavior`.
- `.github/ISSUE_TEMPLATE/regression_report.yml:14-41` bổ sung hai trường khoanh vùng nguyên nhân hồi quy: `Last known good version/date` và `What changed`.
- **Phát hiện độ lệch tài liệu thực tế**: `docs/BUG_BOARD.md:20,35-40` vẫn giữ ví dụ lệnh cũ (`ta run tests/ --parallel 3 --debug`, `ta ls`, `.testerarmy/<timestamp>/`, `TESTERARMY_TARGET_URL`), trong khi `SKILL.md` và `bug_report.yml:15,45-47` đã chuyển sang mô hình cloud `ta tests run <testId> --env ... --wait --json` và `<runId>`/`result.json`. Đây là bằng chứng rõ cho thấy nếu thiếu linter kiểm khớp tài liệu, hướng dẫn tái hiện rất dễ bị lỗi thời cục bộ.

---

## 4. Điểm mạnh đáng học vào TDQ-Workflow vs điểm yếu/giới hạn

| Khía cạnh | Điểm mạnh của `terterarmy-cli` đáng học cho TDQ | Điểm yếu / giới hạn của `terterarmy-cli` (so với năng lực hiện có của TDQ) |
|---|---|---|
| **Cách viết kịch bản E2E** | Kịch bản 7–19 dòng plain-language (`01-landing-page.md`–`03-project-create.md`), cấm CSS selector/wait cứng, tách `act` vs `assert` (`SKILL.md:152-188`). Đọc 10 giây là hiểu ý định người dùng. | Không có cấu trúc Tier rủi ro (Happy Path / Boundary / Failure & Recovery) và rule chống test giả (`ANTI-1`..`ANTI-6`) như `skills/tdq-build/references/vision-test-loop.md:38-62`. |
| **Bằng chứng tái hiện lỗi** | Chuỗi debug chuẩn hóa 4 lớp (`runs get` → `messages` → `telemetry` → `recording` MP4) + `junit` XML (`SKILL.md:295-324`) + khuôn báo cáo cố định kèm `runId` (`reporting-template.md:5-26`). | Không có **Pixel-diff Vision Loop** so sánh pixel-by-pixel với thiết kế gốc kèm bounding box `[1],[2]` và bảng ánh xạ CSS như `tdq_vision_diff.py` (`vision-test-loop.md:78-126`). |
| **Kỷ luật xác thực & chống báo ảo** | Phân tách rạch ròi "đã queue" vs "đã pass" (`--wait`), cấm nhận coverage khi chưa tạo/cập nhật test (`SKILL.md:259-260,388`), bắt buộc nêu `Last known good` & `What changed` khi báo regression (`regression_report.yml:14-41`). | Mọi chạy đều là black-box trên cloud: không có cổng `120s` timeout tự cắt treo tiến trình cục bộ (`qc.md:125-141`), không có vòng tự sửa code giới hạn `<= 3` lượt `QCn.x` gắn vào plan (`qc-vong-fix.md:5-8`), không kiểm ràng buộc kiến trúc/clean code (`QC-F3`, `QC-F4` ở `qc.md:103-108`). |
| **Môi trường & độ tin cậy thực thi** | Hỗ trợ chạy cả web lẫn mobile (`.app`/`.apk`, `SKILL.md:357-376`), lập lịch chạy định kỳ (`--frequency`/`--cron`, `SKILL.md:242-255`), và khám phá lỗi không kịch bản (`ta discover` + khử trùng lặp `issues`, `SKILL.md:326-355`). | **Phụ thuộc cloud `tester.army`**: bắt buộc mạng internet, API key (`ta auth`/`TESTERARMY_API_KEY`) hoặc OAuth (`README.md:51-59,90`), và môi trường dev phải mở preview/tunnel URL reachable từ cloud (`README.md:76-78`, `SKILL.md:16,270`) — khó chạy với app nội bộ/offline/air-gapped. |
| **Kiểm định mã nguồn & hiệu năng** | CI tự động kiểm khớp 9 manifest plugin + schema (`check-plugin-manifests.sh:1-47`, `validate-plugin.yml:1-37`). | **Không thay thế được kiểm định code offline của TDQ**: repo không có runner unit test cục bộ, không chọn vùng chạm AST (`ban_kinh` / `vung-cham` ở `scripts/tdq_test.py:1-59`), và hoàn toàn không kiểm được **Golden Parity 1-1** offline giữa Python ↔ Rust hooks (`22 AGY gates x 6 events` ở `tests/test_rust_dispatch_parity.py:1-48`). |

---

## 5. Bảng ánh xạ cụ thể vào hệ thống TDQ-Workflow

Bảng dưới đây phân tách rạch ròi pattern nào nên **chuyển thẳng vào nội bộ TDQ** (chạy local/offline qua Chrome DevTools MCP, `tdq_test.py`, `tdq-qc-tester`) và pattern nào chỉ nên giữ ở mức **tùy chọn tích hợp ngoài** (khi user có tài khoản TesterArmy hoặc cần cloud/mobile):

| # | Pattern từ `terterarmy-cli` (`path:line`) | Đích ánh xạ trong TDQ | Phân loại tích hợp | Thiết kế cụ thể & điều kiện áp dụng |
|---|---|---|---|---|
| 1 | Kịch bản E2E plain-language 10 giây, tách `act` vs `assert`, cấm selector dễ vỡ (`01-landing-page.md`–`03-project-create.md`, `SKILL.md:152-188`) | `plugins/tdq-workflow-agy/skills/tdq-browser-test/SKILL.md` + `vision-test-loop.md` | **Chuyển nội bộ TDQ** | Thêm chuẩn viết `E2E Journey Card` (1 `Goal:` + 3–10 bước `act`/`assert` theo nhãn UI nhìn thấy, kèm `Given-When-Then` cho Tier 1–3) vào phần khai báo kịch bản của `tdq-browser-test` và `plan`. |
| 2 | Tệp quy ước chung `TESTER.md` + tách `memories` app context (`examples/TESTER.md:1-19`, `SKILL.md:98-106`) | `docs/tdq/` hoặc mẫu cấu hình bối cảnh E2E dự án | **Chuyển nội bộ TDQ** | Hỗ trợ 1 file bối cảnh E2E dùng chung của repo (URL đích cục bộ, flow auth tái sử dụng, vùng nhiễu bỏ qua), tránh lặp lại bước đăng nhập ở từng kịch bản QC. |
| 3 | Chuỗi bằng chứng 4 tầng (`run` → `messages` → `telemetry` → `recording`/screenshot) + xuất JSON/JUnit (`SKILL.md:290-324`) | `tdq-browser-test/SKILL.md:51-75` + `scripts/tdq_test.py` + `docs/tdq/qc/<slug>.md` | **Chuyển nội bộ TDQ** | Đóng gói mọi phiên `tdq-browser-test` thành 1 thư mục/JSON run bundle cục bộ: step transcript (đã click/fill gì) + console/network errors + ảnh desktop/mobile + tùy chọn xuất JUnit XML offline từ `tdq_test.py report`. |
| 4 | Khuôn báo lỗi ngắn kèm lệnh tái hiện chính xác & `Last known good` / `What changed` (`reporting-template.md:5-26`, `regression_report.yml:14-41`) | `agents/tdq-qc-tester.md:20-31` & `skills/tdq-build/references/qc-vong-fix.md:9-19` | **Chuyển nội bộ TDQ** | Bổ sung vào bảng `DEFECTS:` của `tdq-qc-tester` trường `first broken step`, `visible error text`, và `last known good / changed diff` để `QCn.x` sửa đúng 1 chạm. |
| 5 | Chế độ khám phá tự do (`ta discover`) + khử trùng lặp issue qua nhiều run (`SKILL.md:326-355`) | `tdq-browser-test` (chế độ exploratory ở `muc_qc=ultra`) | **Chuyển nội bộ TDQ** (một phần) | Thêm pass "Exploratory Smoke" tùy chọn dùng Chrome DevTools MCP dò link chết / console error ngoài kịch bản cố định, ghi nhận vào debt/issue ledger thay vì lẫn vào DoD bắt buộc. |
| 6 | Check đồng bộ đa manifest + doc-lint tránh lệch cú pháp (`scripts/check-plugin-manifests.sh:1-47`, phát hiện lỗi lệch `BUG_BOARD.md`) | `scripts/doc_lint.py` / CI nội bộ repo TDQ | **Chuyển nội bộ TDQ** | Kiểm tự động tham chiếu lệnh CLI trong `docs/` & `skills/` để không phát sinh doc lỗi thời như `BUG_BOARD.md:38`. |
| 7 | Chạy trình duyệt/mobile trên cloud (`ta tests run`, `ta upload-app` iOS/Android, `ta groups schedule-set`) & Hosted MCP OAuth (`SKILL.md:242-285,357-376`, `README.md:88-90`) | Adapter / Hook hoặc skill tích hợp ngoài (opt-in) | **Tùy chọn tích hợp ngoài** | Chỉ kích hoạt khi dự án cần **test mobile `.app`/`.apk` trên simulator/device cloud**, cần **lịch chạy cron cloud**, hoặc đã có sẵn **staging/preview URL + API key/OAuth `tester.army`**; tuyệt đối không dùng thay thế Chrome DevTools MCP local hay test offline của TDQ. |
