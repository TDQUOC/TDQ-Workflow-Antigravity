# PLAN — Triển khai 3 Chặng Plan V2+, Per-Task Mini-Spec, Luật và Ví dụ Mẫu cho Planner

Ngày: 2026-11-20 · Spec: ../spec/2026-11-20-0015-trien-khai-plan-v2-planner-spec.md (bản 1.0, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — đo thực tế bằng tdq_bench.py simulate (--he-so-agent 1.5): đội thắng main 2.0 phút (18.4 vs 20.4 phút, 10 task chia 6 đợt, giao được 7 task và leader giữ 3 task file-luat) (ĐÃ CHỌN lúc duyệt)
Trạng thái plan: ĐÃ DUYỆT

## Mục lục

- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Chặng 1: Nền Parser, Scaffolder, Linter & Cổng State
- P2 — Chặng 2: Bộ Skill tdq-plan V2+, Tài liệu Hỗ trợ & Agents
- P3 — Chặng 3: AGY Patch, Đóng gói Bundle & Nghiệm thu E2E
- P4 — Log & test bắt buộc
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- Definition of Done

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase và `Cần:` là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → viết test trước (đỏ) → code → test xanh → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Mỗi bước: chạy `tdq_test.py vung-cham`; trọn bộ chỉ chạy ở pha QC (`muc_qc=full`).
4. Lệnh nào chạm state của workflow phải đặt `TDQ_PROJECT_DIR=<thư mục tạm>` ngay trên lệnh đó.
5. QC FAIL → thêm task fix `QCn.x` (dạng `R15-Compact`) vào mục QC của file này (không cần duyệt lại), lặp đến khi pass.
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ `6` mã cấm cơ học (`ANTI-1`..`ANTI-6`); không tự ghi đè plugin AGY cài ngoài repo (`3a`).

## Thiết kế Trước vs Sau

| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau — Plan V2+) |
|---|---|---|
| Per-Task Mini-Spec & Planner Guidance | Task chỉ có kỹ thuật thô hoặc `1` dòng lách `R15`; `tdq-plan/SKILL.md` (`121/121` dòng) thiếu luật và ví dụ cho Planner | Nhúng Per-Task Mini-Spec gọn (`Req:`, `Ngoài phạm vi:`/`GIỮ NGUYÊN`, `Giao tiếp:`, `EARS`) trong `R15-Full` (`<= 30` dòng/task), tách `planner-rules.md` (`<= 30` luật) & `plan-examples.md` (`<= 1,300` tok, `3` cặp ĐẠT/HỎNG) |
| Parser, Scaffolder & Auto-Packet | `doc_plan()` quét `_PATH` toàn dòng làm nhiễm `vung_file`; sửa neo nổ STALE kép; thiếu Scaffolder & lệnh `packet` | `doc_plan()` cô lập `Chạm:`/`Tham chiếu:`/`Sinh ra:` theo `indent`/`in_fence`; thêm `tdq_plan_scaffold.py` & `tdq_team.py packet` trích trọn Symbol-Span |
| Cổng R15 & Token Budget | `rule_r15` dò `1` từ khóa, bỏ sót `QCn.x`/`quick`/non-code `ANTI-2`, không chặn trước trình duyệt; `qc.md` còn `+4` tok | `R15-Full`/`R15-Compact` + Banned-Placeholder + `ANTI-2` 100% task/DoD sau `R15_MOC = "2026-11-20"`, chặn tại `set plan_file`/`--pair`/`approve`; tách `qc-vong-fix.md` giữ toàn bộ skill `<= 3,500` tok |

*Đối chiếu sơ đồ kiến trúc:* Kế thừa bản xem trước Archify đã duyệt [2026-11-20-0015-trien-khai-plan-v2-planner-spec-preview.html](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-20-0015-trien-khai-plan-v2-planner-spec-preview.html) và manifest `2026-11-20-0015-trien-khai-plan-v2-planner-spec-preview.manifest.json`. WBS ánh xạ `1–1` `6` module `M1`..`M6` trong spec §2b tới `P1`..`P4`, không phát sinh thiết kế khác ngoài spec đã duyệt.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- **Ràng buộc toàn cục (Global Constraints):** Thuần Python stdlib (`3.9+`, cấm cú pháp `A | B` trong `isinstance` hay type hint không có `from __future__ import annotations`), dùng `utf8_io`, bật `TDQ_LOG` mặc định (`TDQ_LOG=0` tắt), gọi subprocess qua `tdq_ten_lenh.chay_subprocess` (`CREATE_NO_WINDOW`), `scripts/` cấm import `hooks/`, luật/chú thích/stdout viết tiếng Anh (`i18n_check.py`, dùng `i18n-allow` cho nhãn Việt), mọi file `skills/` `<= 3,500` token trên `anthropic-tokenizer` và `<= 235` dòng/ref.

| Khái niệm / Hợp đồng / Kiểu dữ liệu | Chủ sở hữu duy nhất (file / symbol) | Task tạo · Task dùng |
|---|---|---|
| Cấu trúc `Task` (`vung_file`, `tham_chieu`, `sinh_ra`, `nhan_loai`) & `doc_plan()` | `scripts/tdq_team.py` (`Task`, `doc_plan`) | Tạo: `T1.1` · Dùng: `T1.2`, `T1.3`, `T3.2` |
| Bảng tên lệnh con chính thức (`packet`) & chạy subprocess không popup | `scripts/tdq_ten_lenh.py` (`BANG_DOI_TEN`, `chay_subprocess`) | Tạo: `T1.1` · Dùng: `T1.2`, `T3.2` |
| Chuẩn khung thẻ & xác minh AST/symbol tĩnh (`emit_cards`, `verify_plan`, `check_wave`) | `scripts/tdq_plan_scaffold.py` | Tạo: `T1.2` · Dùng: `T2.1`, `T3.2` |
| Luật kiểm định `R15_MOC`, `r15_loi()`, `SKILL_LINE_LIMITS["tdq-plan"]` | `scripts/doc_lint.py` (`r15_loi`, `rule_r15`, `pair`) | Tạo: `T1.3` · Dùng: `T1.4`, `T2.1`, `T3.2` |
| Cổng kiểm state tiền-duyệt (`_kiem_r15_plan`, `_extract_plan_targets`) | `scripts/tdq_state.py` | Tạo: `T1.4` · Dùng: `T3.2` |
| Nguồn sinh hook `subagent_dispatch_gate.py` của AGY | `tools/patches/agy_hooks.py` (`SUBAGENT_DISPATCH_GATE_PY`) | Tạo: `T3.1` · Dùng: `T3.1` (`build_agy_plugin`) |

## P1 — Chặng 1: Nền Parser, Scaffolder, Linter & Cổng State

- [x] **T1.1** (e18m) Vá parser `doc_plan`, ổn định `plan_assignment_sha`, mở rộng `_TASK_REF` và thêm lệnh `packet` trong `tdq_team.py` + `tdq_ten_lenh.py` — Test: `py -3 -X utf8 -m unittest tests/test_team_packet_v2.py tests/test_team_mode.py tests/test_team_chong_conflict.py -v`
  - Req: `§2 #1, §3c, §6 Q1` · Ngoài phạm vi: `GIỮ NGUYÊN` fallback `t.text[0]` khi task không khai `Chạm:` và toàn bộ hành vi `assign`/`wave`/`merge`/`resolve` hiện có
  - Chạm: `scripts/tdq_team.py`, `scripts/tdq_ten_lenh.py`, `tests/test_team_packet_v2.py`
  - Cần: Không
  - Giao tiếp: Consumes: `duong_dan: str` (plan Markdown) | Produces: `Task(tham_chieu, sinh_ra, nhan_loai)`, `lenh_packet(args, cwd) -> int`, `BANG_DOI_TEN["tdq_team.py"]["packet"] = "packet"`
  - Neo & Công cụ: `Edit` trên `scripts/tdq_team.py` tại `_TASK_REF` (`L52`), `doc_plan()` (`L141-182`), `chieu_phan_cong()` (`L238-279`), `canh_bao_lach_luat()` (`L1617`), `LENH`/`build_parser()` (`L1721-1750`); `Edit` trên `scripts/tdq_ten_lenh.py` (`BANG_DOI_TEN:26-37`); `Write` cho `tests/test_team_packet_v2.py`
  - Trước → Sau: Hiện `doc_plan()` quét `_PATH` mọi dòng (nhiễm `Tham chiếu:` vào `vung_file`), băm mọi dòng `t.text[1:]` vào `plan_assignment_sha` và gọi `sha_file(plan)` ở `L1617` → Sau: theo dõi `indent` & `in_fence`, cô lập `Chạm:`/`Tham chiếu:`/`Sinh ra:` + whitelist `ROOT_FILES`, bỏ dòng neo khỏi `plan_assignment_sha`, đổi `L1617` sang `kiem_tra_stale`, mở rộng `_TASK_REF` cho `T1`/`T2.1a`/`QC1.1`, thêm lệnh `packet` xuất `7` `TRUONG_PROMPT` + Symbol-Span trọn hàm (`<= 2` file, vượt ngưỡng xuất `READ-EXACT`) + `1` dòng chữ ký `Tham chiếu:` + `<= 3` bất biến từ `kien-truc.md`
  - Tiêu chí chấp nhận (EARS): KHI plan có `Tham chiếu:`, `Sinh ra:`, `Chạm:` nhiều dòng và code fence chứa đường dẫn, HỆ THỐNG PHẢI chỉ đưa đường dẫn dưới `Chạm:` vào `t.vung_file`, giữ nguyên `plan_assignment_sha` khi đổi `Vị trí neo:`, và lệnh `tdq_team.py packet <id>` trả mã `0` kèm trọn thân hàm đích + `7` trường giao việc
  - Logic cốt lõi:
    1. Thêm `tham_chieu`, `sinh_ra`, `nhan_loai` vào `Task`; mở rộng `_TASK_REF` và hỗ trợ `ROOT_FILES` (`CLAUDE.md`, `AGENTS.md`, `Cargo.toml`, `pyproject.toml`, `package.json`, `pyrightconfig.json`).
    2. Nâng `doc_plan()` theo dõi `in_fence` và `section_key` (`cham`/`tham_chieu`/`sinh_ra`/`other`) theo mức thụt đầu dòng; chỉ fallback `_PATH` trên `t.text[0]` khi không có mục `Chạm:`.
    3. Trong `chieu_phan_cong()`, lọc dòng tiền tố `vị trí neo:`, `neo & công cụ:`, `tham chiếu:`, `contract-delta:` khỏi `cac_dong`; sửa `canh_bao_lach_luat()` gọi `kiem_tra_stale(ban_do, plan)`.
    4. Cài `lenh_packet(args, cwd)` (trích Symbol-Span qua `ast` với Python hoặc quét block, vượt `120` dòng hoặc `> 2` file xuất `READ-EXACT`, lấy `<= 3` dòng bất biến kiến trúc) và đăng ký `"packet"` trong `LENH`, `build_parser()`, `BANG_DOI_TEN`.
  - Ca góc hiểm & Assert:
    - Ca hiểm: Task không có `Chạm:` (legacy fallback), dòng `- Chạm:` nằm trong code fence, hàm đích > `120` dòng, `task_id` không tồn tại (trả exit `1` kèm thông báo rõ).
    - Tiêu chí: `assert t.vung_file == ["scripts/a.py"] and "scripts/ref.py" in t.tham_chieu`, `assert sha_before == sha_after`, `assert all(f in out for f in ("TASK:", "WORKTREE:", "VÙNG FILE:", "TEST:", "TRẢ VỀ:"))`

- [x] **T1.2** (e20m) Tạo mới công cụ `scripts/tdq_plan_scaffold.py` (AST/Spec Scaffolder, Card Emitter, Verifier & Wave Checker có `TDQ_LOG`) — Test: `py -3 -X utf8 -m unittest tests/test_plan_scaffold.py -v`
  - Req: `§2 #2, §3c, §4, §6 Q2` · Ngoài phạm vi: Không spawn server LSP mới, không sửa trực tiếp `docs/tdq/state.json`, không cài gói ngoài stdlib
  - Chạm: `scripts/tdq_plan_scaffold.py`, `tests/test_plan_scaffold.py`
  - Cần: `T1.1`
  - Giao tiếp: Consumes: `tdq_team.doc_plan`, `tdq_ten_lenh.chay_subprocess`, `utf8_io` | Produces: CLI `tdq_plan_scaffold.py` với `--files`, `--refs`, `--from-spec`, `--emit-cards`, `--verify-plan`, `--check-wave` và các hàm công khai `extract_symbols`, `parse_spec_contracts`, `emit_cards`, `verify_plan`, `check_wave`
  - Neo & Công cụ: `Write` tạo mới `scripts/tdq_plan_scaffold.py` và `tests/test_plan_scaffold.py` (file mới 100%)
  - Trước → Sau: Hiện chưa có công cụ trích neo/chữ ký tĩnh và xác minh symbol/assert trước khi duyệt plan → Sau: có `scripts/tdq_plan_scaffold.py` bật `TDQ_LOG` mặc định (`TDQ_LOG=0` tắt), parse AST Python (`ANCHOR_CONFIDENCE: HIGH`) và fallback regex `.rs`/`.ts`/`.js` (`ANCHOR_CONFIDENCE: LOW`), đọc hợp đồng `§3c` cho Greenfield (`--from-spec`, fail exit `1` nếu rỗng), đổ khung Per-Task Mini-Spec (`--emit-cards`), xác minh symbol trên đĩa + AST `assert` (`--verify-plan`) và kiểm `CONTRACT-DELTA:` (`--check-wave`)
  - Tiêu chí chấp nhận (EARS): KHI chạy `--emit-cards` với file đã có hoặc `--from-spec` cho file mới, HỆ THỐNG PHẢI in khung thẻ kèm chữ ký thật và nhãn `ANCHOR_CONFIDENCE`; KHI chạy `--verify-plan` trên plan chứa symbol giả hoặc `assert True`, HỆ THỐNG PHẢI thoát mã `1` liệt kê đúng dòng lỗi
  - Logic cốt lõi:
    1. Khởi tạo `utf8_io`, bộ ghi log `_log()` bật mặc định có timestamp ra stderr (`TDQ_LOG=0` tắt), và hàm `extract_symbols(path)` dùng `ast.parse` cho `.py`, fallback regex cho `.rs`/`.ts`/`.tsx`/`.js`/`.jsx` kèm `anchor_confidence="LOW"`.
    2. Cài `parse_spec_contracts(spec_path)` trích mục `§3c` (tên file/hàm/chữ ký); fail-closed (`exit 1`) khi `--from-spec` không tìm thấy hợp đồng nào.
    3. Cài `emit_cards(plan_path, refs, spec_path)` gọi `tdq_team.doc_plan()`, tổng hợp neo & chữ ký (từ file thật, `--refs`, và `--from-spec` cho file tạo mới) để sinh khung Per-Task Mini-Spec gọn (`<= 25` dòng/task).
    4. Cài `verify_plan(plan_path, root_dir)` xác minh mọi file trong `Chạm:` (trừ task tạo mới `Write`) & symbol trong `Neo`/`Tham chiếu:` tồn tại trên đĩa, kiểm cú pháp `assert` Python bằng `ast.parse` và chặn `ANTI-2` (`assert True`, `1 == 1`, `len(...) >= 0`); cài `check_wave(plan_path, root_dir)` kiểm tính nhất quán `CONTRACT-DELTA:`.
  - Ca góc hiểm & Assert:
    - Ca hiểm: File tạo mới Greenfield thiếu `--from-spec` (fail-closed exit `1`), file `.rs`/`.ts` không có cache LSP (gắn `ANCHOR_CONFIDENCE: LOW`), biểu thức `assert` bị lỗi cú pháp hoặc hằng luôn đúng, chạy với `TDQ_LOG=0` không in dòng log stderr.
    - Tiêu chí: `assert rc == 1 and "§3c" in err`, `assert "ANCHOR_CONFIDENCE: HIGH" in out`, `assert verify_rc == 1 and any("symbol" in m.lower() for m in errs)`, `assert stderr_silent == ""`

- [x] **T1.3** (e22m) Nâng cấp `scripts/doc_lint.py` với `R15` V2+ (Per-Task Mini-Spec, `R15-Full`/`R15-Compact`, Banned-Placeholder, `ANTI-2` 100% task/DoD, `R15_MOC`, `--pair`, `R12`, `SKILL_LINE_LIMITS`) — Test: `py -3 -X utf8 -m unittest tests/test_plan_v2_linter.py tests/test_doc_lint.py -v`
  - Req: `§2 #3, §3c, §6 Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` kết quả xanh cho toàn bộ `236` plan cũ trước mốc `2026-11-20`, `evals/tuan-thu/` và các luật `R1`..`R14` hiện hành
  - Chạm: `scripts/doc_lint.py`, `tests/test_plan_v2_linter.py`
  - Cần: `T1.1`
  - Giao tiếp: Consumes: `Doc` (`doc.lines`, `doc.in_fence`, `doc.path`) | Produces: `R15_MOC = "2026-11-20"`, `SKILL_LINE_LIMITS["tdq-plan"] = 132`, `r15_loi(doc, check_dir: bool = True) -> list[str]`
  - Neo & Công cụ: `Edit` trên `scripts/doc_lint.py` tại `SKILL_LINE_LIMITS` (`L63`), `rule_r15()` (`L526-568`), `pair()` (`L602-645`), `_r12_van_xuoi()` (`L663-671`); `Write` cho `tests/test_plan_v2_linter.py`
  - Trước → Sau: Hiện `rule_r15` dài `42` dòng chỉ kiểm `1` từ khóa `logic`, bỏ qua `QCn.x`/`quick`/non-code `ANTI-2`, không bỏ qua `doc.in_fence[i]`, không chạy ở `pair()`, `_r12_van_xuoi` đánh lỗi bước `\d+\.\s`, và trần `tdq-plan` là `121` → Sau: tách `r15_loi(doc, check_dir=True)` gọi từ cả `rule_r15` & `pair()`, áp chuẩn V2+ từ mốc `R15_MOC = "2026-11-20"` (bảo toàn plan cũ), kiểm đủ `R15-Full` (Per-Task Mini-Spec + trần `<= 35` dòng/task + `Ownership Map`), `R15-Compact` (`QCn.x`/`quick`/Sweep), `EXT_CAU_HINH`, Banned-Placeholder, `ANTI-2` 100% task/DoD, miễn `\d+\.\s` trong `_r12_van_xuoi` và nâng `SKILL_LINE_LIMITS["tdq-plan"] = 132`
  - Tiêu chí chấp nhận (EARS): KHI lint plan có ngày `>= 2026-11-20` (hoặc gọi `--pair`), HỆ THỐNG PHẢI báo lỗi `R15` nếu task code thiếu trường Per-Task Mini-Spec (`Req:`, `Ngoài phạm vi:`/`GIỮ NGUYÊN`, `EARS`/`Tiêu chí chấp nhận`, `Trước → Sau`, `Neo`, `Logic`, `Assert`), vượt `35` dòng, chứa placeholder cấm (`TBD`/`TODO`/`handle edge cases`/`...`) hoặc chứa `ANTI-2` (kể cả non-code/DoD); KHI lint plan ngày `< 2026-11-20`, HỆ THỐNG PHẢI giữ tương thích cũ
  - Logic cốt lõi:
    1. Đặt `SKILL_LINE_LIMITS["tdq-plan"] = 132`, khai hằng `R15_MOC = "2026-11-20"`, `EXT_CAU_HINH`, danh sách `BANNED_PLACEHOLDERS` và biểu thức `ANTI2_PATTERNS` (`assert True`, `assert 1 == 1`, `len(...) >= 0`, `os.path.exists`/`Test-Path` trần).
    2. Tách helper `_slug_sau_moc(path, moc)` và viết `r15_loi(doc, check_dir=True)` bỏ qua mọi dòng có `doc.in_fence[i]`, bắt cả `- [ ] **Tx.y**`, `**T1**`, `**QCn.x**`, đọc `Chạm:` cả đơn dòng lẫn sub-bullet nhiều dòng.
    3. Phân nhánh kiểm tra cho plan `>= R15_MOC`: `ANTI-2` & Banned-Placeholder trên 100% task/QC/DoD; `R15-Compact` (`5` trường) cho `QCn.x`, `# QUICK —` code và `Uniform Mechanical Sweep` (`<= 6` file); `R15-Full` (đủ Per-Task Mini-Spec + `<= 35` dòng/task) cho task code `full`; kiểm `Ownership Map` khi có `>= 2` task code chia sẻ hợp đồng.
    4. Gọi `r15_loi(Doc(plan_path), check_dir=False)` trong `pair()` và miễn dòng bắt đầu bằng `re.match(r"^\d+\.\s", text.strip())` trong `_r12_van_xuoi()`.
  - Ca góc hiểm & Assert:
    - Ca hiểm: Từ `TBD` nằm trong code fence (không báo lỗi giả), plan cũ ngày `2026-11-15` (giữ hành vi cũ), task Sweep `<= 6` file vs `7` file (vượt ngưỡng phải báo lỗi), task DoD non-code dùng `assert True` (vẫn bị chặn `ANTI-2`).
    - Tiêu chí: `assert any("[R15]" in e and "ANTI-2" in e for e in errs)`, `assert any("TBD" in e or "placeholder" in e.lower() for e in errs_ph)`, `assert errs_old == []`, `assert _r12_van_xuoi("  1. Initialize state and parse input args") is None`

- [>] **T1.4** (e14m) Vá `scripts/tdq_state.py` (cổng tiền-duyệt R15 & đọc `Chạm:` nhiều dòng) và đồng bộ `RE_TICK` trong `scripts/tdq_eval.py` — Test: `py -3 -X utf8 -m unittest tests/test_state_plan_v2_gate.py tests/test_quick_qc.py tests/test_hooks_dual_protocol.py -v`
  - Req: `§2 #4, §3c, §6 Q3` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ chữ ký CLI state hiện hành và fail-open sạch khi lane `quick` không tạo tệp plan trên đĩa
  - Chạm: `scripts/tdq_state.py`, `scripts/tdq_eval.py`, `tests/test_state_plan_v2_gate.py`
  - Cần: `T1.3`
  - Giao tiếp: Consumes: `doc_lint.Doc`, `doc_lint.r15_loi` | Produces: `_extract_plan_targets(cwd, state)` (đa dòng + skip fence), `_kiem_r15_plan(cwd, plan_path, lane)`, `RE_TICK` hỗ trợ `[>]`/`T2.1a`/`QC1.1`
  - Neo & Công cụ: `Edit` trên `scripts/tdq_state.py` tại `_cli_approve()` (`L2392-2395`), `_extract_plan_targets()` (`L2471-2495`), khối `cmd == "set"` (`L3075-3095`); `Edit` trên `scripts/tdq_eval.py` tại `RE_TICK` (`L197`); `Write` cho `tests/test_state_plan_v2_gate.py`
  - Trước → Sau: Hiện `_extract_plan_targets()` chỉ đọc `Chạm:` đơn dòng, `set plan_file` và `approve plan`/`approve quick` chưa chạy `r15_loi`, và `RE_TICK` bỏ lọt `[>]`, `T2.1a`, `QC1.1` → Sau: `_extract_plan_targets()` đọc đủ `Chạm:` nhiều dòng và bỏ qua code fence; `set plan_file=...` chặn ngay khi `r15_loi` có lỗi; `approve plan` & `approve quick` chạy kiểm sạch (fail-open nếu `quick` chưa có file trên đĩa); `RE_TICK` bắt đủ `[ ~x>]` và `T1`/`T1.1`/`T2.1a`/`QC1.1`
  - Tiêu chí chấp nhận (EARS): KHI chạy `tdq_state.py set plan_file=<plan_loi.md>` cho plan từ `2026-11-20` vi phạm `R15`, HỆ THỐNG PHẢI từ chối (exit `1`) trước khi trình duyệt; KHI chạy `approve quick` không có file plan trên đĩa, HỆ THỐNG PHẢI fail-open trả exit `0`
  - Logic cốt lõi:
    1. Nâng `_extract_plan_targets()` theo dõi `in_fence` và `in_cham` để thu mọi đường dẫn trong backtick thuộc dòng `Chạm:` và các sub-bullet thụt ngay dưới nó.
    2. Thêm helper `_kiem_r15_plan(cwd, plan_path, lane)` nạp `doc_lint.r15_loi(Doc(path), check_dir=False)`: nếu `lane == "quick"` và không tồn tại file thì return (fail-open); nếu có lỗi thì gọi `_fail(...)` liệt kê rõ dòng lỗi.
    3. Gọi `_kiem_r15_plan` tại nhánh `key == "plan_file"` trong `cmd == "set"` (khi file tồn tại trên đĩa) và tại `_cli_approve()` cho `target in ("plan", "quick")`.
    4. Cập nhật `RE_TICK = re.compile(r"\[([ ~x>])\]\s*\*\*((?:T\d+(?:\.\d+[a-z]?)?|QC\d+(?:\.\d+)?))\*\*")` tại `scripts/tdq_eval.py:197`.
  - Ca góc hiểm & Assert:
    - Ca hiểm: `set plan_file=null` (xóa khóa, không báo lỗi), `approve quick` với repo tối giản không tạo file `docs/tdq/plan/<slug>.md`, `Chạm:` chứa dòng fence xen kẽ, `RE_TICK.search("- [>] **QC1.1** fix")`.
    - Tiêu chí: `assert proc_set_bad.returncode != 0 and "R15" in proc_set_bad.stderr`, `assert proc_quick_nofile.returncode == 0`, `assert RE_TICK.search("- [>] **T2.1a** x").group(2) == "T2.1a"`

**Xong P1 khi**: Toàn bộ `T1.1`..`T1.4` tick `[x]` và tất cả unit test Chặng 1 + test cũ liên quan (`test_team_mode`, `test_doc_lint`, `test_quick_qc`, `test_hooks_dual_protocol`) đều xanh.

## P2 — Chặng 2: Bộ Skill `tdq-plan` V2+, Tài liệu Hỗ trợ & Agents

- [ ] **T2.1** (e18m) Tạo `planner-rules.md` (`<= 30` luật) & `plan-examples.md` (`3` cặp Contrastive Few-Shot `<= 1,300` tok) và nâng cấp bộ `skills/tdq-plan/` — Test: `py -3 -X utf8 scripts/doc_lint.py skills/tdq-plan && py -3 -X utf8 scripts/i18n_check.py skills/tdq-plan && py -3 -X utf8 -m unittest tests/test_reference_mot_tang.py -v`
  - Req: `§2 #5, §6 Q4` · Ngoài phạm vi: Không vượt `132` dòng cho `SKILL.md`, không vượt `235` dòng và `3,500` token (`anthropic-tokenizer`) cho mỗi file ref, không dùng đường dẫn `scripts/`/`hooks/` trong ví dụ mẫu (dùng `src/foo.py`)
  - Chạm: `skills/tdq-plan/SKILL.md`, `skills/tdq-plan/references/plan-template.md`, `skills/tdq-plan/references/plan-template-huong-dan.md`, `skills/tdq-plan/references/planner-rules.md`, `skills/tdq-plan/references/plan-examples.md`
  - Cần: `T1.2, T1.3`
  - Giao tiếp: Consumes: CLI `tdq_plan_scaffold.py`, `doc_lint.py --pair` | Produces: `5` file chuẩn Tier-1 dưới `skills/tdq-plan/` có `<!-- muc-luc-dong: -->` và `i18n-allow` hợp lệ
  - Neo & Công cụ: `Edit` trên `SKILL.md`, `plan-template.md`, `plan-template-huong-dan.md`; `Write` cho `planner-rules.md` và `plan-examples.md`
  - Trước → Sau: Hiện `tdq-plan/SKILL.md` (`121/121` dòng) chưa nhắc Two-Pass, Scaffolder hay luật/ví dụ Planner; `plan-template.md` chưa có `Global Constraints`, `Ownership Map` và Per-Task Mini-Spec (`Req:`, `Ngoài phạm vi:`, `Giao tiếp:`, `EARS`); `plan-template-huong-dan.md` trộn tiếng Việt không có `i18n-allow` → Sau: `SKILL.md` (`<= 132` dòng) trỏ thẳng sang `planner-rules.md` và `plan-examples.md` (Tier-1), hướng dẫn Two-Pass + `--emit-cards` + `--verify-plan`; `plan-template.md` chuẩn hóa khuôn Per-Task Mini-Spec (`R15-Full`/`R15-Compact`/Sweep) + `Global Constraints` & `Ownership Map`; `planner-rules.md` chốt `<= 30` luật bất biến + `5` câu Self-Review; `plan-examples.md` (`<= 1,300` tok) chứa `3` cặp `70% ĐẠT / 30% HỎNG + [Lý do sai]` (Greenfield, Brownfield Refactor, Uniform Sweep)
  - Tiêu chí chấp nhận (EARS): KHI chạy `doc_lint.py`, `i18n_check.py`, `doc_index.py` và kiểm tra liên kết một tầng trên `skills/tdq-plan/`, HỆ THỐNG PHẢI trả `0` vi phạm và mọi file dưới trần `3,500` token (`plan-examples.md <= 1,300` token)
  - Logic cốt lõi:
    1. Viết `planner-rules.md` bằng tiếng Anh (`<= 140` dòng, `<= 30` chỉ thị đánh số rõ thuộc `5` nhóm: Ground Before Drafting, Decomposition Thresholds Split/Merge/Sweep, Contract-First & Ownership Map, Zero-Ambiguity Banlist, Two-Pass + `5`-Question Semantic Self-Review).
    2. Viết `plan-examples.md` (`<= 125` dòng, `<= 1,300` token) gồm `3` cặp Contrastive Few-Shot (Greenfield Feature, Brownfield Refactor có `GIỮ NGUYÊN` + LSP callers, Uniform Mechanical Sweep `<= 6` file), tỷ lệ ~70% Positive / ~30% Negative + `[Why it fails]`, mọi đường dẫn ví dụ dùng `src/foo.py` và `spec_cases/test_foo.py`.
    3. Cập nhật `plan-template.md` (`<= 150` dòng, `<= 3,350` tok) bổ sung `Global Constraints`, `Ownership Map` và khuôn Per-Task Mini-Spec dùng `` `Edit` ``/`` `Write` ``; cập nhật `plan-template-huong-dan.md` sang tiếng Anh sạch + Adaptive 3-Tier; cập nhật `SKILL.md` (`<= 132` dòng) trỏ trực tiếp cả `2` sibling mới và bước `--emit-cards` / `--verify-plan`.
    4. Chạy `doc_index.py` chèn `<!-- muc-luc-dong: -->` cho các file `>= 90` dòng và đo thực tế token bằng `token_budget.py`.
  - Ca góc hiểm & Assert:
    - Ca hiểm: Liên kết 2 tầng (bị `test_reference_mot_tang.py` chặn), viết chuỗi `scripts/` trong ví dụ (bị `build_portable.py:346` viết lại), quên `<!-- i18n-allow -->` quanh khối mẫu tiếng Việt.
    - Tiêu chí: `assert len(skill_lines) <= 132`, `assert tok_examples <= 1300`, `assert "scripts/" not in open("skills/tdq-plan/references/plan-examples.md").read()`

- [ ] **T2.2** (e16m) Tách `qc-vong-fix.md` và đồng bộ `qc.md`, `team-mode.md`, `team-mode-tra-cuu.md`, `spec-template-huong-dan.md`, `quick-lane-mini.md` dưới trần `R13` — Test: `py -3 -X utf8 scripts/doc_lint.py skills/tdq-build skills/tdq-spec skills/tdq-intake && py -3 -X utf8 scripts/i18n_check.py skills/tdq-build skills/tdq-spec skills/tdq-intake && py -3 -X utf8 -m unittest tests/test_reference_mot_tang.py tests/test_team_mode.py -v`
  - Req: `§2 #6, §6 Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mục bắt buộc của `test_team_mode.py` (`## when it applies`, `## what to do`, `## self-check`, đủ `LY_DO_GIU`, `>= 4` cặp `RIGHT:`/`WRONG:`, đủ `7` `TRUONG_PROMPT`) và trần `<= 3,500` token mỗi file
  - Chạm: `skills/tdq-spec/references/spec-template-huong-dan.md`, `skills/tdq-intake/references/quick-lane-mini.md`, `skills/tdq-build/SKILL.md`, `skills/tdq-build/references/qc.md`, `skills/tdq-build/references/qc-vong-fix.md`, `skills/tdq-build/references/team-mode.md`, `skills/tdq-build/references/team-mode-tra-cuu.md`
  - Cần: `T1.1, T1.3`
  - Giao tiếp: Consumes: `tdq_team.py packet`, `R15-Compact` | Produces: `qc-vong-fix.md` (Tier-1 sibling liên kết từ `tdq-build/SKILL.md`), tài liệu hỗ trợ đồng bộ dưới `3,350` token/file
  - Neo & Công cụ: `Write` cho `skills/tdq-build/references/qc-vong-fix.md`; `Edit` trên `6` file còn lại sau khi đọc dải dòng đích
  - Trước → Sau: Hiện `qc.md` (`3,496/3,500`), `spec-template.md` (`3,486/3,500`) và `team-mode.md` (`3,390/3,500`) gần chạm trần; `quick-lane-mini.md` chưa có `R15-Compact` & ngưỡng `> 4` file nguồn; `team-mode` chưa trỏ `tdq_team.py packet` → Sau: chuyển hướng dẫn vòng sửa `QCn.x` (kèm `R15-Compact`) từ `qc.md` sang `qc-vong-fix.md` (trỏ thẳng từ `tdq-build/SKILL.md`, giải phóng dư biên token cho `qc.md`), thêm hướng dẫn `tdq_team.py packet` vào `team-mode-tra-cuu.md` (trỏ từ `team-mode.md`), thêm hướng dẫn bảng hợp đồng `§3c` (cho Greenfield `--from-spec`) vào `spec-template-huong-dan.md`, và nâng `quick-lane-mini.md` hỗ trợ `R15-Compact` + ngưỡng `> 4` file nguồn nâng lên `full`
  - Tiêu chí chấp nhận (EARS): KHI đo `token_budget.py` và chạy `test_reference_mot_tang.py`, `test_team_mode.py`, `i18n_check.py`, HỆ THỐNG PHẢI xác nhận `0` file vượt `3,500` token hay `235` dòng, `tdq-build/SKILL.md <= 174` dòng và mọi liên kết Tier-1 hợp lệ
  - Logic cốt lõi:
    1. Tạo `skills/tdq-build/references/qc-vong-fix.md` (hướng dẫn lập task sửa `QCn.x` theo `R15-Compact`, nhãn `Sinh ra:`, và Uniform Sweep); rút phần chi tiết vòng fix khỏi `qc.md` và trỏ `qc-vong-fix.md` từ `tdq-build/SKILL.md` (giữ `<= 174` dòng).
    2. Cập nhật `team-mode-tra-cuu.md` với hướng dẫn gọi `tdq_team.py packet <task_id>` + Symbol-Span + `CONTRACT-DELTA:` và thêm dòng con trỏ ngắn trong `team-mode.md` (giữ nguyên toàn bộ mục kiểm của `test_team_mode.py`).
    3. Thêm mục hợp đồng chữ ký `§3c` (để phục vụ `--from-spec`) vào `spec-template-huong-dan.md` (không đụng `spec-template.md` đang `3,486/3,500`).
    4. Cập nhật `quick-lane-mini.md` bổ sung khuôn `R15-Compact` (`5` trường) cho quick task sửa mã nguồn (trần `<= 80` dòng cho quick code, nâng sang `full` khi sửa gốc `> 4` file nguồn).
  - Ca góc hiểm & Assert:
    - Ca hiểm: `tdq-build/SKILL.md` đang `171/174` dòng (chỉ thêm `<= 2` dòng trỏ `qc-vong-fix.md` để không chạm trần `174`), `test_team_mode.py` kiểm `RIGHT:`/`WRONG:` và `TRUONG_PROMPT`.
    - Tiêu chí: `assert len(build_skill_lines) <= 174`, `assert max(tok_map.values()) <= 3500`, `assert "packet" in open("skills/tdq-build/references/team-mode-tra-cuu.md").read()`

- [ ] **T2.3** (e10m) Tối giản `agents/tdq-implementer.md` (`<= 42` dòng, `<= 6` luật + circuit breaker `2` retry) và nâng checklist `agents/tdq-reviewer.md` — Test: `py -3 -X utf8 -m unittest tests/test_agent_frontmatter.py tests/test_team_mode.py -v`
  - Req: `§2 #7, §6 Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` frontmatter Claude (`model: inherit`, `effort: high`), đủ `7` trường `TRUONG_PROMPT`, chuỗi `1,500 characters` và câu cấm dán output thô (`pasting ... is banned`)
  - Chạm: `agents/tdq-implementer.md`, `agents/tdq-reviewer.md`
  - Cần: `T1.1`
  - Giao tiếp: Consumes: `tdq_team.py packet` | Produces: `agents/tdq-implementer.md` (`<= 42` dòng, `<= 6` luật + circuit breaker `<= 2` retries) và `agents/tdq-reviewer.md` (bổ sung mục đối chiếu `spec §3c ↔ plan`, `Ownership Map` & Per-Task Mini-Spec)
  - Neo & Công cụ: `Edit` trên `agents/tdq-implementer.md` (`L1-70`) và `agents/tdq-reviewer.md` (`L11-27`)
  - Trước → Sau: Hiện `agents/tdq-implementer.md` dài `70` dòng với `~20` gạch đầu dòng luật gây quá tải nhận thức cho `Flash` và không có ngưỡng dừng retry → Sau: tinh gọn còn `<= 42` dòng với đúng `6` luật cốt lõi (worktree/VÙNG FILE, Red→Green không placeholder/`ANTI-1`/`ANTI-2`, giữ log mặc định & Surgical Changes, tick `[~]`/`[x]` đúng chỗ, Circuit Breaker dừng báo blocker sau tối đa `2` lần retry không tiến triển, digest `<= 1,500 characters` và `pasting raw tool output is banned`); `agents/tdq-reviewer.md` thêm tiêu chí soi `spec §3c ↔ plan`, `Ownership Map` và kết quả `--verify-plan`
  - Tiêu chí chấp nhận (EARS): KHI chạy `test_agent_frontmatter.py` và `test_team_mode.py`, HỆ THỐNG PHẢI đạt `0` lỗi, `agents/tdq-implementer.md <= 42` dòng và chứa rõ quy tắc circuit breaker `<= 2` retries
  - Logic cốt lõi:
    1. Gọt phần thân `agents/tdq-implementer.md` giữ nguyên frontmatter, khối `7` `TRUONG_PROMPT` và khối Return format; gom toàn bộ chỉ thị thành đúng `6` luật đánh số ngắn kèm quy tắc circuit breaker `2` lần thử.
    2. Cập nhật `agents/tdq-reviewer.md` bổ sung hạng mục `6. Contract & Per-Task Spec Parity` (đối chiếu `1–1` `spec §3c ↔ plan`, `Ownership Map`, `Req:`/`Ngoài phạm vi:`/`EARS` và kiểm định xác định `--verify-plan`).
    3. Kiểm tra bằng `i18n_check.py`, `test_agent_frontmatter.py` và `test_team_mode.py`.
  - Ca góc hiểm & Assert:
    - Ca hiểm: Vô tình xóa chữ `1,500 characters` hoặc mẫu regex `pasting ... is banned` hoặc thiếu 1 trường trong `TRUONG_PROMPT`.
    - Tiêu chí: `assert len(open("agents/tdq-implementer.md").read().splitlines()) <= 42`, `assert "2" in impl_text and "retry" in impl_text.lower()`

**Xong P2 khi**: Toàn bộ `T2.1`..`T2.3` tick `[x]`, `doc_lint.py skills` + `i18n_check.py` + `test_reference_mot_tang.py` + `test_agent_frontmatter.py` + `test_team_mode.py` đều xanh.

## P3 — Chặng 3: AGY Patch, Đóng gói Bundle & Nghiệm thu E2E

- [ ] **T3.1** (e14m) Cập nhật `SUBAGENT_DISPATCH_GATE_PY`, khóa `token-budget.json`, tái dựng `plugins/tdq-workflow-agy/` và kiểm `validate --strict` + `build_portable.py --kiem` — Test: `py -3 -X utf8 scripts/token_budget.py --kiem && py -3 -X utf8 -m unittest tests/test_token_budget.py tests/test_rust_dispatch_parity.py tests/test_agy_plugin_validate.py tests/test_build_portable.py -v`
  - Req: `§2 #8, §6 Q4, §6 Q5` · Ngoài phạm vi: KHÔNG chạy `tools/install_agy_plugin.py` và KHÔNG chỉnh sửa bất kỳ tệp nào trong `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` (`3a`)
  - Chạm: `tools/patches/agy_hooks.py`, `docs/tdq/token-budget.json`
  - Sinh ra: `plugins/tdq-workflow-agy/hooks/scripts/subagent_dispatch_gate.py`, `plugins/tdq-workflow-agy/skills/**`, `plugins/tdq-workflow-agy/agents/**`, `plugins/tdq-workflow-agy/scripts/**`, `plugins/tdq-workflow-agy/manifest.json`
  - Cần: `T2.1, T2.2, T2.3`
  - Giao tiếp: Consumes: `skills/**`, `agents/**`, `scripts/**` | Produces: `docs/tdq/token-budget.json` (đo bằng `anthropic-tokenizer`), `plugins/tdq-workflow-agy/` sạch `agy.EXE plugin validate --strict`
  - Neo & Công cụ: `Edit` trên `tools/patches/agy_hooks.py` tại `SUBAGENT_DISPATCH_GATE_PY` (`L1325-1377`); chạy `scripts/token_budget.py --khoa` và `tools/build_agy_plugin.py`
  - Trước → Sau: Hiện `SUBAGENT_DISPATCH_GATE_PY` chỉ nhắc `5` trường cơ bản và chưa nhắc dùng `tdq_team.py packet`; `token-budget.json` và `plugins/tdq-workflow-agy/` chưa phản ánh các file mới (`tdq_plan_scaffold.py`, `planner-rules.md`, `plan-examples.md`, `qc-vong-fix.md`) → Sau: `SUBAGENT_DISPATCH_GATE_PY` giữ nguyên `REQUIRED_IMPL_FIELDS` và nhánh `Workspace=inherit` để bảo toàn 100% Parity, chỉ thêm gợi ý `remind` dùng `tdq_team.py packet` khi prompt thiếu bối cảnh neo; `token-budget.json` được khóa lại dưới `3,500` tok; `plugins/tdq-workflow-agy/` tái sinh đồng bộ và vượt `agy.EXE plugin validate --strict` với `findings: []`
  - Tiêu chí chấp nhận (EARS): KHI chạy `tools/build_agy_plugin.py` và `agy.EXE plugin validate --strict`, HỆ THỐNG PHẢI trả `0` phát hiện lỗi, `token_budget.py --kiem` trả exit `0`, và `test_rust_dispatch_parity.py` xanh 100%
  - Logic cốt lõi:
    1. Bổ sung nhắc nhở nhẹ mức `remind` trong `SUBAGENT_DISPATCH_GATE_PY` (`tools/patches/agy_hooks.py:1364-1370`) chỉ khi thiếu `REQUIRED_IMPL_FIELDS` (không đổi hành vi `Workspace=inherit` hay payload khi đủ trường -> giữ 100% Parity Rust-Python).
    2. Chạy `py -3 -X utf8 scripts/doc_index.py --sua` (nếu cần) và `py -3 -X utf8 scripts/token_budget.py --khoa` kiểm xác thực trên `anthropic-tokenizer` mọi file `<= 3,500` tok.
    3. Chạy `py -3 -X utf8 tools/build_agy_plugin.py` đồng bộ trọn gói vào `plugins/tdq-workflow-agy/` (kèm `tdq_plan_scaffold.py`, `planner-rules.md`, `plan-examples.md`, `qc-vong-fix.md`).
    4. Chạy `agy.EXE plugin validate --strict plugins/tdq-workflow-agy` và `py -3 -X utf8 scripts/build_portable.py --kiem` xác nhận `0` lỗi.
  - Ca góc hiểm & Assert:
    - Ca hiểm: Môi trường thiếu `anthropic-tokenizer` ở venv mặc định (chạy bằng interpreter có cài hoặc kiểm `token_budget.py` đúng nguồn), test parity nhạy cảm với chuỗi `remind` mới khi đủ `5` trường.
    - Tiêu chí: `assert validate_rc == 0`, `assert parity_rc == 0`, `assert portable_rc == 0`

- [ ] **T3.2** (e16m) Xây dựng và chạy kiểm thử E2E `tests/test_plan_v2_e2e.py` trên `3` kịch bản (`Two-Pass + --emit-cards + packet + --verify-plan + R15 + state gate`) — Test: `py -3 -X utf8 -m unittest tests/test_plan_v2_e2e.py -v`
  - Req: `§2 #9, §4, §6 Q6` · Ngoài phạm vi: Không gọi API LLM ngoài; toàn bộ E2E chạy cô lập trên thư mục tạm (`tempfile.TemporaryDirectory` + `TDQ_PROJECT_DIR`)
  - Chạm: `tests/test_plan_v2_e2e.py`
  - Cần: `T1.4, T3.1`
  - Giao tiếp: Consumes: `tdq_plan_scaffold.py`, `tdq_team.py`, `doc_lint.py`, `tdq_state.py` | Produces: bộ kiểm thử E2E `3` kịch bản + kiểm chứng dịch vụ log `TDQ_LOG`
  - Neo & Công cụ: `Write` tạo mới `tests/test_plan_v2_e2e.py`
  - Trước → Sau: Hiện chưa có bài kiểm tra liên thông toàn bộ chuỗi `Two-Pass -> --emit-cards -> --verify-plan -> doc_lint --pair -> tdq_state set/approve -> tdq_team packet` → Sau: có `tests/test_plan_v2_e2e.py` chứng minh trọn luồng chạy xanh trên đủ `3` kịch bản đại diện (Greenfield với `--from-spec`, Multi-file Refactor kèm `Ownership Map` & `GIỮ NGUYÊN`, Quick Code + Uniform Mechanical Sweep `<= 6` file) cùng kiểm chứng `TDQ_LOG=1` vs `TDQ_LOG=0`
  - Tiêu chí chấp nhận (EARS): KHI chạy `tests/test_plan_v2_e2e.py`, HỆ THỐNG PHẢI chứng minh cả `3` kịch bản hoàn tất trọn vòng với exit `0`, kịch bản hỏng (thiếu Per-Task Mini-Spec / chứa `TBD` / `assert True`) bị chặn exit `1`, và `TDQ_LOG` bật mặc định / tắt qua `TDQ_LOG=0`
  - Logic cốt lõi:
    1. Dựng fixture repo tạm (có `docs/kien-truc.md`, `docs/tdq/spec/...`, file mẫu `.py` & `.rs`) dùng `TDQ_PROJECT_DIR` cô lập.
    2. Kịch bản 1 (Greenfield): Spec `§3c` → Pass 1 plan → `--emit-cards --from-spec` → điền Per-Task Mini-Spec → `--verify-plan` → `doc_lint --pair` → `set plan_file` → `approve plan` → `tdq_team.py packet` xanh.
    3. Kịch bản 2 (Multi-file Refactor + Ownership Map + Stale Guard): Sửa `Vị trí neo:` kiểm `plan_assignment_sha` không đổi, kiểm `packet` trích đúng Symbol-Span và `Tham chiếu:` chỉ lấy `1` dòng signature.
    4. Kịch bản 3 (Quick Code + Uniform Sweep + Negative Cases + `TDQ_LOG`): Kiểm `R15-Compact` + Sweep `<= 6` file pass, chèn `TBD` / `assert True` bị chặn, và kiểm stderr có timestamp khi mặc định / rỗng khi `TDQ_LOG=0`.
  - Ca góc hiểm & Assert:
    - Ca hiểm: Rò biến môi trường `TDQ_PROJECT_DIR` ra repo thật (bắt buộc truyền qua `env` cục bộ của `subprocess`), xung đột đường dẫn Windows `\` vs `/`.
    - Tiêu chí: `assert e2e_greenfield == 0`, `assert e2e_refactor_sha_stable`, `assert e2e_bad_plan_rc == 1`, `assert len(log_on_stderr) > 0 and log_off_stderr == ""`

**Xong P3 khi**: `T3.1` và `T3.2` tick `[x]`, `plugins/tdq-workflow-agy/` vượt `validate --strict`, `token_budget.py --kiem` xanh và E2E `3` kịch bản xanh 100%.

## P4 — Log & test bắt buộc

- [ ] **T4.1** (e10m) Xác minh dịch vụ log `TDQ_LOG` mặc định và chạy bộ kiểm thử đơn vị hợp nhất cho mọi thành phần mới/sửa bằng một lệnh — Test: `py -3 -X utf8 -m unittest tests/test_team_packet_v2.py tests/test_plan_scaffold.py tests/test_plan_v2_linter.py tests/test_state_plan_v2_gate.py tests/test_plan_v2_e2e.py -v`
  - Req: `§4, §6 Q1..Q6` · Ngoài phạm vi: Không thay đổi mã nguồn sản phẩm ở bước tổng kiểm này (nếu đỏ thì sửa ở task tương ứng)
  - Chạm: `tests/test_plan_v2_e2e.py`
  - Cần: `T3.2`
  - Giao tiếp: Consumes: toàn bộ `5` mô-đun test mới | Produces: kết quả `0 failed` của lệnh test hợp nhất + bằng chứng `TDQ_LOG` bật mặc định và tắt qua `TDQ_LOG=0`
  - Neo & Công cụ: Chạy lệnh `unittest` và `tdq_test.py vung-cham`
  - Trước → Sau: Kiểm chứng tập trung trước khi sang pha QC `full` (`tdq_test.py tron-bo`)
  - Tiêu chí chấp nhận (EARS): KHI chạy một lệnh `unittest` qua `5` mô-đun test mới và `tdq_test.py vung-cham`, HỆ THỐNG PHẢI trả exit `0` với `0` test lỗi
  - Logic cốt lõi:
    1. Chạy một lệnh `unittest` gồm cả `5` mô-đun test mới của `M1`..`M6`.
    2. Chạy `py -3 -X utf8 scripts/tdq_test.py vung-cham` kiểm hồi quy toàn bộ bán kính chạm.
    3. Xác nhận `TDQ_LOG` hoạt động đúng trên cả `tdq_plan_scaffold.py` và `tdq_team.py packet`.
  - Ca góc hiểm & Assert:
    - Ca hiểm: Một test cũ chưa thuộc `5` mô-đun mới bị ảnh hưởng dây chuyền (bắt sớm bằng `tdq_test.py vung-cham`).
    - Tiêu chí: `assert unittest_rc == 0 and vung_cham_rc == 0`

## Cụm song song

- **Đợt 1 (tuần tự nền hợp đồng):** `T1.1` (`tdq_team.py`, `tdq_ten_lenh.py`) — đặt làm chủ hợp đồng `Task`/`doc_plan`/`BANG_DOI_TEN`.
- **Đợt 2 (song song `2` nhánh không trùng file):** `T1.2` (`tdq_plan_scaffold.py`) || `T1.3` (`doc_lint.py`).
- **Đợt 3 (song song `2` nhánh):** `T1.4` (`tdq_state.py`, `tdq_eval.py`) || `T2.3` (`agents/tdq-implementer.md`, `agents/tdq-reviewer.md`) — lưu ý `T2.1`/`T2.2` chạm `skills/` (file luật, leader giữ).
- **Đợt 4 (leader giữ — `file-luat`):** `T2.1` (`skills/tdq-plan/**`) và `T2.2` (`skills/tdq-spec|intake|build/**`).
- **Đợt 5 (đóng gói & nghiệm thu tuần tự):** `T3.1` → `T3.2` → `T4.1`.

## Luật file nóng (một file, nhiều task chạm)

- `tests/test_plan_v2_e2e.py` xuất hiện ở `T3.2` (tạo mới) và `T4.1` (chỉ chạy kiểm chứng, phụ thuộc `Cần: T3.2`, không chạy song song).
- Toàn bộ `18` tệp mã nguồn và luật sản phẩm khác (`scripts/`, `skills/`, `agents/`, `tools/patches/`) đều có **đúng 1 chủ ghi duy nhất** (`0` `HOT FILE` trên mã sản phẩm).

## Definition of Done

Trỏ về §6 của spec (`muc_qc=full`). Mỗi dòng một ô tick kiểm được bằng một lệnh:

- [ ] Q1 Cô lập `Chạm:`/`Tham chiếu:`/`Sinh ra:`, ổn định `plan_assignment_sha` và `tdq_team.py packet` đạt chuẩn — `py -3 -X utf8 -m unittest tests/test_team_packet_v2.py tests/test_team_mode.py tests/test_team_chong_conflict.py -v`
- [ ] Q2 `scripts/tdq_plan_scaffold.py` thuần stdlib có `TDQ_LOG` đạt đủ `--files`/`--refs`/`--from-spec`/`--emit-cards`/`--verify-plan`/`--check-wave` — `py -3 -X utf8 -m unittest tests/test_plan_scaffold.py -v`
- [ ] Q3 `doc_lint.py` (`R15-Full`/`R15-Compact`, Per-Task Spec, Banned-Placeholder, `ANTI-2`, `R15_MOC`) & cổng `tdq_state.py`/`tdq_eval.py` xanh, không làm đỏ `236` plan cũ — `py -3 -X utf8 -m unittest tests/test_plan_v2_linter.py tests/test_state_plan_v2_gate.py tests/test_doc_lint.py tests/test_quick_qc.py tests/test_hooks_dual_protocol.py -v`
- [ ] Q4 Toàn bộ `skills/` dưới trần `3,500` token (`anthropic-tokenizer`) & `<= 235` dòng/ref, `tdq-plan/SKILL.md <= 132` dòng, `plan-examples.md <= 1,300` tok, `tdq-implementer.md <= 42` dòng, `doc_lint`/`i18n_check`/`doc_index`/`test_reference_mot_tang` `0` lỗi — `py -3 -X utf8 scripts/doc_lint.py skills && py -3 -X utf8 scripts/token_budget.py --kiem && py -3 -X utf8 scripts/i18n_check.py skills agents scripts && py -3 -X utf8 -m unittest tests/test_token_budget.py tests/test_reference_mot_tang.py tests/test_agent_frontmatter.py -v`
- [ ] Q5 Đóng gói `plugins/tdq-workflow-agy/` sạch `agy.EXE plugin validate --strict`, `build_portable.py --kiem` xanh, 100% Parity Rust-Python và không sửa plugin ngoài repo — `py -3 -X utf8 scripts/build_portable.py --kiem && py -3 -X utf8 -m unittest tests/test_agy_plugin_validate.py tests/test_rust_dispatch_parity.py tests/test_build_portable.py -v`
- [ ] Q6 Nghiệm thu E2E `3` kịch bản và trọn bộ unit test toàn repo (`muc_qc=full`) đạt `0` thất bại, `0` bỏ sót — `py -3 -X utf8 -m unittest tests/test_plan_v2_e2e.py -v && py -3 -X utf8 scripts/tdq_test.py tron-bo --workers 1 --fresh --reuse off`
