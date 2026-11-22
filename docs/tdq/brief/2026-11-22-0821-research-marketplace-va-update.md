# BRIEF — Nghiên cứu custom marketplace GitHub, sẵn sàng Git và cơ chế auto-update của Antigravity
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

Ngày: 2026-11-22 · Mã yêu cầu: 2026-11-22-0821-research-marketplace-va-update · Lane: full · Work kind: investigate · Nhánh đích: docs/research-marketplace-va-update (tách từ dev)

## Nguyên văn

> Chưa. Tôi muốn mở request resreach phân tích và báo cáo xem antigravity có hỗ trợ market place custom từ github không và project này đã đc setup để có thể đưa lên git và khi vậy nếu plugin trỏ về git remote thì có auto check và update khi có version mới không

### Đọc hiểu bước đầu

- **Mục tiêu:** Nghiên cứu và lập báo cáo kiểm chứng ba câu hỏi cốt lõi: (1) Google Antigravity (`agy`) có hỗ trợ khai báo custom marketplace trỏ tới GitHub repo hay không và theo cơ chế/định dạng nào; (2) kho mã nguồn hiện tại đã được cấu hình đầy đủ để đẩy lên Git remote làm marketplace/plugin repo chưa hay còn điểm thiếu cần bổ sung; (3) khi plugin cài đặt trỏ về Git remote, Antigravity có tự động kiểm tra phiên bản mới và auto-update hay cần thao tác thủ công/hook riêng.
- **Phạm vi dự kiến:** Nghiên cứu tài liệu chính thức, built-in skills, tệp cấu hình và hành vi thực tế của Antigravity (`agy` CLI / plugin manager) kết hợp rà soát cấu hình đóng gói và marketplace nội bộ (`.agents/`, `.claude-plugin/`, `plugins/tdq-workflow-agy/`, `tools/build_agy_plugin.py`, `scripts/build_portable.py`, remote và mô hình nhánh `dev`/`main`). Yêu cầu dừng ở phân tích và báo cáo (`work_kind=investigate`), không tự ý sửa mã nguồn hoặc đẩy lên remote.
- **Điểm cần làm rõ ở pha phân tích:** Xác định mức độ sâu thực nghiệm trên `agy` CLI/cấu hình cục bộ và xác nhận xem bạn muốn dừng thuần túy ở báo cáo khuyến nghị hay muốn kèm danh sách đề xuất chỉnh sửa sẵn sàng tách thành request kế tiếp nếu phát hiện cấu hình còn thiếu.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-22: 42 skill trên đĩa (23 giữ lại sau lọc, 19 ẩn khác lĩnh vực), cộng các skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| tdq-intake, tdq-spec, tdq-plan, tdq-build, tdq-conventions, tdq-setup, tdq-status, tdq-check-status, tdq-lean, tdq-checkportable | plugin:tdq-workflow / plugin:tdq-workflow-agy | NỀN | Luồng TDQ Workflow đang chạy (`investigate`) |
| antigravity-guide | built-in | DÙNG | Nguồn sitemap chính thức (`antigravity.google/docs/plugins.md`, `cli/reference.md`, `changelog.md`) để đối chiếu custom marketplace & auto-update |
| plugin | built-in | DÙNG | Tham chiếu quy trình cài/gỡ/liệt kê plugin, catalog ID và RPC `GetAllPlugins` của Antigravity |
| agy-customizations | built-in | DÙNG | Đối chiếu discovery roots (`.agents/`, `~/.gemini/config/`) và thứ tự ưu tiên nạp plugin/skill |
| tdq-browser-research | plugin:tdq-workflow / plugin:tdq-workflow-agy | KHÔNG | `spec §3 đã chọn cách khác tốt hơn` (dùng mirror `.md` chính thức của Antigravity, `search_web`/`tavily` và `agy` CLI) |
| Đã xét 30 skill khác | user/plugin/built-in | KHÔNG | `khác lĩnh vực` |

### Điểm vào hiện trạng và giả thuyết kiểm chứng (`investigate` mức nông)

Đã đọc đầy đủ hồ sơ kiến trúc (`docs/kien-truc.md`) và kiểm tra 6/8 bậc công cụ tìm kiếm (`tdq_lsp.py check` đạt `3/3` tầng trả lời được). Thống kê bước đầu ở mức nông theo `investigate-mode.md` (giữ đọc sâu & đối chứng cho pha `implement`):

- **CLI & môi trường Antigravity (`agy` v`1.4.12`):** `agy plugin --help` liệt kê 8 lệnh (`list`, `import`, `install`, `uninstall`, `enable`, `disable`, `validate`, `link`, `help`), chưa thấy lệnh `update` hay `marketplace`; `agy plugin install --help` báo `install target must be a directory: --help`; `agy plugin list --json` cho thấy các plugin chính thức mang `"source": "antigravity-plugins-official"`, còn `tdq-workflow-agy` (`0.103.1`) không có khóa `"source"`.
- **Cấu hình Git & adapter đóng gói hiện tại trong repo:** Có 3 remote (`origin` → `TDQUOC/TDQ-Workflow-Antigravity.git`, `upstream` → `TDQUOC/TDQ-Workflow.git`, `local-upstream`); `dev` đang đi trước `origin/dev` 25 commit và `main` đang ở `91db3046` (`v0.103.1`, đi trước `origin/main` 62 commit nhưng cũ hơn bản build `0.105.0` tại `plugins/tdq-workflow-agy/`). Adapter gồm `.agents/plugins.json` (`./plugins`), `.agents/plugins/marketplace.json` (`tdq-local`, plugin `tdq-workflow`, `"url": "./"`), `.claude-plugin/marketplace.json` (mô tả còn trỏ `TDQUOC/TDQ-Workflow`), `plugins/tdq-workflow-agy/` (`plugin.json`, `manifest.json`, `bin/tdq-dispatch.exe`), `tools/build_agy_plugin.py`, `scripts/build_portable.py`.

| Vùng file / bề mặt khảo sát | Phát hiện qua lớp nào | Vai trò cần đào sâu ở `implement` |
|---|---|---|
| `antigravity.google/docs/{plugins,cli/reference,changelog}.md` & `C:\Users\admin\.gemini\...` | Built-in `antigravity-guide`, `plugin`, `agy-customizations` | Xác minh chuẩn hỗ trợ custom GitHub marketplace, `agy plugin install/link`, cơ chế check/update version từ remote |
| `.agents/plugins.json`, `.agents/plugins/marketplace.json`, `.claude-plugin/{marketplace,plugin}.json` | File system & `read_file` nông | Kiểm tra tính tương thích cấu trúc marketplace cho `TDQUOC/TDQ-Workflow-Antigravity` vs tên plugin `tdq-workflow-agy` |
| `plugins/tdq-workflow-agy/`, `tools/{build_agy_plugin,install_agy_plugin}.py`, `scripts/build_portable.py` | File system & `read_file` nông | Đối chiếu gói phát hành `dev`/`main`, nhị phân đa nền tảng và tính sẵn sàng đẩy Git remote |

**Ba giả thuyết kiểm chứng ở pha `implement`:**
- **H1 (Custom GitHub Marketplace trong Antigravity):** Antigravity có thể chỉ hỗ trợ chính thức Official/Partner Marketplace catalog + cài từ thư mục/local path hoặc workspace `.agents/plugins/` (thông qua `agy plugin install <dir>` / `import`), hoặc có cơ chế đăng ký repo Git riêng qua `link`/cấu hình ẩn — cần kiểm chứng cả live docs lẫn `agy` CLI/runtime.
- **H2 (Mức độ sẵn sàng Git & marketplace của repo này):** Repo đã có nền đóng gói plugin sạch (`tdq-workflow-agy` pass strict validate) và mô hình 2 nhánh `dev`/`main`, nhưng tệp marketplace nội bộ (`.agents/plugins/marketplace.json`, `.claude-plugin/marketplace.json`) còn lệch tên plugin (`tdq-workflow` vs `tdq-workflow-agy`), trỏ URL tương đối `"./"` / repo cũ `TDQUOC/TDQ-Workflow`, đồng thời `origin/dev` và `main` chưa đồng bộ `0.105.0`.
- **H3 (Cơ chế auto-check & auto-update khi trỏ Git remote):** Nhiều khả năng Antigravity KHÔNG tự động `git pull` / auto-update plugin trỏ GitHub ngoài catalog chính thức (không có subcommand `update` ở CLI `1.4.12` và bản global cài tay không lưu `source` remote), đòi hỏi người dùng tự chạy installer/CLI cập nhật hoặc cơ chế kiểm tra ngoài nếu cần nhắc phiên bản mới.

Vòng scope: BỎ — yêu cầu nghiên cứu chỉ đọc/báo cáo (`work_kind=investigate`), các lựa chọn về phạm vi đầu ra, mô hình phân phối Git mục tiêu và giới hạn thực nghiệm được gộp trực tiếp vào vòng phỏng vấn bên dưới.

### Kiến thức & quyết định đã chốt

- **Đầu ra (`1a`):** Báo cáo đánh giá hiện trạng có dẫn chứng rõ ràng kèm danh sách điểm thiếu/lệch và phương án đề xuất khắc phục cho request tiếp theo; tuyệt đối không sửa mã nguồn sản phẩm trong request này (`work_kind=investigate`).
- **Mục tiêu phát hành (`2b`):** Phân phối công khai cho cộng đồng Antigravity trên GitHub — đánh giá đồng thời khả năng tham gia danh mục công khai (official/partner marketplace vs custom GitHub repo), tương thích đa nền tảng (`Windows`, `macOS`, `Linux`, đặc biệt binary `tdq-dispatch`), và mô hình đồng bộ 2 nhánh `dev`/`main` của `TDQUOC/TDQ-Workflow-Antigravity`.
- **Ranh giới thực nghiệm (`3a`):** Cho phép đọc tài liệu chính thức (`antigravity.google/docs/*.md`, changelog, built-in skills), truy vấn web có kiểm chứng, chạy lệnh read-only và thử nghiệm `agy plugin` trong thư mục tạm cách ly; cấm tuyệt đối thay đổi `~/.gemini/` hoặc đẩy mã lên remote.
- **Mức QC (`4a`):** `muc_qc = full` — áp dụng bộ kiểm chứng bằng chứng cho điều tra (`QC-I1..I4` theo `investigate-mode.md`), không sửa file ngoài `docs/tdq/` và `docs/workinglog/`, kiểm tra `doc_lint` và `Archify HTML` + Tailscale HTTPS `200`.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Phân tích nông & phỏng vấn (`analyze`) | CÓ | Đã hoàn tất 1 vòng phỏng vấn (`1a 2b 3a 4a 5a`), chốt `muc_qc=full` và 3 giả thuyết `H1`–`H3` |
| Đặc tả (`spec` — `investigate`) | CÓ | Khóa phạm vi câu hỏi, đầu ra báo cáo, tiêu chí kiểm chứng `QC-I1..I4` (miễn `§2b` và Archify preview theo `investigate-mode.md`) |
| Lập kế hoạch (`plan`) | CÓ | Chia 3 trục khảo sát độc lập (Antigravity docs/CLI, kiểm toán cấu hình repo/multi-OS, tổng hợp khuyến nghị) và hợp đồng 5 trường cho 3 skill `DÙNG` |
| Thực thi nghiên cứu (`implement`) | CÓ | Chạy nghiên cứu sâu đa nguồn, thực nghiệm cách ly `agy`, ghi sổ bằng chứng `evidence.jsonl` và soạn báo cáo nháp |
| Kiểm chứng bằng chứng (`qc` — `full`) | CÓ | Chạy đủ `QC-I1`–`QC-I4` (đối chiếu trích dẫn đĩa/URL, phản biện counterfactual, gắn nhãn độ tin cậy `Verified`/`Single-source`/`Inferred`/`Unverified`) |
| Báo cáo cuối (`report` + `Archify HTML`) | CÓ | Chốt báo cáo Markdown 4 phần, render và verify `Archify HTML` một lần kèm đường dẫn Tailscale HTTPS `200`, hỏi commit/merge về `dev` |

## Hỏi đáp

### Vòng 1 — Đã chốt (`1a 2b 3a 4a 5a`)

1. **Mức độ đầu ra báo cáo:** Chọn `A` — Đánh giá hiện trạng kèm phương án đề xuất (không sửa code trong request này).
2. **Đối tượng phân phối GitHub mục tiêu:** Chọn `B` — Phát hành rộng ra cộng đồng Antigravity (đánh giá thêm điều kiện danh mục công khai và tương thích đa hệ điều hành Windows/macOS/Linux).
3. **Mức độ thực nghiệm `agy` CLI:** Chọn `A` — Đọc tài liệu chính thức, chạy lệnh read-only và thử nghiệm cách ly ở thư mục tạm, tuyệt đối không chạm `~/.gemini/`.
4. **Mức QC (`muc_qc`):** Chọn `A` — `full` (đã ghi `muc_qc=full` vào state).
5. **Bổ sung thêm:** Chọn `A` — Không, đủ rồi, làm tiếp đi.
