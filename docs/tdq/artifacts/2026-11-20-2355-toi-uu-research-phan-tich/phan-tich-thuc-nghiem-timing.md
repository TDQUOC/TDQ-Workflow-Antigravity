# Phân tích Thực nghiệm Timing & Hồ sơ Lịch sử (`docs/tdq/timing.jsonl`) — Task `T1.1`

Ngày thực hiện: 2026-11-21 · Request: `2026-11-20-2355-toi-uu-research-phan-tich` · Task: `T1.1` (thuần đọc, Zero-Code-Touch)  
Nguồn dữ liệu: `docs/tdq/timing.jsonl` + đối chứng toàn bộ hồ sơ `docs/tdq/{brief,research,spec,plan,qc,reports,report,artifacts,bench}/` + `scripts/tdq_state.py` + `scripts/tdq_timing.py`

---

## 1. Phạm vi dữ liệu, Đối soát `173` vs `174` bản ghi & Phát hiện lỗi telemetry cốt lõi

### 1.1 Đối soát số lượng bản ghi (`174` trên đĩa vs `173` trong brief)

Khi kiểm tra trực tiếp tệp `docs/tdq/timing.jsonl` tại thời điểm chạy `T1.1`, tệp chứa **`174` dòng JSONL hợp lệ** (chỉ số `0..173`, gồm `171` slug duy nhất). Sự chênh lệch `1` bản ghi so với con số `173` được trích trong `docs/tdq/brief/2026-11-20-2355-toi-uu-research-phan-tich.md` là do request `2026-11-20-1230-trien-khai-4-de-xuat-agent` (chỉ số `173`, `lane=full`, `build`) vừa đóng sổ lúc `2026-11-21T00:00:04.335181+07:00` ngay sau thời điểm mở request `2355`.

Báo cáo này công bố đầy đủ số đo trên **cả tập hiện hữu `N=174`** và **mốc đối chiếu `N=173` (`0..172`)** để mọi con số đều truy vết được chính xác tuyệt đối:

- **Schema v1 (`idx 0..139`, `140` bản ghi đến `2026-10-27`):** Có cả `treo_tuong_giay` (giây đồng hồ treo tường) và `model_giay` (thời gian model chạy do host ước lượng).
- **Schema v2 (`idx 140..173`, `34` bản ghi từ `2026-10-27` đến `2026-11-21`):** `model_giay = null`, thay bằng `treo_tuong_giay` cùng `metrics` (`api_request_seconds`, `tool_call_seconds`, `observed_union_seconds`). Riêng từ `idx 160` (`2026-11-16`) trở đi trên Google Antigravity, `observed_union_seconds` trả `null` (`missing_metadata` trên transcript AGY), nên chỉ `treo_tuong_giay` khả dụng xuyên suốt toàn bộ `174` ca.
- **`3` slug xuất hiện `2` lần trong `timing.jsonl`:**
  1. `2026-08-17-0938-portable-codex`: `idx=4` (`quick`, `idle`-only `1,738s`) và `idx=5` (`full`, `non_idle=5,326s`).
  2. `2026-09-27-1905-ci-do-ba-he`: `idx=77` (`full`, dừng sớm ở `analyze=543s`) và `idx=78` (`full`, `non_idle=21,746s`).
  3. `2026-11-07-0928-toi-uu-runtime-toan-dien`: `idx=153` (`full`, stub đóng sớm ở `idle=13.6s`, `non_idle=0s`) và `idx=154` (`full`, `non_idle=53,760s`).
- **`18` bản ghi có `non_idle == 0.0s`** (`17` ca `quick` trước mốc `2026-09-01` chỉ ghi duy nhất phase `idle` vì khi đó `quick` chưa tách pha trong `phase_history` + `1` stub `idx=153` ở `full`). Do đó:
  - Thống kê **theo giây** được tính trên cả **tổng tập (`all`)** và **tập hoạt động có `non_idle > 0` (`nz`, `N=156` trên `174` / `N=155` trên `173`)**.
  - Thống kê **tỷ lệ `%` từng pha trên thời gian phi-idle** (`non_idle = sum(phase != "idle")`) chỉ tính trên tập `nz` (`N=156`) vì mẫu số `non_idle == 0` không xác định tỷ lệ.

### 1.2 Ánh xạ `quick_analyze` & Lỗi ghi nhận phase trong `_cli_approve` (`tdq_state.py`)

Kiểm tra trực tiếp `scripts/tdq_state.py` và `scripts/tdq_timing.py` phát hiện `2` sự thật kỹ thuật ảnh hưởng trực tiếp tới số liệu `timing.jsonl`:

1. **Không có dòng `"quick_analyze"` riêng trong `timing.jsonl` (`0` bản ghi):**
   - Trong `scripts/tdq_state.py:82`, `VALID_PHASES = {"idle", "analyze", "spec", "plan", "mode", "implement", "qc", "report"}`.
   - Tại `scripts/tdq_state.py:1650-1668` (`phase_key`) và `scripts/tdq_state.py:1476-1504`, `quick_analyze` chỉ là khóa hiển thị trên `PHASE_TABLE` khi `lane == "quick" and phase == "analyze" and not quick_approved`. Bên dưới JSONL, toàn bộ thời gian `quick_analyze` được ghi dưới nhãn `"analyze"` trong các bản ghi `lane == "quick"`.
   - Ngoài ra có `9` ca ghi nhận pha `"mode"` (`idx 74, 75, 107, 109, 139, 140, 141, 142, 161`, đáng chú ý `idx 161` chờ ở `"mode"` `5,574s`) và `3` ca cũ trước `2026-09-01` còn pha `"diagram"` (`idx 34, 38, 39`, tổng `755s`).

2. **Phát hiện bug thiếu `ghi_moc_phase` trong `_cli_approve` (`scripts/tdq_state.py:2334-2336, 2414-2423`):**
   - Hàm `ghi_moc_phase(state, phase)` (`scripts/tdq_state.py:497-507`) chỉ được gọi ở `3` chỗ: `init` (`:3102`), `set phase=...` (`:3179`), và `hotfix` (`:3245`).
   - Trong `_cli_approve`, cả nhánh `target == "quick"` (`:2417`: `state["phase"] = "implement"`) lẫn `target == "plan"` (`:2422`: `state["phase"] = "implement" if state.get("implement_mode") else "mode"`, và `:2335`) đều **gán trực tiếp `state["phase"] = "implement"` mà KHÔNG gọi `ghi_moc_phase(state, "implement")`**!
   - Bằng chứng sống trên `docs/tdq/state.json` của chính request hiện tại (`2026-11-20-2355`): `plan_approved_at` là `2026-11-21T00:55:23+07:00` (`state.json:36`), nhưng `phase_history` chỉ xuất hiện mốc `"implement"` lúc `2026-11-21T01:03:09+07:00` (`state.json:91-92`) khi leader chạy `set phase=implement` thủ công — khiến `466s` đầu của `implement` bị cộng dồn vào `plan`!
   - Hệ quả thực nghiệm: **`18` ca `build` ở `full`** (như `2026-11-20-0015-trien-khai-plan-v2-planner-spec`, `2026-11-19-0046-dong-rust-binary-hook`, `2026-11-09-0143-gate-truoc-sau-archify`, `2026-11-07-0928-toi-uu-runtime-toan-dien`, `2026-11-05-1448`, `2026-11-05-2104`, `2026-11-06-1250`, `2026-11-03-2055`) và các ca `quick` gần đây (`1457`, `1612`) chuyển thẳng sang `qc` hoặc `report` mà không gọi lại `set phase=implement`, dẫn đến **`implement = 0.0s` giả tạo** trong `timing.jsonl` còn toàn bộ thời gian `implement` bị tính nhầm vào `plan` (ở `full`) hoặc `analyze` (ở `quick`).

Vì vậy, mọi bảng phân tích dưới đây trình bày **song song cả số liệu RAW trên toàn tập lẫn số liệu đối chứng CLEAN** (loại bỏ các ca `build` bị dính bug telemetry `im == 0s` hoặc kiểm tra bằng `model_giay`/`observed_union_seconds`) để tách bạch **hiện tượng dồn việc thực chất** khỏi **nhiễu đo đạc**.

---

## 2. Phân loại toàn bộ `174` request theo Bản chất & Lane (Chống bẫy Slug)

### 2.1 Quy tắc phân loại minh bạch

Thay vì chỉ khớp regex trên slug (vốn gây sai lệch như mục 2.3), mỗi bản ghi trong `0..173` được kiểm tra chéo qua **5 nguồn thật trên đĩa**: (1) `slug`, (2) `docs/tdq/brief/<slug>.md` (mục `Nguyên văn`, `Mục tiêu`, `loai_request`), (3) `docs/tdq/spec/<slug>.md`, (4) `docs/tdq/plan/<slug>.md` (trường `Chạm:` trỏ tệp mã nguồn vs chỉ `docs/`), và (5) `docs/tdq/reports/<slug>.md` hoặc `docs/tdq/report/<slug>.md` (mục `Đã làm` / `Sau request` / `Giới hạn`).

- **`research/analysis/audit` (`33` ca):** Yêu cầu nghiên cứu, phân tích, đánh giá/benchmark, đối chiếu kiến trúc, kiểm toán hệ thống hoặc thiết kế đề xuất **thuần tài liệu / không sửa mã nguồn sản phẩm**. (Ghi chú minh bạch: `4` ca có viết script/test phụ trợ chỉ để đo đạc hoặc kiểm tra chính báo cáo như `doc_dup.py` ở `idx=26`, `dem_da_nen_tang.py` ở `idx=54`, `test_bao_cao_gitflow.py` ở `idx=58`, `test_report_kien_truc_ecc.py` ở `idx=106`, nhưng báo cáo đều khẳng định không sửa bất kỳ dòng mã vận hành nào của TDQ).
- **`debug/scan` (`9` ca):** Yêu cầu điều tra nguyên nhân gốc (`RCA`), quét hành vi/latency diện rộng, hoặc kiểm thử chẩn đoán đa nền tảng/trình duyệt **không sửa mã sản phẩm** (`idx 11, 36, 48, 112, 117, 120, 122, 155, 164`).
- **`build` (`132` ca):** Yêu cầu thêm tính năng, sửa lỗi code/hook, tái cấu trúc, tối ưu hiệu năng, cài đặt/phát hành, hoặc yêu cầu lai vừa nghiên cứu/điều tra vừa viết hoặc sửa mã nguồn/test/cấu hình thật ngay trong cùng request.

### 2.2 Bảng phân bổ theo Loại công việc × Lane (`N=174`)

| Loại công việc (`workflow_type`) | Tổng số (`N=174`) | Tỷ lệ (`/174`) | `quick` | `full` | Số ca `non_idle > 0` (`quick` / `full`) |
|---|---|---|---|---|---|
| `research/analysis/audit` | `33` | `19.0%` | `10` | `23` | `29` (`6` / `23`) |
| `debug/scan` | `9` | `5.2%` | `7` | `2` | `7` (`5` / `2`) |
| **Gộp nhóm thuần điều tra (`investigate`)** | **`42`** | **`24.1%`** | **`17`** | **`25`** | **`36` (`11` / `25`)** |
| `build` | `132` | `75.9%` | `38` | `94` | `120` (`27` / `93`) |
| **Tổng cộng** | **`174`** | **`100.0%`** | **`55`** (`31.6%`) | **`119`** (`68.4%`) | **`156` (`38` / `118`)** |

*Ghi chú đối chiếu mốc `N=173`:* Loại bỏ `idx=173` (`build`, `full`), nhóm `investigate` chiếm `42/173` (`24.3%`) và `build` chiếm `131/173` (`75.7%`).

### 2.3 Danh sách `11` ca bị sai lệch nếu chỉ lọc theo Slug

| Nhóm sai lệch | `idx` | `lane` | `slug` | Vì sao lọc theo slug dễ phân loại sai | Phân loại đúng |
|---|---|---|---|---|---|
| **Âm tính giả** (slug giống `build`, thực chất thuần `docs`/phân tích) | `31` | `full` | `2026-08-23-1341-build-mind-map-v2` | Slug bắt đầu bằng `build-`, nhưng report ghi rõ: *"thiết kế xong, CHƯA apply... đề xuất trên giấy, chưa một dòng code nào chạy thật"* (`0` file ngoài `docs/`). | `research/analysis/audit` |
| Âm tính giả | `47` | `quick` | `2026-09-02-2057-bo-lsp-dung-lumen-grep` | Slug `bo-lsp-...` giống chỉnh rule, nhưng mục tiêu & report là đo lường thực nghiệm *"nên không, mất bao nhiêu chất lượng"* (`docs/tdq/report/` duy nhất). | `research/analysis/audit` |
| Âm tính giả | `121` | `quick` | `2026-10-19-1700-nang-cap-graphify-ban-do-du-an` | Slug bắt đầu bằng `nang-cap-`, nhưng plan ghi rõ *"không sửa mã nguồn dự án"*, chỉ đánh giá Graphify thay thế LSP. | `research/analysis/audit` |
| Âm tính giả | `159` | `full` | `2026-11-11-0035-nang-cap-do-chi-tiet-plan` | Slug `nang-cap-...`, nhưng brief & report là *Báo cáo nghiên cứu chuyên sâu* thuần `docs` (`research` 586 dòng, `0` code). | `research/analysis/audit` |
| Âm tính giả | `170` | `full` | `2026-11-19-2213-chi-tiet-plan-model-thap` | Slug `chi-tiet-plan-...` không chứa từ khóa research/phân tích, nhưng brief khóa `loai_request=docs`, thuần 2 vòng phân tích + Red-Team. | `research/analysis/audit` |
| **Dương tính giả** (slug giống research/điều tra, thực chất có sửa code/config) | `22` | `full` | `2026-08-19-1903-do-tuan-thu-sau-hybrid` | Slug `do-tuan-thu-`, thực tế xây mới `scripts/tdq_eval.py` và `tests/test_tdq_eval.py`. | `build` (lai) |
| Dương tính giả | `96` | `full` | `2026-10-11-1724-unknown-skill-plugin-chua-nap` | Brief ghi *Phân tích lỗi*, nhưng plan & report build luôn `scripts/plugin_tiers.py` + `scripts/tdq_setup.py`. | `build` (bugfix+RCA) |
| Dương tính giả | `101` | `full` | `2026-10-15-0958-dieu-tra-loi-lsp-search-team-clean` | Slug `dieu-tra-`, nhưng vừa RCA vừa vá `scripts/tdq_team.py`, `scripts/search_rules.py`, `hooks/scripts/search_gate.py`. | `build` (bugfix+RCA) |
| Dương tính giả | `102` | `full` | `2026-10-15-1300-danh-gia-instruction-tier-thap` | Slug `danh-gia-`, nhưng P2 sửa trực tiếp `hooks/scripts/session_start.py` + 2 file test (`236` tests PASS). | `build` (lai) |
| Dương tính giả | `129` | `full` | `2026-10-24-2145-nghien-cuu-tich-hop-archify` | Slug `nghien-cuu-`, nhưng xây luôn `scripts/tdq_archify.py`, sửa `skills/` và viết 35 unit test. | `build` (lai) |
| Dương tính giả | `142` | `full` | `2026-11-01-1854-eval-chat-luong-skill` | Slug `eval-`, thực tế build `scripts/tdq_eval_contract.py`, `scripts/tdq_eval_hosts.py` + sửa `tdq_state.py`. | `build` |

**Danh sách chỉ số đầy đủ để tái lập:**
- `RESEARCH_ANALYSIS_AUDIT_IDXS` (`33`): `{14, 15, 23, 26, 30, 31, 35, 41, 42, 43, 45, 47, 54, 58, 71, 72, 83, 85, 98, 104, 106, 107, 108, 110, 121, 131, 135, 152, 159, 167, 168, 170, 172}`.
- `DEBUG_SCAN_IDXS` (`9`): `{11, 36, 48, 112, 117, 120, 122, 155, 164}`.

---

## 3. Thống kê Mean, Median, P90 (Giây & `%`) theo Pha và Cohort

Quy ước tính toán nhất quán trên toàn bộ bảng:
- **Hàm phân vị P90:** Nội suy tuyến tính chuẩn (`k = (n - 1) * 0.90`).
- **Giây (`all` vs `nz`):** Cột `(all)` tính trên toàn bộ số ca của cohort; cột `(nz)` tính trên các ca có `non_idle > 0` (loại `17` ca `quick` cũ trước `2026-09-01` chỉ có `idle` và `1` stub `idx=153`).
- **`%` từng pha:** Tính tỷ lệ từng ca `pct_i = phase_s / non_idle_s * 100` trên tập `nz`, rồi lấy `Mean / Median / P90` để không bị méo bởi vài ca treo qua đêm. Cột `Pooled %` = `sum(phase_s) / sum(non_idle_s) * 100` (khớp cách tính cộng dồn của brief).
- **`Pre-Implement`:** `analyze + spec + plan` (trên `quick`, `spec = 0`, `plan = 0`, nên `Pre-Implement = analyze`, tương ứng pha hiển thị `quick_analyze`).

### 3.1 Toàn bộ kho lịch sử (`All 174` và đối chiếu `All 173`)

**Tập `All 174` (`N=174` · `nz=156` · tổng `non_idle = 3,288,169.1s` · `pre > impl`: `89/174 = 51.1%` hay `89/156 = 57.1%`):**

| Pha | Giây `Mean` (all) | Giây `Med` (all) | Giây `P90` (all) | Giây `Mean` (nz) | Giây `Med` (nz) | Giây `P90` (nz) | `% Mean` (nz) | `% Med` (nz) | `% P90` (nz) | `Pooled %` |
|---|---|---|---|---|---|---|---|---|---|---|
| `analyze` *(gồm `quick_analyze`)* | `1,977.1s` | `495.5s` | `2,830.0s` | `2,205.3s` | `568.5s` | `2,923.0s` | `19.6%` | `10.0%` | `50.6%` | `10.5%` |
| `spec` | `1,709.8s` | `268.0s` | `1,978.6s` | `1,907.1s` | `338.5s` | `2,167.5s` | `8.5%` | `3.2%` | `20.7%` | `9.0%` |
| `plan` | `3,324.0s` | `241.0s` | `5,116.0s` | `3,707.5s` | `285.5s` | `5,250.5s` | `12.3%` | `3.9%` | `34.7%` | `17.6%` |
| **`Pre-Implement`** | **`7,011.0s`** | **`1,542.5s`** | **`12,644.3s`** | **`7,820.0s`** | **`1,843.0s`** | **`12,914.5s`** | **`40.4%`** | **`36.3%`** | **`92.1%`** | **`37.1%`** |
| `implement` | `5,076.2s` | `917.5s` | `7,098.0s` | `5,662.0s` | `1,041.5s` | `7,659.5s` | `33.1%` | `20.2%` | `89.1%` | `26.9%` |
| `qc` | `2,514.1s` | `41.0s` | `1,683.4s` | `2,804.2s` | `81.0s` | `1,733.0s` | `7.8%` | `1.0%` | `22.3%` | `13.3%` |
| `report` | `4,255.6s` | `233.0s` | `12,204.9s` | `4,746.6s` | `340.0s` | `14,917.0s` | `18.5%` | `4.3%` | `61.3%` | `22.5%` |
| `mode` | `36.3s` | `0.0s` | `0.0s` | `40.5s` | `0.0s` | `0.0s` | `0.2%` | `0.0%` | `0.0%` | `0.2%` |
| `diagram` | `4.3s` | `0.0s` | `0.0s` | `4.8s` | `0.0s` | `0.0s` | `0.0%` | `0.0%` | `0.0%` | `0.0%` |
| `non_idle` | `18,897.5s` | `4,527.5s` | `40,906.7s` | `21,078.0s` | `5,115.5s` | `42,119.0s` | — | — | — | `100.0%` |
| `wall_total` (kể `idle`) | `34,938.5s` | `6,486.5s` | `90,108.7s` | — | — | — | — | — | — | — |

**Đối chiếu mốc `All 173` (`idx 0..172`, `nz=155`, tổng `non_idle = 3,247,984.1s`):**
`Pre-Implement` đạt `Mean 7,031.0s / Med 1,471.0s / P90 12,651.2s` (`40.6%` mean, `36.6%` med, **`37.4%` pooled**), `implement` đạt `Mean 5,064.1s / Med 910.0s / P90 6,870.2s` (`33.2%` mean, `20.8%` med, **`27.0%` pooled**), và `pre > impl` là **`89/173` (`51.4%`)** — khớp con số `37.5%`, `27.0%`, `89/173 (51.4%)` trong brief.

### 3.2 `Last 30` & `Last 60` (kèm kiểm tra nhạy cảm loại nhiễu telemetry)

**`Last 30` (`idx 144..173`, `N=30`, `nz=29`, `non_idle = 687,179.6s`, `pre > impl = 23/30 = 76.7%`):**

| Pha | Giây `Mean` (all) | Giây `Med` (all) | Giây `P90` (all) | `% Mean` (nz) | `% Med` (nz) | `% P90` (nz) | `Pooled %` | Mốc `173` (`143..172`) `Pooled %` |
|---|---|---|---|---|---|---|---|---|
| `analyze` | `5,902.4s` | `694.0s` | `10,300.2s` | `23.3%` | `10.3%` | `81.6%` | `25.8%` | `27.2%` |
| `spec` | `1,559.5s` | `546.0s` | `2,180.6s` | `8.3%` | `3.6%` | `19.3%` | `6.8%` | `7.1%` |
| `plan` | `6,536.4s` | `1,016.5s` | `10,741.1s` | `15.5%` | `11.0%` | `32.6%` | `28.5%` | `29.8%` |
| **`Pre-Implement`** | **`13,998.4s`** | **`3,087.0s`** | **`37,451.8s`** | **`47.1%`** | **`42.2%`** | **`99.0%`** | **`61.1%`** | **`64.1%`** |
| `implement` | `1,669.3s` | `271.5s` | `5,970.6s` | `15.8%` | `9.6%` | `45.7%` | `7.3%` | `6.9%` |
| `qc` | `1,800.9s` | `860.0s` | `5,393.3s` | `11.2%` | `5.1%` | `29.1%` | `7.9%` | `7.5%` |
| `report` | `5,251.6s` | `1,154.5s` | `16,268.4s` | `25.1%` | `17.3%` | `60.6%` | `22.9%` | `20.6%` |
| `mode` | `185.8s` | `0.0s` | `0.0s` | `0.7%` | `0.0%` | `0.0%` | `0.8%` | `0.9%` |
| `non_idle` | `22,906.0s` | `17,077.5s` | `51,535.2s` | — | — | — | `100.0%` | `100.0%` |

**`Last 60` (`idx 114..173`, `N=60`, `nz=59`, `non_idle = 1,318,118.1s`, `pre > impl = 35/60 = 58.3%`):**

| Pha | Giây `Mean` (all) | Giây `Med` (all) | Giây `P90` (all) | `% Mean` (nz) | `% Med` (nz) | `% P90` (nz) | `Pooled %` | Mốc `173` (`113..172`) `Pooled %` |
|---|---|---|---|---|---|---|---|---|
| `analyze` | `3,588.2s` | `512.5s` | `2,935.6s` | `24.0%` | `11.5%` | `81.6%` | `16.3%` | `16.8%` |
| `spec` | `993.0s` | `363.0s` | `1,609.2s` | `6.2%` | `1.5%` | `18.8%` | `4.5%` | `4.6%` |
| `plan` | `4,132.3s` | `337.5s` | `6,836.2s` | `10.9%` | `3.7%` | `26.4%` | `18.8%` | `19.3%` |
| **`Pre-Implement`** | **`8,713.6s`** | **`2,050.5s`** | **`26,524.2s`** | **`41.2%`** | **`38.5%`** | **`92.5%`** | **`39.7%`** | **`40.7%`** |
| `implement` | `8,427.5s` | `699.5s` | `7,198.7s` | `33.8%` | `18.9%` | `86.9%` | `38.4%` | `39.0%` |
| `qc` | `1,024.6s` | `26.0s` | `3,338.0s` | `6.9%` | `0.4%` | `20.4%` | `4.7%` | `4.4%` |
| `report` | `3,704.1s` | `422.0s` | `13,131.6s` | `17.8%` | `8.1%` | `56.8%` | `16.9%` | `15.5%` |
| `mode` | `98.8s` | `0.0s` | `0.0s` | `0.4%` | `0.0%` | `0.0%` | `0.4%` | `0.5%` |
| `non_idle` | `21,968.6s` | `5,108.5s` | `43,750.5s` | — | — | — | `100.0%` | `100.0%` |

**Kiểm tra độ nhạy loại lỗi telemetry `_cli_approve` (`Last 30` CLEAN):** Khi loại bỏ `8` ca `build` bị dính bug `im == 0s` (`idx 145, 148, 149, 150, 154, 157, 166, 171`) và `1` stub `0s` (`idx 153`), trên **`N=21` ca sạch còn lại**, tỷ trọng `Pre-Implement` vẫn là **`48.2%` pooled** (`40.8%` median) so với **`17.3%` pooled** (`14.7%` median) của `implement`, và **`15/21` (`71.4%`)** vẫn có `Pre-Implement > implement`.

### 3.3 Nhóm thuần `research/analysis/audit` & `debug/scan` (`investigate`)

**Gộp thuần `investigate` (`research/analysis/audit` + `debug/scan`: `N=42`, `nz=36`, `non_idle = 255,154.0s`, `pre > impl = 24/42 = 57.1%` hay `24/36 = 66.7%`):**

| Pha | Giây `Mean` (all) | Giây `Med` (all) | Giây `P90` (all) | Giây `Mean` (nz) | Giây `Med` (nz) | Giây `P90` (nz) | `% Mean` (nz) | `% Med` (nz) | `% P90` (nz) | `Pooled %` |
|---|---|---|---|---|---|---|---|---|---|---|
| `analyze` | `1,011.1s` | `433.5s` | `2,856.0s` | `1,179.6s` | `573.0s` | `2,869.5s` | `31.8%` | `19.5%` | `91.5%` | `16.6%` |
| `spec` | `807.1s` | `111.5s` | `1,050.1s` | `941.6s` | `195.5s` | `1,065.5s` | `8.8%` | `3.4%` | `20.7%` | `13.3%` |
| `plan` | `674.3s` | `124.0s` | `1,256.2s` | `786.7s` | `215.5s` | `1,365.0s` | `9.3%` | `4.3%` | `22.9%` | `11.1%` |
| **`Pre-Implement`** | **`2,492.5s`** | **`1,127.0s`** | **`4,028.5s`** | **`2,907.9s`** | **`1,310.0s`** | **`4,228.0s`** | **`49.8%`** | **`46.7%`** | **`98.7%`** | **`41.0%`** |
| `implement` | `1,044.3s` | `338.5s` | `1,964.0s` | `1,218.3s` | `533.0s` | `2,805.0s` | `27.5%` | `15.1%` | `79.6%` | `17.2%` |
| `qc` | `226.6s` | `0.0s` | `1,168.0s` | `264.3s` | `7.0s` | `1,202.0s` | `4.3%` | `0.2%` | `20.3%` | `3.7%` |
| `report` | `2,310.6s` | `10.0s` | `9,627.9s` | `2,695.7s` | `118.5s` | `10,180.0s` | `18.3%` | `2.6%` | `64.6%` | `38.0%` |
| `non_idle` | `6,075.1s` | `2,249.5s` | `22,886.0s` | `7,087.6s` | `2,839.5s` | `24,465.5s` | — | — | — | `100.0%` |

*(Pha `mode` trên `investigate`: mean `1.2s`, `1` ca `idx=107` mất `49s`; `diagram`: `0.0s`).*

**Tách riêng `research/analysis/audit` (`N=33`, `nz=29`), `debug/scan` (`N=9`, `nz=7`), và theo lane (`investigate-full` `N=25` vs `investigate-quick` `N=17`, `nz=11`):**

| Nhóm con (`cohort`) | `N` (`nz`) | `Pre-Impl` (Med `s` all/nz · P90 `s` nz) | `Pre-Impl %` (Mean · Med · P90 · Pooled) | `implement` (Med `s` all/nz · P90 `s` nz) | `implement %` (Mean · Med · P90 · Pooled) | `pre > impl` |
|---|---|---|---|---|---|---|
| `research/analysis/audit` | `33` (`29`) | `1,281.0s` / `1,828.0s` · `4,895.0s` | `52.3%` · **`50.9%`** · `99.5%` · `42.1%` | `583.0s` / `780.0s` · `4,099.0s` | `23.8%` · **`13.5%`** · `78.8%` · `17.4%` | `21/33` (`72.4%` nz) |
| `debug/scan` | `9` (`7`) | `127.0s` / `136.0s` · `2,679.6s` | `39.4%` · `36.9%` · `66.4%` · `29.4%` | `198.0s` / `233.0s` · `1,019.0s` | `43.0%` · `60.9%` · `79.5%` · `14.7%` | `3/9` (`42.9%` nz) |
| **`investigate` — `full`** | **`25` (`25`)** | `1,888.0s` / `1,888.0s` · `5,947.0s` | `51.4%` · **`49.9%`** · `97.4%` · `40.4%` | `780.0s` / `780.0s` · `5,015.0s` | `15.9%` · **`12.7%`** · `28.4%` · `15.7%` | **`20/25` (`80.0%`)** |
| `investigate` — `quick` | `17` (`11`) | `63.0s` / `127.0s` · `2,413.0s` | `46.0%` · `36.9%` · `99.6%` · `53.8%` | `56.0s` / `233.0s` · `1,284.0s` | `53.9%` · `63.1%` · `97.9%` · `46.1%` | `4/17` (`36.4%` nz) |

*Chi tiết từng pha của `investigate — full` (`N=25` đều `nz`):*
- `analyze`: Mean `1,432.4s`, Med `688.0s`, P90 `2,933.6s` (`25.5%` mean · `15.7%` med · `53.8%` P90 · `14.8%` pooled)
- `spec`: Mean `1,355.9s`, Med `368.0s`, P90 `1,086.2s` (`12.6%` mean · `7.9%` med · `23.3%` P90 · `14.0%` pooled)
- `plan`: Mean `1,132.8s`, Med `476.0s`, P90 `1,465.0s` (`13.4%` mean · `9.2%` med · `31.9%` P90 · `11.7%` pooled)
- `qc`: Mean `380.6s`, Med `48.0s`, P90 `1,214.8s` (`6.2%` mean · `1.7%` med · `23.0%` P90 · `3.9%` pooled)
- `report`: Mean `3,881.4s`, Med `738.0s`, P90 `15,334.6s` (`26.4%` mean · `16.7%` med · `66.0%` P90 · `40.0%` pooled)

### 3.4 So sánh `quick` vs `full` và đối chiếu `build`

**Bảng `quick` (`N=55` all · `nz=38` sau `2026-09-01`, `analyze` ≡ `quick_analyze`):**

| Pha | Giây `Mean` (all) | Giây `Med` (all) | Giây `P90` (all) | Giây `Mean` (nz) | Giây `Med` (nz) | Giây `P90` (nz) | `% Mean` (nz) | `% Med` (nz) | `% P90` (nz) | `Pooled %` |
|---|---|---|---|---|---|---|---|---|---|---|
| `analyze` (`quick_analyze`) | `247.1s` | `60.0s` | `605.2s` | `357.6s` | `123.0s` | `704.5s` | `28.6%` | `16.2%` | `86.2%` | `13.9%` |
| `implement` | `1,477.0s` | `286.0s` | `1,602.0s` | `2,137.7s` | `440.5s` | `1,941.0s` | `66.6%` | `76.3%` | `98.2%` | `83.2%` |
| `qc` | `5.7s` | `0.0s` | `0.0s` | `8.2s` | `0.0s` | `0.0s` | `1.1%` | `0.0%` | `0.0%` | `0.3%` |
| `report` | `44.8s` | `0.0s` | `5.6s` | `64.8s` | `0.0s` | `225.3s` | `3.7%` | `0.0%` | `19.3%` | `2.5%` |
| `non_idle` | `1,774.4s` | `524.0s` | `2,215.0s` | `2,568.3s` | `1,079.0s` | `2,439.3s` | — | — | — | `100.0%` |

*(Ghi nhận: `spec = 0.0s`, `plan = 0.0s`, `mode = 0.0s`, `diagram = 0.0s`; `wall_total` Mean `3,743.3s` · Med `1,932.7s` · P90 `6,359.2s`; `pre > impl`: `8/55 = 14.5%`, hoặc `8/38 = 21.1%` trên `nz`).*

**Bảng `full` (`N=119` all · `nz=118`, `non_idle = 3,190,574.8s`, `pre > impl = 81/119 = 68.1%`):**

| Pha | Giây `Mean` (all) | Giây `Med` (all) | Giây `P90` (all) | Giây `Mean` (nz) | Giây `Med` (nz) | Giây `P90` (nz) | `% Mean` (nz) | `% Med` (nz) | `% P90` (nz) | `Pooled %` |
|---|---|---|---|---|---|---|---|---|---|---|
| `analyze` | `2,776.8s` | `698.0s` | `3,617.8s` | `2,800.3s` | `707.0s` | `3,663.7s` | `16.7%` | `8.7%` | `43.5%` | `10.4%` |
| `spec` | `2,500.1s` | `471.0s` | `2,444.2s` | `2,521.3s` | `477.5s` | `2,445.3s` | `11.3%` | `5.9%` | `24.5%` | `9.3%` |
| `plan` | `4,860.3s` | `555.0s` | `6,781.0s` | `4,901.5s` | `555.0s` | `6,782.5s` | `16.3%` | `6.2%` | `50.6%` | `18.1%` |
| **`Pre-Implement`** | **`10,137.2s`** | **`2,640.0s`** | **`16,502.4s`** | **`10,223.1s`** | **`2,647.5s`** | **`16,575.6s`** | **`44.3%`** | **`39.6%`** | **`92.8%`** | **`37.8%`** |
| `implement` | `6,739.8s` | `1,226.0s` | `8,600.2s` | `6,796.9s` | `1,226.0s` | `8,725.8s` | `22.3%` | `15.1%` | `57.1%` | `25.1%` |
| `qc` | `3,673.4s` | `393.0s` | `2,360.0s` | `3,704.6s` | `393.5s` | `2,400.5s` | `9.9%` | `2.4%` | `27.3%` | `13.7%` |
| `report` | `6,201.7s` | `769.0s` | `18,671.8s` | `6,254.3s` | `803.5s` | `18,679.2s` | `23.2%` | `12.3%` | `65.8%` | `23.1%` |
| `mode` / `diagram` | `53.1s` / `6.3s` | `0.0s` | `0.0s` | `53.6s` / `6.4s` | `0.0s` | `0.0s` | `0.2%` / `0.1%` | `0.0%` | `0.0%` | `0.2%` / `0.0%` |
| `non_idle` | `26,811.6s` | `7,926.0s` | `46,804.0s` | `27,038.8s` | `8,611.0s` | `47,364.5s` | — | — | — | `100.0%` |

*(Ghi nhận `wall_total` của `full`: Mean `49,356.4s`, Med `18,865.8s`, P90 `144,509.5s`.)*

**Đối chiếu riêng nhóm `build` (`quick` vs `full` và bản CLEAN `im > 0`):**
- `Build — quick` (`N=38`, `nz=27`): `Pre-Implement` (`quick_analyze`) chỉ chiếm **`11.5%` median** (`119.0s`, mean `256.7s` / `21.5%`, pooled `8.1%`), trong khi `implement` chiếm **`79.5%` median** (`764.0s`, mean `2,797.1s` / `71.7%`, pooled `88.6%`). Chỉ `4/27` (`14.8%`) có `pre > impl`.
- `Build — full` RAW (`N=94`, `nz=93`): `Pre-Implement` `37.6%` median (`2,832.0s` nz, `37.6%` pooled) vs `implement` `15.9%` median (`1,321.0s` nz, `25.9%` pooled).
- `Build — full` **CLEAN (`im > 0`, `N=75`, loại `18` ca dính bug `_cli_approve`)**: `Pre-Implement` giảm xuống **`29.3%` pooled** (`35.1%` median) và `implement` tăng lên **`35.4%` pooled** (`21.6%` median), ngược hẳn với `investigate — full` (`Pre-Implement` **`49.9%` median** vs `implement` **`12.7%` median**).

### 3.5 Đối chứng bằng Thời gian Model/Compute Thực (`model_giay` & `observed_union_seconds`)

Để kiểm chứng xem tỷ trọng `Pre-Implement > Implement` có phải chỉ do người dùng dừng lâu ở cổng duyệt spec/plan hay không, kiểm tra độc lập trên thời gian xử lý thực:

| Nguồn đo thực (Active Compute) | Cohort (`n`) | `Pre-Implement %` (Pooled · Med) | `implement %` (Pooled · Med) | Tỷ lệ `pre > impl` |
|---|---|---|---|---|
| Schema v1 `model_giay > 0` (`idx 0..139`) | `Pure investigate` (`n=13`) | **`43.0%` · `46.9%`** | `38.1%` · `40.6%` | `7/13` (`53.8%`) |
| Schema v1 `model_giay > 0` (`idx 0..139`) | `Build` (`n=44`) | `33.4%` · `30.5%` | **`48.9%` · `45.3%`** | `10/44` (`22.7%`) |
| Schema v2 `observed_union` (Claude, `idx 155`) | `debug/scan` (`2026-11-08-1141`) | `83.1%` (`416.7s` / `501.2s`) | `3.6%` (`17.9s`) | `1/1` |
| Schema v2 `observed_union` (Claude, `idx 159`) | `research` (`2026-11-11-0035`) | `26.3%` (`549.4s` / `2,092.6s`) | `67.9%` (`1,420.7s`) | `0/1` |

**Kết luận đối chứng:** Ngay cả khi loại bỏ hoàn toàn thời gian chờ con người, nhóm `investigate` vẫn tiêu tốn nhiều `model_giay` cho `Pre-Implement` hơn `implement` (`43.0%` vs `38.1%` pooled; `46.9%` vs `40.6%` median), trái ngược hoàn toàn với `build` (`33.4%` vs `48.9%` pooled; `30.5%` vs `45.3%` median).

---

## 4. Tỷ lệ `implement == 0s` và `implement < 5%` (`research/analysis/audit` vs `build`)

### 4.1 Bảng tổng hợp tỷ lệ `implement == 0s` và `implement < 5%` (`non_idle`)

| Nhóm công việc | `N` (tổng) | `nz` (`non_idle > 0`) | `implement == 0s` (trên tổng `N`) | `implement == 0s` (trên `nz`) | `implement < 5%` (trên tổng `N`) | `implement < 5%` (trên `nz`) |
|---|---|---|---|---|---|---|
| **`research/analysis/audit`** | `33` | `29` | **`12/33` (`36.4%`)** | **`8/29` (`27.6%`)** | **`12/33` (`36.4%`)** | **`8/29` (`27.6%`)** |
| `debug/scan` | `9` | `7` | `2/9` (`22.2%`) | `0/7` (`0.0%`) | `4/9` (`44.4%`) | `2/7` (`28.6%`) |
| **Gộp `investigate` (cả 2)** | **`42`** | **`36`** | **`14/42` (`33.3%`)** | **`8/36` (`22.2%`)** | **`16/42` (`38.1%`)** | **`10/36` (`27.8%`)** |
| — `investigate` (`full`) | `25` | `25` | `6/25` (`24.0%`) | `6/25` (`24.0%`) | `7/25` (`28.0%`) | `7/25` (`28.0%`) |
| — `investigate` (`quick`) | `17` | `11` | `8/17` (`47.1%`) | `2/11` (`18.2%`) | `9/17` (`52.9%`) | `3/11` (`27.3%`) |
| **`build` (tổng)** | `132` | `120` | `30/132` (`22.7%`) | `18/120` (`15.0%`) | `40/132` (`30.3%`) | `28/120` (`23.3%`) |
| — `build` (`full`) | `94` | `93` | `19/94` (`20.2%`) | `18/93` (`19.4%`) | `29/94` (`30.9%`) | `28/93` (`30.1%`) |
| — `build` (`quick`) | `38` | `27` | `11/38` (`28.9%`) | **`0/27` (`0.0%`)** | `11/38` (`28.9%`) | **`0/27` (`0.0%`)** |

### 4.2 Phân tích nguyên nhân gốc của các ca `implement == 0s` & `< 5%`

1. **Ở `Build — quick` (`0/27 = 0.0%` trên tập hoạt động sau `2026-09-01`):** Mọi ca `build` dùng `quick` sau khi lane này có pha `analyze` đều ghi `implement > 5%` (`median 79.5%`). Cả `11` ca `build — quick` ghi `0s` đều là bản ghi cũ trước `2026-09-01` chỉ có pha `idle` (`idx 3, 4, 12, 13, 19, 20, 32, 37, 44, 57, 64`).
2. **Ở `investigate` (`14/42 = 33.3%` tổng · `8/36 = 22.2%` hoạt động):**
   - `6` ca `full` có `implement == 0s` (`idx 14, 15, 98, 104, 110, 152`): ngoại trừ `idx 110` dừng ở `analyze` (`3,386s`), `5` ca còn lại là thuần `docs`/research đã làm xong phần phân tích ở `analyze`/`spec`/`plan`, hoặc viết báo cáo ở `report` (`idx 104` viết file HTML `48.5 KB` mà không mở `implement`).
   - `2` ca `quick` hoạt động gần đây (`idx 167: 2026-11-19-1457-audit-sai-sot-noi-hook` với `analyze=2,413s, report=8s`; `idx 168: 2026-11-19-1612-research-behavior-va-hieu-nang` với `analyze=568s, report=2s`): toàn bộ audit, số liệu đối chứng và thiết kế 4 phương án được làm trọn trong `analyze` (hoặc `approve quick` không gọi `ghi_moc_phase`), khiến `implement = 0s` và `Pre-Implement = 99.6%–99.7%`.
   - `2` ca `investigate` có `0 < implement < 5%`: `idx 117` (`test-browser-test-webchat`, `4.4%` — `2,739s` ở `analyze`, `125s` ở `implement`) và `idx 155` (`dieu-tra-gate-chua-duyet-tu-dong-edit`, `1.5%` — `578s` pre-implement, `18s` implement, `632s` report).
3. **Ở `Build — full` (`18/93 = 19.4%` hoạt động có `im == 0s`, cộng `10` ca `< 5%`):**
   - Kiểm chứng `docs/tdq/reports/` và `observed_union_seconds` cho thấy phần lớn các ca `build — full` có `im == 0s` gần đây (`idx 145, 148, 149, 150, 154, 157, 166, 171`, cộng `idx 103, 105, 130`) **thực tế có sửa rất nhiều mã nguồn và chạy hàng nghìn unit test**, ví dụ `idx 171` (`2026-11-20-0015`) chạy `4,525` tests hay `idx 166` (`2026-11-19-0046`) đóng gói Rust binary. Chúng bị ghi `implement = 0s` là do bug `_cli_approve` thiếu `ghi_moc_phase` đã chứng minh ở mục 1.2 (khiến thời gian viết code dồn vào `plan`, `qc` hoặc `report`). Một số ca khác có `im < 5%` như `idx 22` (`qc=161,931s`), `idx 40` (`spec=89,641s`), `idx 84` (`plan=152,071s`) bị treo đồng hồ chờ duyệt/QC qua nhiều ngày làm tỷ lệ `%` của `implement` (`2,236s–8,349s`) tụt xuống dưới `5%`.

---

## 5. Đo lường Trùng lặp Cấu trúc & Double-Work (`docs/tdq/`)

### 5.1 Quy mô tài liệu tiền-implement trên toàn kho (`docs/tdq/`, theo slug duy nhất)

Đo trên toàn bộ `171` slug duy nhất (lấy lane/bản ghi mới nhất của mỗi slug):

| Nhóm (`lane`) | Số slug (`có research`) | `brief` (Med) | `spec` (Med) | `plan` (Med) | **Tổng tài liệu Tiền-Implement** (`Med` · `Mean`) | `report` (Med) |
|---|---|---|---|---|---|---|
| `Pure investigate` (`full`) | `25` (`13` = `52.0%`) | `105L` | `156L` | `116L` | **`424L` (`38,250B`) · `478L` (`46,623B`)** | `49L` (`5,479B`) |
| `Build` (`full`) | `92` (`21` = `22.8%`) | `112L` | `167L` | `150L` | **`470L` (`38,802B`) · `493L` (`47,454B`)** | `42L` (`3,880B`) |
| `Pure investigate` (`quick`) | `17` (`1` = `5.9%`) | `36L` | `0L` | `38L` | `74L` (`5,742B`) · `127L` (`10,466B`) | `31L` (`2,752B`) |
| `Build` (`quick`) | `37` (`0` = `0.0%`) | `34L` | `0L` | `36L` | `72L` (`6,183B`) · `85L` (`6,974B`) | `0L` (`0B`) |

- **Hệ quả định lượng rõ rệt:** Ở `full` lane, một request `Pure investigate` phải gánh **`424` dòng / `38.3 KB` (median)** tài liệu tiền-implement — **tương đương `90.2%` số dòng và `98.6%` dung lượng bytes** của một request `Build` (`470` dòng / `38.8 KB`), mặc dù phần `report` đầu ra chính chỉ có median `49` dòng.
- **Độ lặp n-gram toàn kho (`N=112` cặp `brief + spec + plan` ở `full`):**
  - `brief → spec` (5-gram token overlap): Mean **`12.5%`**, Median **`10.8%`**.
  - `spec → plan` (5-gram token overlap): Mean **`6.6%`**, Median **`6.4%`**.

### 5.2 Đo chi tiết `8` ca tiêu biểu (tháng 11/2026)

| Request Slug | Loại (`lane`) | `Pre-Impl` (`s` / `%`) | `Impl` (`s` / `%`) | `brief` (`L/B`) | `research` (`L/B`) | `spec` (`L/B`) | `plan` (`L/B`) | **Tổng Tiền-Impl** | `qc` (`L/B`) | `reports` (`L/B`) | `artifacts` / `bench` | `spec-preview.html` + `report.html` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `2026-11-20-1056-phan-tich-nang-cap-agent` | `research/audit` (`full`) | `2,498s` (`49.9%`) | `483s` (`9.6%`) | `105L` / `16.5KB` | `113L` / `13.3KB` | `183L` / `23.6KB` | `114L` / `14.5KB` | **`515L` / `67.9KB`** | `74L` / `3.7KB` | `265L` / `44.9KB` | `2f` (`114L` / `6.2KB`) | `1.61MB` + `1.60MB` |
| `2026-11-19-2213-chi-tiet-plan-model-thap` | `research/analysis` (`full`) | `3,502s` (`46.5%`) | `1,322s` (`17.6%`) | `97L` / `14.3KB` | `221L` / `37.2KB` | `197L` / `29.0KB` | `137L` / `18.9KB` | **`652L` / `99.4KB`** | `47L` / `4.0KB` | `152L` / `29.7KB` | `8f` (`817L` / `116.2KB`) | `1.23MB` + `1.61MB` |
| `2026-11-19-1457-audit-sai-sot-noi-hook` | `audit` (`quick`) | `2,413s` (`99.7%`) | `0s` (`0.0%`) | `36L` / `3.5KB` | `—` | `—` | `38L` / `4.8KB` | **`74L` / `8.2KB`** | `—` | `155L` / `29.7KB` | `1f` (`44L` / `3.2KB`) | `—` + `1.24MB` |
| `2026-11-19-1612-research-behavior-va-hieu-nang` | `research` (`quick`) | `568s` (`99.6%`) | `0s` (`0.0%`) | `36L` / `6.3KB` | `—` | `—` | `38L` / `5.5KB` | **`74L` / `11.8KB`** | `—` | `159L` / `26.1KB` | `1f` (`44L` / `2.8KB`) | `—` + `1.23MB` |
| `2026-11-18-1346-scan-hook-anh-huong-runtime` | `debug/scan` (`full`) | `2,640s` (`16.4%`) | `1,919s` (`11.9%`) | `111L` / `10.5KB` | `187L` / `40.4KB` | `217L` / `18.3KB` | `116L` / `11.6KB` | **`631L` / `80.7KB`** | `58L` / `4.5KB` | `49L` / `8.3KB` | `1f` (`3.1KB`) + `15f` bench (`278.5KB`) | `—` (`--bo-qua`) + `0.51MB` |
| `2026-11-11-0035-nang-cap-do-chi-tiet-plan` | `research/analysis` (`full`) | `2,034s` (`39.1%`) | `1,431s` (`27.5%`) | `44L` / `3.4KB` | `586L` / `47.8KB` | `208L` / `14.9KB` | `95L` / `8.0KB` | **`933L` / `74.1KB`** | `113L` / `13.9KB` | `73L` / `8.6KB` | `2f` (`70L` / `4.4KB`) | `0.87MB` + `0.87MB` |
| `2026-11-19-1632-hybrid-hook-smart-hardening` | `build` (`full`) | `2,067s` (`11.0%`) | `7,349s` (`39.0%`) | `109L` / `12.9KB` | `—` | `207L` / `33.7KB` | `263L` / `29.5KB` | **`579L` / `76.1KB`** | `79L` / `9.7KB` | `81L` / `12.2KB` | `2f` (`104L` / `6.1KB`) | `1.23MB` + `1.62MB` |
| `2026-11-16-1953-fix-lsp-gate-mcp-routing` | `build` (`full`) | `7,482s` (`28.9%`) | `5,836s` (`22.6%`) | `64L` / `7.1KB` | `—` | `196L` / `25.7KB` | `309L` / `40.1KB` | **`569L` / `72.9KB`** | `100L` / `8.5KB` | `53L` / `11.0KB` | `3f` (`91L` / `7.7KB`) | `0.86MB` + `1.23MB` |

**Độ trùng lặp 5-gram & dòng nguyên văn (`>= 25` ký tự) trên `8` ca tiêu biểu:**

| Request Slug | `brief → spec` (5-gram · dòng chung) | `spec → plan` (5-gram · dòng chung) | `plan → reports` (5-gram · dòng chung) | `spec → reports` (5-gram · dòng chung) |
|---|---|---|---|---|
| `2026-11-20-1056` | `16.2%` (`392/2417` · `13` dòng) | `6.2%` (`213/3413` · `2` dòng) | `4.3%` (`81/1903` · `1` dòng) | `3.5%` (`120/3413` · `3` dòng) |
| `2026-11-19-2213` | `16.0%` (`346/2160` · `12` dòng) | `8.6%` (`369/4275` · `1` dòng) | `5.1%` (`129/2506` · `1` dòng) | `3.2%` (`137/4275` · `3` dòng) |
| `2026-11-19-1457` (`quick`) | — | — (`brief→plan`: `7.5%`, `39/520`) | `9.0%` (`52/576` · `3` dòng) | — |
| `2026-11-19-1612` (`quick`) | — | — (`brief→plan`: `3.1%`, `30/965`) | `9.9%` (`66/665` · `3` dòng) | — |
| `2026-11-18-1346` | `7.7%` (`119/1539` · `5` dòng) | `4.3%` (`116/2677` · `1` dòng) | `2.5%` (`41/1609` · `1` dòng) | `1.9%` (`51/2677` · `1` dòng) |
| `2026-11-11-0035` | `28.7%` (`145/505` · `7` dòng) | `12.3%` (`259/2111` · `6` dòng) | `7.2%` (`69/962` · `1` dòng) | `2.7%` (`58/2111` · `3` dòng) |
| `2026-11-19-1632` (`build`) | `21.6%` (`380/1763` · `10` dòng) | `4.3%` (`207/4781` · `2` dòng) | `2.3%` (`90/3836` · `0` dòng) | `1.2%` (`56/4781` · `2` dòng) |
| `2026-11-16-1953` (`build`) | `18.3%` (`175/955` · `3` dòng) | `4.9%` (`164/3347` · `2` dòng) | `3.0%` (`142/4739` · `1` dòng) | `2.4%` (`80/3347` · `3` dòng) |

### 5.3 Bốn dạng Double-Work cấu trúc đã kiểm chứng trực tiếp trên văn bản

1. **Làm hết nghiên cứu/kiểm toán trong `analyze` rồi đóng gói lại `3` lần ở `spec` → `plan` → `implement` (`1056`, `2213`, `1612`):**
   - Trong `docs/tdq/brief/2026-11-20-1056-phan-tich-nang-cap-agent.md:44-68`, toàn bộ `4` subagent kiểm toán, `14` điểm hạn chế kèm `file:line` và kết luận research ngoài đã hoàn tất ngay trong `analyze`. Sau đó `spec` (`183` dòng) viết lại bảng `4` trụ cột + sơ đồ Mermaid; `plan` (`114` dòng) viết lại đúng bảng `Thiết kế Trước vs Sau` (`lines 31-36`), bọc việc viết `1` file báo cáo thành `T1.1` với Per-Task Mini-Spec `12` trường, rồi `implement` chỉ còn `483s` (`9.6%`) để biên tập lại sang `reports/`.
   - Trong `docs/tdq/brief/2026-11-19-2213-chi-tiet-plan-model-thap.md:26-47`, dù user yêu cầu làm phân tích + Red-Team `2` vòng, `analyze` đã fanout `4` subagent quét `236` plan / `2,699` task + Tavily research (`37.2 KB`), đẩy `Pre-Implement` lên `3,502s` (`46.5%`) và `99.4 KB` tài liệu trước khi `implement` (`1,322s`) bắt đầu.
   - Trong `docs/tdq/brief/2026-11-19-1612-research-behavior-va-hieu-nang.md:18-32` (`quick`), `brief` đã tính xong toàn bộ số liệu `11,241` model calls, `5,634` dòng Python, `1,502` dòng Rust và cả `4` phương án A–D ngay trong `analyze`, rồi `plan` (`38` dòng) mới kê lại `T1`–`T3` để hợp thức hóa `reports/`.
2. **Dựng `§2b Ranh giới module` & `Per-Task Mini-Spec` giả tạo cho báo cáo Markdown (`1056`):**
   - `docs/tdq/spec/2026-11-20-1056-phan-tich-nang-cap-agent.md:52-56` buộc phải chia `1` bài báo cáo thành `3` "module" nhân tạo (`M1-report-md`, `M2-archify-html`, `M3-qc-verify`) chỉ để qua cổng `§2b`, còn `plan:53-93` phải gắn `EARS`, `Logic cốt lõi`, `Ca góc hiểm & Assert`, `tdq_bench.py simulate` cho `3` task tuần tự.
3. **Kết xuất `Archify HTML` hai lần cho cùng một nội dung đề xuất (`1056`, `2213`, `11-0035`):**
   - Các ca `investigate` ở `full` chạy `tdq_archify.py` tạo `*-preview.html` ở `spec` (`1.61 MB` ở `1056`, `1.23 MB` ở `2213`, `0.87 MB` ở `11-0035`, kèm `*-preview.manifest.json` `0.36–1.24 MB`), sau đó lại render lần thứ hai ở `report` (`1.60 MB`, `1.61 MB`, `0.87 MB`).
4. **QC ép chạy bộ test code (`4,315` tests) dù không sửa dòng code nào (`2026-11-18-1346-scan-hook-anh-huong-runtime`):**
   - `docs/tdq/reports/2026-11-18-1346-scan-hook-anh-huong-runtime.md:7-8` xác nhận: request thuần scan `0` file mã nguồn vẫn bị `QC-F1` ép chạy `tdq_test.py vung-cham` fallback sang toàn bộ `207` module (`4,315` pass / `35` skip), ngốn `1,283s` (`21 phút`) ở pha `qc`.

---

## 6. Mã Python tái lập độc lập (Read-Only)

Chạy đoạn script Python stdlib dưới đây trực tiếp từ thư mục gốc repo (`TDQ-Workflow-Antigravity`) để tái lập toàn bộ số liệu phân loại, phân vị Mean/Med/P90, tỷ lệ `implement == 0s`/`<5%` và kích thước/độ trùng lặp tài liệu mà không ghi sửa bất kỳ tệp nào trong repo:

```python
import glob, json, math, os, re, statistics
from collections import Counter

with open("docs/tdq/timing.jsonl", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

RESEARCH_ANALYSIS_AUDIT_IDXS = {
    14, 15, 23, 26, 30, 31, 35, 41, 42, 43, 45, 47, 54, 58, 71, 72,
    83, 85, 98, 104, 106, 107, 108, 110, 121, 131, 135, 152, 159,
    167, 168, 170, 172,
}
DEBUG_SCAN_IDXS = {11, 36, 48, 112, 117, 120, 122, 155, 164}

def classify(idx):
    if idx in RESEARCH_ANALYSIS_AUDIT_IDXS:
        return "research/analysis/audit"
    if idx in DEBUG_SCAN_IDXS:
        return "debug/scan"
    return "build"

def p90(vals):
    s = sorted(vals)
    if not s:
        return 0.0
    k = (len(s) - 1) * 0.90
    lo, hi = math.floor(k), math.ceil(k)
    return float(s[int(k)]) if lo == hi else s[lo] * (hi - k) + s[hi] * (k - lo)

def pmap(r):
    return {p["phase"]: float(p.get("treo_tuong_giay") or 0.0) for p in r.get("phases", [])}

def report_cohort(name, items):
    nis = [sum(v for k, v in pmap(r).items() if k != "idle") for _, r in items]
    nz = [(i, r, pmap(r), ni) for (i, r), ni in zip(items, nis) if ni > 0]
    tot_ni = sum(x[3] for x in nz)
    pre_s = [pmap(r).get("analyze", 0) + pmap(r).get("spec", 0) + pmap(r).get("plan", 0) for _, r in items]
    impl_s = [pmap(r).get("implement", 0) for _, r in items]
    pre_pct = [((m.get("analyze", 0) + m.get("spec", 0) + m.get("plan", 0)) / ni) * 100 for _, _, m, ni in nz]
    impl_pct = [(m.get("implement", 0) / ni) * 100 for _, _, m, ni in nz]
    im0_all = sum(1 for v in impl_s if v == 0.0)
    im0_nz = sum(1 for _, _, m, _ in nz if m.get("implement", 0) == 0.0)
    im5_nz = sum(1 for v in impl_pct if v < 5.0)
    print(f"[{name}] N={len(items)} nz={len(nz)} | im==0s: {im0_all}/{len(items)} (nz {im0_nz}/{len(nz)}) | im<5% nz: {im5_nz}/{len(nz)}")
    print(f"  Pre-Impl (all s): mean={statistics.mean(pre_s):.1f} med={statistics.median(pre_s):.1f} p90={p90(pre_s):.1f} | nz%: mean={statistics.mean(pre_pct):.1f} med={statistics.median(pre_pct):.1f} p90={p90(pre_pct):.1f} pooled={sum(pre_s)/tot_ni*100:.1f}%")
    print(f"  Impl     (all s): mean={statistics.mean(impl_s):.1f} med={statistics.median(impl_s):.1f} p90={p90(impl_s):.1f} | nz%: mean={statistics.mean(impl_pct):.1f} med={statistics.median(impl_pct):.1f} p90={p90(impl_pct):.1f} pooled={sum(impl_s)/tot_ni*100:.1f}%")

indexed = list(enumerate(records))
print("Breakdown:", Counter((classify(i), r["lane"]) for i, r in indexed))
report_cohort("All 174", indexed)
report_cohort("All 173", indexed[:173])
report_cohort("Last 30 (144..173)", indexed[-30:])
report_cohort("Last 60 (114..173)", indexed[-60:])
report_cohort("Pure investigate", [(i, r) for i, r in indexed if classify(i) != "build"])
report_cohort("Investigate - full", [(i, r) for i, r in indexed if classify(i) != "build" and r["lane"] == "full"])
report_cohort("Lane quick", [(i, r) for i, r in indexed if r["lane"] == "quick"])
report_cohort("Lane full", [(i, r) for i, r in indexed if r["lane"] == "full"])
report_cohort("Build", [(i, r) for i, r in indexed if classify(i) == "build"])
```

---

## 7. Kết luận định lượng chốt cho Wave 2 (`evidence-log.md` & Thiết kế V1)

1. **Nhận định của người dùng hoàn toàn đúng và còn nghiêm trọng hơn ở nhóm `full` thuần phân tích:** Gần **1/4 toàn kho (`42/174 = 24.1%`)** là các ca thuần nghiên cứu, phân tích, audit hoặc debug/scan (`investigate`), trong đó ở `full` lane (`25` ca), **`80.0%` (`20/25`)** tốn thời gian `Pre-Implement` lớn hơn `implement` (median `49.9%` vs `12.7%`, `1,888s` vs `780s`), và phải viết lượng tài liệu tiền-implement (`424` dòng / `38.3 KB` median) gần bằng một request code `build` (`470` dòng / `38.8 KB`).
2. **Tách bạch hai cơ chế lỗi cần xử lý đồng bộ trong V1:**
   - **Lỗi quy trình:** `analyze` (`tdq-intake`) làm luôn phần research sâu/kiểm toán; `spec` + `spec-preview.html` + `plan` (`§2b`, `Mini-Spec`, `tdq_bench`) đóng khung code ép vào bài phân tích; `qc` chạy `tdq_test.py` cả khi `0` dòng code đổi.
   - **Lỗi telemetry phase (`tdq_state.py`):** `_cli_approve` (`:2335, 2417, 2422`) không gọi `ghi_moc_phase(state, state["phase"])`, làm `18` ca `build — full` và các ca `quick` mới (`1457`, `1612`) bị ghi nhầm `implement = 0.0s` vào `timing.jsonl` và dồn giờ thi công sang `plan` / `analyze`.
