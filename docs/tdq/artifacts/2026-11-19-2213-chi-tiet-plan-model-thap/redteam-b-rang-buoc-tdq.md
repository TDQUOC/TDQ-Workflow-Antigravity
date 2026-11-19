# Red-Team B — Phản biện Xung đột Hệ thống, Linter, Parser & Tương thích Ngược TDQ (Vòng 2)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Vai trò & Phương pháp:** Kiểm toán đối kháng trực tiếp từng hạng mục của `de-xuat-v1.md` với mã nguồn, khóa token, linter, hook, parser và test suite thực tế trong `scripts/`, `skills/`, `agents/`, `hooks/rust/tdq-dispatch/`, `tools/patches/` và `tests/`.

---

### Nhược điểm B-1: V1 đâm thẳng vào trần R13 (`3,500` token) ở `qc.md`, `spec-template.md`, `team-mode.md`, bẫy `tiktoken` ở plugin và bỏ sót `plan-template-huong-dan.md`

- **Mức độ nghiêm trọng:** `Cao`
- **Bằng chứng cụ thể (`docs/tdq/token-budget.json`, `scripts/token_budget.py:45`):**
  - `skills/tdq-build/references/qc.md`: đang ở **`3,496 / 3,500` token** (`195` dòng) — chỉ còn trống đúng **`4` token**! Đề xuất V1 chèn quy định + khuôn `5` trường cho `**QCn.1**` sẽ lập tức nổ `[R13]` ở `scripts/doc_lint.py:522` và `tests/test_token_budget_lock.py:168`.
  - `skills/tdq-spec/references/spec-template.md`: đang ở **`3,486 / 3,500` token** (`156` dòng) — chỉ còn **`14` token**! Thêm tiểu mục và bảng `Hợp đồng Dữ liệu & Chữ ký Dùng chung` vào `§3c` sẽ vượt ngưỡng ngay.
  - `skills/tdq-build/references/team-mode.md`: đang ở **`3,390 / 3,500` token** (`177` dòng) — chỉ còn **`110` token**, không đủ chỗ cho hướng dẫn `Auto Task Packet` và đồng bộ rule.
  - **Bẫy sai số đo giữa repo gốc và AGY plugin:** `plugins/tdq-workflow-agy/docs/tdq/token-budget.json` đang ghi thấp hơn giả tạo (`3,223` / `3,040` / `2,679`) do `tools/patches/cli_fixes_b.py:242` fallback sang `tiktoken`, trong khi CI repo gốc đo bằng `anthropic-tokenizer`.
  - **File bị sót & khóa bất biến test:** V1 quên không cập nhật `skills/tdq-plan/references/plan-template-huong-dan.md:40-53` (`1,535` token — đang khóa khuôn 8 trường cũ). Khi rút gọn `plan-template.md` (`3,279` token), bắt buộc phải giữ dòng `Soul:` (`tests/test_soul_rules.py:65-86`) và bảng `Hiện trạng (Trước)` / `Thiết kế mới (Sau)` (`tests/test_khao_sat_3_chieu.py:100-111`). File mới `task-card-guide.md` phải `<= 235` dòng (`tests/test_token_budget.py:149`), có `<!-- muc-luc-dong: -->` nếu `>= 90` dòng hoặc `>= 2,000` token (`scripts/doc_index.py:39,43`) và được `tdq-plan/SKILL.md` (`121/121` dòng, `doc_lint.py:63`) trỏ trực tiếp (`tests/test_reference_mot_tang.py:155`).
- **Cơ chế sửa V2:**
  - Tách nội dung mở rộng sang sibling sạch hoặc tái phân bổ: chuyển hướng dẫn chi tiết `**QCn.1**` từ `qc.md` sang sibling mới (`qc-vong-fix.md`), chuyển hướng dẫn + bảng mẫu `§3c` từ `spec-template.md` sang `spec-template-huong-dan.md` (`2,840` token, còn `660` token), chuyển chi tiết `Auto Task Packet` từ `team-mode.md` sang `team-mode-tra-cuu.md` (`1,141` token, còn `2,359` token), và đưa `plan-template-huong-dan.md` vào danh sách sửa. Luôn kiểm bằng `anthropic-tokenizer` giữ mọi file `<= 3,350` token.

---

### Nhược điểm B-2: Cách cô lập `Chạm:` của V1 trong `tdq_team.py:doc_plan()` nuốt mất `Chạm:` nhiều dòng, phá test fallback `t.text[0]` và trả rỗng `t.tham_chieu`

- **Mức độ nghiêm trọng:** `Cao`
- **Bằng chứng cụ thể (`scripts/tdq_team.py:49,162-182`, `scripts/tdq_state.py:2487`):**
  1. **Nuốt `Chạm:` dạng sub-bullet nhiều dòng:** Tại `tdq_team.py:162-163`, `if line.strip().startswith("- ") and line.startswith((" ", "\t")): hien_tai.text.append(line.strip()[2:])` — parser cắt sạch khoảng trắng thụt lề! Nếu `Chạm:` viết thành sub-bullet nhiều dòng (`  - Chạm:\n    - \`a.py\``), trong `t.text` các dòng đó tách thành `"Chạm:"`, `"`a.py`"`, khiến điều kiện `dong.lstrip().startswith(("Chạm:", "Touch:"))` của V1 **bỏ sót toàn bộ file** → `t.vung_file = []` → `quyet_dinh_task` gán nhầm `tu_lam / vung-khoa` (`:387-388`) và làm mù `ngoai_vung_khai` (`:1673-1674`).
  2. **Làm đỏ test tương thích ngược `PLAN_DUONG_DAN_DONG_NOI`:** `tests/test_team_mode.py:1265-1268,1305-1307` test đúng tình huống plan **không có dòng `Chạm:`** mà path nằm ở dòng continuation của tiêu đề task (`t.text[0]`). Chỉ quét `Chạm:` sẽ làm test này thất bại (`[] != ["scripts/tdq_team.py"]`).
  3. **Regex `_PATH` mù với định dạng `` `<file.py:ten_symbol>` `` của V1:** `tdq_team.py:49` dùng `_PATH = re.compile(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`")`. Trong khuôn V1 (`- Tham chiếu: \`file_chi_doc.py:ten_symbol\``), phần `:ten_symbol` nằm trong backtick khiến `_PATH.findall()` trả về **`[]`** — làm `t.tham_chieu` rỗng hoàn toàn! Đồng thời check `if "/" in duong:` (`:178`) bỏ sót file gốc không có `/` (`CLAUDE.md`, `AGENTS.md`, `Cargo.toml`) dù `TIEN_TO_FILE_LUAT` ở `:72` có liệt kê chúng.
- **Cơ chế sửa V2:**
  - Trong `doc_plan()` (và `_extract_plan_targets` ở `tdq_state.py:2487`), lưu kèm `indent = len(line) - len(line.lstrip())` để nối mọi sub-bullet thụt sâu hơn của `Chạm:` / `Tham chiếu:` vào đúng khối cha cho tới khi `indent <= indent_nhan`.
  - Nếu task **có** khai `Chạm:` → chỉ rút `t.vung_file` từ khối `Chạm:` (cô lập tuyệt đối); chỉ dùng fallback `t.text[0]` khi toàn task không có nhãn `Chạm:`.
  - Định dạng `Tham chiếu:` chuẩn thành `` `path/file.py` (`sym1`, `sym2`) `` (giữ path sạch trong backtick riêng) HOẶC thêm regex `_REF_PATH = re.compile(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)(?::([A-Za-z0-9_.]+))?`")` và không lọc bỏ file gốc có trong tập whitelist tên tệp gốc.

---

### Nhược điểm B-3: `JIT Wave Check` tự kích nổ khóa STALE kép ở `plan_assignment_sha` và `canh_bao_lach_luat` (`sha_file` toàn file)

- **Mức độ nghiêm trọng:** `Cao`
- **Bằng chứng cụ thể (`scripts/tdq_team.py:254-275,327-336,592-595,1617-1618`, `hooks/scripts/edit_gate.py:206-211`):**
  - `chieu_phan_cong()` đưa toàn bộ các dòng `t.text[1:]` (trừ mỗi `"tiến độ:"`, `"progress:"`, `"status:"`) vào `dong_hop_dong` để băm `plan_assignment_sha` — nghĩa là `Vị trí neo:` và `Tham chiếu:` bị khóa trong SHA phân công.
  - Tệ hơn nữa, `canh_bao_lach_luat()` ở `tdq_team.py:1617-1618` kiểm **`ban_do.get("plan_sha") != sha_file(plan)`** (SHA toàn bộ file plan, kể cả dấu checkbox và `Vị trí neo:`). Khi `JIT Wave Check` (`de-xuat-v1.md`) cập nhật `Vị trí neo:` ở đợt $k+1$, cả `wave`/`open` (`LoiLuat: The plan changed after assignment`) lẫn `edit_gate.py:206-211` (chặn luôn cả leader sửa code!) bị khóa cứng cho tới khi chạy lại `assign`.
- **Cơ chế sửa V2:**
  - Trong `chieu_phan_cong()`, chỉ băm các trường cấu trúc điều phối (`ma`, `phase`, `vung_file`, `can_mcp`, `test`, `deps`, `uoc_luong`, `Dùng:`/`Cần:`), loại trừ `Vị trí neo:` / `Tham chiếu:` / ghi chú delta khỏi `plan_assignment_sha`.
  - Đổi `canh_bao_lach_luat()` (`:1617`) sang dùng `kiem_tra_stale(plan, ban_do)` (so `plan_assignment_sha` thay vì `sha_file(plan)` toàn file).

---

### Nhược điểm B-4: Hở cổng `approve quick`, gãy regex `RE_TICK` / `_TASK_REF` với `**QCn.1**` & `T2.1a`, và xung đột `rule_r15` với `R12` & `in_fence`

- **Mức độ nghiêm trọng:** `Cao`
- **Bằng chứng cụ thể (`scripts/tdq_state.py:2123,2343`, `scripts/tdq_eval.py:197`, `scripts/doc_lint.py:528-550,602,666`):**
  1. **Lane `quick` dùng `approve quick`, không dùng `approve plan`:** Trong `quick-lane.md:57,86` và `tdq_state.py:2343`, lane `quick` chỉ gọi `approve quick` (`target == "quick"`) và không bắt buộc set `plan_file`. Điều kiện `if target == "plan"` của V1 bỏ lọt hoàn toàn quick-lane; mặt khác khi mở sang `target == "quick"`, phải fail-open nếu `docs/tdq/plan/<slug>.md` không tồn tại trên đĩa để giữ xanh `tests/test_quick_qc.py:148` & `tests/test_hooks_dual_protocol.py:84`.
  2. **Vỡ regex với `**QC1.1**`, `T2.1a` và `T1`:** `scripts/tdq_eval.py:197` (`RE_TICK = re.compile(r"\[([ ~x])\]\s*\*\*(T[\d.]+)\*\*")`) bỏ sót `T2.1a`, `**QC1.1**` và `[>]`; `scripts/tdq_team.py:52` (`_TASK_REF = re.compile(r"\b(T\d+[A-Za-z]*\.\d+[a-z]?)\b")`) bỏ sót cả `QC1.1` lẫn `T1`/`T2` của quick-lane.
  3. **Bẫy false-positive của `R12` trên bước đánh số `1. Bước 1:`:** `scripts/doc_lint.py:666` (`_r12_van_xuoi`) chỉ bỏ qua dòng bắt đầu bằng `| > # - * <!--` — **KHÔNG bỏ qua dòng `1. `, `2. `, `3. `**! Nếu task block có `>= 3` bước đánh số dùng thuật ngữ/mô tả ASCII không dấu tiếng Việt (`>= 6` từ ngoài backtick), `R12` báo đỏ ngay trên plan `doc_lang=vi`.
  4. **`rule_r15` không kiểm `doc.in_fence[i]` & lệch thư mục với `--pair`:** `doc_lint.py:536-552` quét xuyên qua code fence thụt lề (vốn là yêu cầu của V1!), nên đoạn ví dụ markdown trong fence có thể kích hoạt nhầm `R15`. Ngoài ra `doc_lint.py:528` chặn `dirname != "plan"` trong khi `pair()` (`:602`) chấp nhận file ở thư mục tạm (`tests/test_doc_lint.py:403`).
- **Cơ chế sửa V2:**
  - Mở `_r15_gate` kiểm cả `target in ("plan", "quick")` (tự suy `docs/tdq/plan/<slug>.md`, chỉ chặn nếu file tồn tại), đồng thời chạy kiểm sớm ngay ở `tdq_finish.py` & `tdq_state.py set plan_file=...`.
  - Cập nhật `RE_TICK` (`tdq_eval.py:197`) khớp `[ ~x>]` và `[A-Za-z][A-Za-z0-9.]*`; cập nhật `_TASK_REF` (`tdq_team.py:52`) khớp `(?:T|QC)\d+[A-Za-z]*(?:\.\d+[a-z]*)?`.
  - Vá `doc_lint.py`: bỏ qua dòng `doc.in_fence[i]` trong `rule_r15`; cho `_r12_van_xuoi` bỏ qua dòng bắt đầu bằng `\d+\.\s`; tách `r15_loi(text, path, check_dir=True)` để `--pair` chạy với `check_dir=False` và đọc mốc `R15_MOC` theo chuẩn slug (nếu tên file không chứa prefix ngày thì áp dụng hành vi an toàn tương thích `tests/test_doc_lint_r15.py`).

---

### Nhược điểm B-5: Chỉnh sửa nhầm file generated của AGY plugin, làm vỡ Parity/Dual-Protocol test và rò tên tool AGY sang Claude Code

- **Mức độ nghiêm trọng:** `Cao`
- **Bằng chứng cụ thể (`tools/patches/agy_hooks.py:1325-1377,2610`, `tools/patches/skills_and_agents.py:45-50,90-100,140-169`, `tests/test_rust_dispatch_parity.py:535`, `tests/test_hooks_dual_protocol.py:115`):**
  1. `plugins/tdq-workflow-agy/hooks/scripts/subagent_dispatch_gate.py` được **sinh đè tự động** từ `SUBAGENT_DISPATCH_GATE_PY` trong `tools/patches/agy_hooks.py` bởi `tools/build_agy_plugin.py:221,239` — không được sửa trực tiếp file trong `plugins/`.
  2. `tests/test_rust_dispatch_parity.py:535` & `tests/test_hooks_dual_protocol.py:115` gửi payload chỉ có `2` hoặc `5` trường cũ và assert trả về `allow` + `overwrite Workspace=inherit`. Nếu `subagent_dispatch_gate.py` chuyển sang `block` trên `3` trường mới hoặc đổi nhánh xử lý trước `set_overwrite`, parity giữa Python và `hooks/rust/tdq-dispatch` + bộ test sẽ vỡ.
  3. Ghi thẳng `edit_file/write_file` vào `skills/tdq-plan/` gốc (`de-xuat-v1.md:47`) sẽ sai tên tool của **Claude Code** (phải viết `` `Edit` `` / `` `Write` `` có backtick để `skills_and_agents.py:90-100` tự dịch sang AGY khi build). Tương tự ở root `agents/tdq-implementer.md`, `tests/test_agent_frontmatter.py:50,56-59,83-99` cấm `model: flash` (chỉ AGY override thành `flash`), và `tests/test_team_mode.py:1158,1204-1221` khóa chặt `7` nhãn `TRUONG_PROMPT` + danh sách lệnh `tdq_team.LENH` & `tdq_ten_lenh.py` (`tests/test_team_chong_conflict.py:92-105`).
- **Cơ chế sửa V2:**
  - Chuyển target hook AGY sang `tools/patches/agy_hooks.py` (`SUBAGENT_DISPATCH_GATE_PY`) + rebuild qua `tools/build_agy_plugin.py`; giữ 3 nhãn kiểm tra mới ở mức `remind` (không đè lên `set_overwrite({"Workspace": "inherit"})`, giữ 100% parity Rust/Python).
  - Trong `skills/**` gốc luôn dùng `` `Edit` `` / `` `Write` ``; tách rạch ròi rule gốc cho `agents/tdq-implementer.md` vs bản override `tools/patches/skills_and_agents.py`; đồng bộ đăng ký `"packet"` vào cả `tdq_team.LENH` lẫn `tdq_ten_lenh.BANG_DOI_TEN`.

---

### Nhược điểm B-6: `tdq_plan_scaffold.py` & `task-card-guide.md` chạm bẫy Windows popup (`CREATE_NO_WINDOW`), `i18n_check.py`, `build_portable.py:346` và `tdq_bench.py`

- **Mức độ nghiêm trọng:** `Trung bình`
- **Bằng chứng cụ thể (`scripts/build_portable.py:346`, `scripts/tdq_bench.py:119-120`, `tests/test_no_window_flags.py:43-55`, `scripts/i18n_check.py`):**
  1. `scripts/build_portable.py:346` (`_sua_duong_dan_tuong_doi_agy`) tự động chèn tiền tố `~/.gemini/config/plugins/tdq-workflow/` trước các đường dẫn bắt đầu bằng `scripts/` hoặc `hooks/` trong `skills/**/*.md`. Nếu ví dụ mẫu Task Card trong `task-card-guide.md` dùng `Chạm: \`scripts/foo.py\``, bản sinh ra sẽ biến dạng thành đường dẫn cài đặt tuyệt đối!
  2. Mọi lệnh gọi `subprocess.run` trong script mới `scripts/tdq_plan_scaffold.py` phải qua `tdq_ten_lenh.chay_subprocess` (hoặc `CREATE_NO_WINDOW` — khóa bởi `tests/test_no_window_flags.py`), giữ comment/stdout tiếng Anh chuẩn `i18n_check.py`, và **tuyệt đối không** khởi động tiến trình LSP server mới bên trong CLI (chỉ đọc file đĩa + AST + cache tĩnh nếu có để giữ cam kết `< 1s`).
  3. `scripts/tdq_bench.py:119-120` (`sinh_plan`) sinh task 1 dòng không có `Đặc tả`/`Logic` và DoD đánh số `1.` — cần đảm bảo các plan thử nghiệm tạm do `tdq_bench.py` tạo không bị vướng `R15` (giữ phạm vi `R15` chỉ cho `docs/tdq/plan/` hoặc miễn tên file không qua `R15_MOC`).
- **Cơ chế sửa V2:** Dùng đường dẫn minh họa `src/foo.py` trong `task-card-guide.md`; bổ sung ràng buộc cài đặt chuẩn `utf8_io`, `TDQ_LOG`, `tdq_ten_lenh.chay_subprocess`, pure AST/static cache cho `tdq_plan_scaffold.py`; và khóa rõ điều kiện kích hoạt `R15-Strict` theo thư mục `docs/tdq/plan/` + mốc `R15_MOC` để không phá `tdq_bench.py`.
