# REPORT — Phân tích Thực nghiệm, Red-Team 3 Chiều & Đề xuất Kiến trúc `work_kind=investigate` (`2026-11-20-2355-toi-uu-research-phan-tich` · lane `full` · mode `subagent` · `10/10` task + `6/6` DoD tick đủ)

Soul: chất lượng > runtime > context cost · luật gốc: `skills/tdq-conventions/references/soul.md`

**Trước request (trạng thái/flow):** TDQ Workflow chỉ có một luồng mặc định `build`, ép cả các task nghiên cứu, phân tích, debug và báo cáo (`42/174 = 24.1%` ca lịch sử) dồn việc nặng ra tiền-implement (`49.9%` median thời gian và `424` dòng tài liệu ở `investigate — full` vs `12.7%` trong `implement`), render Archify HTML `2` lần (`2.88 MB`), mù checkpoint trên MCP web/đọc theo dải (`pre_tool_use.rs:444`), và chạy thừa `4,315` unit tests (`1,283s`) ở `qc` dù `0` dòng mã nguồn sửa.
**Sau request (trạng thái/flow):** Ban hành **Đề xuất Kiến trúc Hoàn chỉnh V2** (`docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md`) tách rõ `work_kind` (`build | investigate`), đưa toàn bộ điều tra/tổng hợp sâu vào `implement`, vá `100%` `9` cụm nhược điểm Red-Team (`ND-1`–`ND-9`, truy vết từ `17/17` mã `ND-A1..A5`, `ND-B1..B6`, `ND-C1..C6`), kèm kho bằng chứng `29` mục `EV-xxx` (`evidence-log.md`) và lộ trình triển khai code `3` đợt — bảo toàn `0` tệp mã nguồn bị sửa trong request này · **Đã làm:** P1 (`T1.1`–`T1.3` song song `timing.jsonl` + codebase + `29` URL sơ cấp) · P2 (`T2.1` `evidence-log.md` + `T2.2` Đề xuất V1 `M1`–`M6`) · P3 (`T3.1`–`T3.3` Red-Team A/B/C độc lập trên `4` ca thật) · P4 (`T4.1` V2 + `29` `EV-xxx`) · P5 (`T5.1` đối soát đĩa + `doc_lint` + Zero-Code-Touch) · QC độc lập bởi `tdq-qc-tester` (`Q1`–`Q6` & `QC-F1`–`QC-F4`).
**Đã test gì:** Đối soát toàn bộ `174` bản ghi `docs/tdq/timing.jsonl` (`173` trước 00:00, `171` slug duy nhất) và kiểm định chéo `5` loại tệp `docs/tdq/`; rà `token-budget.json`, test pinning (`test_phase_table.py`, `test_gate_guidance.py`, `test_agent_frontmatter.py`, `test_doc_lint.py`, `test_read_gate.py`) và parity Python ↔ Rust; trích xuất `29` nguồn sơ cấp qua `tavily_extract`; `tdq-qc-tester` độc lập kiểm tự động `100%` `path:line` tồn tại trên đĩa, spot-check `5/5` cụm gốc (`timing.jsonl`, `scripts/tdq_state.py:2334-2337,2416-2424`, `hooks/scripts/edit_gate.py:96` + `pre_tool_use.rs:65-72,444-450`, `bash_gate.py:238` + `tdq_team.py:2480`, `gate_guidance.json` + `token-budget.json`), `doc_lint.py`, `tdq_archify.py verify`, Tailscale HTTP `200`, và `git status` / `git diff --name-only dev`.
**Kết quả test:** PASS `6/6` hạng mục DoD (`Q1`–`Q6`) & `10/10` bảng kiểm QC độc lập (`VERDICT: PASS everything`): `Q1` đạt `29` `EV-xxx` (`105/105` refs hợp lệ); `Q2` đủ `4` tệp V1 phủ `173`/`174` bản ghi & `M1`–`M6`; `Q3` đủ `3` tệp Red-Team (`5` `ND-A*`, `6` `ND-B*`, `6` `ND-C*`); `Q4` kiểm chéo toàn bộ `path:line` (V2 `77+35`, Report `9+25`, V1 `7+11` `bad=0`) & `5/5` spot-check chống ALCE F6 (`0` lỗi); `Q5` `doc_lint.py` `0` vi phạm, `tdq_archify.py verify` `status=current` (`valid=true`), Tailscale HTTP `200` (`1,612,572` B); `Q6` `0` tệp ngoài `docs/` bị chạm (`~/.gemini/` nguyên mtime) · **Kết quả:** Xác nhận thực chứng `80.0%` (`20/25`) ca `investigate — full` có tiền-implement > `implement` (`49.9%` vs `12.7%` median); Đề xuất V2 vá `100%` `ND-1`–`ND-9` · **Kiểm:** `doc_lint` `0` lỗi · QC PASS `6/6` DoD (`QC-F4`: không áp dụng vì `loai_request=docs`).
**Đầu ra:** `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md` · `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/evidence-log.md` (`29` `EV-xxx`) · `docs/tdq/qc/2026-11-20-2355-toi-uu-research-phan-tich.md` · **Archify HTML:** `docs/tdq/reports/2026-11-20-2355-toi-uu-research-phan-tich.html` · **Tailscale:** `https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-20-2355-toi-uu-research-phan-tich.html`
**Giới hạn:** Request thuần `docs` (`Zero-Code-Touch`) nên chưa chỉnh sửa mã nguồn vận hành (đã chia rõ lộ trình `3` đợt code ở §5 của V2). Phiên mở qua `--bo-qua-lsp` (`ly_do`: `LSP rust:hooks/rust/tdq-dispatch DAT (3 refs); probe python:. chon tools/patches/agy_manifests.py nam ngoai include cua pyrightconfig.json (scripts/hooks/tests) nen chi tra 1 ref noi tep, pyright van ` · `module`: `python:. → CHUA_KIEM (chưa chạy kịch bản)`).
**Lệch spec chờ duyệt:** không có
**Git:** nhánh `docs/toi-uu-research-phan-tich` (từ `dev`), chưa commit (`0` tệp ngoài `docs/` thay đổi).

## 1. Kết quả Kiểm chứng Thực nghiệm Hiện trạng (`EV-001`–`EV-005`, `Verified`)

- **Nhận định ban đầu đúng rõ rệt với nhóm điều tra:** Sau khi hiệu đính `11` ca bẫy đặt tên slug (`5` âm tính giả + `6` dương tính giả sửa code), nhóm thuần `investigate` chiếm **`42/174` (`24.1%`: `33` research/analysis/audit + `9` debug/scan; `17` quick, `25` full)**.
- **Độ lệch pha ở `investigate — full` (`N=25`):** Tiền-implement chiếm median **`1,888s` (`49.9%`**, mean `51.4%`, P90 `97.4%`) so với `implement` **`780s` (`12.7%`**, P90 `28.4%`); **`20/25` (`80.0%`)** tốn tiền-implement dài hơn `implement`. Trên `Last 30` sạch bug (`CLEAN N=21`), tiền-implement đạt **`48.2%` pooled (`40.8%` med)** > `17.3%` `implement`.
- **Đối chứng compute thực (`model_giay`, schema v1, loại chờ người dùng duyệt):** `Pure investigate` (`n=13`) dành **`43.0%` pooled (`46.9%` med)** cho tiền-implement > `38.1%` `implement`, ngược hoàn toàn với `Build` (`n=44`: `33.4% < 48.9%`).
- **Lỗi telemetry phát hiện trong mã nguồn (`Verified`):** `_cli_approve` (`scripts/tdq_state.py:2335,2417,2422`) đặt `state["phase"] = "implement"` cho `plan`/`quick` mà thiếu gọi `ghi_moc_phase(state, "implement")` (`scripts/tdq_state.py:497`), gây `im=0s` giả tạo ở `18` ca `build — full` (và góp phần cộng dồn `466s` đầu `implement` của chính request này vào `plan`).

## 2. Đề xuất Kiến trúc V2 & Truy vết Vá `100%` Red-Team (`ND-1`–`ND-9`)

| Mã V2 | Mức độ | Ánh xạ Red-Team (`17/17`) | Vấn đề V1 bị Red-Team bắt | Giải pháp Vá Chính thức trong V2 (`M1`–`M6`) | Độ tin cậy |
|---|---|---|---|---|---|
| **`ND-1`** | Cao | `ND-A1`, `ND-B5` | `read_gate` mù MCP/LSP; bỏ `has_range` ở `pre_tool_use.rs:444` phá tốc độ `<0.5ms` (`test_read_gate.py:175`); `post_tool_use.rs:76` lệch schema | Giữ `100%` fast-path Rust `L444`; cài **Weighted Burden Counter thuần Rust theo từng `sid`** (`checkpoint-<sid>.json`, ngưỡng `40` phủ MCP/Grep/Read/Bash), reset theo ghi nhận của chính `sid` đó | `Verified` |
| **`ND-2`** | Cao | `ND-A2`, `ND-B2`, `ND-C5` | Mất giả thuyết trước compact; ghi `4` bề mặt tốn `1/3` actions; `--claim` nhắc `rm`/`write_text` dính `[TDQ:READONLY]`; `blackboard_record` (`tdq_team.py:2480`) thiếu NTFS lock; lọt `cmd /c` & `[IO.File]` | **Shard + Leader-Merge** (`<task>.md` / `.ev.jsonl` qua `scoped-write`); truyền **`--claim-file` / `--excerpt-file`**; bọc **`with_ntfs_lock`**; Anchor tĩnh không timestamp giây (giữ KV-cache 10x) + bơm subagent; vá `cmd /c` & `[IO.File]` đồng bộ Python/Rust | `Verified` |
| **`ND-3`** | Cao | `ND-B1` | `"reviewer"` substring cho `tdq-security-reviewer` lọt quyền ghi (`edit_gate.py:96`, `pre_tool_use.rs:65`); `canonical_or_ancestor` (`L110`) chỉ resolve `1` cấp; đè `evidence*`/`trial_*.json`; rơi `DelegatePython` (`L333`) | **Deny-first** (`security-reviewer`, `browser`, `"subagent"`) + exact allowlist `_SCOPED_ARTIFACT_ROLES`; leo `ancestors()` `realpath` đa tầng; denylist cấm ghi trực tiếp `evidence*`/`trial_*.json`/`rec_*.json`; **Allow trực tiếp tại Rust** | `Verified` |
| **`ND-4`** | Cao | `ND-A3`, `ND-B6`, `ND-C2` | Thiếu `quick+investigate` & `_archify_gate` (`tdq_state.py:2254`) gây Double Archify; `1` subagent phạm trần `>45%` SAS; `next_headline` vượt `600` chars; `handoff-schema.json:84` chặn `no_worktree`; `subagent_stop.py:134` chấm sớm | Thêm **Tier 0 Zero-Fanout SAS** (`mode=main`); miễn pre-approval Archify preview (render `1` lần tại `report`); gộp `main|subagent` vào duyệt plan (bỏ `codex`); hậu tố gọn `· kind:inv` (`<=600` chars); mở `handoff-schema.json:74-84` & tách đăng ký `PostToolUse` | `Verified` |
| **`ND-5`** | Cao | `ND-A4`, `ND-C1` | Bugfix Paradox (`1953`): đẩy RCA mù vào `build` khiến thiếu `Chạm:`; đổi `work_kind` bằng `set` thiếu `§2b`/`QC-F2..F3`; `cong_dang_cho` (`tdq_state.py:1294`) không check `spec_sha256` | **Two-Stage Bugfix Routing**: lỗi đa tầng chạy **Micro-Spike `investigate` (`<=10m`)** rồi dùng `tdq_state.py escalate-to-build --by` (khóa `set work_kind` tự do), đồng bộ kiểm `spec_sha256` drift | `Verified` |
| **`ND-6`** | Cao | `ND-B4`, `ND-C3` | Cạn `SKILL_LINE_LIMITS` (`tdq-conventions 209`, `tdq-intake 148`, `tdq-plan 132`) & `3,500` tok (`spec-template`/`qc`/`team-mode` còn `14/21/28`); `i18n_check`; `rule_r10`/`r14_loi`/`quick-lane-mini`/`--verify-plan` | Dọn ví dụ dư trước khi gắn pointer; viết `investigate-mode.md` **tiếng Anh (`<=3,000` tok, `<=40` từ/câu)**; tỉa `40–60` tok ngoài vùng bảng pin của `qc.md`; miễn có điều kiện `rule_r10` (`doc_lint.py:441`) & `r14_loi` (`L1144`); nâng `quick+investigate` lên `<=65L` (`quick-lane-mini.md:29`); cờ `is_created` (`tdq_plan_scaffold.py:659`) | `Verified` |
| **`ND-7`** | Cao | `ND-B3`, `ND-B6`, `ND-A1` | Thêm mã `#23` `"CHECKPOINT"` phá `3` bộ test **22 mã AGY** (`gate_guidance.json:31-54`); `READONLY_AGENTS` (`test_agent_frontmatter.py:27`); `PHASE_TABLE` (`test_phase_table.py:165`); `WORKTREE:` gate | **Tái sử dụng mã `"DOC"`** giữ nguyên `22` mã AGY; tách `_STRICT_READONLY_AGENTS` vs `_SCOPED_INVESTIGATION_AGENTS`; giữ object `PHASE_TABLE`; hỗ trợ `worktree_required: false` qua `4` chốt (`agy_hooks.py:1463`, `tdq_team.py:1788,2625`, `tdq_bench.py:283`); biên dịch qua `tools/patches/*` | `Verified` |
| **`ND-8`** | Cao | `ND-C4` | Ca `1346` viết `7` `.py` (`2,738L`) trong `docs/tdq/bench/1346/` kích hoạt nhầm failsafe `QC-F1` (`4,315` tests = `1,283s`) | Phân tách **Script Chẩn đoán** (`docs/tdq/{artifacts,bench}/<slug>/*.py`) với **Product Code**; `QC-F1` chỉ bật lại khi `git diff` chạm tệp **ngoài `docs/tdq/`** | `Verified` |
| **`ND-9`** | TB | `ND-A5`, `ND-C6` | `QC-I2` dựa vào `excerpt`/`tdq_ccr.py:161` (`128MB` LRU) dễ tự duyệt F6; `TDQ:GON` bơm `7KB` vào điều tra; `report` tốn `632s–10,240s` | `QC-I1/I2` kiểm cặp **(Claim ↔ File gốc / `raw/<ev_id>.txt`)**; `Write` soạn thẳng vào `reports/<slug>.md` (rút `report <=120s`); đổi `TDQ:GON` thành `3` dòng kỷ luật bằng chứng (`~1,800` tok/lượt) | `Verified` (nguồn) · `Inferred` (mức tiết kiệm) |

## 3. Lộ trình Triển khai Đề xuất V2 (`3` Đợt Cho Request `feature` Tiếp Theo)

1. **Đợt 1 (Core State, Lint, Archify & Docs Foundation):** Sửa `tdq_state.py`, `doc_lint.py`, `tdq_plan_scaffold.py`, `tdq_bench.py`, thêm `investigate-mode.md` (EN `<3,000` tok), tỉa nhẹ `spec-template`/`qc`/`team-mode` và cập nhật `quick-lane-mini.md` + `issue-triage.md`.
2. **Đợt 2 (Evidence Engine, Security & Rust Burden Checkpoint):** Bổ sung `evidence add/merge/render` (`--claim-file`, `with_ntfs_lock`), vá Python+Rust `scoped-write` (5 tầng bảo vệ + `cmd /c` + `[IO.File]`), cài Weighted Burden `sid` tại Rust giữ `<0.5ms` `has_range`, và thêm bộ vector đối kháng `tests/test_investigate_workflow.py`.
3. **Đợt 3 (Agent Prompts, Compiler AGY & Validate E2E):** Cập nhật `agents/tdq-{explorer,debugger,reviewer}.md`, `tools/patches/*`, `hooks/hooks.json`, tách test `_STRICT_READONLY_AGENTS`, build plugin & chạy `agy.EXE plugin validate --strict` + hồi quy toàn suite.

## Thời gian

Request `2026-11-20-2355-toi-uu-research-phan-tich` · lane full · opened at 2026-11-21T00:00:16+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 24 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 10 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 2 |
| plan | 29 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 2 |
| implement | 55 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 11 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 0s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 2h 09min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
- api_request_seconds: no_usable_source
- tool_call_seconds: no_usable_source
- background_job_seconds: no_usable_source
- observed_union_seconds: no_usable_observations
- unattributed_seconds: wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |

*(Ghi chú đo lường: trong tổng `29 min` của pha `plan`, có `~466s` đầu tiên của `implement` bị cộng dồn vào `plan` do chính bug `_cli_approve` vừa phát hiện tại `scripts/tdq_state.py:2335,2422`, `EV-004`.)*

## Thân PR (soạn sẵn)

**Tóm tắt:** Hoàn thành điều tra thực nghiệm (`174` bản ghi `timing.jsonl`), kiểm toán codebase & `29` nguồn sơ cấp, phản biện Red-Team 3 chiều (`A/B/C`) và xuất Đề xuất Kiến trúc Hoàn chỉnh V2 (`work_kind=investigate`) vá `100%` `9` cụm nhược điểm (`ND-1`–`ND-9`) theo quy chuẩn `Zero-Code-Touch`.
**Trước/Sau:** `docs/tdq/spec/2026-11-20-2355-toi-uu-research-phan-tich-preview.html` · `docs/tdq/reports/2026-11-20-2355-toi-uu-research-phan-tich.html` (`https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-20-2355-toi-uu-research-phan-tich.html`).
**Đã kiểm:**
- `Q1`–`Q3`: `evidence-log.md` (`29` `EV-xxx`), `4` tệp V1 (`173`/`174` + `M1`–`M6`), `3` tệp Red-Team (`17` mã `ND-A/B/C`) → PASS.
- `Q4`–`Q5`: Kiểm chéo tự động `248+` `path:line` trên đĩa (`0` lỗi), spot-check `5/5` cụm gốc chống F6, `doc_lint.py` (`0` vi phạm), `tdq_archify.py verify` (`current`), Tailscale HTTP `200` → PASS.
- `Q6`: `git status --porcelain` & `git diff --name-only dev` có `0` tệp ngoài `docs/` bị tạo/sửa/xóa → PASS (`ZERO-CODE-TOUCH VERIFIED`).
**Rủi ro hồi quy:** Không có rủi ro runtime ở request này (`0` tệp mã nguồn thay đổi); mọi thay đổi code tương lai đã có bản đồ test ghim chặt ở `ND-7` (`M6`).
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-20-2355-toi-uu-research-phan-tich.manifest.json -->
<!-- manifest_digest: 0cd0c2fcfa023cf220922a7c10032b4e7f7429e55d3614309bc8b0c0b094c685 -->
<!-- tdq-archify-binding:end -->