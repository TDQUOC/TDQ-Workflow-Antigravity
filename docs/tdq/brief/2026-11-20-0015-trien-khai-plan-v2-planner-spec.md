# Brief: Triển khai 3 Chặng Plan V2, Per-Task Spec, Rule/Ví dụ cho Planner và Nghiên cứu Học hỏi các Planner Hàng đầu

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay làm cả 3 chặng đi, nhưng tôi muốn từng task cũng phải có thêm spec của nó để hiểu cần làm gì và set rule, example cho planer luôn và resreach thêm cách tối ưu mà các planer khác làm thế. nào mà học hỏi để hoàn thiện. mở request để thực hiện

### Đọc hiểu ban đầu

- **Mục tiêu:** Hiện thực trọn bộ `3` chặng của Kiến trúc Plan V2 (từ báo cáo `docs/tdq/reports/2026-11-19-2213-chi-tiet-plan-model-thap.md` đã qua 2 vòng phân tích & Red-Team vá `ND-1`..`ND-12`) vào `TDQ-Workflow-Antigravity`, đồng thời tích hợp `3` nâng cấp cốt lõi từ người dùng và kết quả nghiên cứu `10` Coding Planner hàng đầu:
  1. **Per-Task Mini-Spec ngay trong từng task:** Hợp nhất lớp đặc tả nghiệp vụ gọn (truy vết `Req:` về `spec.md`, ranh giới `Ngoài phạm vi:` / `GIỮ NGUYÊN`, tiêu chí chấp nhận hành vi `EARS`, hợp đồng `Consumes`/`Produces`, cùng bảng `Ràng buộc toàn cục` & `Sở hữu hợp đồng & Kiểu dữ liệu / Ownership Map` ở đầu Plan) vào khuôn Task Card để model tier thấp chỉ đọc Header Plan + đúng `1` task là hiểu trọn ngữ cảnh nghiệp vụ lẫn kỹ thuật mà không cần nạp cả `spec.md`.
  2. **Bộ Rule & Few-Shot Examples cho chính Planner:** Đóng gói hệ thống luật chống lỗi cho Planner tầm trung/yếu (`<= 25–30` chỉ thị rời rạc dưới ngưỡng IFScale) và `3` cặp ví dụ tương phản (`70% ĐẠT / 30% HỎNG + [Lý do sai]` chống Pink Elephant Effect cho Greenfield / Brownfield Refactor / Uniform Mechanical Sweep) dưới `skills/tdq-plan/references/` theo cơ chế progressive disclosure, tuân thủ nghiêm trần `3,500` token (`R13`), `<= 235` dòng/file và `SKILL_LINE_LIMITS`.
  3. **Nghiên cứu học hỏi các Coding Planner hàng đầu:** Đã hoàn tất khảo sát `10` hệ thống thực chiến (Claude Code Plan Mode, Superpowers `writing-plans`, Cursor Plan Mode, Amazon Kiro + AWS Specship, GitHub Spec-Kit, BMAD-METHOD v6, Claude Task Master, Aider Architect/Editor, Cline / Roo Code, Windsurf Cascade / Devin / OpenHands / SWE-agent) và các nghiên cứu 2025–2026 (IFScale, Curse of Instructions `p^N`, Anthropic Context Engineering, Cognition 2025) tại `docs/tdq/research/2026-11-20-0015-trien-khai-plan-v2-planner-spec.md`.
- **Phạm vi triển khai (`Loại request: feature`, `lane: full`, nhánh `feature/trien-khai-plan-v2-planner-spec` từ `dev`):**
  - **Chặng 1 (Parser, Scaffolder, Linter & Gates):** `scripts/tdq_team.py`, `scripts/tdq_plan_scaffold.py` (mới), `scripts/doc_lint.py`, `scripts/tdq_state.py`, `scripts/tdq_eval.py`, `scripts/tdq_ten_lenh.py` + bộ unit test mới & giữ xanh toàn bộ test cũ.
  - **Chặng 2 (Skills, Templates, Planner Rules/Examples, Agents & AGY Build):** `skills/tdq-plan/**`, `skills/tdq-spec/references/spec-template-huong-dan.md`, `skills/tdq-intake/references/quick-lane-mini.md`, `skills/tdq-build/references/{qc.md,qc-vong-fix.md,team-mode.md,team-mode-tra-cuu.md}`, `agents/tdq-implementer.md`, `agents/tdq-reviewer.md`, `tools/patches/agy_hooks.py`, `tools/patches/skills_and_agents.py`, `docs/tdq/token-budget.json`, đồng bộ `plugins/tdq-workflow-agy/`.
  - **Chặng 3 (Nghiệm thu E2E & Đóng gói):** E2E `Two-Pass + --emit-cards + packet + --verify-plan` trên `3` kịch bản đại diện, `build_portable.py`, `build_agy_plugin.py` + `agy.EXE plugin validate --strict`, và chạy bộ regression test theo `muc_qc`.

## Hiểu & kiến thức

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-20: `42` skill trên đĩa (`skill_inventory.py --loc` giữ `23`, ẩn `19`), cộng `26` skill built-in/khác trong context. Không xoá bảng này kể cả khi không có dòng DÙNG nào.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| tdq-intake | plugin:tdq-workflow | NỀN | Mở request, kiểm kê B0, khảo sát 3 chiều, research ngoài và phỏng vấn chốt thiết kế |
| tdq-spec | plugin:tdq-workflow | NỀN | Viết spec §1–§6 + Archify preview trước khi lập plan |
| tdq-plan | plugin:tdq-workflow | NỀN | Viết plan chi tiết theo phase, kiểm `--pair`, trình duyệt |
| tdq-build | plugin:tdq-workflow | NỀN | Triển khai code 3 chặng theo red → green, QC và xuất báo cáo Markdown + Archify HTML |
| tdq-conventions | plugin:tdq-workflow | NỀN | Luật nền 1-turn, state, approval, workinglog, trình bày 6 ký hiệu |
| tdq-setup | plugin:tdq-workflow | NỀN | Luật tìm kiếm 3 tầng (LSP → Grep → Graphify) và kiểm chứng môi trường |
| tdq-status / tdq-check-status / tdq-lean / tdq-checkportable | plugin:tdq-workflow | NỀN | Bộ công cụ phụ trợ trạng thái, soát tinh gọn và kiểm tra bundle |
| Đã xét 47 skill khác (gồm 19 skill ẩn trên đĩa, tdq-browser-*, 26 built-in/plugin khác) | user/plugin/built-in | KHÔNG | khác lĩnh vực |

### Khảo sát mã nguồn 3 chiều (Triangulation)

Đã chạy `tdq_lsp.py module` (`python:.` ĐẠT `510` file, `rust:hooks/rust/tdq-dispatch` ĐẠT `15` file), khởi động `start_lsp` (`python`), gọi `find_references` trên `doc_plan`, `rule_r15`, `_extract_plan_targets`, `BANG_DOI_TEN`, truy vấn `graphify query` 2 bước nhảy và đọc đối chiếu trực tiếp `docs/kien-truc.md`, `docs/tdq/token-budget.json`, `scripts/`, `skills/`, `agents/`, `tools/patches/`, `tests/`.

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `scripts/tdq_team.py` (`_PATH:49`, `_TASK_REF:52`, `doc_plan:141-182`, `chieu_phan_cong:238-279`, `canh_bao_lach_luat:1617`, `LENH:1721`) | LSP (`doc_plan` có `40` tham chiếu: `7` trong `scripts/`, `33` trong `tests/`) · Graphify · Đọc trực tiếp | Parser hiện quét `_PATH` toàn dòng (rò `Tham chiếu:` vào `vung_file`), thiếu theo dõi `indent`/`in_fence`, băm toàn bộ thân task vào `plan_assignment_sha` & `sha_file`; cần cô lập `Chạm:`/`Tham chiếu:`/`Sinh ra:`, giữ fallback `t.text[0]`, thêm lệnh `packet` |
| `scripts/tdq_ten_lenh.py` (`BANG_DOI_TEN:25`, `chay_subprocess:149`) | LSP (`BANG_DOI_TEN` có `16` tham chiếu: `5` `scripts/`, `11` `tests/`) · Đọc trực tiếp | Mọi lệnh con mới (`packet`) bắt buộc khai tại đây để qua `test_team_mode.py:1158` và `test_team_chong_conflict.py:92`; `tdq_plan_scaffold.py` phải gọi `chay_subprocess` (`CREATE_NO_WINDOW`) |
| `scripts/tdq_plan_scaffold.py` (tệp mới) | Thiết kế V2 (`ND-1`, `ND-2`, `ND-11`, `ND-12`) · `docs/kien-truc.md` | Nằm trong `scripts/` để Graphify lập chỉ mục; thuần stdlib + `utf8_io` + `TDQ_LOG`, không spawn LSP mới; hỗ trợ `--files`, `--refs`, `--from-spec`, `--emit-cards`, `--verify-plan`, `--check-wave` |
| `scripts/doc_lint.py` (`SKILL_LINE_LIMITS:63`, `FENCE:131`, `rule_r15:526-568`, `pair:602`, `_r12_van_xuoi:666`) | LSP (`rule_r15` có `2` tham chiếu) · Graphify · Đọc trực tiếp | Nâng `SKILL_LINE_LIMITS["tdq-plan"]` (`121 → 132`); vá `FENCE`/`in_fence` và `_r12_van_xuoi` miễn `\d+\.\s`; tách `r15_loi(..., check_dir=...)` chạy cả ở `--pair`; áp `R15-Full`/`R15-Compact` + trường Per-Task Spec + Banned-Placeholder + `ANTI-2` độc lập (mọi task/QC/DoD) sau `R15_MOC` |
| `scripts/tdq_state.py` (`_TASK_LINE:924`, `_cli_approve:2311`, `_extract_plan_targets:2471`, `set:3041`) & `scripts/tdq_eval.py` (`RE_TICK:197`) | LSP (`_extract_plan_targets` có `2` tham chiếu) · Graphify (`_cli_approve`, `cli`) · Đọc trực tiếp | Hub hệ thống; hỗ trợ `Chạm:` nhiều dòng; kiểm `R15`/`ANTI-2` tại `set plan_file` và kiểm sạch tại `approve plan`/`approve quick` (fail-open khi `quick` không tạo file plan); vá `RE_TICK` nhận `[>]`, `T2.1a`, `QC1.1` |
| `skills/tdq-plan/**`, `skills/tdq-spec/references/spec-template-huong-dan.md`, `skills/tdq-intake/references/quick-lane-mini.md`, `skills/tdq-build/references/{qc*,team-mode*}` | Grep · Đọc trực tiếp `docs/tdq/token-budget.json` & `tests/test_token_budget.py`, `test_reference_mot_tang.py`, `scripts/i18n_check.py` | Đầu dư token sát trần: `qc.md` (`3,496/3,500`, `+4`), `spec-template.md` (`3,486/3,500`, `+14`), `team-mode.md` (`3,390/3,500`, `+110`), `tdq-plan/SKILL.md` (`121/121` dòng). Phải tách Tier-1 sibling (`qc-vong-fix.md`, `planner-rules.md`, `plan-examples.md`), giữ mỗi file `<= 235` dòng & `<= 3,500` token (đo bằng `anthropic-tokenizer`), gắn `<!-- muc-luc-dong: -->` nếu `>= 90` dòng, viết luật bằng tiếng Anh (`i18n-allow` cho nhãn/mẫu Việt), ví dụ dùng `src/foo.py` (tránh `build_portable.py:346`) |
| `agents/tdq-implementer.md`, `agents/tdq-reviewer.md`, `tools/patches/agy_hooks.py:1325-1377`, `tools/patches/skills_and_agents.py:45-100`, `plugins/tdq-workflow-agy/` | Graphify (`apply_all`, `transform_agents`, `transform_skills`, `sinh_ban_antigravity`) · Đọc trực tiếp | Gọt `tdq-implementer.md` còn `<= 30` dòng (`<= 6` luật + circuit breaker `2` retry) nhưng giữ frontmatter Claude hợp lệ (`effort >= high`, `1,500 characters`, cấm raw dump); nâng `tdq-reviewer.md` đối chiếu `spec §3c ↔ plan`; sửa `SUBAGENT_DISPATCH_GATE_PY` trong `tools/patches/agy_hooks.py` ở mức `remind` bảo toàn 100% Parity/Dual-Protocol; tái build `plugins/tdq-workflow-agy/` |

### Tổng hợp nghiên cứu 10 Coding Planner hàng đầu & Thiết kế hợp nhất V2+

Nguồn đầy đủ: `docs/tdq/research/2026-11-20-0015-trien-khai-plan-v2-planner-spec.md`.

1. **Hợp nhất Per-Task Mini-Spec vào khung Task Card V2 (Kiro + BMAD + Superpowers + V2):**
   - Bổ sung vào đầu Plan (tối đa `<= 15` dòng): `Ràng buộc toàn cục (Global Constraints)` và bảng `Sở hữu hợp đồng & Kiểu dữ liệu (Ownership Map)` (bắt buộc khi có `>= 2` task code chia sẻ kiểu/state — khóa lỗi trùng định nghĩa `obra/superpowers#2587` & xung đột quyết định ngầm Cognition 2025).
   - Bổ sung lớp **Per-Task Mini-Spec** súc tích vào mỗi task code (`R15-Full`): `Req:` (trỏ ID mục `spec §2`/`§6`) + `Ngoài phạm vi:` (hoặc `GIỮ NGUYÊN` khi refactor — học từ Kiro & BMAD), `Giao tiếp:` (`Consumes` / `Produces`), và `Tiêu chí chấp nhận (EARS):` (`KHI <điều kiện>, HỆ THỐNG PHẢI <hành vi đo được>`), kết hợp với 4 chốt an toàn cơ học V2 (`Chạm:`/`Tham chiếu:`/`Sinh ra:`, `Vị trí neo:` theo symbol + `ANCHOR_CONFIDENCE`, `Trước → Sau`, `Công nghệ & Đặc tả:` có `Edit`/`Write`, `Logic & Ràng buộc <= 5 bước`, `Ca góc hiểm & Assert`).
   - Giữ **Adaptive 3-Tier** chặt chẽ: Tier 1 Compact/Sweep (`<= 8` dòng cho doc/config và Uniform Mechanical Sweep `<= 6` file đồng nhất), Tier 2 Standard (`16–24` dòng, trần cứng `<= 30` dòng/task), Tier 3 Cross-Boundary (tham chiếu `Ownership Map` & `Global Constraints` ở đầu Plan, không copy lặp).
2. **Chống bão hòa IFScale (`p^N`) & Pink Elephant Effect cho Weak Planner:**
   - Giữ `planner-rules.md` ở mức `<= 25–30` chỉ thị cốt lõi, chuyển toàn bộ kiểm tra cơ học (đủ trường, placeholder cấm `TBD`/`TODO`/`edge cases`/`...`, vượt trần dòng, `ANTI-2`, `Hot-File`) sang `doc_lint.py` và `tdq_plan_scaffold.py --verify-plan`.
   - Cung cấp `plan-examples.md` (`<= 1,300` token, progressive disclosure chỉ nạp ở pha `plan`) gồm đúng `3` cặp Contrastive Few-Shot (`70% ĐẠT / 30% HỎNG + [Lý do sai]`): Greenfield Feature, Brownfield Refactor và Uniform Mechanical Sweep.
3. **Lý do bỏ qua vòng Scope Round:** Phạm vi yêu cầu đã được người dùng chốt rõ ngay trong đề bài ("làm cả `3` chặng" từ báo cáo V2 + thêm `3` hạng mục cụ thể: Per-Task Spec, Planner Rules/Examples, Research các Planner ngoài), nên đi thẳng vào vòng hỏi chốt các điểm phân nhánh kỹ thuật thay đổi sản phẩm + `muc_qc`.

### Quyết định đã chốt (Vòng 1 — 2026-11-20T00:55:27+07:00)

- **1a — Hợp nhất Per-Task Mini-Spec gọn trong `R15-Full` (`16–24` dòng/task, trần cứng `<= 30` dòng):** Mỗi task code mang thêm `Req:` (trỏ mục `spec.md`), `Ngoài phạm vi:` / `GIỮ NGUYÊN`, `Giao tiếp:` (`Consumes`/`Produces`) và `Tiêu chí chấp nhận (EARS)` ngay trên phần kỹ thuật (`Chạm:`/`Tham chiếu:`/`Sinh ra:`, `Neo & Công cụ`, `Trước → Sau`, `Logic <= 5 bước`, `Ca hiểm & Assert`); phần dùng chung (`Ràng buộc toàn cục` + bảng `Sở hữu hợp đồng & Kiểu dữ liệu / Ownership Map`) đặt `1` lần ở đầu Plan.
- **2a — Tách `2` file Tier-1 sibling mới cho Planner dưới `skills/tdq-plan/references/`:** Nâng `SKILL_LINE_LIMITS["tdq-plan"]` từ `121` → `132` và trỏ thẳng tới `planner-rules.md` (`<= 25–30` chỉ thị bất biến, Two-Pass + Scaffolder + ngưỡng tách/gộp + `5` câu Self-Review) và `plan-examples.md` (`<= 1,300` token, `3` cặp Contrastive Few-Shot `70% ĐẠT / 30% HỎNG + [Lý do sai]` cho Greenfield / Refactor / Uniform Mechanical Sweep, chỉ nạp ở pha `plan`).
- **3a — Mốc tương thích `R15_MOC = "2026-11-20"` & build trong repo:** Áp bộ kiểm cứng mới (`R15-Full`/`R15-Compact`, Per-Task Spec, Banned-Placeholder, `ANTI-2`) từ mốc `2026-11-20` (bảo toàn `236` plan cũ và `evals/tuan-thu/`); tái build `plugins/tdq-workflow-agy/` + `agy.EXE plugin validate --strict`; chưa ghi đè bản cài ngoài repo tại `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy`.
- **4a — `muc_qc = full`:** DoD + trọn unit test + hồi quy vùng chạm + ràng buộc kiến trúc + clean code (không bắt buộc runtime test tách riêng hay agent QC độc lập).
- **5a — Không bổ sung thêm yêu cầu ngoài phạm vi đã chốt.**

### Lộ trình

| Bước/phase | CÓ-BỎ | Vì sao |
|---|---|---|
| Nghiên cứu bổ sung (`10` Coding Planner ngoài thực tế) | CÓ | Đã hoàn tất qua subagent Tavily tại `docs/tdq/research/2026-11-20-0015-trien-khai-plan-v2-planner-spec.md` |
| Phỏng vấn chốt thiết kế & `muc_qc` | CÓ | Đã hoàn tất Vòng 1 (`1a 2a 3A 4A 5a`, `muc_qc=full`) |
| Spec §1–§6 + Archify BA Preview | CÓ | Bắt buộc ở lane `full`; khóa hợp đồng `§3c`, ranh giới module `§2b` và tiêu chí `§6` trước khi lập plan |
| Plan + Kiểm `--pair` + Chọn Mode | CÓ | Bắt buộc ở lane `full`; áp dụng chính chuẩn Plan V2+ cho bản plan triển khai `3` chặng |
| Triển khai `3` Chặng (Red → Green từng task) | CÓ | Chặng 1 (Parser/Scaffolder/Linter/State), Chặng 2 (Skills/Rules/Examples/Agents/AGY), Chặng 3 (E2E & Đóng gói) |
| QC mức `full` (`DoD` + `tdq_test.py tron-bo` + ràng buộc kiến trúc) | CÓ | Theo lựa chọn `4a` (`muc_qc=full`) của người dùng |
| QC độc lập bằng agent ngoài (`ultra`) | BỎ | Người dùng chọn `4a` (`muc_qc=full`, không chạy `ultra`) |
| Đồng bộ cài thẳng plugin AGY ngoài repo (`install_agy_plugin.py`) | BỎ | Người dùng chọn `3a` (chỉ tái build + validate `plugins/tdq-workflow-agy/` trong repo) |
| Report Markdown + Archify HTML (Tailscale Serve) | CÓ | Bắt buộc kết thúc request với đủ `4` phần Trước/Sau/Đã test/Kết quả test và kiểm HTTP Tailscale |

## Hỏi đáp

### Vòng 1 (2026-11-20T00:55:27+07:00)

- **Câu 1:** Cách nhúng khối Per-Task Spec vào Task Block V2?
  - A (đề xuất): Hợp nhất gọn Per-Task Mini-Spec vào `R15-Full` (`16–24` dòng, trần `<= 30` dòng) + `Ràng buộc toàn cục` & `Ownership Map` ở đầu Plan.
  - B: Mục đặc tả nghiệp vụ dài hơn (`30–45` dòng/task, chép lại bối cảnh từ `spec.md`).
- **Câu 2:** Cách tổ chức bộ Planner Rules & Few-Shot Examples dưới `skills/tdq-plan/references/`?
  - A (đề xuất): Tách `2` file Tier-1 sibling (`planner-rules.md` + `plan-examples.md`), nâng `SKILL_LINE_LIMITS["tdq-plan"]` `121 → 132`.
  - B: Gộp vào `1` file `task-card-guide.md` (`128` dòng).
- **Câu 3:** Phạm vi mốc tương thích `R15` và cập nhật plugin AGY cài cục bộ?
  - A (đề xuất): `R15_MOC = "2026-11-20"`, tái build `plugins/tdq-workflow-agy/` + `agy.EXE plugin validate --strict`, chưa ghi đè bản cài ngoài repo.
  - B: Tương tự A + chạy `tools/install_agy_plugin.py` sau QC xanh.
- **Câu 4:** Mức QC cho request này (`muc_qc`)?
  - A (đề xuất): `full` · B: `lite` · C: `ultra`.
- **Câu 5:** Bạn muốn bổ sung thêm gì không?
  - A (đề xuất): Không, đủ rồi — làm tiếp đi · B: Có — tôi nói thêm.
- **Trả lời nguyên văn của người dùng:** `1a 2a 3A 4A 5a`

