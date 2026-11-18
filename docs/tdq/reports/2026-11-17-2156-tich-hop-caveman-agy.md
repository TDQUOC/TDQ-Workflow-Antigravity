# REPORT — Tích hợp Caveman 5 hướng tối ưu ngữ cảnh và xin quyền vào TDQ-Workflow-Antigravity (`2026-11-17-2156-tich-hop-caveman-agy` · lane full · mode subagent · 15/15 task tick đủ · giao sub-agent 7/15 task)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

**Trước request (trạng thái/flow):** `3` server MCP mặc định (`lsp`, `chrome-devtools`, `tavily-primary`, tổng `108` tool cả backup) nạp thô `99.968` ký tự (`~24.992` token) mô tả & metadata thừa mỗi phiên; `6` subagent chưa ép chuẩn trả về `Compact Handoff` + `Auto-Clarity`; file dữ liệu và DOM lớn `> 32 KB` không có kho lưu khôi phục `SHA-256`; `token_audit.py` chỉ đọc nhật ký Claude Code; và chỉ có cơ chế xin quyền cài đặt cho `RTK`, chưa có cờ opt-in cho Caveman.
**Sau request (trạng thái/flow):** Bổ sung trọn bộ `5` module Python stdlib (`100%` giấy phép `MIT`, cộng sinh `RTK v1.2.0`) kích hoạt opt-in qua `--with-caveman` (`~/.tdq/caveman.json`) · **Đã làm:** `P1` tạo `scripts/tdq_mcp_shrink.py` (proxy `stdio` JSON-RPC 2.0 cắt metadata dư, giữ nguyên khóa schema, từ phủ định & `tools/call`) + `context_surface.py --mcp-prefix` · `P2` chuẩn `Compact Handoff` (`path:line — symbol — note`) & `Auto-Clarity` cho `6` `agents/tdq-*.md`, `skills_and_agents.py`, `agy_hooks.py` và hướng dẫn `CCR` tại `skills/tdq-browser-research/SKILL.md` · `P3` tạo `scripts/tdq_ccr.py` (ngưỡng `> 32 KB` / `>= 200` dòng, trần `128 MB`, khớp `100%` `SHA-256`) + nhắc không chặn trong `hooks/scripts/read_gate.py` · `P4` mở rộng `scripts/tdq_transcript.py` & `scripts/token_audit.py` kiểm toán đa host (`Antigravity`, `Codex`, `Claude Code`, mặc định `5` phiên, nhãn `measured`/`inferred`) · `P5` tạo `scripts/caveman_config.py`, tích hợp `--with-caveman`/`--without-caveman`/`--check-caveman`/`--mute-caveman-prompt` vào `scripts/tdq_setup.py`, `scripts/tdq_lsp.py check`, `hooks/scripts/session_start.py`, `tools/patches/agy_manifests.py`, `tools/install_agy_plugin.py`, `install.py`, `install.ps1`, `install.sh` · `P6` biên dịch `plugins/tdq-workflow-agy/`, khóa `docs/tdq/token-budget.json`, đồng bộ bản cài cục bộ `~/.gemini/config/plugins/tdq-workflow-agy` và chạy E2E sống · `P7` kiểm log `TDQ_LOG=0` và trọn bộ `tdq_test.py tron-bo`.
**Đã test gì:** Unit test cho từng module mới & vùng chạm (`test_tdq_mcp_shrink`, `test_subagent_start`, `test_agent_frontmatter`, `test_tdq_ccr`, `test_read_gate`, `test_transcript`, `test_token_audit`, `test_caveman_setup`, `test_tdq_setup_rtk`, `test_tdq_setup`, `test_tdq_lsp`, `test_installer_rtk_trigger`, `test_agy_plugin_validate`, `test_build_portable`), trọn bộ `207` module `tdq_test.py tron-bo --workers 4 --fresh --reuse off` sau lần sửa cuối, linter (`doc_lint`, `i18n_check`, `token_budget --kiem`, `tdq_checkportable`), `agy.EXE plugin validate --strict --json`, và E2E sống trên bản cài cục bộ (`agent-lsp` qua proxy `M1`, CCR `SHA-256`, `token_audit --host all --sessions 5`, `tdq_setup --check-caveman`).
**Kết quả test:** `tdq_test.py tron-bo` đạt `PASS` `4.350/4.350` ca thu thập (`35` skipped do thiếu `anthropic-tokenizer` ở test tokenizer Claude cũ, `0` failed trong `346,29s`; `radius misses: 0`) · **Kết quả:** schema `108` tool MCP `99.968 → 73.578` ký tự (`-26,4%`); live `agent-lsp` `65` tool `61.106 B → 44.662 B` (`-26,9%`, `11,8 ms`); live CCR `36.010 B` khôi phục `SHA-256` khớp `100%`; `token_audit` quét `8` phiên thật (`5 agy + 3 codex`) · **Kiểm:** `doc_lint` `0` lỗi, `i18n_check` `0` dòng tiếng Việt ở `9` file mới/sửa, `token_budget --kiem` `62` lock OK, `agy.EXE plugin validate` `0 findings` · QC `PASS 10/10` hạng mục (`Q1`–`Q6` & `QC-F1`–`QC-F4`, đã sửa `1` defect đăng ký `APPROVED_RUNTIME_MODULES` trong `tests/test_build_portable.py` trước lần chạy `tron-bo` cuối).
**Đầu ra:** `scripts/tdq_mcp_shrink.py`, `scripts/tdq_ccr.py`, `scripts/caveman_config.py`, `scripts/context_surface.py`, `scripts/tdq_transcript.py`, `scripts/token_audit.py`, `scripts/tdq_setup.py`, `scripts/tdq_lsp.py`, `hooks/scripts/read_gate.py`, `hooks/scripts/session_start.py`, `agents/tdq-*.md`, `skills/tdq-browser-research/SKILL.md`, `tools/patches/*`, `tools/install_agy_plugin.py`, `install.*`, `plugins/tdq-workflow-agy/**` · **Archify HTML:** `docs/tdq/reports/2026-11-17-2156-tich-hop-caveman-agy.html` · Backup: `~/.gemini/config/plugins/tdq-workflow-agy/mcp_config.json.bak`, `~/.tdq/caveman.json`
**Giới hạn:** `ruff` chưa có binary toàn cục trên PATH Windows nên ghi nhận `chưa kiểm tra`; `anthropic-tokenizer` chưa cài trong env mặc định nên `35` ca (gồm `9` ca `test_token_audit.py`) skip có điều kiện và `token_audit` đa host xuất nhãn `inferred`; `eval: chưa kích hoạt (opt-in)`.
**Lệch spec chờ duyệt:** không có
**Git:** Nhánh `feature/tich-hop-caveman-agy` có các commit trung gian do team merge & gỡ block merge (`9341ab65`..`7aeb788e`, chưa push), và đang có chỉnh sửa cuối `tests/test_build_portable.py` + tài liệu `docs/tdq/` chờ bạn quyết định commit.

## Thời gian

Request `2026-11-17-2156-tich-hop-caveman-agy` · lane full · opened at 2026-11-17T23:22:20+07:00

| Phase | Wall clock | API request | Tool wait | Background job | Observed union | Unattributed | Times entered |
|---|---|---|---|---|---|---|---|
| idle | 11s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| analyze | 12h 05min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| spec | 32 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| plan | 7 min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| implement | 1h 13min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| qc | 38s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| report | 1s | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | 1 |
| Total | 13h 58min | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] | — [unavailable] |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
- api_request_seconds: no_usable_source
- tool_call_seconds: no_usable_source
- background_job_seconds: no_usable_source
- observed_union_seconds: no_usable_observations
- unattributed_seconds: wall_minus_observed_union;no_usable_observations

## Thân PR (soạn sẵn)

**Tóm tắt:** Tích hợp `5` module tối ưu ngữ cảnh & token chuẩn Caveman (`M1` proxy MCP schema `tdq_mcp_shrink.py`, `M2` `Compact Handoff` & `Auto-Clarity`, `M3` kho lossless `CCR` `tdq_ccr.py` + nhắc `read_gate.py`, `M4` kiểm toán đa host `token_audit.py`, `M5` cấu hình opt-in `--with-caveman` trong `tdq_setup.py` & installer) bằng `Python stdlib` thuần (`100%` `MIT`, cộng sinh `RTK v1.2.0`), đồng thời biên dịch và kiểm chứng trên `plugins/tdq-workflow-agy/`.
**Trước/Sau:** `docs/tdq/spec/2026-11-17-2156-tich-hop-caveman-agy-preview.html` · Báo cáo: `docs/tdq/reports/2026-11-17-2156-tich-hop-caveman-agy.html`
**Đã kiểm:**
`py -3 scripts/tdq_test.py tron-bo --workers 4 --fresh --reuse off` → `PASS (4350 tests, 35 skipped, 0 failed in 346.29s)`
`py -3 -m pytest tests/test_build_portable.py -v` → `38 passed, 4 subtests passed in 8.61s`
`py -3 -m unittest tests/test_tdq_mcp_shrink.py tests/test_tdq_ccr.py tests/test_caveman_setup.py tests/test_transcript.py -v` → `PASS (81/81)`
`py -3 scripts/context_surface.py --mcp-prefix --quiet` → `108 tools: 99.968 -> 73.578 chars (-26.4%)`
`py -3 scripts/token_audit.py --host all --sessions 5 --top 5` → `PASS (scanned 8 sessions: 5 agy + 3 codex, basis=inferred)`
`agy.EXE plugin validate --strict --json plugins/tdq-workflow-agy` → `findings: []`
`py -3 scripts/token_budget.py --kiem && py -3 scripts/doc_lint.py docs/tdq/spec/2026-11-17-2156-tich-hop-caveman-agy.md` → `0 violations`
**Rủi ro hồi quy:** `hooks/scripts/read_gate.py` & `hooks/scripts/session_start.py` giữ nguyên cơ chế không chặn (`allow`) và nhánh `RTK` cũ (`test_read_gate.py` `21/21`, `test_tdq_setup_rtk.py` `7/7` xanh); `tests/test_build_portable.py` đã đăng ký `3` module runtime mới vào `APPROVED_RUNTIME_MODULES` (`38/38` xanh) để không gãy release `--sinh-main`.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-17-2156-tich-hop-caveman-agy.manifest.json -->
<!-- manifest_digest: 2ab1afeb3adf79513389f699cdb2869c6c5d7b23ca53319fad1b0f3032fda0c2 -->
<!-- tdq-archify-binding:end -->