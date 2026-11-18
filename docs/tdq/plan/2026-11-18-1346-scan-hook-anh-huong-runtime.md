# PLAN — Scan ảnh hưởng của hook TDQ tới runtime & đề xuất hook dạng hướng dẫn

Ngày: 2026-11-18 · Spec: ../spec/2026-11-18-1346-scan-hook-anh-huong-runtime.md (bản 1.1, ĐÃ DUYỆT) · Lane: full
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: subagent — `tdq_bench.py simulate --he-so-agent 1.5` cho Winner: đội, nhanh hơn 5,1 phút (14,3 → 9,2 phút model): T1.2/T1.3/T1.4 độc lập sau T1.1, mỗi task một file riêng (ĐỀ XUẤT, user chốt lúc duyệt)
Trạng thái plan: ĐÃ DUYỆT

## Mục lục

- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- P1 — Bằng chứng đo
- P2 — Kiểm kê cổng & lời chỉ dẫn
- P3 — Báo cáo nghiên cứu
- Cụm song song
- Luật file nóng
- Px — Log & test bắt buộc
- Definition of Done

## Quy tắc thi hành (áp cho mọi task)

1. Thứ tự phase là thứ tự phụ thuộc — không đảo.
2. Mỗi task: đánh `[~]` khi bắt đầu → chạy kiểm (đỏ khi chưa có đầu ra) → làm → kiểm xanh → đổi sang `[x]` NGAY vào file này.
3. KHÔNG sửa file ngoài `docs/` (spec 1c). Script đo chỉ ĐỌC bản cài `~/.gemini/config/plugins/tdq-workflow-agy` và transcript.
4. Mọi lệnh chạy hook bản cài dùng `session_id` bắt đầu bằng `bench-`, xóa file runtime `*bench*` sau đo; repo thử commit/merge nằm trong thư mục tạm của hệ điều hành.
5. QC FAIL → thêm task fix vào mục QC của file này, loop đến khi pass.
6. Không commit/push cho đến khi user yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (ANTI-1 Fake Red, ANTI-2 Blind Assertion, ANTI-3 Dirty State Git, ANTI-4 Late Tick, ANTI-5 Raw Dump, ANTI-6 Broad Area).

## Thiết kế Trước vs Sau

Không áp dụng cho mã nguồn: request không sửa sản phẩm. Bảng Trước/Sau của thiết kế hook ĐỀ XUẤT nằm ở spec §2c và sẽ được trình bày lại trong báo cáo (T3.1) + Archify HTML phase report.

## P1 — Bằng chứng đo

- [x] **T1.1** (e6m) Đưa 4 script đo (`bench_hooks.py`, `hook_impact.py`, `long_turns.py`, `model_latency.py`) vào thư mục bằng chứng, thêm cờ `--json <file>`, chạy và lưu kết quả — Test: `py -3 -c "import json,glob; fs=glob.glob('docs/tdq/bench/2026-11-18-1346-hook-runtime/*.json'); assert len(fs)==4; [json.load(open(f,encoding='utf-8')) for f in fs]"`
  - Chạm: `docs/tdq/bench/2026-11-18-1346-hook-runtime/`
  - Mục tiêu: biến số đo ở brief thành bằng chứng tái chạy được (Q1).
  - Ràng buộc: thuần stdlib; không ghi vào state; N bench ≥ 12.
- [ ] **T1.2** (e8m) Viết & chạy `commit_merge_trial.py`: repo tạm 200 file, đo `git add -A`, `git commit`, `git switch -c` + `git merge --no-ff` thuần và khi mỗi lệnh đi qua `command_gate.py` bản cài (spawn hook với payload `run_command` trước lệnh), N ≥ 5 — Test: `py -3 -c "import json; d=json.load(open('docs/tdq/bench/2026-11-18-1346-hook-runtime/commit_merge_trial.json',encoding='utf-8')); assert d['n']>=5 and d['git_only']['median_ms']>0 and d['git_with_hook']['median_ms']>0"`
  - Chạm: `docs/tdq/bench/2026-11-18-1346-hook-runtime/commit_merge_trial.py`, `docs/tdq/bench/2026-11-18-1346-hook-runtime/commit_merge_trial.json`
  - Cần: T1.1
  - Mục tiêu: tách phần git + hook khỏi phần model cho ca "commit/merge 15 phút" (Q9).
  - Ca hiểm: git chưa cấu hình user → đặt `-c user.name/-c user.email` trên lệnh; dọn repo tạm cả khi lỗi.
- [ ] **T1.3** (e8m) Tái hiện ca chặn nhầm: đưa các lệnh thật đã bị `[TDQ:SEARCH] malformed` (py `-c`, here-string, `curl ... -split`) qua `search_gate.py`/`command_gate.py` bản cài; đưa `call_mcp_tool` → `chrome-devtools navigate_page/new_page` qua `lsp_gate.py`; dựng chuỗi edit không tick để xem `[TDQ:TICK]` trong `TDQ_PROJECT_DIR` tạm — Test: `py -3 -c "import json; d=json.load(open('docs/tdq/bench/2026-11-18-1346-hook-runtime/false_positive_repro.json',encoding='utf-8')); assert len(d['cases'])>=3 and all(k in {c['group'] for c in d['cases']} for k in ('search_malformed','lsp_non_lsp','tick_loop'))"`
  - Chạm: `docs/tdq/bench/2026-11-18-1346-hook-runtime/false_positive_repro.py`, `docs/tdq/bench/2026-11-18-1346-hook-runtime/false_positive_repro.json`
  - Cần: T1.1
  - Mục tiêu: bằng chứng chặn nhầm cho Q5.
- [ ] **T1.4** (e6m) Phân rã ≥ 6 lượt dài (gồm `f9e21752` "1 commit") thành 5 thành phần: chờ lỗi API, model sinh (kèm token/cache), tool, hook ước tính, deny/Stop; tính độ phủ = tổng thành phần / thời lượng — Test: `py -3 -c "import json; d=json.load(open('docs/tdq/bench/2026-11-18-1346-hook-runtime/long_turns.json',encoding='utf-8')); ts=d['turns']; assert len(ts)>=6 and any(t['conv'].startswith('f9e21752') for t in ts) and all(t['do_phu']>=0.9 or t.get('ghi_chu') for t in ts)"`
  - Chạm: `docs/tdq/bench/2026-11-18-1346-hook-runtime/long_turns.py`, `docs/tdq/bench/2026-11-18-1346-hook-runtime/long_turns.json`
  - Cần: T1.1
  - Mục tiêu: trả lời "tại sao lâu" (Q7).

**Xong P1 khi**: 6 file JSON bằng chứng tồn tại và parse được; `git status --short` không có file ngoài `docs/`.

## P2 — Kiểm kê cổng & lời chỉ dẫn

- [ ] **T2.1** (e12m) Kiểm kê toàn bộ mã chặn/nhắc `[TDQ:*]` trong `hooks/scripts/*.py` (grep `MA =`, `block(`, chuỗi `[TDQ:`): mỗi mã một dòng gồm sự kiện, điều kiện, số deny đo được, phân loại (chặn cứng / tự sửa `overwrite` / hướng dẫn / xóa), lời hiện tại và lời đề xuất 4 phần — Test: `py -3 -c "import json; d=json.load(open('docs/tdq/bench/2026-11-18-1346-hook-runtime/gate_inventory.json',encoding='utf-8')); assert d['grepped_count']==len(d['cong']) and all(all(r['loi_de_xuat'].get(k) for k in ('chuyen_gi','vi_sao','lam_gi','bo_qua')) for r in d['cong'])"`
  - Chạm: `docs/tdq/bench/2026-11-18-1346-hook-runtime/gate_inventory.py`, `docs/tdq/bench/2026-11-18-1346-hook-runtime/gate_inventory.json`
  - Cần: T1.3
  - Mục tiêu: Q2 + Q8.
  - Dùng: `tdq-lean`
  - Để: soát từng cổng xem XÓA được không trước khi làm mềm, nạp skill TRƯỚC bước đỏ
  - Ra: cột `phan_loai` có giá trị `xoa` cho cổng thừa (nếu có) trong `gate_inventory.json`
  - Kiểm: `py -3 -c "import json; d=json.load(open('docs/tdq/bench/2026-11-18-1346-hook-runtime/gate_inventory.json',encoding='utf-8')); assert all(r['phan_loai'] in ('chan_cung','tu_sua','huong_dan','xoa') for r in d['cong'])"`
  - Không dùng cho: viết lại code hook (ngoài phạm vi 1c)

**Xong P2 khi**: `gate_inventory.json` đủ mã, đủ 4 phần lời chỉ dẫn.

## P3 — Báo cáo nghiên cứu

- [ ] **T3.1** (e18m) Viết báo cáo 9 mục (a–i theo spec §3c bước 5), mọi số trích từ JSON P1/P2, ước tính tiết kiệm ghi công thức = chi phí đo × tần suất đo; đối chiếu hợp đồng hook `agy-customizations` (`hooks.md`) — Test: `py -3 scripts/doc_lint.py docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md`
  - Chạm: `docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md`
  - Cần: T1.2, T1.4, T2.1
  - Dùng: `agy-customizations (docs/hooks.md)`
  - Để: trích đúng kênh `overwrite`, `metadata.user_markdown`, `continuationActive`, giới hạn "hooks run synchronously", nạp skill TRƯỚC bước đỏ
  - Ra: mục (g) của `docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md` dẫn dòng tài liệu hook
  - Kiểm: `rg -n "overwrite|user_markdown|continuationActive|synchronously" docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md`
  - Không dùng cho: tạo hook/plugin mới
  - Dùng: `tdq-conventions`
  - Để: định dạng báo cáo, Soul line, quy ước trình bày, nạp skill TRƯỚC bước đỏ
  - Ra: dòng Soul ở dòng 2 của `docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md`
  - Kiểm: `rg -n "^Soul:" docs/tdq/research/2026-11-18-1346-scan-hook-anh-huong-runtime.md`
  - Không dùng cho: report phase (do phase `report` lo)

**Xong P3 khi**: báo cáo đủ 9 mục, lint 0, mọi con số có nguồn JSON.

## Cụm song song

Đợt 1: T1.1 (leader). Đợt 2 song song: T1.2, T1.3, T1.4 — mỗi task ghi một file riêng trong thư mục bằng chứng, chỉ đọc script T1.1. Đợt 3: T2.1 (cần T1.3). Đợt 4: T3.1 (leader, cần toàn bộ). Đo `tdq_bench.py simulate`: đội 9,2 phút vs chính 14,3 phút.

## Luật file nóng

Không có file nào bị từ 2 task trở lên khai ở `Chạm:` (T1.1 khai thư mục; T1.2–T2.1 mỗi task một file riêng trong thư mục đó) — cách xử lý: **một chủ ghi duy nhất** (hội thoại chính).

## Px — Log & test bắt buộc

Log: BỎ — không có task tạo/sửa mã sản phẩm chạy được; script đo là công cụ bằng chứng, in kết quả ra stdout/JSON.

- [ ] **Tx.2** Kiểm tái chạy bằng một lệnh cho mỗi script bằng chứng — Test: `py -3 docs/tdq/bench/2026-11-18-1346-hook-runtime/bench_hooks.py --json <tmp>` và `hook_impact.py --json <tmp>` exit 0, số lệch ≤ 20% so với bản lưu

## Definition of Done

- [ ] Q1 Số đo tái lập (lệch ≤ 20%) — chạy lại `bench_hooks.py`, `hook_impact.py` và so với JSON đã lưu
- [ ] Q2 Kiểm kê cổng đủ 100% mã — so số mã grep `hooks/scripts/*.py` với số dòng `gate_inventory.json`
- [ ] Q3 Không sửa mã sản phẩm — `git diff --stat dev` + `git status --short` chỉ có `docs/`
- [ ] Q4 Tài liệu sạch — `py -3 scripts/doc_lint.py` trên spec/plan/research/report = 0 vi phạm
- [ ] Q5 Ca chặn nhầm có bằng chứng — `false_positive_repro.json` đủ 3 nhóm ca
- [ ] Q6 Ước tính truy được — mỗi con số tiết kiệm trong báo cáo có công thức + nguồn JSON
- [ ] Q7 Trả lời "tại sao lâu" — `long_turns.json` ≥ 6 lượt, `do_phu >= 0.9` hoặc ghi lý do
- [ ] Q8 Lời chỉ dẫn đủ 4 phần — kiểm `gate_inventory.json` mọi dòng có 4 khóa không rỗng
- [ ] Q9 Thử commit/merge — `commit_merge_trial.json` có median 2 nhánh, N ≥ 5
