# PLAN — Nghiên cứu khả thi, simulate test và đề xuất tích hợp cơ chế Paperclip vào TDQ-Workflow

Ngày: 2026-11-25 · Spec: ../spec/2026-11-25-1439-paperclip-tdq-integration-sim.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main — simulate thắng với chênh lệch 1.1 phút (`main` 14.3 phút vs `team` 15.3 phút ở hệ số agent 1.5, 7 task qua 5 đợt); nếu chọn `subagent` vẫn tách song song được `T1.1`–`T1.3` ở Đợt 1 (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: HOÀN THÀNH · Work kind: investigate

> **Tóm tắt dễ hiểu:** Kế hoạch chia đợt kiểm chứng tích hợp Paperclip thành ba chặng hoàn toàn cô lập và an toàn. Chặng một khảo sát song song hai mã nguồn về điều hành, đa lĩnh vực và bảo mật. Chặng hai chạy sáu kịch bản mô phỏng bằng Python để đo số liệu thực tế. Chặng ba kiểm chứng độc lập toàn bộ chứng cứ và xuất báo cáo.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Khảo sát đối chiếu sâu 2 codebase (H1–H3)
- P2 — Xây dựng & chạy bộ simulate test (SIM-1..SIM-6), tổng hợp blueprint và báo cáo 2 tầng (H1–H4)
- P3 — Log & kiểm chứng bắt buộc mức ultra (Q1–Q6)
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Phân bổ Model & Effort

> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` (`T1.1`, `T1.2`, `T1.3`) | `tdq-explorer` (khảo sát đối chiếu read-only + ghi shard artifact) | `inherit` | `high` | Chạy `Worktree: none`, chỉ ghi vào đúng file shard được giao |
| `implement` (`T2.1`, `T2.2`, `T2.3`) | Leader (lập & chạy `SIM-1..SIM-6`, hợp nhất chứng cứ, blueprint & báo cáo) | `inherit` | `xhigh` | Viết `sim/run_simulations.py`, đo số liệu thực tế và soạn báo cáo 2 tầng |
| `qc` (`T3.1`) | Leader + `tdq-qc-tester` độc lập (`muc_qc=ultra`) | `inherit` | `high` | Kiểm grounding `QC-I1..I4`, tái chạy `SIM-1..SIM-6` và phản biện độc lập |
| `report` | Leader (Archify HTML + Tailscale verify) | `inherit` | `medium` | Dựng Archify HTML xác minh `current` và HTTP `200` trước khi hỏi commit |

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo (`P1` → `P2` → `P3`).
2. Mỗi task: đánh `[~]` (hoặc `[>]` khi giao subagent) trước khi bắt đầu; đổi sang `[x]` ngay khi tiêu chí kiểm đạt, cấm gộp tick cuối lượt.
3. Tuyệt đối giữ nguyên mã nguồn sản phẩm (`scripts/`, `hooks/`, `plugins/`, `tools/`, `tests/`) của TDQ và toàn bộ kho `C:/Users/admin/Documents/paperclip`; mọi code chạy thử chỉ nằm trong `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/`.
4. Mọi bằng chứng mã nguồn phải ghi vào shard `.ev.jsonl` qua `py -3 -X utf8 scripts/tdq_team.py evidence add --shard <id> ...`.
5. QC FAIL → thêm task fix `QCn.x` vào mục QC của file này, sửa xong kiểm lại đến khi PASS.
6. Không commit hoặc push cho đến khi user yêu cầu rõ.
7. Tuân thủ đủ 6 mã cấm cơ học (`ANTI-1` đến `ANTI-6`), `doc_lint.py` exit `0` và `Work kind: investigate`.

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Đích đề xuất (Sau) |
|---|---|---|
| Điều hành `phase`/`task` | TDQ khóa slot wave và file state cơ bản; Paperclip có lease checkout, 4-tier queue, `blockedBy` và circuit breaker | Có bằng chứng đối chiếu + số liệu `SIM-1..SIM-3` đo rõ lợi ích và độ trễ của từng cơ chế trên TDQ |
| Mở rộng đa lĩnh vực | TDQ tối ưu cho `build` code phần mềm; chưa có khung Domain Pack đa ngành | Có mẫu Domain Pack cho 3 lĩnh vực phi-code kèm `SIM-5` chứng minh nhánh `Code Build` giữ 100% kỷ luật gốc |
| Hướng tích hợp tối ưu | Chưa đo thực nghiệm giữa `Pattern-Native` và `Hybrid Bridge` trên Windows/Antigravity | Có bảng lọc 4 tiêu chí + add-on tùy chọn (`2a+c`), lộ trình `P0`–`P2` và danh sách `CẤM` sao chép |

*Đối chiếu sơ đồ kiến trúc:* Spec `2026-11-25-1439-paperclip-tdq-integration-sim.md` miễn Archify preview trước duyệt theo `investigate-mode.md:13`; WBS ánh xạ 1–1 tới 5 đầu ra §2 và 6 cổng kiểm `Q1`–`Q6` của spec đã duyệt.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ràng buộc chung: `0` sửa code sản phẩm TDQ và `0` sửa kho `paperclip` · Bảo toàn 100% hành vi TDQ (`5b`) · Báo cáo tiếng Việt (`doc_lang=vi`).

| Hợp đồng / Ký hiệu (§2 & §3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| Bằng chứng `S1` (điều hành `phase`/`task`, lock state, queue, circuit breaker) | `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/s1.md` (`T1.1`) | `T2.1`, `T2.2` |
| Bằng chứng `S2` (đa lĩnh vực `Domain Pack`, roles, catalog & bảo toàn `5b`) | `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/s2.md` (`T1.2`) | `T2.1`, `T2.2` |
| Bằng chứng `S3` (MCP policy/quarantine, budget `hard_stop`, `Pattern-Native` vs `Hybrid Bridge`) | `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/s3.md` (`T1.3`) | `T2.1`, `T2.2` |
| Bộ simulate `SIM-1..SIM-6` + kết quả JSON/Markdown | `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/run_simulations.py`, `sim-results.json`, `sim-summary.md` (`T2.1`) | `T2.2`, `T2.3`, `T3.1` |
| Đối chiếu `S4` + Blueprint tích hợp `P0`–`P2` + Báo cáo 2 tầng + QC `ultra` | `s4.md`, `integration-blueprint.md`, `docs/tdq/reports/<slug>.md/.html`, `docs/tdq/qc/<slug>.md` (`T2.2`, `T2.3`, `T3.1`) | User & cổng `Q1`–`Q6` |

## P1 — Khảo sát đối chiếu sâu 2 codebase (H1–H3)

- [x] **T1.1** (e10m) Shard `S1`: Đối chiếu sâu cơ chế điều hành `phase`/`task`, lock state, wave và phục hồi lỗi giữa TDQ (`tdq_state.py`, `tdq_team.py`, `tdq_worktree_registry.py`, `agy_stop_gate.py`, `edit_gate.py`) và Paperclip (`issues.ts`, `queue.ts`, `automatic-run-brake.ts`), ghi `>= 6` bằng chứng `s1.ev.jsonl` (`H1`) — Test: `py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/s1.md').read_text(encoding='utf-8'); assert 'H1' in t and 'tdq_state.py' in t and 'automaticRunBrakes' in t"`
  - Req: `§1, §2#2, §3c` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn sản phẩm ở cả hai repository
  - Chạm: `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/s1.md` (tạo mới)
  - Cần: Không
  - Giao tiếp: Consumes: `scripts/tdq_state.py`, `scripts/tdq_team.py`, `scripts/tdq_worktree_registry.py`, `hooks/scripts/agy_stop_gate.py`, `hooks/scripts/edit_gate.py`, `C:/Users/admin/Documents/paperclip/server/src/services/{issues.ts,heartbeat/queue.ts,recovery/automatic-run-brake.ts}` | Produces: `s1.md` + `s1.ev.jsonl`
  - Neo & Công cụ: `read_file` có dải dòng; `tdq_team.py evidence add --shard s1`; `write_file` tạo `s1.md`
  - Trước → Sau: Mới biết tên các cơ chế rời rạc → Có bảng ánh xạ 1–1 từng điểm mạnh/hổng của TDQ và Paperclip trong quản trị `phase`/`task` kèm `path:line`
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T1.1`, HỆ THỐNG PHẢI ghi `>= 6` bằng chứng thật từ cả hai codebase vào `s1.ev.jsonl` và đưa kết luận sơ bộ cho `H1`
  - Logic cốt lõi: Đọc lock state `tdq_state.py` + cơ chế wave `tdq_team.py` đối chiếu với `checkoutRunId`, 4-tier queue, `blockedBy` và `automaticRunBrakes`
  - Ca góc hiểm & Assert: Chỉ ra rõ cơ chế nào phụ thuộc DB transaction nên phải viết lại bằng atomic file lock NTFS · `assert len(s1_ev) >= 6`

- [x] **T1.2** (e10m) Shard `S2`: Đối chiếu mở rộng đa lĩnh vực (`Domain Pack`, `work_kind`, `skill_router.py`, `skill_inventory.py`, `doc_lint.py` vs Paperclip `AGENT_ROLES`, `teams-catalog/`, `skills-catalog/`) cho 3 lĩnh vực phi-code song song bảo toàn 6 trụ cột `Code Build` (`H2`, `5b`), ghi `>= 6` bằng chứng `s2.ev.jsonl` — Test: `py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/s2.md').read_text(encoding='utf-8'); assert 'H2' in t and 'Domain Pack' in t and '5b' in t"`
  - Req: `§1, §2#2, §3c, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn sản phẩm ở cả hai repository
  - Chạm: `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/s2.md` (tạo mới)
  - Cần: Không
  - Giao tiếp: Consumes: `scripts/skill_router.py`, `scripts/skill_inventory.py`, `scripts/doc_lint.py`, `skills/tdq-intake/SKILL.md`, `C:/Users/admin/Documents/paperclip/packages/{shared/src/constants.ts,teams-catalog,skills-catalog}` | Produces: `s2.md` + `s2.ev.jsonl`
  - Neo & Công cụ: `read_file` có dải dòng; `tdq_team.py evidence add --shard s2`; `write_file` tạo `s2.md`
  - Trước → Sau: Chưa có thiết kế tách khung lõi với nghiệp vụ ngành → Có hợp đồng Domain Pack cho `Nghiên cứu/Phân tích`, `PM/BA/Nội dung`, `Vận hành/Checklist` mà nhánh `Code Build` giữ 100% cổng chặt
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T1.2`, HỆ THỐNG PHẢI ghi `>= 6` bằng chứng từ hai repo và mô tả ranh giới cách ly giữa Domain Pack phi-code và kỷ luật code TDQ
  - Logic cốt lõi: Phân tích `work_kind` và `skill_router.py` của TDQ ghép với `teams-catalog`/`skills-catalog` của Paperclip
  - Ca góc hiểm & Assert: Chặn tuyệt đối việc nhánh phi-code tắt nhầm cổng `build` hoặc hook `Stop` · `assert len(s2_ev) >= 6`

- [x] **T1.3** (e10m) Shard `S3`: Đối chiếu bảo mật MCP (`Profile/Policy`, `changed-tool quarantine`), ngân sách `hard_stop` (`token_budget.py`, `tdq_timing.py` vs `budgets.ts`) và đánh đổi `Pattern-Native` vs `Hybrid Bridge` trên Windows + `tdq-workflow-agy` (`H3`, `H4`), ghi `>= 6` bằng chứng `s3.ev.jsonl` — Test: `py -3 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/s3.md').read_text(encoding='utf-8'); assert 'H3' in t and 'Pattern-Native' in t and 'Hybrid Bridge' in t"`
  - Req: `§1, §2#2, §3c, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn sản phẩm ở cả hai repository
  - Chạm: `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/s3.md` (tạo mới)
  - Cần: Không
  - Giao tiếp: Consumes: `scripts/token_budget.py`, `scripts/tdq_timing.py`, `hooks/scripts/agy_pretooluse_gate.py`, `README-Antigravity.md`, `C:/Users/admin/Documents/paperclip/{doc/MCP-ACCESS-GOVERNANCE.md,doc/DEPLOYMENT-MODES.md,server/src/services/budgets.ts}` | Produces: `s3.md` + `s3.ev.jsonl`
  - Neo & Công cụ: `read_file` có dải dòng; `tdq_team.py evidence add --shard s3`; `write_file` tạo `s3.md`
  - Trước → Sau: Mới biết chung chung nên tránh Postgres → Có phân tích định tính và tiêu chí đo cho MCP quarantine, `hard_stop` ngân sách và 2 hướng `Pattern-Native` vs `Hybrid Bridge` trên Windows
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T1.3`, HỆ THỐNG PHẢI ghi `>= 6` bằng chứng thật và chốt rõ cấu trúc đo độ trễ/chi phí cho `SIM-4` và `SIM-6`
  - Logic cốt lõi: Kiểm tra vị trí móc nối hợp lệ trong `agy_pretooluse_gate.py` / `tdq_mcp_launcher.mjs` và chi phí Docker/WSL2 Bridge trên Windows
  - Ca góc hiểm & Assert: Tách rõ phần nào làm thuần stdlib đạt 0-dependency và phần nào chỉ nên là add-on tắt mặc định · `assert len(s3_ev) >= 6`

**Xong P1 khi**: Đủ 3 shard `s1.md`, `s2.md`, `s3.md` và `s1..s3.ev.jsonl` với `>= 18` bằng chứng thật từ cả hai repo.

## P2 — Xây dựng & chạy bộ simulate test (SIM-1..SIM-6), tổng hợp blueprint và báo cáo 2 tầng (H1–H4)

- [x] **T2.1** (e14m) Viết và chạy bộ Python `simulate test` cô lập `sim/run_simulations.py` (`SIM-1`–`SIM-6`, Baseline vs Proposed, timestamp log + `TDQ_LOG=0`), xuất `sim/sim-results.json` và `sim/sim-summary.md` — Test: `py -3 -X utf8 docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/run_simulations.py --out-json docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/sim-results.json --out-md docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/sim-summary.md`
  - Req: `§1, §2#3, §3c, §4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ `scripts/`, `hooks/`, `docs/tdq/state.json` (chỉ chạy trong `tempfile.TemporaryDirectory()`)
  - Chạm: `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/run_simulations.py` (tạo mới), `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/sim-results.json` (tạo mới), `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/sim-summary.md` (tạo mới)
  - Cần: `T1.1`, `T1.2`, `T1.3`
  - Giao tiếp: Consumes: `s1.md..s3.md`, hợp đồng Baseline TDQ & cơ chế Paperclip | Produces: `run_simulations.py`, `sim-results.json`, `sim-summary.md`
  - Neo & Công cụ: Python 3 stdlib (`threading`, `tempfile`, `time`, `json`, `hashlib`); viết script mô phỏng và thực thi trực tiếp đo số thật
  - Trước → Sau: Chưa có số liệu thực nghiệm kiểm chứng tích hợp → Có 6 kịch bản chạy thật chứng minh định lượng tác động của `checkout+lease`, `priority+blockedBy`, `circuit breaker+hard_stop`, `MCP policy+12 TDQ invariants`, `4 Domain Packs`, và độ trễ Windows `Pattern-Native` vs `Hybrid Bridge`
  - Tiêu chí chấp nhận (EARS): KHI chạy `run_simulations.py`, HỆ THỐNG PHẢI thực thi đủ `6/6` kịch bản trong sandbox tạm, xuất JSON với số liệu Baseline vs Proposed rõ ràng (kèm kiểm tra `TDQ_LOG=0` và `TDQ_LOG=1`) và không chạm bất kỳ tệp hệ thống nào ngoài thư mục `sim/`
  - Logic cốt lõi: Mỗi kịch bản cài kiểm chứng phản chứng thực sự (Baseline gặp xung đột/lỗi/bỏ sót còn Proposed xử lý đúng trong ngưỡng độ trễ `ms`), kèm `SIM-6` ghi nhận công bằng điểm `Hybrid Bridge` chậm khởi động/tốn RAM hơn trên Windows
  - Ca góc hiểm & Assert: Kiểm tra contention khóa tệp Windows với `8` luồng song song; cấm assert rỗng (`ANTI-2`) · `assert data['summary']['total_scenarios'] == 6 and data['summary']['passed'] == 6`

- [x] **T2.2** (e10m) Hợp nhất `evidence.jsonl`, soạn shard `S4` (`H4` + danh mục CẤM copy) và xuất phụ lục `integration-blueprint.md` (lọc 4 tiêu chí cứng + add-on `2a+c`, lộ trình `P0`–`P2`, file TDQ dự kiến chạm, schema mẫu và mục CẤM sao chép) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/integration-blueprint.md`
  - Req: `§1, §2#1-2, §2#4, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn sản phẩm ở cả hai repo
  - Chạm: `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/s4.md` (tạo mới), `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/integration-blueprint.md` (tạo mới)
  - Cần: `T2.1`
  - Giao tiếp: Consumes: `s1..s3.md`, `s1..s3.ev.jsonl`, `sim-results.json`, `sim-summary.md` | Produces: `evidence.jsonl`, `evidence-log.md`, `s4.md`, `integration-blueprint.md`
  - Neo & Công cụ: `tdq_team.py evidence add --shard s4` + `merge` + `render`; `write_file`; `doc_lint.py`
  - Trước → Sau: Số liệu đối chiếu còn tách rời giữa code và mô phỏng → Có bản thiết kế tích hợp `P0`–`P2` hoàn chỉnh đã sàng lọc qua 4 tiêu chí bảo toàn chất lượng TDQ và phân tách rõ lõi vs add-on tùy chọn
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T2.2`, HỆ THỐNG PHẢI hợp nhất sạch `evidence.jsonl`, trích dẫn số đo thật từ `sim-results.json`, nêu rõ từng file TDQ dự kiến chạm và danh sách hạng mục CẤM copy qua `doc_lint.py` exit `0`
  - Logic cốt lõi: Tổng hợp bằng chứng từ code + `SIM-1..SIM-6`; xếp hạng từng cơ chế vào `P0` (ổn định lõi), `P1` (mở rộng đa lĩnh vực), `P2` (add-on tùy chọn) hoặc `CẤM`
  - Ca góc hiểm & Assert: Không ghi số đo nào không xuất hiện nguyên văn trong `sim-results.json` · `assert rc == 0 and 'P0' in bp and 'CẤM' in bp`

- [x] **T2.3** (e8m) Soạn bản thảo báo cáo 2 tầng (`docs/tdq/reports/2026-11-25-1439-paperclip-tdq-integration-sim.md`) và tệp ứng viên Archify (`bao-cao.archify.md`) — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-25-1439-paperclip-tdq-integration-sim.md`
  - Req: `§1, §2#5, §4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn sản phẩm
  - Chạm: `docs/tdq/reports/2026-11-25-1439-paperclip-tdq-integration-sim.md` (tạo mới), `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/bao-cao.archify.md` (tạo mới)
  - Cần: `T2.2`
  - Giao tiếp: Consumes: `evidence.jsonl`, `sim-results.json`, `integration-blueprint.md`, `tdq_timing.py show` | Produces: report MD 2 tầng + `bao-cao.archify.md`
  - Neo & Công cụ: `write_file`; `tdq_timing.py show`; `doc_lint.py`
  - Trước → Sau: Chưa có báo cáo tổng hợp cho người dùng → Có báo cáo 2 tầng (Tầng 1 trả lời thẳng câu hỏi khả thi + kết quả test + đề xuất tối ưu; Tầng 2 đủ bằng chứng `[EV]`, `SIM-1..SIM-6`, `H1`–`H4`, thời gian và thân PR)
  - Tiêu chí chấp nhận (EARS): KHI kiểm định báo cáo, `doc_lint.py` PHẢI trả `0` vi phạm (bao gồm `R12`, `R16`, `R5`, `R6` `< 500` dòng) và `bao-cao.archify.md` giữ `<= 4` node/hàng
  - Logic cốt lõi: Tóm tắt đời thường ở Tầng 1 dễ nắm trong 15 giây; đẩy chi tiết schema và log xuống phụ lục `integration-blueprint.md` và `sim-summary.md`
  - Ca góc hiểm & Assert: Bọc nguyên stdout `tdq_timing.py show` trong khối fenced code (`R12`) · `assert rc == 0`

**Xong P2 khi**: Bộ `SIM-1..SIM-6` chạy thật exit `0`, `evidence.jsonl` hợp nhất, `integration-blueprint.md` và `report.md` qua `doc_lint.py` exit `0`.

## P3 — Log & kiểm chứng bắt buộc mức ultra (Q1–Q6)

Log: BỎ cho mã nguồn sản phẩm (`work_kind=investigate`, `0` file code TDQ sửa); riêng script mô phỏng `sim/run_simulations.py` bật timestamp log mặc định và hỗ trợ `TDQ_LOG=0`.

- [x] **T3.1** (e10m) Chạy trọn bộ kiểm chứng mức `ultra` (`Q1`–`Q6`): `QC-I1..I4`, đối chiếu nguyên văn `L2`, tái chạy `SIM-1..SIM-6` (kèm kiểm `TDQ_LOG=1/0`), gọi `tdq-qc-tester` độc lập soi chéo, xuất `docs/tdq/qc/2026-11-25-1439-paperclip-tdq-integration-sim.md`, dựng Archify HTML `current` và xác nhận Tailscale HTTP `200` — Test: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-25-1439-paperclip-tdq-integration-sim.md --manifest docs/tdq/reports/2026-11-25-1439-paperclip-tdq-integration-sim.manifest.json`
  - Req: `§2#5, §6 Q1-Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn sản phẩm ở cả hai repo
  - Chạm: `docs/tdq/reports/2026-11-25-1439-paperclip-tdq-integration-sim.html` (tạo mới), `docs/tdq/qc/2026-11-25-1439-paperclip-tdq-integration-sim.md` (tạo mới)
  - Cần: `T2.3`
  - Giao tiếp: Consumes: `run_simulations.py`, `sim-results.json`, `evidence.jsonl`, `integration-blueprint.md`, `bao-cao.archify.md`, `report.md` | Produces: report HTML + manifest + biên bản `docs/tdq/qc/<slug>.md`
  - Neo & Công cụ: Python script `QC-I1`, `run_simulations.py`, subagent `tdq-qc-tester` (độc lập, read-only audit), `doc_lint.py`, `tdq_archify.py render/verify`, Tailscale HTTP probe
  - Trước → Sau: Mới có bản thảo tự kiểm → Có xác nhận độc lập từ `tdq-qc-tester`, bằng chứng tái lập `SIM-1..SIM-6`, `6/6` cổng `Q1`–`Q6` PASS, Archify HTML `current` và HTTP `200`
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất `T3.1`, `Q1`–`Q6` PHẢI đạt `PASS` đủ `6/6` trong biên bản QC, `tdq-qc-tester` xác nhận không có số liệu bịa hay assert giả, và `tdq_archify.py verify` trả `"status": "current"`
  - Logic cốt lõi: Chạy xác minh `L1/L4/L2`, tái chạy `SIM-1..SIM-6`, giao `tdq-qc-tester` đọc chéo toàn bộ artifact/code mô phỏng trước khi xuất HTML cuối
  - Ca góc hiểm & Assert: Chỉ render + verify Archify HTML SAU chỉnh sửa cuối cùng của `report.md`; nếu `tdq-qc-tester` phát hiện lỗ hổng phải ghi `## QC vòng N — fix` sửa dứt điểm · `assert verify['status'] == 'current' and http == 200`

**Xong P3 khi**: `6/6` hạng mục `Q1`–`Q6` đạt `PASS`, `tdq-qc-tester` ký xác nhận độc lập và Archify HTML trả `current` + HTTP `200`.

---

## QC vòng 1 — fix

- [x] **QC1.1** (e6m) Sửa `SIM-2` để nhánh aging `OLDEST_DISPATCH_SHARE` (`step_idx % 4 == 0`) kích hoạt thật (`W_AGED` vượt chuỗi `person` ở lượt 4, `aging_share_hits >= 1`) và thay thế các baseline/check tĩnh ở `SIM-2`/`SIM-3`/`SIM-4`/`SIM-5` bằng hàm thực thi đối chứng thật + đọc bất biến đĩa — Test: `py -3 -X utf8 docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/run_simulations.py --out-json docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/sim-results.json --out-md docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/sim-summary.md`
- [x] **QC1.2** (e6m) Tách bằng chứng `a22d6a034353` (`package.json`), bổ sung chứng cứ riêng cho `PLUGIN_SPEC.md:15-35` và `SKILL.md:10-24`, tái hợp nhất `evidence.jsonl`, đồng bộ ID/số liệu vào `s3.md`, `s4.md`, `integration-blueprint.md`, `report.md`, dựng Archify HTML `current` + HTTP `200`, rồi chạy lại `tdq-qc-tester` xác nhận `6/6` PASS — Test: `py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-25-1439-paperclip-tdq-integration-sim.md --manifest docs/tdq/reports/2026-11-25-1439-paperclip-tdq-integration-sim.manifest.json`

## Cụm song song

- **Đợt 1 (chạy song song 3 luồng đọc-chỉ, `Worktree: none`, `Chạm:` tách rời):**
  - `T1.1` (`tdq-explorer`) → `s1.md`
  - `T1.2` (`tdq-explorer`) → `s2.md`
  - `T1.3` (`tdq-explorer`) → `s3.md`
- **Đợt 2 (tuần tự trên Leader + subagent QC độc lập ở cuối):** `T2.1` → `T2.2` → `T2.3` → `T3.1` (kèm `tdq-qc-tester`).

## Luật file nóng (một file, nhiều task chạm)

Không có file nóng: cả 7 task `T1.1`–`T3.1` sở hữu đường dẫn `Chạm:` hoàn toàn tách rời, không xung đột ghi. Sổ bằng chứng `evidence.jsonl` được ghi qua `tdq_team.py evidence add --shard <id>` có khóa file an toàn và hợp nhất một lần ở `T2.2`.

## Definition of Done

Trỏ về §6 của spec `2026-11-25-1439-paperclip-tdq-integration-sim.md` (`muc_qc=ultra`):

- [x] Q1 `QC-I1` Grounding chứng cứ & không placeholder — chạy script Python kiểm tra `100%` ID trích dẫn tồn tại trong `evidence.jsonl`, `100%` `path:line` tồn tại trên đĩa cả hai repo và `0` placeholder
- [x] Q2 `QC-I2` Đối chiếu nguyên văn `L2` — đọc trực tiếp mã nguồn các điểm neo cốt lõi của `paperclip` và `TDQ-Workflow-Antigravity`, đối khớp trong `docs/tdq/qc/2026-11-25-1439-paperclip-tdq-integration-sim.md`
- [x] Q3 Thực thi tái lập `SIM-1..SIM-6` — chạy `py -3 -X utf8 docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/run_simulations.py` (kèm kiểm `TDQ_LOG=1` và `TDQ_LOG=0`) đạt `6/6` kịch bản PASS không assert rỗng
- [x] Q4 Kết luận `H1`–`H4`, bộ lọc `2a+c` & bảo toàn `5b` — kiểm tra đủ `4` kết luận kèm phản ví dụ, bảng so sánh `Pattern-Native` vs `Hybrid Bridge` và lộ trình `P0`–`P2` + mục `CẤM` copy trong `integration-blueprint.md` và `report.md`
- [x] Q5 Kiểm định `doc_lint.py`, ranh giới `0` code diff & Archify HTML — `py -3 -X utf8 scripts/doc_lint.py` exit `0`, `git -C C:/Users/admin/Documents/paperclip status --porcelain` rỗng, `git diff --name-only dev -- scripts/ hooks/ plugins/ tools/ tests/` rỗng, `tdq_archify.py verify` trả `current` và Tailscale HTTP `200`
- [x] Q6 QC độc lập `tdq-qc-tester` (`muc_qc=ultra`) — subagent `tdq-qc-tester` kiểm tra độc lập mã mô phỏng `run_simulations.py`, `sim-results.json`, `evidence.jsonl` và báo cáo để xác nhận không gian lận hay suy diễn thiếu chứng cứ
