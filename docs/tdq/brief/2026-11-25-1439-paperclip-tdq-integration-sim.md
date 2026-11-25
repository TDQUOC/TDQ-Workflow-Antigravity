# BRIEF — Nghiên cứu tích hợp cơ chế Paperclip vào TDQ-Workflow kèm simulate test
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay commit và mở request resreach , check, phan tích, tổng hợp và có thể simulate test và cho tôi biết liệu có thể tích hợp vào tdq-workflow để việc quản trị và điều hành phase, task ổn hơn và có thể xử lí tốt nhiều lĩnh vực hơn không? và nếu đc thì phân tích và simulate test và cho tôi đề xuất tối ưu để tích hợp nó vào tdq-workflow để hoàn thiện hơn, cần đảm bảo và check kĩ, có chứng cứ và căn cứ rõ, không đoán không bịa

- **Mục tiêu ban đầu:** Kiểm tra tính khả thi, phân tích sâu, tổng hợp và chạy `simulate test` thực nghiệm để đánh giá xem các cơ chế quản trị/điều hành của Paperclip (nhận việc/phân việc, điều hành phase/task, vai trò/kỹ năng đa lĩnh vực, khóa chi phí/circuit breaker/interaction) có thể tích hợp vào `TDQ-Workflow` để điều hành `phase`/`task` ổn định hơn và xử lý tốt nhiều lĩnh vực hơn hay không; nếu khả thi, đề xuất phương án tích hợp tối ưu có chứng cứ mã nguồn và kết quả `simulate test` rõ ràng.
- **Phạm vi dự kiến:** Đối chiếu hai codebase thật (`C:/Users/admin/Documents/paperclip` và `TDQ-Workflow-Antigravity`), thiết kế kịch bản và chạy `simulate test` cục bộ trên sandbox/tệp tạm an toàn (không đoán mò, không tự sửa code sản phẩm TDQ trước khi được duyệt phương án).
- **Điểm cần làm rõ qua phỏng vấn:** Mức độ ưu tiên giữa 2 mục tiêu (ổn định điều hành `phase`/`task` so với mở rộng đa lĩnh vực phi-code), phạm vi hạ tầng cho phép tích hợp vào TDQ (giữ thuần Git + JSON/Python nhẹ hay chấp nhận dịch vụ phụ), và phạm vi của bài `simulate test` (chạy benchmark mô phỏng trong sandbox hay chỉ kiểm thử tĩnh).

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-25: 42 skill trên đĩa (`plugin:tdq-workflow` và `plugin:tdq-workflow-agy`, qua `skill_inventory.py`), cộng các skill built-in trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-intake`, `tdq-conventions`, `tdq-spec`, `tdq-plan`, `tdq-build`, `tdq-lean`, `tdq-status`, `tdq-setup` | `plugin:tdq-workflow`, `plugin:tdq-workflow-agy` | `NỀN` | Quy trình nền điều hành phân tích, đặc tả, lập kế hoạch, kiểm chứng `QC-I1..I4` và báo cáo |
| Đã xét `40+` skill khác (`chrome-devtools`, `a11y-debugging`, `tdq-browser-*`, `gemini-api-*`, `gdocs`/`gsheets`/`gslides`/`gdrive`, `run-workflow`, `swarm_*`…) | `plugin`, `built-in` | `KHÔNG` | `khác lĩnh vực` |

*(Ghi chú năng lực subagent khi thực thi nếu cần: `tdq-explorer`, `tdq-reviewer`, `tdq-security-reviewer`, `tdq-qc-tester` sẵn sàng ở mức read-only/scoped-write; quyết định chạy `main` hay `subagent` sẽ chốt ở cổng duyệt plan.)*

### Điểm neo khảo sát sơ bộ (Shallow B1)

- **`TDQ-Workflow-Antigravity` (hệ thống đích):**
  - Điều hành phase, state & vòng đời: `scripts/tdq_state.py`, `scripts/tdq_finish.py`, `scripts/tdq_plan_scaffold.py`, `scripts/tdq_bench.py`, `scripts/tdq_timing.py`, `scripts/token_budget.py`, `scripts/tdq_eval.py`.
  - Điều phối task, team & worktree: `scripts/tdq_team.py`, `scripts/tdq_worktree_registry.py`, `scripts/tdq_vungfile.py`, `scripts/skill_router.py`, `scripts/skill_inventory.py`.
  - Cổng chặn & launcher đa HĐH: `hooks/scripts/agy_pretooluse_gate.py`, `hooks/scripts/agy_stop_gate.py`, `hooks/scripts/stop_gate.py`, `hooks/scripts/edit_gate.py`, `hooks/rust/tdq-dispatch`, `skills/`.
- **`C:/Users/admin/Documents/paperclip` (hệ thống tham chiếu, `2026-11-25`):**
  - Nhận việc, khóa nguyên tử & phân việc: `server/src/services/issues.ts` (`checkout`, `release`), `server/src/routes/issues.ts` (wakeup coalescing), `server/src/services/heartbeat/queue.ts` (4-tier dispatch order, `deferred_issue_execution`), `doc/TASKS.md`, `skills/paperclip/SKILL.md`.
  - Ổn định runtime & ngân sách: `server/src/services/recovery/automatic-run-brake.ts`, `server/src/services/budgets.ts`, `doc/MCP-ACCESS-GOVERNANCE.md`.
  - Vai trò & mở rộng đa lĩnh vực: `packages/shared/src/constants.ts` (12 `AGENT_ROLES`), `packages/teams-catalog/`, `packages/skills-catalog/`.

### Giả thuyết kiểm chứng sơ bộ (H1–H4)

- **H1 (Ổn định điều hành `phase` và `task` không cần PostgreSQL):** Các cơ chế cốt lõi của Paperclip (atomic task lock/lease, hàng đợi ưu tiên nhiều tầng kèm fairness chống bỏ đói, `blockedBy` tường minh + `issue_blockers_resolved`, và `automaticRunBrakes` circuit breaker) có thể chuyển thể gọn nhẹ sang mô hình file JSON/SQLite cục bộ + file lock NTFS của `TDQ-Workflow` để giảm kẹt wave, đụng hàng task và vòng lặp retry lỗi.
- **H2 (Mở rộng đa lĩnh vực phi-code giữ nguyên 6 trụ cột TDQ):** Tách "khung lõi phase" (`analyze -> spec/plan -> implement -> qc -> report`) khỏi "bộ luật & cổng kiểm chứng theo lĩnh vực" (`Domain Pack` + `work_kind` mở rộng học từ `teams-catalog` / `skills-catalog`) giúp TDQ xử lý bài bản cả Nghiên cứu, PM/BA, Vận hành/Nội dung mà không làm yếu kỷ luật coding của `build`.
- **H3 (Đánh đổi kiến trúc `Pattern-Native` vs `Hybrid Bridge` kiểm chứng bằng `simulate test`):** Trên Windows + Google Antigravity, phương án `Pattern-Native` (hấp thụ pattern vào Python/Hook TDQ, 0 server nền) đạt độ ổn định, chi phí vận hành và tốc độ phản hồi tốt hơn so với dựng cầu nối trực tiếp sang Paperclip server — cần chứng minh bằng kịch bản `simulate test` đo số liệu thật trong sandbox cô lập.
- **H4 (Ranh giới an toàn và những thứ KHÔNG nên tích hợp):** Cưỡng ép đưa PostgreSQL nhúng, 11 bản vá `pnpm`, `Plugin UI same-origin JS`, hoặc ghép 2 state machine song song vào TDQ sẽ gây xung đột quyền ghi state (`tdq_state.py`), đội chi phí token vì heartbeat poll và phá vỡ kiến trúc nhẹ đa nền tảng.

### Phạm vi & Ràng buộc đã chốt (Vòng 1 — Scope Round)

- **Bốn mặt bao quanh (`1abcd`):** (A) quản trị và ổn định điều hành `phase`/`task`, (B) mở rộng xử lý đa lĩnh vực phi-code, (C) bảo mật công cụ MCP, phân quyền và ngân sách token, (D) tương thích Windows/Antigravity và giữ gọn kiến trúc.
- **Hướng đánh giá (`2a`):** So sánh khách quan cả 2 hướng (`Pattern-Native` thuần Python/Git vs `Hybrid Bridge` nối Paperclip server Docker/WSL2) trên Windows và Antigravity qua số liệu `simulate test`.
- **Quy mô & simulate test (`3a`):** Quy mô 1–5 người / 5–30 task mỗi đợt; chạy bộ Python `simulate test` thật trong sandbox cô lập (`4`–`6` kịch bản sự cố và đa lĩnh vực, `0` sửa code sản phẩm TDQ).
- **Đầu ra kỳ vọng (`4a`):** Báo cáo tính khả thi kèm kết quả `simulate test` có chứng cứ và đề xuất kiến trúc tích hợp tối ưu theo lộ trình pha, chưa sửa code sản phẩm.
- **Ràng buộc bất biến (`5b`):** Bảo toàn 100% hành vi (`behavior`) và chất lượng cốt lõi của `TDQ-Workflow`; tuyệt đối không đánh đổi kỷ luật hay chất lượng để lấy thêm tính năng.
- **Mức đầu tư suy luận:** Trung bình – cao (bắt buộc kiểm chứng edge case, bảo mật và bảo toàn behavior TDQ trong DoD).

### Quyết định đã chốt (Vòng 2)

- **Nhóm lĩnh vực phi-code ưu tiên (`1a`):** Kiểm chứng `3` nhóm ngoài code sát thực tế nhất (`Nghiên cứu/Phân tích`, `PM/BA/Nội dung`, `Vận hành/Checklist tự động`) đối chiếu song song nhánh `Code Build` chuẩn của TDQ. Mục tiêu là chứng minh khung đa lĩnh vực không làm yếu kỷ luật code.
- **Điều kiện đạt bắt buộc (`2a + c`):** Áp dụng bộ lọc `4` tiêu chí cứng cho lõi mặc định (`0` hồi quy hành vi/hook TDQ, không ép DB server trên Windows, độ trễ hook/CLI thấp đo theo `ms`, chứng minh giảm sự cố qua `simulate test`). Tầng mở rộng `Hybrid Bridge` hoặc `SQLite` chỉ được đề xuất dưới dạng **add-on tùy chọn tắt mặc định** nếu số liệu mô phỏng chứng minh lợi ích vượt trội mà không ảnh hưởng người dùng TDQ chuẩn.
- **Độ sâu đề xuất tích hợp (`3a`):** Xuất lộ trình `3` pha (`P0` ổn định lõi `phase`/`task` → `P1` mở rộng đa lĩnh vực → `P2` tùy chọn nâng cao), nêu rõ file TDQ dự kiến chạm, hợp đồng dữ liệu mẫu và danh sách `CẤM` sao chép từ Paperclip.
- **Mức QC (`4c`):** **`ultra`** (`muc_qc=ultra`) — chạy đủ `QC-I1..I4`, chạy thực nghiệm lại bộ `simulate test`, kèm agent `tdq-qc-tester` độc lập soi chéo mã mô phỏng, lập luận và rủi ro hồi quy.

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| `analyze` (B0 + B1 nông + phỏng vấn 2 vòng) | CÓ | Khung bất biến — đã chốt đủ `4` mặt bao quanh, `3` lĩnh vực phi-code, bộ lọc `4` tiêu chí + add-on tùy chọn và `muc_qc=ultra` |
| `spec` (Đặc tả nghiên cứu + thiết kế simulate test) | CÓ | Khung bất biến — chốt giả thuyết `H1`–`H4`, `6` kịch bản `SIM-1..SIM-6`, `5` đầu ra và `6` cổng DoD; miễn preview trước duyệt theo `investigate-mode.md:13` |
| `plan` (Kế hoạch 4 shard + suite simulate test) | CÓ | Khung bất biến — phân rã shard khảo sát đối chiếu, mã mô phỏng Python sandbox và tổng hợp kiến trúc |
| `implement` (Khảo sát sâu 2 repo + chạy `SIM-1..SIM-6` + soạn báo cáo) | CÓ | Khung bất biến — thu bằng chứng `path:line` hai codebase, chạy thực nghiệm `SIM-1..SIM-6` (Baseline vs Proposed), xuất blueprint `P0`–`P2` và báo cáo `2` tầng |
| `qc` (`QC-I1..I4` mức `ultra`) | CÓ | Theo lựa chọn `4c` (`muc_qc=ultra`) — kiểm grounding `100%` bằng chứng, tái chạy `SIM-1..SIM-6`, xác minh `0` sửa code TDQ và giữ đủ hành vi lõi |
| `qc` Red-Team độc lập (`tdq-qc-tester`) | CÓ | Theo lựa chọn `4c` (`muc_qc=ultra`) — subagent độc lập phản biện mã mô phỏng, dữ liệu đo và rủi ro hồi quy TDQ |
| `report` (Báo cáo MD + Archify HTML + Tailscale verify) | CÓ | Khung bất biến — xuất báo cáo trực quan `current`, Tailscale HTTP `200` và mở cổng hỏi commit/merge |

## Hỏi đáp

### Vòng 1 — Định khung phạm vi (2026-11-25 15:28+07:00)

1. **Mặt chất lượng bao quanh:** Chọn `A, B, C, D` (quản trị `phase`/`task`, đa lĩnh vực phi-code, bảo mật MCP/ngân sách, tương thích Windows/Antigravity).
2. **Hướng tích hợp đánh giá:** Chọn `A` (so sánh cả 2 hướng `Pattern-Native` và `Hybrid Bridge` trên Windows + Antigravity bằng `simulate test`).
3. **Quy mô & độ sâu simulate test:** Chọn `A` (1–5 người / 5–30 task/đợt; bộ Python `simulate test` 4–6 kịch bản cô lập trong sandbox).
4. **Đầu ra cuối cùng:** Chọn `A` (báo cáo khả thi + chứng cứ `simulate test` + đề xuất lộ trình tích hợp, chưa sửa code sản phẩm).
5. **Bổ sung của người dùng:** Chọn `B`.
- **Trả lời nguyên văn:** `"1abcd 2a 3a 4a 5b tôi muốn ưu tiên vẫn đảm bảo đủ behavior và chất lượng tdq-workflow ko đổi chất lượng để lấy thêm tính năng"`

### Vòng 2 — Chi tiết kỹ thuật & Mức QC (2026-11-25 15:31+07:00)

1. **Nhóm lĩnh vực phi-code tập trung:** Chọn `A` (`3` nhóm: Nghiên cứu/Phân tích, PM/BA/Nội dung, Vận hành/Checklist đối chiếu cùng luồng Code).
2. **Điều kiện đạt bắt buộc để đề xuất tích hợp:** Chọn `A + C` (`4` tiêu chí cứng cho lõi mặc định, chấp nhận add-on tắt mặc định nếu `simulate test` chứng minh vượt trội).
3. **Độ sâu đề xuất tối ưu:** Chọn `A` (lộ trình `3` pha `P0`–`P2`, file TDQ dự kiến chạm, hợp đồng mẫu và danh sách CẤM copy).
4. **Mức QC:** Chọn `C` (`ultra` kèm agent `tdq-qc-tester` độc lập).
5. **Bổ sung thêm:** Chọn `A` (đủ rồi).
- **Trả lời nguyên văn:** `"1a 2a +c 3a 4c 5a"`
