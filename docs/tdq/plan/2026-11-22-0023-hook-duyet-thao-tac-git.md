# PLAN — Cập nhật hook cho phép thao tác git khi người dùng duyệt

Ngày: 2026-11-22 · Spec: ../spec/2026-11-22-0023-hook-duyet-thao-tac-git.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — đo thực tế bằng tdq_bench.py simulate (--he-so-agent 1.5): đội 12.3 phút vs main 14.3 phút (chênh 2.0 phút qua 4 wave, 4 task giao subagent và 3 task leader giữ) (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: CHỜ DUYỆT

> **Tóm tắt dễ hiểu:** Kế hoạch chia thành bốn đợt kế tiếp nhau với bảy công việc tách biệt tệp để không xung đột vùng sửa. Hai đợt đầu nâng cấp bộ phân tích lệnh và cổng sự kiện trên nền Rust kèm bảng hướng dẫn chuẩn. Hai đợt sau đồng bộ tầng kịch bản Python, đóng gói lại bản dựng plugin và kiểm chứng toàn bộ đối chiếu hai tầng cùng bộ kiểm thử hồi quy.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Lõi phân tích shell & bảng hướng dẫn
- P2 — Cổng sự kiện Rust & lưu trữ vé duyệt
- P3 — Đồng bộ tầng hook Python & patch Antigravity
- P4 — Log & test bắt buộc và đóng gói plugin
- Cụm song song
- Luật file nóng
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | `tdq-implementer` (Rust hooks & Python parity) | `gemini-4-neon` | `high` | Suy luận ranh giới bảo mật Rust/Python; user được đổi model/effort khi duyệt |
| `qc` | `tdq-qc-tester` / kiểm chứng `full` | `inherit` | `high` | Chạy trọn `cargo test`, `pytest` toàn repo, `agy plugin validate --strict`, `i18n_check`, `ruff` |
| `report` | Leader (`main`) | `inherit` | `medium` | Tổng hợp báo cáo 4 phần Markdown và Archify HTML tiếng Việt (HTTP 200 qua Tailscale) |

## Quy tắc thi hành (áp cho mọi task)
1. Thứ tự phase là thứ tự phụ thuộc — không đảo; mở nhánh `feature/hook-duyet-thao-tac-git` từ `dev` ngay sau khi người dùng duyệt plan.
2. Mỗi task: đánh `[~]` khi bắt đầu → viết test trước (đỏ) → code → test xanh → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Mỗi bước chạy kiểm thử vùng chạm (`cargo test` / `pytest` module đích); trọn bộ hồi quy toàn repo chạy ở cổng QC `full`.
4. Lệnh nào chạm state của workflow phải cô lập bằng `TDQ_PROJECT_DIR` trên thư mục tạm trong test.
5. QC FAIL → thêm task fix gọn vào mục QC của file này (không cần duyệt lại), lặp đến khi PASS.
6. Không commit, merge, push hoặc sửa ngoài repo (`~/.gemini/config/plugins/tdq-workflow-agy/`) cho đến khi người dùng yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (`ANTI-1` Fake Red, `ANTI-2` Blind Assertion, `ANTI-3` Dirty State Git, `ANTI-4` Late Tick, `ANTI-5` Raw Dump, `ANTI-6` Broad Area).

## Thiết kế Trước vs Sau
| Khía cạnh | Hiện trạng (Trước) | Thiết kế mới (Sau) |
|---|---|---|
| Luồng duyệt lệnh git | Chặn cứng mọi `git push`, `git reset --hard`, `git clean -f` không có ngoại lệ | `PreInvocation`/`UserPromptSubmit` lọc tin nhắn gốc ghi `git_grants` single-turn vào `.tdq-runtime/turn-meta-<sid>.json` (khóa agent sửa); `PreToolUse` mở đúng loại khi `!turn_closed` và phiên chính |
| Phân tích shell & bước 3b | Quét chuỗi con thô gây chặn nhầm đối số không phải git; chặn `git switch -c` trước `spec_approved`; thẻ `TDQ:GIT` báo sai lý do | Phân tích phân đoạn và token lệnh shell (độ sâu bọc 2, bỏ cờ toàn cục `git -C`/`-c`); tách chi tiết lỗi trên thẻ `GIT` (giữ 23 mã); miễn trừ lệnh tạo nhánh bước 3b thuần túy ở pha `analyze`/`idle` |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu trực tiếp bản xem trước Archify đã duyệt tại `docs/tdq/spec/2026-11-22-0023-hook-duyet-thao-tac-git-preview.html` và manifest `docs/tdq/spec/2026-11-22-0023-hook-duyet-thao-tac-git-preview.manifest.json` (`current`, `valid`).

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ: English comments/docstrings/CLI (`i18n_check.py` delta `+0`) · `utf8_io` · `TDQ_LOG=0` tắt log timestamp stderr · hàm `<= 50` dòng (`cyc <= 10`, `cog <= 15`) · `GIỮ NGUYÊN` 23 mã trong `gate_guidance.json`, chặn cứng force-push, `Co-Authored-By:` và tiền tố nhánh AI, không chạm `~/.gemini/`, `main`, `soul.md`.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| `CommandSafetyViolation`, `inspect_command_safety`, `extract_git_grants`, `is_pure_intake_branch_create`, `mutates_tdq_state` | `hooks/rust/tdq-dispatch/src/command_parser.rs` (`T1.1`) | `T2.1` (`pre_tool_use.rs`, `user_prompt_submit.rs`), `T4.2` (`test_rust_dispatch_parity.py`) |
| Thẻ `GIT` trong `gate_guidance.json` (23 mã, `model_hint <= 160` ASCII) | `tools/patches/gate_guidance.json` (`T1.2`) | `T2.1` (Rust `include_str!`), `T4.1` (plugin bundle), `T4.2` |
| `TurnMeta.git_grants: Vec<String>`, `mark_turn_closed`, khóa `.tdq-runtime/`, log `TDQ_LOG` trong Rust events | `hooks/rust/tdq-dispatch/src/storage.rs` + `events/{pre_tool_use,user_prompt_submit,pre_invocation}.rs` (`T2.1`) | `T4.1` (`tdq-dispatch.exe`), `T4.2` (`test_rust_dispatch_parity.py`) |
| Python `extract_git_grants`, `inspect_git_command_safety`, khóa `.tdq-runtime/` trong `hooks/scripts/` | `hooks/scripts/{prompt_context,bash_gate,edit_gate,agy_pretooluse_gate}.py` (`T3.1`) | `T3.2` (`tools/patches/agy_hooks.py`), `T4.2` (`test_bash_gate.py`, `test_hooks_dual_protocol.py`) |
| Patch Antigravity `_has_banned_agy_git`, `_patch_prompt_context`, `_patch_edit_gate` | `tools/patches/agy_hooks.py` (`T3.2`) | `T4.1` (`build_agy_plugin.py`), `T4.2` (`test_agy_hooks.py`, `test_rust_dispatch_parity.py`) |
| Bản dựng `plugins/tdq-workflow-agy/` + binary `tdq-dispatch.exe` | `plugins/tdq-workflow-agy/` (`T4.1`) | `T4.2` (parity test chạy trên binary & bundle thật) |

## P1 — Lõi phân tích shell & bảng hướng dẫn

- [x] **T1.1** (e18m) Nâng cấp bộ phân tích token shell, `extract_git_grants`, khóa `.tdq-runtime/` và miễn trừ bước 3b trong `command_parser.rs` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml command_parser`
  - Req: `§1, §2 #1, §3c Bước 1-2` · Ngoài phạm vi: `GIỮ NGUYÊN` các luật chặn `RemoteScriptExecution`, `ExecutionPolicyBypass`, `has_banned_ai_branch` và chữ ký `is_shell_mutator`
  - Chạm: `hooks/rust/tdq-dispatch/src/command_parser.rs`
  - Cần: Không
  - Giao tiếp: Consumes: `strip_powershell_herestrings`, `split_shell_segments`, `tokenize_command`, `extract_shell_subcommands` | Produces: `CommandSafetyViolation::{GitPushNeedsApproval, GitForcePushForbidden, GitResetHardNeedsApproval, GitCleanForceNeedsApproval, CoAuthoredTrailer}`, `required_grant(&self)`, `extract_git_grants(&str) -> Vec<String>`, `is_pure_intake_branch_create(&str) -> bool`, mở rộng `mutates_tdq_state(&str)`
  - Neo & Công cụ: edit_file trên `hooks/rust/tdq-dispatch/src/command_parser.rs` tại `CommandSafetyViolation` (L59), `inspect_command_safety` (L68) và `mutates_tdq_state` (L311)
  - Trước → Sau: Kiểm tra `lower.contains("git push")` thô chặn cứng mọi ca và chặn nhầm đối số → Phân tích phân đoạn và token lệnh thực thi `git` (đệ quy bọc độ sâu 2, bỏ cờ `-C`/`-c`/`--git-dir`/`--work-tree`), phân tách force-push với push thường, bảo vệ `.tdq-runtime/`
  - Tiêu chí chấp nhận (EARS): KHI nhận lệnh shell không phải git có chứa cụm từ git trong đối số, HỆ THỐNG PHẢI trả `None`; KHI nhận `git push --force` hoặc `git commit` mang `Co-Authored-By:`, HỆ THỐNG PHẢI trả biến thể chặn cứng tuyệt đối; KHI nhận tin nhắn gốc hợp lệ của người dùng, `extract_git_grants` PHẢI trả đúng tập khóa trong `{"push", "reset_hard", "clean_f"}`
  - Logic cốt lõi:
    1. Tách phân đoạn shell, mở vỏ bọc `bash -c`/`sh -c`/`pwsh -Command`/`cmd /c` tối đa 2 tầng, bỏ tiền tố `env`/`rtk`/`rtk bypass` và cờ toàn cục của `git`, định danh tiểu lệnh `push`/`reset`/`clean`/`commit`/`merge`/`tag`.
    2. Bắt force-push (`-f`, `--force`, `--force-with-lease`, `--force-if-includes`, refspec `+`) thành `GitForcePushForbidden`; bắt `Co-Authored-By:` và AI trailer thành `CoAuthoredTrailer`; phân loại push thường, `reset --hard`, `clean -f` sang biến thể cần duyệt.
    3. Thêm `extract_git_grants` (lọc ngoặc kép, thẻ hệ thống, trích dẫn, dấu `?`, phủ định Việt/Anh, thảo luận meta về hook/spec), `is_pure_intake_branch_create` (1 phân đoạn `git switch -c`/`checkout -b` đúng 5 tiền tố loại request, không nhánh AI, không redirect) và mở rộng `mutates_tdq_state` chặn ghi `docs/tdq/.tdq-runtime/`.
  - Ca góc hiểm & Assert: `inspect_command_safety("py -3 scripts/skill_inventory.py --loc \"hook git push\"") == None`; `inspect_command_safety("bash -c \"git -C repo push --force origin dev\"") == Some(GitForcePushForbidden)`; `inspect_command_safety("git commit -m \"feat: x\" -m \"Co-Authored-By: Claude\"") == Some(CoAuthoredTrailer)`; `extract_git_grants("không push nhé") == Vec::<String>::new()`; `extract_git_grants("mở request update hook cho phép git push") == Vec::<String>::new()`; `extract_git_grants("ok push lên origin đi") == vec!["push"]`; `mutates_tdq_state("echo {} > docs\\tdq\\.tdq-runtime\\turn-meta-1.json") == true`; `is_pure_intake_branch_create("git switch -c feature/abc; echo x > src/a.py") == false`

- [x] **T1.2** (e10m) Cập nhật nội dung thẻ `GIT` trong `gate_guidance.json` (giữ đúng 23 mã) và kiểm thử hợp đồng guidance — Test: `py -3 -X utf8 -m pytest tests/test_gate_guidance.py -q`
  - Req: `§1, §2 #3, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` danh sách 23 mã (`9` hard deny, `2` overwrite, `13` guidance) và toàn bộ 22 mã khác ngoài `GIT`
  - Chạm: `tools/patches/gate_guidance.json`, `tests/test_gate_guidance.py`
  - Cần: Không
  - Giao tiếp: Consumes: cấu trúc `guidance_codes.GIT` (`chuyen_gi`, `vi_sao`, `lam_gi`, `bo_qua`, `model_hint`) | Produces: thẻ `GIT` phản ánh đúng cả 2 nhóm (thao tác git cần duyệt lượt hiện tại và bất biến cấm nhánh AI / `Co-Authored-By:` / force-push)
  - Neo & Công cụ: edit_file trên `tools/patches/gate_guidance.json` (L74-80) và `tests/test_gate_guidance.py` (`TestGateGuidanceConstants`)
  - Trước → Sau: Thẻ `GIT` chỉ ghi lỗi tên nhánh/trailer AI → Thẻ `GIT` mô tả chính xác cả thao tác git chưa có duyệt lượt hiện tại lẫn các bất biến cấm tuyệt đối
  - Tiêu chí chấp nhận (EARS): KHI chạy `tests/test_gate_guidance.py`, HỆ THỐNG PHẢI giữ đúng 23 mã, không chứa ký tự cấm, `model_hint` thuần ASCII và độ dài `[TDQ:GIT] <model_hint>` `<= 160` ký tự
  - Logic cốt lõi: Cập nhật 5 trường của `guidance_codes.GIT` trong `gate_guidance.json` và bổ sung test xác nhận nội dung mới giữ chuẩn 4 phần cùng giới hạn 160 ký tự.
  - Ca góc hiểm & Assert: `len(gate_guidance.ALL_AGY_CODES) == 23`; `len(f"[TDQ:GIT] {entry['model_hint']}") <= 160`; `assert "duyệt" in entry["lam_gi"] and "Co-Authored-By:" in entry["bo_qua"]`

**Xong P1 khi**: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml command_parser` và `pytest tests/test_gate_guidance.py -q` cùng đạt 0 fail.

## P2 — Cổng sự kiện Rust & lưu trữ vé duyệt

- [x] **T2.1** (e20m) Mở rộng `TurnMeta` (`git_grants`) và nối cơ chế vé single-turn, khóa `.tdq-runtime/`, miễn trừ bước 3b cùng log `TDQ_LOG` trên tầng sự kiện Rust — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Req: `§1, §2 #1-2, §3c Bước 1 & 3, §4` · Ngoài phạm vi: `GIỮ NGUYÊN` cổng `READONLY`, `VUNG`, `ZERO-POPUP`, `SUBAGENT`, `UNFINISHED` và hành vi chặn mặc định khi không có vé
  - Chạm: `hooks/rust/tdq-dispatch/src/storage.rs`, `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs`, `hooks/rust/tdq-dispatch/src/events/user_prompt_submit.rs`, `hooks/rust/tdq-dispatch/src/events/pre_invocation.rs`
  - Cần: `T1.1`, `T1.2`
  - Giao tiếp: Consumes: `command_parser::{CommandSafetyViolation, inspect_command_safety, extract_git_grants, is_pure_intake_branch_create, mutates_tdq_state}` | Produces: `TurnMeta.git_grants: Vec<String>`, `mark_turn_closed` xóa `git_grants`, `is_state_target` khóa `.tdq-runtime/`, cổng cấp & kiểm tra vé trên `PreToolUse`/`UserPromptSubmit`/`PreInvocation`
  - Neo & Công cụ: edit_file trên `storage.rs` tại `TurnMeta` (L138) và `mark_turn_closed` (L348); `pre_tool_use.rs` tại `is_state_target` / `handle_edit_tool` (L403) và `handle_command_tool` (L484-537); `user_prompt_submit.rs` (`handle_user_prompt_submit`, L9-38); `pre_invocation.rs` (`handle_pre_invocation`, L178-213)
  - Trước → Sau: `TurnMeta` chưa lưu vé lượt, `user_prompt_submit.rs` ghi JSON lệch schema `TurnMeta`, `pre_tool_use.rs` chặn cứng `git push`/`reset --hard`/`clean -f` và `git switch -c` bước 3b, không khóa sửa `.tdq-runtime/` → Chuẩn hóa `TurnMeta` có `git_grants`, xóa vé khi đóng lượt, kiểm vé theo loại trên phiên chính (`role_opt.is_none()`), ghi log stderr mặc định (tắt qua `TDQ_LOG=0`), khóa sửa `.tdq-runtime/` cả file lẫn shell và miễn trừ bước 3b thuần túy ở pha `analyze`/`idle`
  - Tiêu chí chấp nhận (EARS): KHI phiên chính có `turn_closed == false` và `git_grants` chứa `"push"`, HỆ THỐNG PHẢI cho phép `git push origin dev`, ghi log timestamp stderr (trừ khi `TDQ_LOG=0`) và vẫn chặn `git reset --hard`, `git push --force`, `Co-Authored-By:` và subagent; KHI agent sửa `docs/tdq/.tdq-runtime/turn-meta-1.json`, HỆ THỐNG PHẢI chặn với mã `STATE`
  - Logic cốt lõi:
    1. Thêm `#[serde(default)] pub git_grants: Vec<String>` vào `TurnMeta`; xóa `meta.git_grants.clear()` trong `mark_turn_closed`.
    2. Cập nhật `handle_user_prompt_submit` giữ nguyên schema `TurnMeta` (`turn_closed = false`, cập nhật `git_grants = extract_git_grants(prompt)`, ghi dòng `signal` vào `turns-<sid>.jsonl` và log `TDQ_LOG`).
    3. Trong `pre_tool_use.rs`: mở rộng `is_state_target` khóa `docs/tdq/.tdq-runtime/`; xử lý các biến thể `CommandSafetyViolation` (chặn cứng force-push & `Co-Authored-By:`, kiểm vé single-turn cho 3 biến thể cần duyệt chỉ với `role_opt.is_none()`, ghi log `TDQ_LOG` + dòng `observe` khi cho phép, truyền `detail` riêng rõ ràng khi chặn); miễn trừ `is_pure_intake_branch_create` tại nhánh `mutates_outside_docs_any` khi `effective_phase` là `analyze` hoặc `idle`.
  - Ca góc hiểm & Assert: Test Rust xác minh `turn_closed=true` từ chối vé cũ; `role_opt=Some("tdq-implementer")` bị từ chối dù có vé; lệnh ghép `git push origin dev && git reset --hard HEAD~1` chỉ có vé `"push"` bị từ chối; JSON hỏng trong `turn-meta` fail-closed; `write_file` vào `docs/tdq/.tdq-runtime/turn-meta-s.json` trả `deny` chứa `TDQ:STATE`; `git switch -c feature/demo` ở pha `analyze` trả `allow`

**Xong P2 khi**: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml` pass 100% (0 fail, gồm đủ toàn bộ test cũ và test mới).

## P3 — Đồng bộ tầng hook Python & patch Antigravity

- [x] **T3.1** (e18m) Đồng bộ trích xuất vé `git_grants`, bộ phân tích lệnh git theo token và khóa `.tdq-runtime/` trong `hooks/scripts/` — Test: `py -3 -X utf8 -m pytest tests/test_bash_gate.py tests/test_hooks_dual_protocol.py -q`
  - Req: `§1, §2 #3, §3c Bước 1-3, §4, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` luật gọi `hooks/ → scripts/`, không để `scripts/` import `hooks/`, không tăng lỗi `i18n_check.py` so với `dev`
  - Chạm: `hooks/scripts/prompt_context.py`, `hooks/scripts/bash_gate.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/agy_pretooluse_gate.py`
  - Cần: `T1.1`
  - Giao tiếp: Consumes: `hooks/scripts/_common.py`, `scripts/tdq_state.py` | Produces: `extract_git_grants(prompt)` trong `prompt_context.py`, `inspect_git_command_safety(cmd)` và `is_pure_intake_branch_create(cmd)` trong `bash_gate.py`, khóa `.tdq-runtime/` trong `edit_gate.py`, `bash_gate.py` và `agy_pretooluse_gate.py`
  - Neo & Công cụ: edit_file trên `prompt_context.py` tại `looks_like_approval` (L125) và `main` (L296); `bash_gate.py` tại `STATE` (L44), `_enforce_agy_bash_guards` (L253) và `_check_git_conventions` (L273); `edit_gate.py` tại `main` (L138-151); `agy_pretooluse_gate.py` tại `_writes_state` (L105)
  - Trước → Sau: Tầng Python chưa nhận diện vé duyệt git, chưa khóa `.tdq-runtime/` và còn kiểm tra chuỗi thô → Tầng Python có cùng tập hàm `extract_git_grants`, phân tích token lệnh shell, ghi log `TDQ_LOG` và khóa cứng `.tdq-runtime/` đồng nhất 1-1 với Rust
  - Tiêu chí chấp nhận (EARS): KHI chạy `prompt_context.py` với tin nhắn duyệt push, HỆ THỐNG PHẢI ghi dòng `signal` `target="git_grant"` vào sổ lượt và log `TDQ_LOG`; KHI chạy `edit_gate.py` hoặc `agy_pretooluse_gate.py` vào `docs/tdq/.tdq-runtime/`, HỆ THỐNG PHẢI chặn với `TDQ:STATE`; `i18n_check.py` trên 4 file giữ delta `+0`
  - Logic cốt lõi:
    1. Thêm `extract_git_grants(prompt)` vào `prompt_context.py` dùng chung `NON_HUMAN_RE`, `QUOTED_SPEECH_RE`, `_tach_prompt_thuc` và bộ lọc phủ định/câu hỏi/meta-request giống hệt Rust; ghi `signal` `target="git_grant"` khi có vé.
    2. Thêm `inspect_git_command_safety(cmd)` (dùng `_split_shell_segments`, `_extract_shell_subcommands`, `shlex`/tokenizer an toàn) và `is_pure_intake_branch_create(cmd)` vào `bash_gate.py`; mở rộng mẫu `STATE` chặn ghi `docs/tdq/.tdq-runtime/`.
    3. Mở rộng `edit_gate.py` và `agy_pretooluse_gate.py` chặn chỉnh sửa trực tiếp `docs/tdq/.tdq-runtime/**` bằng `TDQ:STATE`.
  - Ca góc hiểm & Assert: `extract_git_grants("đừng push") == []`; `extract_git_grants("duyệt git reset --hard") == ["reset_hard"]`; `inspect_git_command_safety("git commit -m 'docs: git push'") is None`; `inspect_git_command_safety("git commit -m 'Co-Authored-By: Claude'") == "co_authored_trailer"`; `agy_pretooluse_gate._writes_state("echo x > docs/tdq/.tdq-runtime/turn-meta-1.json") is True`

- [x] **T3.2** (e20m) Cập nhật patch Antigravity trong `tools/patches/agy_hooks.py` đồng bộ 1-1 hành vi vé duyệt git, đọc `USER_INPUT` từ `transcriptPath`, khóa `.tdq-runtime/` và miễn trừ bước 3b — Test: `py -3 -X utf8 -m pytest tests/test_agy_hooks.py tests/test_gate_guidance.py -q`
  - Req: `§1, §2 #3, §3c Bước 1-3, §4, §5` · Ngoài phạm vi: `GIỮ NGUYÊN` các patch không liên quan (`_patch_read_gate`, `_patch_lsp_gate`, `_patch_search_gate`, `_patch_stop_gate`) và `i18n_check` delta `+0`
  - Chạm: `tools/patches/agy_hooks.py`
  - Cần: `T2.1`, `T3.1`
  - Giao tiếp: Consumes: `TurnMeta` JSON schema (`git_grants`, `turn_closed`), `hooks/scripts/{prompt_context,bash_gate,edit_gate}.py` | Produces: bản patch Antigravity đồng bộ hành vi với `tdq-dispatch.exe` cho fallback Python
  - Neo & Công cụ: edit_file trên `tools/patches/agy_hooks.py` tại các hàm `_patch_bash_gate` (L1805-1950), `_patch_edit_gate` (L1953-2010), `_patch_prompt_context` (L2351-2555) và các chuỗi patch nội sinh (mark_turn_closed, _extract_transcript_user_sig, _has_banned_agy_git)
  - Trước → Sau: Patch `_has_banned_agy_git` dùng `"git push" in low` chặn cứng và không đọc `git_grants`; `mark_turn_closed` không xóa `git_grants`; `_patch_edit_gate` chưa khóa `.tdq-runtime/` → Patch dùng `inspect_git_command_safety` theo token, đọc/ghi `git_grants` từ tin nhắn gốc hoặc `USER_INPUT` trong `transcriptPath`, xóa `git_grants` khi đóng lượt, ghi log `TDQ_LOG`, khóa `.tdq-runtime/` và miễn trừ bước 3b
  - Tiêu chí chấp nhận (EARS): KHI `tools/patches/agy_hooks.py` áp patch lên bản dựng plugin, nhánh Python fallback PHẢI trả quyết định giống hệt Rust `tdq-dispatch.exe` trên toàn bộ ca duyệt/chặn/hết lượt/subagent/anti-spoof/false-positive/bước 3b
  - Logic cốt lõi:
    1. Trong `mark_turn_closed`: đặt `meta["turn_closed"] = True` và `meta["git_grants"] = []`.
    2. Trong `_patch_prompt_context`: trích nội dung tin nhắn gốc từ `payload` hoặc bản ghi `USER_INPUT` (có `source` rỗng hoặc `USER_EXPLICIT`) trong `<= 64 KB` đuôi `transcriptPath`, chạy `extract_git_grants`, lưu `git_grants` vào `turn-meta-<sid>.json` và ghi log stderr theo `TDQ_LOG`.
    3. Trong `_patch_bash_gate` và `_patch_edit_gate`: thay kiểm tra chuỗi con thô trong `_has_banned_agy_git` bằng `inspect_git_command_safety`, kiểm `turn-meta` (`!turn_closed`, không phải subagent, khớp khóa grant) với `detail` rõ từng nguyên nhân; khóa ghi `docs/tdq/.tdq-runtime/` ở cả shell và file edit; miễn trừ `is_pure_intake_branch_create` ở pha `analyze`/`idle`.
  - Ca góc hiểm & Assert: `transcriptPath` có bản ghi `USER_INPUT` mang `source="SYSTEM"` không được cấp vé; `turn_closed=True` bị từ chối; `git push --force` và `Co-Authored-By:` bị chặn cứng kể cả khi `git_grants=["push"]`; `i18n_check.py` trên `tools/patches/agy_hooks.py` giữ delta `+0`

**Xong P3 khi**: `pytest tests/test_bash_gate.py tests/test_hooks_dual_protocol.py tests/test_agy_hooks.py tests/test_gate_guidance.py -q` và `ruff check` trên các file Python chạm đạt 0 lỗi.

## P4 — Log & test bắt buộc và đóng gói plugin

- [x] **T4.1** (e12m) Biên dịch release `tdq-dispatch.exe` và đóng gói lại `plugins/tdq-workflow-agy/` sạch trong repo — Test: `py -3 -X utf8 tools/build_agy_plugin.py --upstream .` và `agy plugin validate plugins/tdq-workflow-agy --strict --json`
  - Req: `§1, §2 #5, §5, §6 Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` `~/.gemini/config/plugins/tdq-workflow-agy/` (không tự động copy hay cài ngoài repo theo lựa chọn 5a) và nhánh `main`
  - Chạm: `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`, `plugins/tdq-workflow-agy/hooks/scripts/bash_gate.py`, `plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py`, `plugins/tdq-workflow-agy/hooks/scripts/prompt_context.py`, `plugins/tdq-workflow-agy/hooks/scripts/_common.py`, `plugins/tdq-workflow-agy/hooks/scripts/gate_guidance.json`, `plugins/tdq-workflow-agy/manifest.json`
  - Cần: `T2.1`, `T3.1`, `T3.2`
  - Giao tiếp: Consumes: nguồn Rust (`hooks/rust/tdq-dispatch/`), `hooks/scripts/`, `tools/patches/{agy_hooks.py,gate_guidance.json}` | Produces: binary `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` và bundle plugin Antigravity đồng bộ SHA
  - Neo & Công cụ: run_command biên dịch `cargo build --release --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`, sao chép binary vào `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`, chạy `tools/build_agy_plugin.py` và `agy plugin validate`
  - Trước → Sau: Bản dựng plugin cũ trong repo chạy logic chặn cứng chuỗi con → Bản dựng plugin mới trong repo chứa binary Rust và script Python đã đồng bộ toàn bộ thiết kế vé duyệt single-turn
  - Tiêu chí chấp nhận (EARS): KHI chạy build và validate plugin, HỆ THỐNG PHẢI trả exit `0`, `"status": "OK"`, `"findings": []` và `pytest tests/test_agy_plugin_validate.py -q` đạt 0 fail
  - Logic cốt lõi: Biên dịch bản tối ưu release của `tdq-dispatch`, đồng bộ binary vào `plugins/tdq-workflow-agy/bin/`, chạy `build_agy_plugin.py --upstream .` cập nhật toàn bộ script và manifest, kiểm chứng bằng `agy plugin validate --strict --json`.
  - Ca góc hiểm & Assert: `json.loads(validate_stdout)["findings"] == []`; phiên bản trong `~/.gemini/config/plugins/tdq-workflow-agy/plugin.json` giữ nguyên không đổi

- [x] **T4.2** (e18m) Bổ sung kiểm thử log service (`TDQ_LOG=1/0`) và ma trận parity Rust ↔ Python trên bản build thật — Test: `py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py tests/test_gate_guidance.py -q`
  - Req: `§2 #4, §4, §6 Q1-Q2 & Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ 137 test hiện hành và không dùng mock che mất hệ thống đang kiểm (`ANTI-1`)
  - Chạm: `tests/test_rust_dispatch_parity.py`, `tests/test_bash_gate.py`, `tests/test_agy_hooks.py`, `tests/test_hooks_dual_protocol.py`
  - Cần: `T4.1`
  - Giao tiếp: Consumes: `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe` và `plugins/tdq-workflow-agy/hooks/scripts/dispatch.py` | Produces: bộ test tự động khóa toàn bộ ma trận bảo mật, parity Rust ↔ Python và kiểm tra log `TDQ_LOG=1/0`
  - Neo & Công cụ: edit_file trên `tests/test_rust_dispatch_parity.py` (quanh L455), `tests/test_bash_gate.py` (quanh L98), `tests/test_agy_hooks.py` (quanh L253) và `tests/test_hooks_dual_protocol.py` (quanh L541)
  - Trước → Sau: Test mới chỉ kiểm tra chặn mặc định `git push`/`git reset --hard` → Test bao phủ đủ ma trận đối chiếu Rust ↔ Python: duyệt đúng loại, chặn chéo loại, hết lượt (`turn_closed`), subagent bị chặn, chặn cứng force-push & `Co-Authored-By:` & nhánh AI, chặn sửa `.tdq-runtime/`, không chặn nhầm chuỗi con, miễn trừ bước 3b và bật/tắt log `TDQ_LOG=1/0`
  - Tiêu chí chấp nhận (EARS): KHI chạy 5 module kiểm thử, HỆ THỐNG PHẢI trả exit `0` với 0 fail, xác nhận đầu ra `decision` giữa Rust binary và Python `dispatch.py` khớp 100% ở mọi dòng ma trận và `stderr` có dòng log timestamp khi `TDQ_LOG=1` nhưng câm lặng khi `TDQ_LOG=0`
  - Logic cốt lõi:
    1. Thêm nhóm test ma trận đối chiếu Rust ↔ Python trong `test_rust_dispatch_parity.py` chạy trực tiếp cả `tdq-dispatch.exe` và `dispatch.py` trong `TDQ_PROJECT_DIR` tạm.
    2. Bổ sung ca kiểm `extract_git_grants` (dương/âm/anti-spoof/transcript `USER_INPUT`), khóa `.tdq-runtime/`, miễn trừ bước 3b và xác minh `TDQ_LOG=1` vs `TDQ_LOG=0` trong `test_agy_hooks.py`, `test_bash_gate.py` và `test_hooks_dual_protocol.py`.
  - Ca góc hiểm & Assert: `rust_out["decision"] == py_out["decision"]` trên mọi ca ma trận; `assert "TDQ:GIT" in denied_reason`; `assert "TDQ:STATE" in runtime_edit_denied`; `assert "[20" in stderr_when_log_on and stderr_when_log_off == ""`

**Xong P4 khi**: `cargo test` và 5 module `pytest` cốt lõi đạt 0 fail, log `TDQ_LOG=1/0` được xác minh bằng assert thật và `agy plugin validate --strict` trả 0 findings.

## QC vòng 1 — fix

- [x] **QC1.1** (e12m) Harden Rust `command_parser.rs` and `protocol.rs` against security findings #1, #2, #3, #5 — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Chạm: `hooks/rust/tdq-dispatch/src/command_parser.rs`, `hooks/rust/tdq-dispatch/src/protocol.rs`
  - Cần: Không
  - Neo & Công cụ: `edit_file` on `command_parser.rs` (`strip_powershell_herestrings`, `tokenize_command`, `skip_command_wrappers`, `extract_shell_subcommands`, `mutates_tdq_state`, `has_banned_ai_branch`) and `protocol.rs` (`HookPayload`)
  - Trước → Sau: Naive herestring stripping, empty-quote drops, depth-2 wrappers, missing `../`/`cd`/PS-alias/Py `.tdq-runtime` lock and missing camelCase `agentType`/`agentId` aliases → Quote-aware herestrings, depth-4 balanced `$()`/`{}`/`-enc` decoding, normalized path/alias state protection, tokenized recursive branch guard, camelCase aliases
  - Logic: Parse quotes around PowerShell herestrings, keep empty tokens during quoting, unwrap shell wrappers and encoded/nested commands to depth 4, normalize paths/aliases in state protection, check branches recursively, and alias camelCase agent fields.
  - Tiêu chí & Assert: Adversarial tests cover every Finding #1, #2, #3, #5 bypass while keeping reads and clean builds green; all new/edited fns `<= 50` lines

- [x] **QC1.2** (e12m) Mirror security fixes #1, #2, #3, #5 in Python `bash_gate.py`, `edit_gate.py`, and `agy_pretooluse_gate.py` — Test: `py -3 -X utf8 -m pytest tests/test_bash_gate.py tests/test_hooks_dual_protocol.py -q`
  - Chạm: `hooks/scripts/bash_gate.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/agy_pretooluse_gate.py`
  - Cần: Không
  - Neo & Công cụ: `edit_file` on `hooks/scripts/{bash_gate,edit_gate,agy_pretooluse_gate}.py`
  - Trước → Sau: Unquoted/quoted herestring bugs, missing depth-4 wrappers/`-enc`/`$()`, missing normalized state & alias checks, case-sensitive Windows `within()` → 1-1 Python parity with `QC1.1` + `os.path.normcase` Windows path checks
  - Logic: Mirror `QC1.1` herestring, tokenizer, depth-4 wrapper/command substitution, normalized path/alias state guards, and recursive branch checks across Python hooks, plus `os.path.normcase` in `within()`.
  - Tiêu chí & Assert: Existing hook tests pass `0 fail`, adversarial probe catches all bypass vectors, `i18n_check` and `ruff` delta `+0`

- [x] **QC1.3** (e10m) Fix stale-sig `git_grants` re-mint (#4) and sync hardened helpers/anchors in `tools/patches/agy_hooks.py` — Test: `py -3 -X utf8 -m pytest tests/test_agy_hooks.py tests/test_gate_guidance.py -q`
  - Chạm: `tools/patches/agy_hooks.py`
  - Cần: `QC1.1`, `QC1.2`
  - Neo & Công cụ: `edit_file` on `tools/patches/agy_hooks.py` (`_patch_prompt_context`, `_patch_bash_gate`, `_patch_edit_gate`)
  - Trước → Sau: Stale `sig == last_user_sig` could re-open/re-mint old `git_grants` on `SYSTEM`/`resume`, and patch used local duplicate helpers → Fail-closed empty `git_grants` when stale/non-human sig and reuse `QC1.2` hardened `mutates_tdq_state`/`has_banned_ai_branch`
  - Logic: Reject stale closed-turn or `compact`/`resume`/`system` turns from minting `git_grants`, keep `turn_closed` preserved on stale ticks, add `agentId` camelCase checks, and delegate branch/herestring guards to `QC1.2` helpers.
  - Tiêu chí & Assert: `pytest tests/test_agy_hooks.py tests/test_gate_guidance.py -q` passes `0 fail`, stale-sig probe never re-mints grants, `i18n`/`ruff` delta `+0`

- [x] **QC1.4** (e10m) Rebuild release `tdq-dispatch.exe` and repackage `plugins/tdq-workflow-agy/` cleanly in-repo — Test: `py -3 -X utf8 tools/build_agy_plugin.py --upstream .`
  - Chạm: `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`, `plugins/tdq-workflow-agy/hooks/scripts/bash_gate.py`, `plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py`, `plugins/tdq-workflow-agy/hooks/scripts/prompt_context.py`, `plugins/tdq-workflow-agy/hooks/scripts/_common.py`, `plugins/tdq-workflow-agy/manifest.json`
  - Cần: `QC1.1`, `QC1.2`, `QC1.3`
  - Neo & Công cụ: `cargo build --release` + `tools/build_agy_plugin.py --upstream .` + `agy plugin validate --strict --json`
  - Trước → Sau: Previous release binary & bundle lacked `QC1.1`–`QC1.3` security fixes → Clean in-repo rebuild with matching release SHA-256 and `0` strict validation findings
  - Logic: Compile release `tdq-dispatch.exe`, rebuild `plugins/tdq-workflow-agy/` via `tools/build_agy_plugin.py --upstream .`, and verify SHA-256 parity and `agy plugin validate --strict` with zero host changes.
  - Tiêu chí & Assert: `agy plugin validate plugins/tdq-workflow-agy --strict --json` returns exit `0`, `"findings": []`; `~/.gemini/config/plugins/` untouched

- [x] **QC1.5** (e10m) Add adversarial regression & parity tests for all 5 QC1 security findings — Test: `py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py tests/test_gate_guidance.py -q`
  - Chạm: `tests/test_rust_dispatch_parity.py`, `tests/test_bash_gate.py`, `tests/test_agy_hooks.py`
  - Cần: `QC1.4`
  - Neo & Công cụ: `edit_file` on the 3 test modules targeting newly hardened Rust & Python paths
  - Trước → Sau: Test suites did not exercise Finding #1–#5 exploit strings against real binary & fallback Python → Full adversarial parity suite running real `tdq-dispatch.exe` and `dispatch.py`
  - Logic: Add adversarial test vectors across `test_bash_gate.py`, `test_agy_hooks.py`, and `test_rust_dispatch_parity.py` covering Findings #1-#5 and run the 6 core test suites plus `cargo test`.
  - Tiêu chí & Assert: All 5 core modules pass `0 fail`, `tdq-security-reviewer` re-audit clears CRITICAL/HIGH, `i18n_check` delta `+0`

## QC vòng 2 — fix

- [x] **QC2.1** (e10m) Close QC2 Rust security findings (#1 fd-redirect and cd-runtime, #2 empty herestring and PS-context/quote-breakout guard) — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Chạm: `hooks/rust/tdq-dispatch/src/command_parser.rs`
  - Cần: Không
  - Neo & Công cụ: `edit_file` on `command_parser.rs` (`ps_herestring_end`, `strip_powershell_herestrings`, `part_stdout_targets_depth`, `is_state_or_runtime_text`, `mutates_tdq_state_depth`)
  - Trước → Sau: Naive digit-redirect skip (`1>`), partial `.tdq-runtime` `cd` match, off-by-one empty herestring end, and depth-0 non-PS herestring strip → Standalone fd redirects captured, all writes inside `.tdq-runtime` blocked after `cd`, search from `i + step - 1`, and PS-context + safe-body gating
  - Logic: Add `has_ps_herestring_context` and `herestring_body_safe_for_strip`, search herestring terminators from `i + step - 1`, allow digit-fd redirects in `part_stdout_targets_depth` (keeping `&`/null filters), and track `seen_cd_runtime` for full `.tdq-runtime` coverage.
  - Tiêu chí & Assert: `cargo test` passes `0 fail`, catching `1>` state redirects, `cd docs/tdq/.tdq-runtime` mutations, empty herestring splice, and non-PS echo splice while keeping `2>$null` and `2>&1` allowed

- [x] **QC2.2** (e12m) Mirror QC2 security fixes and LOW residuals in Python hooks and `tools/patches/agy_hooks.py` — Test: `py -3 -X utf8 -m pytest tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py -q`
  - Chạm: `hooks/scripts/bash_gate.py`, `hooks/scripts/edit_gate.py`, `hooks/scripts/agy_pretooluse_gate.py`, `tools/patches/agy_hooks.py`
  - Cần: `QC2.1`
  - Neo & Công cụ: `edit_file` on `hooks/scripts/{bash_gate,edit_gate,agy_pretooluse_gate}.py` and `tools/patches/agy_hooks.py`
  - Trước → Sau: Unmatched `1>` redirects, partial `cd .tdq-runtime` checks, non-PS herestring stripping, missing `-B`/`-C` branch flags, and missing `agentId` camelCase on upstream gates → 1-1 Python parity with `QC2.1`, full `-B`/`-C` branch flags, and consistent `agentId` handling
  - Logic: Update `STDOUT_WRITE`, `_strip_powershell_herestrings`, and `_mutates_tdq_state_depth` in `bash_gate.py`; add `_extract_agy_redir_targets`, `seen_cd_runtime`, and `-B`/`-C` regexes in `agy_pretooluse_gate.py`; sync `agentId` across `edit_gate.py`, `bash_gate.py`, and `agy_hooks.py`.
  - Tiêu chí & Assert: `pytest tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py -q` exits `0`, `i18n_check` delta `+0`, `ruff` delta `+0`

- [x] **QC2.3** (e8m) Rebuild release `tdq-dispatch.exe` and repackage `plugins/tdq-workflow-agy/` in-repo — Test: `py -3 -X utf8 tools/build_agy_plugin.py --upstream .`
  - Chạm: `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`, `plugins/tdq-workflow-agy/hooks/scripts/bash_gate.py`, `plugins/tdq-workflow-agy/hooks/scripts/edit_gate.py`, `plugins/tdq-workflow-agy/hooks/scripts/_common.py`, `plugins/tdq-workflow-agy/hooks/scripts/subagent_dispatch_gate.py`, `plugins/tdq-workflow-agy/manifest.json`
  - Cần: `QC2.1`, `QC2.2`
  - Neo & Công cụ: `cargo build --release` + `tools/build_agy_plugin.py --upstream .` + `agy plugin validate --strict --json`
  - Trước → Sau: Staged binary & bundle from round 1 → Rebuilt release binary with matching SHA-256 and cleanly patched in-repo plugin bundle passing strict validation
  - Logic: Build release `tdq-dispatch.exe`, run `tools/build_agy_plugin.py --upstream .`, verify binary SHA-256 match and `agy plugin validate --strict --json` zero findings without touching host install or `main`.
  - Tiêu chí & Assert: `build_agy_plugin.py` exits `0`, `agy plugin validate --strict` returns `"findings": []`, SHA-256 matches `target/release/tdq-dispatch.exe`

- [x] **QC2.4** (e10m) Add QC2 adversarial regression and parity tests and verify 6 core pytest suites plus cargo test — Test: `py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py tests/test_gate_guidance.py tests/test_agy_plugin_validate.py -q`
  - Chạm: `tests/test_bash_gate.py`, `tests/test_agy_hooks.py`, `tests/test_rust_dispatch_parity.py`
  - Cần: `QC2.3`
  - Neo & Công cụ: `edit_file` adding QC2 regression & parity test vectors in the 3 test modules
  - Trước → Sau: QC1 test suites lacked `1>`/`cd .tdq-runtime`/empty-herestring/non-PS-echo/`-C`/`agentId` vectors → Full round-2 adversarial matrix running against live binary and fallback Python
  - Logic: Add unit, hook, and real-binary parity tests covering all 4 CRITICAL/HIGH blocking issues and 3 LOW residuals; run all 6 core pytest suites, `cargo test`, `i18n_check`, and `ruff`.
  - Tiêu chí & Assert: All 6 core pytest suites and `cargo test` exit `0` with `0 fail`, `i18n_check` and `ruff` delta `+0`

## QC vòng 3 — fix

- [x] **QC3.1** (e10m) Neutralize unquoted `#`/`<#...#>` comment quotes and enforce `@'`/`@"` value delimiters in Rust `command_parser.rs` — Test: `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
  - Chạm: `hooks/rust/tdq-dispatch/src/command_parser.rs`
  - Cần: Không
  - Neo & Công cụ: `edit_file` on `command_parser.rs` (`strip_powershell_herestrings`, `neutralize_comment_quotes`, `split_shell_segments`, `mask_quoted_shell_ops`, `tokenize_command`, `extract_command_substitutions`)
  - Trước → Sau: Comments `# @'\n` or `<# ' #>` opened false here-strings or poisoned quotes → Single-pass unquoted comment quote neutralization plus `@'`/`@"` delimiter validation across Rust parsers
  - Logic: Add `is_comment_delim`, `is_herestring_delim`, and `neutralize_comment_quotes`; handle unquoted `<#...#>` and `#...\n` inside `strip_powershell_herestrings` before `@'`/`@"` matching and call `neutralize_comment_quotes` at lexer/splitter boundaries.
  - Tiêu chí & Assert: `cargo test` passes `0 fail`, catching `Write-Output ok # @'\n...`, `<# ' #> ...`, `cmd /c "echo # & ..."`, while keeping safe PS here-strings allowed

- [x] **QC3.2** (e10m) Mirror comment neutralization and fix `--git-dir`/`--work-tree` regex in Python `bash_gate.py` and `agy_pretooluse_gate.py` — Test: `py -3 -X utf8 -m pytest tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py -q`
  - Chạm: `hooks/scripts/bash_gate.py`, `hooks/scripts/agy_pretooluse_gate.py`
  - Cần: `QC3.1`
  - Neo & Công cụ: `edit_file` on `hooks/scripts/bash_gate.py` and `hooks/scripts/agy_pretooluse_gate.py`
  - Trước → Sau: Python lexers lacked `#`/`<#...#>` neutralization and `agy_pretooluse_gate.py` missed leading `-` on `git-dir`/`work-tree` → 1-1 comment quote neutralization across Python gates and fixed `--git-dir`/`--work-tree` regex
  - Logic: Mirror `QC3.1` `_neutralize_comment_quotes` and delimiter checks in `bash_gate.py` and `agy_pretooluse_gate.py`, and fix `-(?:[Cc]|-git-dir|-work-tree)` in `_branch_names`.
  - Tiêu chí & Assert: `pytest tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py -q` passes `0 fail`, `i18n_check` and `ruff` delta `+0`

- [x] **QC3.3** (e8m) Rebuild release `tdq-dispatch.exe` and repackage `plugins/tdq-workflow-agy/` in-repo — Test: `py -3 -X utf8 tools/build_agy_plugin.py --upstream .`
  - Chạm: `plugins/tdq-workflow-agy/bin/tdq-dispatch.exe`, `plugins/tdq-workflow-agy/hooks/scripts/bash_gate.py`, `plugins/tdq-workflow-agy/manifest.json`
  - Cần: `QC3.1`, `QC3.2`
  - Neo & Công cụ: `cargo build --release` + `tools/build_agy_plugin.py --upstream .` + `agy plugin validate --strict --json`
  - Trước → Sau: Round-2 plugin binary & scripts lacked comment neutralization → Clean in-repo rebuild with matching SHA-256 and `0` strict validation findings
  - Logic: Compile release `tdq-dispatch.exe`, run `tools/build_agy_plugin.py --upstream .`, verify SHA-256 parity and strict plugin validation without modifying host install or `main`.
  - Tiêu chí & Assert: `agy plugin validate --strict --json` returns `"findings": []`, SHA-256 matches `target/release/tdq-dispatch.exe`

- [x] **QC3.4** (e10m) Add QC3 comment-injection and `--git-dir` adversarial parity tests and verify 6 core pytest suites plus cargo test — Test: `py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py tests/test_gate_guidance.py tests/test_agy_plugin_validate.py -q`
  - Chạm: `tests/test_bash_gate.py`, `tests/test_agy_hooks.py`, `tests/test_rust_dispatch_parity.py`
  - Cần: `QC3.3`
  - Neo & Công cụ: `edit_file` adding QC3 regression and parity vectors in the 3 test modules
  - Trước → Sau: Test suites lacked `# @'\n`, `<# ' #>`, and `--git-dir` comment/flag bypass assertions → Full round-3 parity suite exercising Rust binary and fallback Python
  - Logic: Add adversarial test functions across `test_bash_gate.py`, `test_agy_hooks.py`, and `test_rust_dispatch_parity.py`, then run all 6 core pytest suites, `cargo test`, `i18n_check`, and `ruff`.
  - Tiêu chí & Assert: All 6 core pytest suites and `cargo test` exit `0` with `0 fail`, `i18n_check` and `ruff` delta `+0`

## Cụm song song

Phân tích đồ thị phụ thuộc (`Cần:`) cho thấy 7 task có tập `Chạm:` hoàn toàn tách rời nhau (0 file trùng), xếp thành 5 đợt:
- Đợt 1 (song song): `T1.1` (Rust `command_parser.rs`) và `T1.2` (`gate_guidance.json` + `test_gate_guidance.py`).
- Đợt 2 (song song sau `T1.1`, `T1.2`): `T2.1` (Rust `storage.rs` + `events/*.rs`) và `T3.1` (Python `hooks/scripts/*.py`).
- Đợt 3 (tuần tự sau `T2.1`, `T3.1`): `T3.2` (`tools/patches/agy_hooks.py`).
- Đợt 4 (tuần tự sau `T3.2`): `T4.1` (build release binary & đóng gói `plugins/tdq-workflow-agy/`).
- Đợt 5 (tuần tự sau `T4.1`): `T4.2` (bổ sung & chạy ma trận test parity + log service).

## Luật file nóng

Không có file nóng (`HOT FILE = 0`): mọi tệp nguồn, tệp patch, bản dựng plugin và tệp test đều chỉ xuất hiện ở đúng một task trong toàn bộ kế hoạch, bảo đảm không có xung đột ghi song song dù chạy theo mode `main` hay `subagent`.

## Definition of Done

Trỏ về §6 của spec `docs/tdq/spec/2026-11-22-0023-hook-duyet-thao-tac-git.md` (mức QC `full`, mỗi dòng kiểm chứng bằng một lệnh thực tế):

- [ ] Q1 Kiểm thử Rust `tdq-dispatch` pass 100% (0 fail, bao phủ phân tích token, 3 loại vé single-turn, chặn cứng force-push/`Co-Authored-By:`/nhánh AI, khóa `.tdq-runtime/`, bước 3b) — `cargo test --manifest-path hooks/rust/tdq-dispatch/Cargo.toml`
- [ ] Q2 Kiểm thử parity Rust ↔ Python & cổng hook (5 module cốt lõi) pass 100% (0 fail, giữ đúng 23 mã guidance) — `py -3 -X utf8 -m pytest tests/test_rust_dispatch_parity.py tests/test_gate_guidance.py tests/test_bash_gate.py tests/test_agy_hooks.py tests/test_hooks_dual_protocol.py -q`
- [ ] Q3 Trọn bộ hồi quy Python toàn repo theo mức QC `full` đạt 0 fail — `py -3 -X utf8 -m pytest -q`
- [ ] Q4 Đóng gói binary release & plugin Antigravity sạch (exit 0, `"status": "OK"`, 0 findings) — `py -3 -X utf8 tools/build_agy_plugin.py --upstream .` và `agy plugin validate plugins/tdq-workflow-agy --strict --json` và `py -3 -X utf8 -m pytest tests/test_agy_plugin_validate.py -q`
- [ ] Q5 Ràng buộc kiến trúc, `i18n_check` delta `+0` trên mọi file sửa so với `dev`, `doc_lint` 0 violation trên `brief`/`spec`/`plan`/`report`, không chạm `~/.gemini/`, `main`, `soul.md` — `py -3 -X utf8 scripts/doc_lint.py --pair docs/tdq/spec/2026-11-22-0023-hook-duyet-thao-tac-git.md docs/tdq/plan/2026-11-22-0023-hook-duyet-thao-tac-git.md` và `py -3 -X utf8 scripts/i18n_check.py` (đối chiếu delta từng file sửa)
- [ ] Q6 Kiểm tra clean code (`ruff check` 0 lỗi mới trên các file Python chạm, hàm `<= 50` dòng) và log service (`TDQ_LOG=1/0` xác minh trong test) — `ruff check hooks/scripts/prompt_context.py hooks/scripts/bash_gate.py hooks/scripts/edit_gate.py hooks/scripts/agy_pretooluse_gate.py tools/patches/agy_hooks.py`
