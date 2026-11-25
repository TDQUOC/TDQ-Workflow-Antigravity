# QC — Nghiên cứu chi tiết chức năng và tiềm năng ứng dụng Paperclip
Ngày: 2026-11-25 · Plan: ../plan/2026-11-24-2359-research-paperclip-features-apps.md (Vòng 1)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## Dev Behavior QC Card
- Auto Meta-Gate: `KHÔNG ÁP DỤNG` (`work_kind=investigate`, ranh giới `git diff` ngoài `docs/tdq/` rỗng nên áp dụng `QC-I1..I4` thay cho `QC-F1..F4`)
- Luồng đổi: Tổng hợp `4` shard `s1`–`s4`, sổ bằng chứng `evidence.jsonl`, ma trận chấm điểm `feature-and-application-matrix.md`, báo cáo `2` tầng và Archify HTML trực quan.
- Chạy thử thật (Before -> After + Bằng chứng tươi): Từ chưa có hồ sơ kiểm chứng, sau `T3.1` đạt `28/28` dòng bằng chứng hợp lệ (`line_errors=0`), `28/28` ID được trích dẫn đầy đủ (`missing=0`), `0` placeholder, `12/12` đối chiếu `L2` khớp nguyên văn, `doc_lint.py` exit `0`, `tdq_archify.py verify` trả `status=current`, và Tailscale Serve trả `TAILSCALE_HTTP 200 bytes 1226606`.
- Rủi ro còn lại: Không cài đặt hoặc chạy server Paperclip thực tế tại máy (theo phạm vi chỉ đọc), nên dự báo ma sát runtime trên Windows mang nhãn `Inferred` từ tài liệu `Verified`.

| # | Hạng mục | Lệnh đã chạy | Kết quả | PASS/FAIL |
|---|---|---|---|---|
| Q1 | `QC-I1` Grounding tự động (`100%` ID, biên dòng `path:line`, `0` placeholder) | Script Python rà `evidence.jsonl`, `report.md`, `feature-and-application-matrix.md` | `FINAL_Q1: rows=28 line_errors=0 cited=28 missing=0 placeholders=0` | **PASS** |
| Q2 | `QC-I2` Đối chiếu nguyên văn `L2` (`paperclip` và `TDQ-Workflow-Antigravity`) | Đọc nguyên văn `12` lát cắt nguồn qua script Python đối chiếu trực tiếp trên đĩa | `12/12` đoạn nguồn khớp thông số (16 adapters, khóa `darwin-arm64`, `local_trusted`, quarantine, same-origin UI, `hard_stop`, brake, `npx`) | **PASS** |
| Q3 | `QC-I3` Kiểm chứng `4` giả thuyết `H1`–`H4` kèm phản ví dụ / giới hạn | Rà `H1`–`H4` trong `report.md` và `s1`–`s4` | Đủ `4/4` giả thuyết (`H1..H4=True`), nêu rõ phần chưa làm (`Planned`), lỗ hổng Windows và danh sách cấm copy | **PASS** |
| Q4 | `QC-I4` Nhãn độ tin cậy & tài liệu sạch lỗi `doc_lint.py` | `py -3 -X utf8 scripts/doc_lint.py` trên `report.md`, `feature-and-application-matrix.md`, `qc.md` | `0 violation(s) total, exit 0` | **PASS** |
| Q5 | Ranh giới phạm vi `0` file code sửa, Archify HTML `current` & Tailscale `200` | `git status` `paperclip`, `git diff` TDQ, `tdq_archify.py verify`, `urllib.request.urlopen` | Hai repo `0` file code sửa, Archify `status: current`, `TAILSCALE_HTTP 200 bytes 1226606` | **PASS** |

## Bằng chứng

### Q1
```text
FINAL_Q1: rows=28 line_errors=0 cited=28 missing=0 placeholders=0
```

### Q2
```text
--- C:/Users/admin/Documents/paperclip/server/src/adapters/builtin-adapter-types.ts:4-21 (total=21) ---
16 builtin adapters: acpx_local, claude_local, codex_local, paperclip_runner, cursor_cloud, cursor, gemini_local, grok_local, hermes_gateway, hermes_local, kimi_local, openclaw_gateway, opencode_local, pi_local, process, http
--- C:/Users/admin/Documents/paperclip/server/src/services/native-runtime/acpx-qualification.ts:5-24 (total=86) ---
if (!encoded || !input.companyId || process.platform !== "darwin" || process.arch !== "arm64") return undefined;
--- C:/Users/admin/Documents/paperclip/doc/DEPLOYMENT-MODES.md:81-87 (total=240) ---
On Linux and macOS, a request that comes from inside an agent run's process tree receives no implicit board access... Other platforms keep the previous behavior.
--- C:/Users/admin/Documents/paperclip/doc/MCP-ACCESS-GOVERNANCE.md:213-230 (total=474) ---
Paperclip sets status: quarantined and records the reason in quarantineReason.
--- C:/Users/admin/Documents/paperclip/doc/plugins/PLUGIN_SPEC.md:15-35 (total=1994) ---
Plugin UI bundles currently run as same-origin JavaScript inside the main Paperclip app.
--- C:/Users/admin/Documents/paperclip/server/src/services/budgets.ts:365-390 (total=1405) ---
.for("update") ... pauseReason: "budget"
--- C:/Users/admin/Documents/paperclip/server/src/services/recovery/automatic-run-brake.ts:8-32 (total=633) ---
windowMs: 10 * 60_000, minCounted: 12, failureShare: 0.8, consecutiveProviderRefusals: 5, state: "closed" | "open" | "half_open"
--- C:/Users/admin/Documents/paperclip/skills/paperclip/SKILL.md:20-31 (total=809) ---
CLI safety — use npx paperclipai for content-bearing arguments... Do not use pnpm paperclipai for such an argument.
--- README.md:28-65 · docs/kien-truc.md:1-45 · README-Antigravity.md:1-25 ---
TDQ 6 tru cot bat bien, tach tang scripts/hooks/skills, plugin native Antigravity (8 Subagents, 12 Skills, 6 Hooks, 10 Rules).
```

### Q3
```text
H_IN_REPORT={'H1': True, 'H2': True, 'H3': True, 'H4': True}
H1-H4 trong report.md va s1..s4 deu co ket luan ro rang + phan vi du/gioi han va bang cam copy sang TDQ.
```

### Q4
```text
[2026-11-25T11:03:33] doc_lint: lint 2 file: feature-and-application-matrix.md, 2026-11-24-2359-research-paperclip-features-apps.md
[2026-11-25T11:03:33] doc_lint: R16 2026-11-24-2359-research-paperclip-features-apps.md → 0 finding(s)
[2026-11-25T11:03:33] doc_lint: done — 0 violation(s) total, exit 0
```

### Q5
```text
=== PAPERCLIP GIT STATUS ===
(empty)
=== TDQ CODE DIFF ===
(empty)
--- tdq_archify.py verify ---
"status": "current", "valid": true, "reasons": [],
"document_digest": "41b22ad7f9b68657a7bad6d88e423cbc94470bfa4205d707355fc450349e044d",
"manifest_digest": "f04ae4d9ffb66a85d9d5fe838d71152c9dee6bbafeb621709e23e09d689a7888"
--- Tailscale Serve ---
TAILSCALE_HTTP 200 bytes 1226606
```

## Lệch spec chờ duyệt
không có

## Kết luận
PASS toàn bộ (`5/5` hạng mục `Q1`–`Q5`, `QC-I1..I4` đạt sạch trên tài liệu nghiên cứu, không chạm mã nguồn sản phẩm).
