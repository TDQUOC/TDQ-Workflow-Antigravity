# PLAN — Phân tích chuyên sâu, Phản biện Red-Team & Đề xuất Kiến trúc `work_kind=investigate` (Thuần `docs`)

Ngày: 2026-11-21 · Spec: ../spec/2026-11-20-2355-toi-uu-research-phan-tich.md (bản 2.0, ĐÃ DUYỆT) · Lane: full · Loại: docs (Zero-Code-Touch)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — đo thực tế bằng `tdq_bench.py simulate` (`--he-so-agent 1.5`): đội thắng `main` `17.2` phút (`15.3` phút vs `32.6` phút, `5` đợt song song; 2 wave fan-out `3` nhánh độc lập)
Trạng thái plan: HOÀN THÀNH

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Wave 1 Thu thập Đa chiều song song (Collect)
- P2 — Wave 2 Kho Bằng chứng Wave 1 & Tổng hợp Đề xuất V1
- P3 — Wave 3 Phản biện Red-Team Độc lập 3 Chiều (A · B · C)
- P4 — Wave 4 Cập nhật Kho Bằng chứng & Hội tụ Đề xuất Hoàn chỉnh V2
- Cụm song song
- Luật file nóng (một file, nhiều task chạm)
- P5 — Kiểm chứng Bằng chứng & Zero-Code-Touch
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md) (`tdq-config.json`: `gemini-3.8-flash` → `gemini-4-hydrogen` → `gemini-4-neon` → `gemini-4-carbon`).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | Wave 1 (`T1.1` Thực nghiệm · `T1.2` Codebase · `T1.3` Research ngoài) | `inherit` (`gemini-4-neon`) | `high` | Chạy song song 3 nhánh cô lập (`research` / `self`), xuất raw findings ra đĩa, trả digest `<= 1,500` ký tự; user được đổi model lúc duyệt |
| `implement` | Wave 2 & Wave 4 Leader (`T2.1` `evidence-log.md` · `T2.2` Đề xuất V1 · `T4.1` Đề xuất V2) | `inherit` (`gemini-4-neon`) | `xhigh` | Tổng hợp xuyên tầng, ghi checkpoint bền vững chống mất dữ liệu khi `/compact` |
| `implement` | Wave 3 Red-Team A · B · C (`T3.1`, `T3.2`, `T3.3`) | `inherit` (`gemini-4-neon`) / `pro` (`gemini-4-carbon` cho Red-Team B bảo mật) | `high` | Chạy song song 3 luồng phản biện độc lập trên bản V1, định danh `ND-1`..`ND-k` |
| `qc` | Leader + `tdq-reviewer` (QC bằng chứng FActScore, chống F6, Zero-Code-Touch) | `inherit` (`gemini-4-neon`) | `high` | Kiểm chéo `100%` `path:line` trên đĩa, đối chiếu raw `evidence-log.md`, kiểm `0` tệp mã nguồn bị sửa |
| `report` | Leader (Báo cáo Đề xuất V2 Markdown + Archify HTML) | `inherit` (`gemini-4-neon`) | `high` | Xuất `docs/tdq/reports/2026-11-20-2355-toi-uu-research-phan-tich.{md,html}` và xác minh Tailscale HTTP `200` |

## Quy tắc thi hành (áp cho mọi task)
1. **Zero-Code-Touch:** Tuyệt đối không chỉnh sửa bất kỳ tệp nào ngoài `docs/` (`scripts/`, `hooks/`, `skills/`, `agents/`, `tools/`, `plugins/`, `tests/`, `tdq-config.json`, `~/.gemini/`).
2. **Thứ tự wave:** Hoàn tất đủ wave trước và ghi checkpoint vào `evidence-log.md` + `docs/workinglog/2026-11-21.md` trước khi mở wave tiếp theo để không mất dữ liệu nếu phiên bị `/compact`.
3. **Tick ngay tức thì:** Đánh `[~]` (leader) hoặc `[>]` (subagent fan-out) khi bắt đầu, chuyển `[x]` ngay khi lệnh kiểm `Test:` của task đạt xanh.
4. **Chống tam sao thất bản:** Mọi subagent đổ toàn bộ số liệu, trích dẫn `path:line` và URL đã kiểm chứng vào tệp artifact riêng của mình, chỉ trả digest `<= 1,500` ký tự về leader.
5. **QC FAIL:** Nếu phát hiện `path:line` lệch, lỗi F6 hay thiếu truy vết `ND-*` → thêm task fix `QCn.x` và sửa phẫu thuật tới khi PASS.
6. Không commit/push cho đến khi user yêu cầu.

## Thiết kế Trước vs Sau
| Khía cạnh | Hiện trạng (Trước) | Quy trình thực thi & Đề xuất V2 (Sau) |
|---|---|---|
| Trọng tâm thực thi của request phân tích này | Làm gần hết phân tích ở `analyze`/`spec`, `implement` chỉ chép lại báo cáo | Toàn bộ `3` nhánh Collect, Đề xuất V1, `3` luồng Red-Team A/B/C và Đề xuất V2 chạy trong `implement` |
| Chống mất dữ liệu khi `/compact` | Dữ kiện research nằm rải rác trong lịch sử chat | Ghi `EV-xxx` vào `evidence-log.md` + workinglog sau mỗi wave; mọi subagent đổ raw artifact ra đĩa |
| Phạm vi chạm mã nguồn | Spec v1.0 cũ định sửa code trực tiếp `6` module | Thuần `docs` (`0` tệp mã nguồn bị sửa); ra Báo cáo Đề xuất Hoàn chỉnh V2 để user duyệt trước khi mở request code |

*Đối chiếu sơ đồ kiến trúc:* Tham chiếu Archify HTML Preview đã duyệt `docs/tdq/spec/2026-11-20-2355-toi-uu-research-phan-tich-preview.html` và manifest `docs/tdq/spec/2026-11-20-2355-toi-uu-research-phan-tich-preview.manifest.json` (`status: current`).

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ngôn ngữ báo cáo & hồ sơ: tiếng Việt (`doc_lang=vi`), giữ nguyên tên file/lệnh/ký hiệu kỹ thuật · Mọi `path:line` phải đọc trực tiếp từ đĩa thật · Mọi URL research phải từ `tavily_search`/`tavily_extract` thật · Mọi khẳng định trong V2 phải gắn nhãn độ tin cậy (`Verified` / `Single-source` / `Inferred`).

| Khối Đầu ra (§2b) | Tệp sở hữu & Task | Task tiêu thụ |
|---|---|---|
| **D1 — Thực nghiệm & Evidence Log** | `phan-tich-thuc-nghiem-timing.md` (`T1.1`) · `evidence-log.md` (`T2.1`) | `T2.2`, `T3.1`, `T3.2`, `T3.3`, `T4.1`, `T5.1` |
| **D2 — Codebase, Research Sâu & V1** | `phan-tich-kien-truc-codebase.md` (`T1.2`) · `phan-tich-research-ngoai-sau.md` (`T1.3`) · `de-xuat-kien-truc-v1.md` (`T2.2`) | `T3.1`, `T3.2`, `T3.3`, `T4.1` |
| **D3 — Red-Team 3 Chiều** | `redteam-a-luong-va-compact.md` (`T3.1`) · `redteam-b-bao-mat-va-tinh-tuong-thich.md` (`T3.2`) · `redteam-c-stress-test-cases.md` (`T3.3`) | `T4.1`, `T5.1` |
| **D4 — Hội tụ V2, QC & Report** | `de-xuat-kien-truc-v2.md` (`T4.1`) · `qc/<slug>.md` · `reports/<slug>.{md,html}` | Người dùng cuối & request triển khai tiếp theo |

## P1 — Wave 1 Thu thập Đa chiều song song (Collect)

- [x] **T1.1** (e12m) Phân tích thực nghiệm toàn bộ `173` request trong `docs/tdq/timing.jsonl` và hồ sơ `docs/tdq/{brief,research,spec,plan,reports}/` — tách theo loại (`research`/`analysis`/`audit`/`debug`/`build`) và `quick` vs `full`, đo tỷ trọng từng pha, tỷ lệ `implement=0s`, độ lặp nội dung giữa các tệp — Test: `py -3 -X utf8 -c "t = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/phan-tich-thuc-nghiem-timing.md', encoding='utf-8').read(); assert '173' in t and 'quick' in t and 'full' in t and len(t) > 1500"`
  - Req: `§1, §2#2, Q2` · Ngoài phạm vi: chỉ đọc dữ liệu lịch sử, không sửa `timing.jsonl` hay bất kỳ tệp mã nguồn nào
  - Chạm: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/phan-tich-thuc-nghiem-timing.md` (tạo mới)
  - Cần: `Không`
  - Đầu ra kỳ vọng: bảng thống kê phân vị (median/mean/p90) từng pha, danh sách đầy đủ các ca research/analysis/audit/debug tiêu biểu kèm số giây thực tế và lệnh Python tái lập được.

- [x] **T1.2** (e15m) Kiểm toán sâu toàn bộ điểm chạm Codebase (`scripts/tdq_state.py`, `scripts/tdq_team.py`, `scripts/tdq_bench.py`, `scripts/doc_lint.py`, `hooks/scripts/*`, `hooks/rust/tdq-dispatch/src/*`, `skills/*`, `agents/*`, `tools/patches/*`) và đo chính xác số token dư còn lại của từng tệp luật so với `docs/tdq/token-budget.json` — Test: `py -3 -X utf8 -c "t = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/phan-tich-kien-truc-codebase.md', encoding='utf-8').read(); assert 'tdq_state.py' in t and 'pre_tool_use.rs' in t and 'token-budget.json' in t and len(t) > 2000"`
  - Dùng: `agy-customizations` / `antigravity-guide`
  - Để: đối chiếu chính xác cơ chế lifecycle hooks, frontmatter subagent và giới hạn tool của Google Antigravity 2.0 khi kiểm toán `tools/patches/*` và `hooks/`
  - Ra: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/phan-tich-kien-truc-codebase.md` có mục đối chiếu cụ thể cấu trúc plugin/hook Antigravity 2.0
  - Kiểm: `py -3 -X utf8 -c "t = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/phan-tich-kien-truc-codebase.md', encoding='utf8').read(); assert 'Antigravity' in t and 'PreInvocation' in t and 'skills_and_agents.py' in t"`
  - Không dùng cho: không chỉnh sửa mã nguồn `tools/patches/` hay bản cài ngoài repo `~/.gemini/`
  - Req: `§1, §2#3, §3b, Q2` · Ngoài phạm vi: chỉ đọc và trích `path:line` xác minh từ đĩa thật
  - Chạm: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/phan-tich-kien-truc-codebase.md` (tạo mới)
  - Cần: `Không`

- [x] **T1.3** (e15m) Mở rộng Research ngoài nâng cao (`tavily-primary`: `tavily_search` + `tavily_extract`) đi sâu 3 chuyên đề còn mở: (1) compact-resilient evidence checkpointing & context folding cho agent chạy dài, (2) adaptive budget / early-stopping / error-reflection cap, (3) dual-track verification (FActScore + ALCE F6 + Counterfactual RCA) gọn nhẹ — Test: `py -3 -X utf8 -c "t = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/phan-tich-research-ngoai-sau.md', encoding='utf-8').read(); assert 'http' in t and 'F6' in t and 'compact' in t.lower() and len(t) > 2000"`
  - Req: `§1, §2#3, §3c, Q2` · Ngoài phạm vi: chỉ lưu kết quả vào artifact mới, không ghi đè mã nguồn
  - Chạm: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/phan-tich-research-ngoai-sau.md` (tạo mới)
  - Cần: `Không`
  - Ghi chú MCP: gọi `tavily-primary` (`tavily_search`/`tavily_extract`) qua nhánh `self` độc lập; mọi nguồn phải trích URL thật đã đọc.

**Xong P1 khi**: Cả `3` tệp thu thập Wave 1 hoàn tất, có đủ số liệu đo, `path:line` thật và URL đã xác minh.

## P2 — Wave 2 Kho Bằng chứng Wave 1 & Tổng hợp Đề xuất V1

- [x] **T2.1** (e8m) Khởi tạo kho bằng chứng bền vững `evidence-log.md` và ghi checkpoint toàn bộ dữ kiện đã kiểm chứng từ Wave 1 (`EV-001`..`EV-015+`) kèm timestamp, nguồn, trích đoạn và nhãn độ tin cậy — Test: `py -3 -X utf8 -c "import re; t = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/evidence-log.md', encoding='utf-8').read(); assert len(re.findall(r'\bEV-\d{3}\b', t)) >= 12 and 'Verified' in t"`
  - Req: `§1, §2#1, Q1` · Ngoài phạm vi: chỉ tổng hợp bằng chứng thật đã quan sát ở Wave 1
  - Chạm: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/evidence-log.md` (tạo mới)
  - Cần: `T1.1`, `T1.2`, `T1.3`

- [x] **T2.2** (e15m) Tổng hợp **Đề xuất Kiến trúc V1** đầy đủ `6` mảng (`M1` `work_kind=investigate` cho `quick`/`full`, `M2` `no_worktree` + `evidence` CLI + `doc_lint`/`tdq_bench`, `M3`/`M4` `scoped-write` Python+Rust + nhắc `[TDQ:CHECKPOINT]` + `Compact recovery`, `M5` `investigate-mode.md` + tách Debug-RCA vs Bugfix + `QC-I1..I4`, `M6` AGY parity & chiến lược test) — Test: `py -3 -X utf8 -c "t = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v1.md', encoding='utf-8').read(); assert all(k in t for k in ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'work_kind', 'QC-I1', 'evidence-log')) and len(t) > 3000"`
  - Req: `§1, §2#4, §3c, Q2` · Ngoài phạm vi: không sửa mã nguồn; mọi chữ ký đề xuất phải đối chiếu thật với `T1.2`
  - Chạm: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v1.md`
  - Cần: `T2.1`

**Xong P2 khi**: `evidence-log.md` đã lưu checkpoint Wave 1 (`>= 12` mục `EV-xxx`) và `de-xuat-kien-truc-v1.md` đủ `6` mảng sẵn sàng cho Red-Team tấn công.

## P3 — Wave 3 Phản biện Red-Team Độc lập 3 Chiều (A · B · C)

- [x] **T3.1** (e15m) **Red-Team A (Nhận thức, Compact nhiều vòng & Chi phí Token):** Phản biện độc lập V1 ở góc độ context rot, kịch bản `/compact` `3` lần liên tiếp, điểm mù `read_gate` khi research chủ yếu gọi MCP web (`tavily`/`chrome-devtools`) thay vì `Read`, điểm hòa vốn token khi fan-out vs single-agent, và ranh giới xám Debug-RCA vs Bugfix — Test: `py -3 -X utf8 -c "import re; t = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/redteam-a-luong-va-compact.md', encoding='utf-8').read(); assert len(re.findall(r'\bND-A\d+\b', t)) >= 3 and 'compact' in t.lower()"`
  - Req: `§1, §2#5, Q3` · Ngoài phạm vi: chỉ đọc V1 + codebase để phản biện, không sửa V1 hay mã nguồn
  - Chạm: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/redteam-a-luong-va-compact.md` (tạo mới)
  - Cần: `T2.2`

- [x] **T3.2** (e15m) **Red-Team B (Bảo mật `scoped-write`, Parity Python↔Rust & Xung đột Linter/Token-Budget/Test):** Phản biện độc lập V1 về path traversal `..`, symlink/Windows case-sensitivity, shell bypass, rò quyền `security-reviewer`, xung đột `doc_lint` (R8/R11/R13/R14/R15), `i18n_check`, trần `token-budget.json` thực tế của từng `SKILL.md`, `test_phase_table`, và `tools/patches/agy_hooks.py` — Test: `py -3 -X utf8 -c "import re; t = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/redteam-b-bao-mat-va-tinh-tuong-thich.md', encoding='utf-8').read(); assert len(re.findall(r'\bND-B\d+\b', t)) >= 3 and 'scoped-write' in t.lower()"`
  - Req: `§1, §2#5, Q3` · Ngoài phạm vi: chỉ đọc và kiểm toán, không sửa hook/linter/test
  - Chạm: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/redteam-b-bao-mat-va-tinh-tuong-thich.md`
  - Cần: `T2.2`

- [x] **T3.3** (e15m) **Red-Team C (Stress-Test trên `4` ca thật trong kho `docs/tdq/`):** Mô phỏng walkthrough end-to-end thiết kế V1 trên `4` ca lịch sử thật của repo (`1` research/phân tích `full`, `1` research/audit `quick`, `1` debug-RCA/scan, `1` bugfix có sửa code) để đo tác động thực tế và bắt mọi điểm nghẽn ẩn — Test: `py -3 -X utf8 -c "import re; t = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/redteam-c-stress-test-cases.md', encoding='utf-8').read(); assert len(re.findall(r'\bND-C\d+\b', t)) >= 3 and '2026-11-' in t"`
  - Req: `§1, §2#5, Q3` · Ngoài phạm vi: chỉ đọc hồ sơ thật trong `docs/tdq/`, không sửa dữ liệu lịch sử
  - Chạm: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/redteam-c-stress-test-cases.md` (tạo mới)
  - Cần: `T2.2`

**Xong P3 khi**: Đủ `3` tệp Red-Team A/B/C độc lập, mô phỏng đủ `4` ca thật và định danh rõ mọi mã nhược điểm `ND-A*`, `ND-B*`, `ND-C*`.

## P4 — Wave 4 Cập nhật Kho Bằng chứng & Hội tụ Đề xuất Hoàn chỉnh V2

- [x] **T4.1** (e15m) Hợp nhất toàn bộ mã nhược điểm Red-Team (`ND-1`..`ND-k`), cập nhật checkpoint vào `evidence-log.md` (đạt `>= 20` mục `EV-xxx`) và viết **Đề xuất Kiến trúc Hoàn chỉnh V2** (`de-xuat-kien-truc-v2.md`) truy vết vá `100%` mã `ND-*` kèm lộ trình triển khai từng đợt & bảng độ tin cậy (`Verified`/`Single-source`/`Inferred`) — Test: `py -3 -X utf8 -c "import re; ev = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/evidence-log.md', encoding='utf-8').read(); v2 = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md', encoding='utf-8').read(); assert len(re.findall(r'\bEV-\d{3}\b', ev)) >= 20 and 'ND-1' in v2 and 'Verified' in v2 and len(v2) > 3500"`
  - Req: `§1, §2#1, §2#6, Q1, Q5` · Ngoài phạm vi: chỉ xuất đề xuất V2, không sửa mã nguồn
  - Chạm: `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md` (tạo mới)
  - Cần: `T3.1`, `T3.2`, `T3.3`

**Xong P4 khi**: `evidence-log.md` đạt `>= 20` mục `EV-xxx` và `de-xuat-kien-truc-v2.md` vá kín `100%` nhược điểm Red-Team.

## Cụm song song

- **Đợt 1 (3 nhánh song song độc lập):** `T1.1` (Thực nghiệm `timing.jsonl`) · `T1.2` (Kiểm toán Codebase & token-budget) · `T1.3` (Research ngoài nâng cao qua `tavily-primary`).
- **Đợt 2 (tuần tự hội tụ bởi leader):** `T2.1` (`evidence-log.md`) → `T2.2` (`de-xuat-kien-truc-v1.md`).
- **Đợt 3 (3 luồng Red-Team song song độc lập):** `T3.1` (Red-Team A) · `T3.2` (Red-Team B) · `T3.3` (Red-Team C).
- **Đợt 4 (tuần tự hội tụ & kiểm chứng bởi leader):** `T4.1` (`de-xuat-kien-truc-v2.md` + cập nhật `evidence-log.md`) → `T5.1` (kiểm chứng `path:line`, F6, Zero-Code-Touch).

## Luật file nóng (một file, nhiều task chạm)

- Không có tệp nào bị từ `2` task cùng đợt chạm chung: mỗi nhánh ở Wave 1 (`T1.1`/`T1.2`/`T1.3`) và Wave 3 (`T3.1`/`T3.2`/`T3.3`) ghi vào một tệp `.md` độc lập trong `docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/`. Riêng `evidence-log.md` có **một chủ ghi duy nhất là Leader** (cập nhật tại `T2.1` và nối thêm sau Wave 3 tại `T4.1`).

## P5 — Kiểm chứng Bằng chứng & Zero-Code-Touch

Log: BỎ — request thuần phân tích và đề xuất thiết kế (`loai_request=docs`), không tạo hoặc sửa mã nguồn chạy được; thay bằng ghi checkpoint `evidence-log.md` và `docs/workinglog/` sau mỗi wave.

- [x] **T5.1** (e10m) Chạy kiểm chéo tự động `100%` trích dẫn `path:line` tồn tại thật trên đĩa trong `de-xuat-kien-truc-v1.md` và `de-xuat-kien-truc-v2.md`, kiểm `0` placeholder (`TBD`/`TODO`), kiểm `100%` mã `ND-*` được truy vết trong V2, và kiểm `git diff --name-only dev` có `0` tệp ngoài `docs/` — Test: `py -3 -X utf8 -c "import subprocess; diff = [l for l in subprocess.check_output(['git', 'diff', '--name-only', 'dev'], text=True).splitlines() if l.strip() and not l.startswith('docs/')]; assert not diff, f'Code touched: {diff}'; print('ZERO-CODE-TOUCH OK')"`
  - Cần: `T4.1`

## Definition of Done

Trỏ về §6 của spec `docs/tdq/spec/2026-11-20-2355-toi-uu-research-phan-tich.md` (bản `2.0`, `muc_qc=full`, thuần `docs` & Zero-Code-Touch):

- [x] **Q1** `evidence-log.md` chứa tối thiểu `20` mục `EV-xxx` có đủ timestamp, nguồn (`file:line`/URL/output), trích đoạn thật và nhãn độ tin cậy — `py -3 -X utf8 -c "import re; t = open('docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/evidence-log.md', encoding='utf-8').read(); ids = set(re.findall(r'\bEV-\d{3}\b', t)); assert len(ids) >= 20, len(ids); print('EV count:', len(ids))"`
- [x] **Q2** Đủ `4` tệp Vòng 1 & Đề xuất V1 không placeholder, phủ đủ `173` bản ghi `timing.jsonl` và `6` mảng `M1`–`M6` — `py -3 -X utf8 -c "base='docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/'; fs=['phan-tich-thuc-nghiem-timing.md','phan-tich-kien-truc-codebase.md','phan-tich-research-ngoai-sau.md','de-xuat-kien-truc-v1.md']; texts=[open(base+f, encoding='utf-8').read() for f in fs]; assert all(len(x)>1500 for x in texts) and '173' in texts[0] and all(m in texts[3] for m in ('M1','M2','M3','M4','M5','M6')); print('V1 artifacts OK')"`
- [x] **Q3** Đủ `3` tệp Red-Team độc lập A/B/C mô phỏng đủ `4` ca thật trong kho `docs/tdq/` và định danh rõ `ND-*` — `py -3 -X utf8 -c "import re; base='docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/'; fs=['redteam-a-luong-va-compact.md','redteam-b-bao-mat-va-tinh-tuong-thich.md','redteam-c-stress-test-cases.md']; texts=[open(base+f, encoding='utf-8').read() for f in fs]; assert all(len(re.findall(r'\bND-[ABC]\d+\b', x))>=3 for x in texts); print('Red-Team A/B/C OK')"`
- [x] **Q4** Xác minh tự động `100%` `path:line` trong V1/V2/Report tồn tại thật trên đĩa và trong giới hạn dòng tệp, `0` lỗi F6, đủ nhãn độ tin cậy — `py -3 -X utf8 -c "import os, re; files=['docs/tdq/artifacts/2026-11-20-2355-toi-uu-research-phan-tich/de-xuat-kien-truc-v2.md','docs/tdq/reports/2026-11-20-2355-toi-uu-research-phan-tich.md']; pat=re.compile(r'\`((?:scripts|hooks|skills|agents|tools)/[A-Za-z0-9_./-]+\.(?:py|rs|md|json)):(\d+)(?:-(\d+))?\`'); bad=[]; cnt=0; [((bad.append((f,p,ln)) if (not os.path.isfile(p) or int(ln)>len(open(p,encoding='utf-8',errors='ignore').readlines())) else None), cnt:=cnt+1) for f in files if os.path.isfile(f) for p,ln,_ in pat.findall(open(f,encoding='utf-8').read())]; assert cnt>=10 and not bad, (cnt, bad); print('Verified path:line refs:', cnt)"`
- [x] **Q5** Báo cáo V2 truy vết vá `100%` `ND-*`, `0` vi phạm `doc_lint`, Archify HTML manifest `current` và Tailscale Serve HTTP `200` — `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-20-2355-toi-uu-research-phan-tich.md && py -3 -X utf8 scripts/tdq_archify.py verify --document docs/tdq/reports/2026-11-20-2355-toi-uu-research-phan-tich.md --manifest docs/tdq/reports/2026-11-20-2355-toi-uu-research-phan-tich.manifest.json`
- [x] **Q6** Zero-Code-Touch — `0` tệp ngoài `docs/` bị tạo/sửa/xóa so với nhánh gốc `dev` và plugin ngoài repo `~/.gemini/` giữ nguyên `mtime` — `py -3 -X utf8 -c "import subprocess; lines=[l for l in subprocess.check_output(['git','status','--porcelain'], text=True).splitlines() if l.strip()]; non_docs=[l for l in lines if not l[3:].strip('\"').startswith('docs/')]; assert not non_docs, non_docs; print('ZERO-CODE-TOUCH VERIFIED')"`
