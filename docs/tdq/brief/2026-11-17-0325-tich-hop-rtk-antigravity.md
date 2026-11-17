# BRIEF — Tích hợp cộng sinh RTK tối ưu token và tự động kiểm/cài cho Antigravity
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Nguyên văn

> okay làm cả 4 nhưng phân tích và cho tôi đề xuất làm sao để colapse với tdq-workflow antigravity có behavior tiết kiệm full, và có trigger nếu install tdq-workflow- antigravity mà chưa có rtk thì sẽ nhắc để xin quyền install và setup vào máy để đủ công cụ cho tdq-workflow antigravity. hãy phân tích và resreach và cho tôi plan tích hợp tối ưu tiết kiệm nhưng vẫn nhanh vẫn có kết quả đầu ra tốt đẹp

**Đọc bước đầu:**
- **Mục tiêu:** Hợp nhất (collapse) cơ chế tiết kiệm token của `rtk` trực tiếp vào `tdq-workflow-agy` trên Google Antigravity để đạt hiệu quả tiết kiệm toàn diện ("tiết kiệm full") mà vẫn nhanh, an toàn chất lượng đầu ra; đồng thời bổ sung cơ chế phát hiện thiếu `rtk` khi cài đặt/khởi động `tdq-workflow-agy` để nhắc và xin quyền người dùng cài đặt + cấu hình user-level đầy đủ.
- **Phạm vi (bao gồm đủ 4 hạng mục đã chốt):**
  1. Giữ repo `TDQ-Workflow-Antigravity` sạch bản quyền MIT (không bundle mã nguồn/binary `rtk` vào repo; kiểm tra và cài `rtk` user-level khi được người dùng cho phép).
  2. Collapse trực tiếp luồng cổng kiểm soát `run_command` (`bash_gate` + `search_gate`) và bước rewrite của `rtk` vào một pipeline `PreToolUse` thống nhất ngay trong `tdq-workflow-agy` (không phải gánh 2 plugin rời xung đột thứ tự hook hay trùng `AGENTS.md`).
  3. Thiết lập cấu hình `rtk` (`%APPDATA%\rtk\config.toml` trên Windows / `~/.config/rtk/config.toml` trên Linux / `~/Library/Application Support/rtk/config.toml` trên macOS) hòa hợp với luật TDQ (`awareness.level = "default"`, SQLite lossless recall `rtk recall <hash>`, bảo vệ tìm kiếm 3 tầng và môi trường Python/PowerShell).
  4. Cập nhật `scripts/search_rules.py` (`_chuan_hoa`) bóc tiền tố `rtk` / `rtk bypass` / `rtk proxy` để không lách cổng `[TDQ:SEARCH]`, kèm trigger kiểm/nhắc/xin quyền cài `rtk` tại `install.py` (`install.ps1`/`install.sh`), `SessionStart`, `setup_status.py`/`tdq_lsp.py` và `tdq_setup.py`.
- **Điểm cần làm rõ/chốt thêm trong pipeline:**
  - Nguồn cài và biến thể `rtk` + `rg` mặc định (`rtk` bản đầy đủ vs `rtk-oss` Apache-2.0 thuần qua GitHub Release kiểm SHA256 vào `~/.local/bin` vs `winget`).
  - Cho phép hay chưa cho phép cài thật `rtk` + `rg` lên máy hiện tại trong quá trình thi công/QC.
  - Chính sách nén với `git diff` (đặc biệt trên subagent audit/QC) và bảo vệ môi trường `.venv`/`pytest`.
  - Hành vi nhắc `[TDQ:SETUP]` ở `SessionStart` trên máy chưa cài `rtk`/`rg`, và mức `muc_qc`.

## Hiểu & kiến thức

- Bỏ qua vòng hỏi phạm vi tổng quát (`scope-round`) vì người dùng đã chỉ định tường minh cả 4 hạng mục tích hợp, kiến trúc Collapse `PreToolUse` và cơ chế xin quyền cài/setup `rtk` ngay từ đầu.
- Xem chi tiết chứng cứ ngoài và số đo nền tại `docs/tdq/research/2026-11-17-0325-tich-hop-rtk-antigravity.md`.

### Phạm vi đã chốt

- **Mặt CHỌN (từ câu trả lời `1a 2a 3a 4a 5a 6a`):**
  - Mặc định tải bản phát hành chính thức đầy đủ `rtk` (`v1.2.0+`) kèm `rg` (`BurntSushi/ripgrep` `15.2.0+`) từ GitHub Releases có đối chiếu `SHA256`, giải nén nguyên tử vào `~/.local/bin` và đăng ký User `PATH` trên Windows (`1a`).
  - Cho phép cài thật `rtk` + `rg` user-level lên máy hiện tại (`C:\Users\admin\.local\bin`, User `PATH`, `%APPDATA%\rtk\config.toml`, kèm hướng dẫn gỡ sạch) ngay trong pha thi công & QC để kiểm chứng E2E sống (`2a`).
  - Nén tối đa ở luồng chính (`git diff`/`git log`/`git show` với SQLite recall `rtk recall <hash>`), tự miễn nén `git diff` cho subagent kiểm định (`tdq-qc-tester`, `tdq-security-reviewer`, `tdq-reviewer`), giữ nguyên `.venv`/`py -3 -m pytest`, và khóa `exclude_commands = ["grep", "rg"]` (`3a`).
  - Bộ cài `install.py` tương tác (`TTY`) hỏi `[y/N]` ngay tại terminal; `SessionStart` nhắc gọn 1 dòng `[TDQ:SETUP]` tối đa 1 lần mỗi phiên và hỗ trợ ghi nhớ ẩn nhắc (`--mute-rtk-prompt`) nếu user từ chối (`4a`).
  - Mức QC `muc_qc = ultra`: chạy trọn bộ unit/integration test, smoke test, runtime test thực tế luồng hook + installer/setup và agent QC độc lập `tdq-qc-tester` (`5a`).
- **Mặt LOẠI:**
  - Không bundle mã nguồn hay binary `rtk`/`rg` vào kho `TDQ-Workflow-Antigravity` (giữ repo sạch giấy phép MIT 100%).
  - Không tự động cài ngầm `rtk` hoặc `rg` trong `tdq_setup.py --nen` (nền) nếu chưa có cờ `--with-rtk` đã được người dùng đồng ý.
  - Không phá vỡ interface Python của `hooks/scripts/bash_gate.py` và `hooks/scripts/search_gate.py` (đang được `tests/test_bash_gate.py`, `tests/test_search_gate.py`, `tests/test_lane_label.py`, `scripts/context_surface.py` và `scripts/tdq_codex_mcp.py` gọi trực tiếp).
  - Không đụng `PostToolUse` để biến đổi output (Antigravity `PostToolUse` chỉ nhận `{}`).

### Năng lực dùng được

Phân vân → DÙNG. Kiểm kê ngày 2026-11-17: 42 skill trên đĩa (`skill_inventory.py --tat-ca`), cộng 11 skill built-in trong context.

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `agy-customizations` | `built-in` | `DÙNG` | đối chiếu hợp đồng `hooks.json` (`PreToolUse` `overwrite`, `SessionStart`) và cấu trúc plugin Antigravity |
| `tdq-setup` | `plugin:tdq-workflow-agy` / `plugin:tdq-workflow` | `DÙNG` | tái sử dụng quy ước 7 bậc kiểm tra, tải GitHub Release kiểm SHA256 nguyên tử (`cai_agent_lsp`) và khóa `TDQ_KHONG_CHAM_MAY=1` |
| `tdq-conventions` · `tdq-intake` · `tdq-spec` · `tdq-plan` · `tdq-build` · `tdq-lean` · `tdq-check-status` · `tdq-status` · `tdq-checkportable` · `tdq-browser-research` · `tdq-browser-test` | `plugin:tdq-workflow-agy` / `plugin:tdq-workflow` | `NỀN` | quy trình TDQ Workflow đang chạy |
| Đã xét 19 skill khác trên đĩa + 10 skill built-in khác | user/plugin/built-in | `KHÔNG` | `khác lĩnh vực` |

### Khảo sát mã nguồn 3 chiều (Grep · LSP · Graphify)

| Vùng file chạm | Phát hiện qua lớp nào (Grep/LSP/Graphify) | Tác động & quan hệ |
|---|---|---|
| `scripts/search_rules.py` (`_chuan_hoa` L382) | LSP `find_references` (`symbols=4`) + `git grep` + Graphify `query` | Điểm chuẩn hóa lệnh shell duy nhất trước `_kieu` và `quyet_dinh`; cần bóc `rtk`, `rtk bypass`, `rtk proxy`, `rtk.exe` có path và xử lý `rtk read` để không lách `[TDQ:SEARCH]`. |
| `hooks/scripts/_common.py` + `tools/patches/agy_hooks.py` | Grep + Đọc mã + Đo `context_surface.py` | `read_payload()` cần cache khi gộp cổng in-process; `_flush_agy_stdout()` cần xuất thêm `"overwrite": {"CommandLine": ...}` khi `PreToolUse` allow kèm viết lại lệnh. |
| `hooks/scripts/bash_gate.py` · `hooks/scripts/search_gate.py` · `hooks/scripts/agy_pretooluse_gate.py` | `git grep` + Graphify `query` | Được import trực tiếp bởi `tests/test_bash_gate.py`, `tests/test_search_gate.py`, `tests/test_lane_label.py`, `scripts/context_surface.py`, `scripts/tdq_codex_mcp.py`. Phải giữ nguyên interface module cũ; thêm cổng hợp nhất `hooks/scripts/command_gate.py` cho `matcher: "run_command"` trên Antigravity và thu hẹp matcher của `search_gate.py` trong `hooks.json` về `grep_search|find_by_name|list_dir|search_directory|find_file|list_directory`. |
| `tools/build_agy_plugin.py` · `tools/patches/{agy_manifests,cli_fixes_a,cli_fixes_b}.py` | LSP (`find_references` `generate_manifest_and_readme` L247) + `git grep` | Biên dịch từ `scripts/` + `hooks/scripts/` sang `plugins/tdq-workflow-agy/`. Mọi thay đổi phải đặt tại mã nguồn gốc + `tools/patches/` để build lại không mất; `agy_manifests.py` cập nhật `hooks.json` hợp nhất và 2 dòng hướng dẫn trong `AGENTS.md`. |
| `scripts/tdq_setup.py` · `scripts/tdq_lsp.py` · `scripts/setup_status.py` · `hooks/scripts/session_start.py` | `git grep` (`CONG_CU`, `TIEN_TO_CAI_DUOC`) + Graphify `query` | Thêm lớp kiểm/cài `rtk` + `rg` theo mẫu `cai_agent_lsp` (GitHub Release + kiểm SHA256 + ghi nguyên tử vào `~/.local/bin` + khóa `TDQ_KHONG_CHAM_MAY=1`), và nhắc gọn `[TDQ:SETUP]` trong `session_start.py` khi thiếu công cụ. |
| `install.py` · `install.ps1` · `install.sh` · `tools/install_agy_plugin.py` | `git grep` + Đọc mã | Bổ sung bước hậu cài plugin: kiểm `rtk` (kèm Collision Guard `rtk --version` + `rtk gain`) và `rg`; nếu thiếu ở terminal TTY thì xin quyền `[y/N]` cài đặt user-level + ghi `config.toml` an toàn; hỗ trợ cờ `--with-rtk` / `--skip-rtk`. |
| `scripts/context_surface.py` | `git grep` + Chạy thực nghiệm | `measure_dispatcher_parity` đo baseline `136.29 ms` (2 tiến trình) vs `68.85 ms` (1 tiến trình, nhanh hơn `49.48%`). |

### Kiến trúc & Ràng buộc luật khóa

- **Luật gọi tầng (`docs/kien-truc.md`):** Code mới thuộc `scripts/rtk_integration.py` (tầng CLI, stdlib only) và `hooks/scripts/command_gate.py` (tầng Hook). `hooks/` được gọi `scripts/rtk_integration.py` bằng `from rtk_integration import ...` (để Graphify tạo cạnh `calls`); `scripts/` tuyệt đối không import `hooks/`.
- **Chuẩn ngôn ngữ & kiểm định:** Comment/docstring và chuỗi máy trong `scripts/` + `hooks/` viết tiếng Anh cố định (`scripts/i18n_check.py`); giữ nguyên 100% file sạch giấy phép MIT trong repo (không nhúng source/binary `rtk`).

### Lộ trình

| Bước/phase | Chạy? | Vì sao |
|---|---|---|
| Research web / API | CÓ (xong) | Đã truy vấn GitHub Releases `rtk-ai/rtk` (`v1.2.0`) và `BurntSushi/ripgrep` (`15.2.0`), kiểm hợp đồng hook Antigravity và đo baseline `context_surface.py` |
| Interview | CÓ (xong) | Đã chốt đủ 6 câu hỏi vòng 1 (`1a 2a 3a 4a 5a 6a`), ghi đầy đủ vào brief và khóa `muc_qc = ultra` |
| Spec + Archify Preview | CÓ | Chạm nhiều tầng (`scripts/`, `hooks/scripts/`, `tools/patches/`, `install.py`), cần khóa hợp đồng và xem trước kiến trúc Trước/Sau |
| Plan + Implement (`mode` do user chọn) | CÓ | Triển khai `red -> green` qua 5 module M1–M5 theo ranh giới call-graph độc lập |
| QC độc lập (`tdq-qc-tester`) | CÓ (`ultra`) | Đúng lựa chọn `5a`: trọn bộ test + smoke + runtime sống + cài thật `rtk` & `rg` kiểm `rtk gain` theo `2a` + `tdq-qc-tester` soi độc lập |
| Report + Archify HTML | CÓ | Xuất báo cáo kèm sơ đồ Archify HTML phục vụ qua Tailscale và hỏi commit/cập nhật local |

## Hỏi đáp

- **Vòng 0 (Chọn pipeline — `2026-11-17T11:43:25+07:00`):**
  1. Chọn pipeline cho yêu cầu tích hợp RTK + trigger xin quyền cài đặt → User trả lời nguyên văn: `"1a"` (chốt `lane = full`, `loai_request = feature`).
- **Vòng 1 (Phỏng vấn chi tiết & Mức QC — chốt ngày `2026-11-17T12:03:19+07:00`, trả lời nguyên văn: `"1a 2a 3a 4a 5a 6a"`):**
  1. Bản phát hành mặc định khi người dùng đồng ý cài `rtk` → User chọn `1a`: bản chính thức đầy đủ `rtk` (`v1.2.0+`) kèm tự kiểm/cài `rg` (`BurntSushi/ripgrep` `15.2.0+`) qua GitHub Release có đối chiếu `SHA256` vào `~/.local/bin` và cập nhật User `PATH`.
  2. Quyền cài thật `rtk` + `rg` user-level trên máy hiện tại để nghiệm thu E2E → User chọn `2a`: cho phép cài thật user-level vào `C:\Users\admin\.local\bin`, thêm vào User `PATH` Windows và ghi cấu hình an toàn `%APPDATA%\rtk\config.toml` (kèm hướng dẫn gỡ sạch) ở pha thi công/QC.
  3. Chính sách nén `git diff` và bảo vệ `pytest` → User chọn `3a`: nén tối đa ở luồng chính (`git diff`/`git log`/`git show` kèm `rtk recall <hash>`), tự miễn nén `git diff` cho subagent kiểm định (`tdq-qc-tester`, `tdq-security-reviewer`, `tdq-reviewer`), giữ nguyên `.venv`/`py -3 -m pytest`, và khóa `exclude_commands = ["grep", "rg"]`.
  4. Cơ chế nhắc `[TDQ:SETUP]` ở `SessionStart` khi thiếu công cụ → User chọn `4a`: `install.py` tương tác hỏi `[y/N]` tại terminal; `SessionStart` nhắc gọn 1 dòng `[TDQ:SETUP]` tối đa 1 lần mỗi phiên và hỗ trợ ghi nhớ ẩn nhắc khi user từ chối.
  5. Mức QC (`muc_qc`) → User chọn `5a`: `ultra` (trọn suite + smoke test + runtime test sống + `tdq-qc-tester` độc lập).
  6. Bổ sung thêm → User chọn `6a`: Không bổ sung thêm.
