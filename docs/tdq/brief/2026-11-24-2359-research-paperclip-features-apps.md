# BRIEF — Phân tích, nghiên cứu chức năng và ứng dụng của Paperclip

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay tôi muốn mở request phân tích và resreach chi tiết các chức năng và những gì có thể ứng dụng của paperclip và làm report cho tôi, cần report đầy đủ thonng tin và dễ hiểu

**Đọc hiểu ban đầu (`work_kind=investigate`):**
- **Mục tiêu:** Khảo sát và nghiên cứu chi tiết kho mã nguồn `C:/Users/admin/Documents/paperclip` (`github.com/paperclipai/paperclip`) để bóc tách kiến trúc, toàn bộ nhóm chức năng cốt lõi và đề xuất các hướng ứng dụng thực tế. Tổng hợp thành báo cáo đầy đủ thông tin, trực quan và dễ hiểu.
- **Phạm vi:** Nghiên cứu chỉ đọc kho `paperclip` và xuất tài liệu báo cáo (`docs/tdq/reports/` kèm Archify HTML) trong workspace hiện tại. Không chỉnh sửa mã nguồn của `paperclip` hay `TDQ-Workflow-Antigravity`.
- **Điểm cần làm rõ sau khi chọn pipeline:** Mục tiêu ứng dụng ưu tiên (học ý tưởng cho TDQ Workflow, dùng trực tiếp tự vận hành, hay tích hợp vào dự án riêng), chiều sâu khảo sát từng phân hệ (`server`, `ui`, `cli`, `packages`, `integrations`, `skills`) và mức độ kiểm chứng cần thiết.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-25: `42` skill trên đĩa (`23` giữ qua `--loc`, `19` ẩn), cộng skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake`, `tdq-conventions`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-status`, `tdq-setup`, `tdq-check-status`, `tdq-lean`, `tdq-checkportable` | `plugin:tdq-workflow-agy` | NỀN | Khung vận hành workflow TDQ (`full` + `investigate`) |
| Đã xét 40+ skill khác (`tdq-browser-research`, `tdq-browser-test`, Google Workspace, Gemini API, `a11y-debugging`, `generative_ui`, `plugin`…) | `user/plugin/built-in` | KHÔNG | khác lĩnh vực |

### Phạm vi đã chốt

- Mặt CHỌN: Kiến trúc & danh mục chức năng toàn hệ thống (4 trụ cột, đối chiếu code thật vs README/ROADMAP), Khả năng học hỏi & áp dụng cho TDQ Workflow, Khả năng cài đặt & sử dụng trực tiếp thực chiến, Bảo mật/phân quyền & kiểm soát chi phí (Secrets per-agent, MCP Access Governance, RBAC, audit log, khóa ngân sách).
- Mặt LOẠI: Chỉnh sửa mã nguồn của `paperclip` hoặc `TDQ-Workflow-Antigravity`; cài đặt hoặc khởi chạy server Paperclip thực tế trên máy cá nhân.
- Bối cảnh: Cả 3 hướng ứng dụng (dùng trực tiếp, học kiến trúc cho TDQ Workflow, ứng dụng cho dự án riêng); giai đoạn nghiên cứu công nghệ tham khảo chưa chốt quy mô triển khai; nguồn bằng chứng từ mã nguồn/tài liệu local `C:/Users/admin/Documents/paperclip` kết hợp đối chiếu web chính thức khi cần.
- Mức đầu tư suy ra: đầy đủ — vì người dùng chọn phủ sâu đủ cả 4 mặt (bao gồm bảo mật, phân quyền, kiểm soát chi phí và đối chiếu đa góc độ) cho cả 3 hướng ứng dụng.

### Khảo sát nông điểm vào & giả thuyết (B1)

**Hồ sơ kho mục tiêu (`C:/Users/admin/Documents/paperclip`):**
- Kho Git `https://github.com/paperclipai/paperclip` (nhánh `master`, giấy phép MIT, cập nhật local `2026-11-17`).
- Công nghệ nền: monorepo TypeScript/Node.js (`pnpm`), backend `server/src/`, frontend React/Vite `ui/src/`, CLI `cli/src/` (`paperclipai`), dữ liệu PostgreSQL nhúng (`packages/db`).
- Bốn trụ cột công bố trong `README.md` và `ROADMAP.md`: (1) Agentic Task Manager, (2) Org Chart for Agents, (3) Agent Employee Training (Skill Studio & Evals), (4) Agentic OS (BYO Agent adapters, MCP Tool Gateway, Connected Apps, Sandbox cloud, Budgets, Recovery).

**Bảng đối chiếu vùng khảo sát 3 chiều (nông trước spec — đào sâu thực hiện ở pha `implement`):**

| Vùng file khảo sát (chỉ đọc) | Phát hiện qua lớp nào | Tác động & quan hệ |
|---|---|---|
| `README.md`, `ROADMAP.md`, `package.json` (tại `C:/Users/admin/Documents/paperclip`) | Read | Xác định tầm nhìn 4 trụ cột, danh sách tính năng đã hoàn thiện vs kế hoạch, hệ thống script kiểm thử và eval |
| `packages/` (`adapters`, `adapter-utils`, `db`, `mcp-server`, `paperclip-runner`, `paperclip-eval-kernel`, `plugins`, `shared`, `skills-catalog`, `teams-catalog`, `tailscale-https-broker`) | Dir | 13 package cốt lõi tách rõ runtime điều phối, adapter agent, plugin SDK, MCP server và catalog mẫu |
| `server/src/`, `ui/src/`, `cli/src/`, `skills/`, `integrations/`, `doc/`, `docs/` | Dir | Phân hệ Control Plane, giao diện quản trị web/mobile, CLI cài đặt, 9 skill tích hợp và tài liệu đặc tả sâu |

**Giả thuyết cần kiểm chứng sâu trong pha `implement` (có thể bác bỏ):**
- **H1 (Độ hoàn thiện thật trong code so với README/ROADMAP):** Đối chiếu mã nguồn thực tế để tách rõ tính năng đã chạy hoàn chỉnh, tính năng thử nghiệm và giới hạn vận hành trên Windows/local so với Docker/cloud.
- **H2 (Cơ chế điều phối & quản trị Control Plane):** Kiểm chứng luồng heartbeat + adapter runtime, Org Chart + phân quyền/duyệt, giới hạn ngân sách, MCP Tool Gateway, Secrets per-agent và cơ chế khôi phục chạy lỗi.
- **H3 (Hệ sinh thái mở rộng & huấn luyện agent):** Kiểm chứng thiết kế Plugin SDK, Skill Studio, `companies.sh` import/export và `paperclip-eval-kernel` về khả năng mở rộng và tái sử dụng.
- **H4 (Giá trị ứng dụng thực tế):** Ánh xạ điểm mạnh cốt lõi của Paperclip sang các kịch bản dùng trực tiếp, học ý tưởng nâng cấp TDQ Workflow hoặc áp dụng cho dự án phần mềm riêng.

### Quyết định đã chốt

- **Cấu trúc báo cáo 2 tầng (`1a`):** Phần đầu trình bày tóm tắt dễ hiểu, sơ đồ trực quan và bảng tính năng/ứng dụng để nắm trọn trong vài phút. Phần sau và phụ lục giữ đủ bằng chứng kỹ thuật (`path:line`, cơ chế chi tiết).
- **Trọng tâm nhóm agent BYO (`2a`):** Kiểm tra sâu khả năng kết nối thực tế cho 6 công cụ `Antigravity`, `Claude Code`, `Codex`, `Gemini CLI`, `OpenCode` và `OpenClaw` (tách rõ adapter gốc và ghép nối custom/HTTP/CLI).
- **Khung đề xuất ứng dụng ưu tiên (`3a`):** Kèm bảng chấm điểm Giá trị / Độ khó / Rủi ro và phân 3 nhóm (nên áp dụng ngay, cân nhắc sau, không nên học theo kèm lý do) cho cả 3 hướng ứng dụng.
- **Mức kiểm định (`4a`):** Chốt `muc_qc=full` áp dụng bộ `QC-I1..I4` (100% grounding `[EV]` + `path:line`, đối chiếu nguyên văn, kiểm chứng 4 giả thuyết và gắn nhãn độ tin cậy; không chạy Red-Team `ultra`).
- **Phương án đã loại:** (1) Sửa mã nguồn của `paperclip` hoặc `TDQ-Workflow-Antigravity`; (2) Cài đặt hoặc chạy thử server Paperclip lên máy cá nhân; (3) Viết báo cáo thuần kỹ thuật khó đọc hoặc chỉ nêu tổng quan thiếu bằng chứng.

### Lộ trình

| Bước/phase | CÓ-BỎ | Vì sao |
|---|---|---|
| `analyze` (B0 + B1 nông + phỏng vấn 2 vòng) | CÓ | Khung bất biến — đã chốt đủ 4 mặt khảo sát, 3 hướng ứng dụng, nhóm 6 agent và mức `muc_qc=full` |
| `spec` (Đặc tả nghiên cứu, miễn Archify preview) | CÓ | Khung bất biến — chốt mục tiêu, 4 giả thuyết `H1`–`H4`, đầu ra và cổng kiểm `Q1`–`Q5`; miễn preview trước duyệt theo `investigate-mode.md:13` |
| `plan` (Kế hoạch 4 shard điều tra độc lập) | CÓ | Khung bất biến — chia 4 shard đọc-chỉ (`S1`–`S4`) với `Worktree: none` và ngân sách tool rõ ràng |
| `implement` (Khảo sát sâu code local + đối chiếu web + viết báo cáo) | CÓ | Khung bất biến — đào sâu `C:/Users/admin/Documents/paperclip`, đối chiếu web chính thức khi cần, hợp nhất `evidence.jsonl` và soạn báo cáo 2 tầng |
| `qc` (`QC-I1..I4` mức `full`) | CÓ | Theo lựa chọn `4a` (`muc_qc=full`) — kiểm grounding `100%` `[EV]` và `path:line`, bác bỏ giả thuyết, nhãn độ tin cậy và `0` file code sửa |
| `qc` Red-Team độc lập (`ultra`) | BỎ | Người dùng chọn `full` (`4a`), không chọn `ultra` (`4c`) |
| `report` (Hoàn thiện MD + Archify HTML + Tailscale verify) | CÓ | Khung bất biến — xuất cặp báo cáo trực quan và hỏi commit/merge |

## Hỏi đáp

- **Chọn pipeline (2026-11-25 00:01):** Hỏi `1. Bạn muốn chạy pipeline nào?` (`A` chuyên sâu `deep` / `B` nhanh `express`, loại `docs`) → Người dùng trả lời nguyên văn: `"1a"` (`full`, `work_kind=investigate`, mở nhánh `docs/research-paperclip-features-apps` từ `dev`).
- **Vòng 1 — Phạm vi & Bối cảnh (2026-11-25 00:06):**
  - Câu hỏi: (1) Mặt phân tích sâu (`A` kiến trúc & 4 trụ cột, `B` đối chiếu TDQ Workflow, `C` cài đặt & dùng thực chiến, `D` bảo mật/phân quyền/ngân sách, `E` chỉ tổng quan); (2) Hướng ứng dụng ưu tiên (`A` cả 3 hướng, `B` chỉ TDQ, `C` chỉ dùng trực tiếp, `D` tự nhập); (3) Quy mô áp dụng (`A` 1–5 người, `B` 5–20 người, `C` nghiên cứu tham khảo chưa chốt quy mô, `D` tự nhập); (4) Mức bằng chứng (`A` code local + web chính thức không cài server, `B` chỉ offline local, `C` chạy thử trên máy, `D` khác); (5) Bổ sung (`A` không / `B` có).
  - Người dùng trả lời nguyên văn: `"1abcd; 2a ;3c; 4a; 5a"`.
- **Vòng 2 — Chi tiết & Mức QC (2026-11-25 00:12):**
  - Câu hỏi: (1) Cấu trúc báo cáo (`A` 2 tầng dễ hiểu + phụ lục `path:line`, `B` thuần kỹ thuật, `C` thuần sản phẩm); (2) Nhóm BYO Agent (`A` soi kỹ 6 agent đang dùng, `B` quét đều toàn bộ, `C` chỉ cơ chế chung); (3) Định dạng đề xuất ứng dụng (`A` bảng chấm điểm ưu tiên + 3 nhóm, `B` liệt kê không chấm điểm); (4) Mức QC (`A` `full`, `B` `lite`, `C` `ultra`); (5) Bổ sung (`A` không / `B` có).
  - Người dùng trả lời nguyên văn: `"1a 2a 3a 4a 5a"` (chọn `A` cho cả 5 câu, chốt `muc_qc=full`).
