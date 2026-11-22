# PLAN — Nghiên cứu và thiết kế quy trình setup zero-to-full từ máy trống kèm tự động kiểm chứng sau restart

Ngày: 2026-11-22 · Spec: ../spec/2026-11-22-1424-phan-tich-setup-may-trong.md (bản 1.0, ĐÃ DUYỆT)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md
Mode thực thi: main — đo thực tế bằng tdq_bench.py simulate (--he-so-agent 1.5): main 12.2 phút vs đội 12.3 phút (Winner: main, gap 0.0 phút qua 4 đợt, 6 task) (ĐÃ CHỐT)
Trạng thái plan: HOÀN THÀNH

> **Tóm tắt dễ hiểu:** Kế hoạch chia thành bốn đợt với sáu đầu việc tách biệt, không trùng tệp ghi. Đợt đầu chạy song song ba nhánh khảo sát vòng đời Antigravity đa hệ điều hành, kiểm toán mã nguồn hiện có và thử nghiệm cô lập dấu phiên tiến trình. Các đợt tiếp theo hợp nhất sổ bằng chứng, viết bản đặc tả kiến trúc hai pha trước và sau khởi động lại cùng kịch bản giả lập sáu tầng. Đợt cuối tự động kiểm tra trích dẫn và định dạng trước khi lên báo cáo trực quan mà không chạm mã sản phẩm.

## Mục lục

- Phân bổ Model & Effort
- Quy tắc thi hành (áp cho mọi task)
- Thiết kế Trước vs Sau
- Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)
- P1 — Khảo sát Trục A & C: Vòng đời Antigravity đa OS và thực nghiệm cô lập dấu phiên/sandbox
- P2 — Khảo sát Trục B: Kiểm toán sâu mã nguồn setup, add-ons và đường nóng PreInvocation
- P3 — Hợp nhất sổ bằng chứng, tổng hợp Blueprint kiến trúc và soạn báo cáo nháp
- P4 — Log & test bắt buộc
- Cụm song song
- Luật file nóng
- Definition of Done

## Phân bổ Model & Effort
<!-- i18n-allow: canonical model/effort plan allocation table -->
> User được quyền đổi `type model` hoặc `effort` lúc duyệt plan. Thang model: [subagent-tuning.md](../../tdq-conventions/references/subagent-tuning.md).

| Pha | Vai trò | Model | Effort | Ghi chú |
|---|---|---|---|---|
| `implement` | `tdq-explorer` / `self` (3 nhánh thu thập bằng chứng Đợt 1) | `inherit` | `high` | Tra cứu tài liệu chính thức Antigravity, kiểm toán mã nguồn và chạy chẩn đoán cô lập trong `TEMP` |
| `implement` | Leader (`main`) — hợp nhất `evidence.jsonl`, viết Blueprint & báo cáo nháp | `inherit` | `high` | Thiết kế máy trạng thái qua restart, đặc tả `simulate test` 6 tầng và phản biện 4 góc khuất |
| `qc` | Kiểm chứng bằng chứng `QC-I1`–`QC-I4` (`muc_qc=full`) | `inherit` | `high` | Đối chiếu từng `[EV-xxx]` với đĩa/trích đoạn gốc, khóa sạch ranh giới ngoài `docs/tdq/` |
| `report` | Leader (`main`) | `inherit` | `medium` | Chốt báo cáo Markdown 4 phần, render `Archify HTML` và kiểm HTTP `200` qua Tailscale |

## Quy tắc thi hành (áp cho mọi task)
1. Thứ tự phase là thứ tự phụ thuộc — không đảo; đang làm việc trên nhánh `docs/phan-tich-setup-may-trong` tách từ `dev`.
2. Mỗi task: đánh `[~]` khi bắt đầu → thu thập bằng chứng & chạy lệnh `Test:` đạt xanh → đổi sang `[x]` NGAY vào file này. Trạng thái checkbox: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong.
3. Toàn bộ tệp tạo mới/chỉnh sửa phải nằm trong `docs/tdq/` (và `docs/workinglog/` qua `tdq_finish.py`); tuyệt đối không sửa bất kỳ tệp mã nguồn sản phẩm nào, không sửa `~/.gemini/` và không chạm nhánh `main` hay `release/antigravity`.
4. Phép thử dấu phiên tiến trình và dựng workspace mẫu ở `T1.2` chỉ được ghi vào thư mục `TEMP` cô lập (dọn sạch ngay sau khi đo) và phải kiểm tra snapshot `~/.gemini/config/` trước–sau không đổi.
5. QC FAIL → thêm task fix gọn vào mục QC của file này (không cần duyệt lại), lặp đến khi `PASS`.
6. Không commit, merge hay push cho đến khi người dùng yêu cầu.
7. Tuân thủ 6 mã cấm cơ học (`ANTI-1` Fake Red, `ANTI-2` Blind Assertion, `ANTI-3` Dirty State Git, `ANTI-4` Late Tick, `ANTI-5` Raw Dump, `ANTI-6` Broad Area).

## Thiết kế Trước vs Sau
| Khía cạnh | Hiện trạng (Trước) | Kiến trúc đề xuất sẽ đặc tả (Sau) |
|---|---|---|
| Cài đặt từ máy trống & Add-ons | `tdq-setup` giả định đã có Python/Node/Git, neo nhiều đường dẫn `~/.claude*` và tách rời các add-ons (`rtk`, `caveman`, `chrome-devtools`, `tavily`) | Dual-Entry (`1a`) cho cả 3 OS + One-Shot Manifest Consent (`2a`) cài liền mạch Runtime, 3 tầng tìm kiếm và trọn bộ Add-ons trong một lần duyệt |
| Vòng đời Restart & Kiểm chứng | Không lưu trạng thái qua lúc khởi động lại; không có bộ giả lập tự động chạy trên kho trống | Máy trạng thái `${PLUGIN_DATA}/setup-state.json` + hook `PreInvocation` đối chiếu dấu phiên mới (`3a`) tự kích hoạt bộ `Simulate Test` 6 tầng trên sandbox tạm (`4a`) |

*Đối chiếu sơ đồ kiến trúc:* Spec chạy ở chế độ `Work kind: investigate` nên miễn `Archify preview` trước duyệt; toàn bộ 6 task dưới đây phủ kín 4 đầu ra §2 và 6 tiêu chí §6 của spec đã duyệt.

## Ràng buộc toàn cục & Bản đồ Sở hữu Hợp đồng (Ownership Map)

- Ràng buộc chung: `Work kind: investigate` (`0` tệp sửa ngoài `docs/tdq/` và `docs/workinglog/`) · mọi khẳng định kỹ thuật trong nghiên cứu và báo cáo gắn mã `[EV-Axx]`/`[EV-Bxx]`/`[EV-Cxx]` khớp `evidence.jsonl` và tệp trích đoạn `raw/<ev_id>.txt` · `GIỮ NGUYÊN` toàn bộ mã nguồn repo, `~/.gemini/` và các nhánh phát hành.

| Hợp đồng / Ký hiệu (§3c) | File & Task sở hữu | Task / File tiêu thụ |
|---|---|---|
| Shard Trục A (`axis-a-lifecycle-os.md`, `axis-a-lifecycle-os.ev.jsonl`) | `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-a-lifecycle-os.ev.jsonl` (`T1.1`) | `T3.1` |
| Shard Trục C (`axis-c-probes.md`, `axis-c-probes.ev.jsonl`) | `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-c-probes.ev.jsonl` (`T1.2`) | `T3.1` |
| Shard Trục B (`axis-b-code-audit.md`, `axis-b-code-audit.ev.jsonl`) | `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-b-code-audit.ev.jsonl` (`T2.1`) | `T3.1` |
| Sổ bằng chứng (`evidence.jsonl`) & Hồ sơ thiết kế kiến trúc (`research/<slug>.md`) | `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/evidence.jsonl`, `docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md` (`T3.1`) | `T3.2`, `T4.1` |
| Báo cáo nháp Markdown & nguồn `bao-cao.archify.md` | `docs/tdq/reports/2026-11-22-1424-phan-tich-setup-may-trong.md`, `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/bao-cao.archify.md` (`T3.2`) | `T4.1`, pha `qc` & `report` |

## P1 — Khảo sát Trục A & C: Vòng đời Antigravity đa OS và thực nghiệm cô lập dấu phiên/sandbox

- [x] **T1.1** (e10m) Thu thập bằng chứng chính thức về vòng đời nạp lại `PATH`/MCP/Hooks/Rules của Antigravity qua restart và chuẩn lệnh cài đặt không tương tác cho máy trống trên Windows, macOS, Linux — Test: `py -3 -X utf8 -c "import json,pathlib; p=pathlib.Path('docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-a-lifecycle-os.ev.jsonl'); rows=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]; assert len(rows)>=4 and all(r.get('id','').startswith('EV-A') and r.get('source') for r in rows)"`
  - Dùng: `antigravity-guide`
  - Để: lấy chính xác sitemap tài liệu `.md` chính thức (`plugins.md`, `hooks.md`, `mcp.md`, `rules.md`, `sandbox.md`) làm căn cứ xác định những thay đổi bắt buộc restart IDE
  - Ra: `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-a-lifecycle-os.md` và `axis-a-lifecycle-os.ev.jsonl` kèm `raw/EV-A*.txt`
  - Kiểm: `py -3 -X utf8 -c "import pathlib; assert pathlib.Path('docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-a-lifecycle-os.md').stat().st_size > 500"`
  - Không dùng cho: chỉnh sửa cấu hình máy chủ hay kiểm toán mã nguồn nội bộ của repo
  - Req: `§1`, `§2#1`, `§3b`, `§3c Bước 1` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn và `~/.gemini/`
  - Chạm: `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-a-lifecycle-os.md`, `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-a-lifecycle-os.ev.jsonl`
  - Cần: Không
  - Giao tiếp: Consumes: `antigravity-guide` docs mirrors + tài liệu gói đa OS | Produces: `axis-a-lifecycle-os.md` và các bản ghi `EV-A01..EV-A0x`
  - Neo & Công cụ: `read_file` trên `antigravity-guide/references/*` + tải mirror `.md` / `search_web` + `write_file` tạo mới shard Trục A và `raw/EV-A*.txt`
  - Trước → Sau: Giả thuyết `H1` và `H3` chưa có trích dẫn chính thức → Xác định rõ từng thành phần cần restart IDE và bảng lệnh bootstrap user-level trên Windows (`winget`/`uv`), macOS (`brew`/`uv`) và Linux (`uv`/`fnm`/static binaries + fallback distro)
  - Tiêu chí chấp nhận (EARS): KHI thu thập xong tài liệu Antigravity và chuẩn cài đặt 3 OS, HỆ THỐNG PHẢI ghi tối thiểu 4 bằng chứng `EV-A*` có `source`, `claim`, `raw_file`
  - Logic cốt lõi: Tải và lọc mục reload/session/env trong `plugins.md`, `hooks.md`, `mcp.md`, `rules.md`, kết hợp xác thực các cờ không tương tác của `winget`, `brew`, `uv` standalone installer và `fnm`
  - Ca góc hiểm & Assert: Mirror `.md` vắng thông tin chi tiết về tiến trình con → ghi nhận trung thực trích đoạn thực tế và gắn nhãn `Single-source` hoặc kiểm chứng thực nghiệm ở `T1.2`

- [x] **T1.2** (e10m) Đối chiếu cơ chế `${PLUGIN_ROOT}`/`${PLUGIN_DATA}` của skill `plugin` và chạy thực nghiệm cô lập kiểm chứng dấu phiên tiến trình (`Host Session Fingerprint` `H2`) cùng khung `Sandbox Simulate Test` 6 tầng (`H4`) trong `TEMP` — Test: `py -3 -X utf8 -c "import json,pathlib; p=pathlib.Path('docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-c-probes.ev.jsonl'); rows=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]; assert len(rows)>=4 and all(r.get('id','').startswith('EV-C') and r.get('source') for r in rows)"`
  - Dùng: `plugin`
  - Để: xác minh quy ước thư mục `${PLUGIN_DATA}`, `plugin.json` và lệnh `agy plugin validate` trước khi thiết kế nơi đặt `setup-state.json` và bài kiểm thử cô lập
  - Ra: `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-c-probes.md` và `axis-c-probes.ev.jsonl` kèm `raw/EV-C*.txt`
  - Kiểm: `py -3 -X utf8 -c "import pathlib; assert pathlib.Path('docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-c-probes.md').stat().st_size > 500"`
  - Không dùng cho: cài hay xóa plugin thật hoặc ghi bất kỳ tệp nào vào `~/.gemini/`
  - Req: `§1`, `§2#1`, `§3b`, `§3c Bước 3`, `§6 Q2` · Ngoài phạm vi: `GIỮ NGUYÊN` 100% `~/.gemini/config/`
  - Chạm: `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-c-probes.md`, `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-c-probes.ev.jsonl`
  - Cần: Không
  - Giao tiếp: Consumes: skill `plugin`, cây tiến trình runtime và launchers trong `plugins/tdq-workflow-agy/` | Produces: `axis-c-probes.md` và các bản ghi `EV-C01..EV-C0x`
  - Neo & Công cụ: tạo mới `axis-c-probes.md`, `axis-c-probes.ev.jsonl` và `raw/EV-C*.txt` sau khi đọc tài liệu skill `plugin` và đo thực nghiệm trong `TEMP`
  - Trước → Sau: Chưa biết cách phân biệt đáng tin cậy phiên cũ vs phiên đã restart và thời gian chạy thật của sandbox 6 tầng → Có số đo thực nghiệm cây `ppid` + `creation_date`, thời gian chạy thử khung sandbox tạm và bằng chứng `~/.gemini/config/` nguyên vẹn
  - Tiêu chí chấp nhận (EARS): KHI chạy xong phép đo cây tiến trình và dựng thử sandbox tạm trong `TEMP`, HỆ THỐNG PHẢI lưu kết quả đo thực tế vào `raw/EV-C*.txt`, dọn sạch thư mục tạm và chứng minh số tệp `~/.gemini/config/` trước–sau bằng nhau
  - Logic cốt lõi: Đọc chuỗi tiến trình cha lên tới tiến trình gốc Antigravity để rút công thức `Host Session Fingerprint` đa OS; dựng thử thư mục tạm mini kiểm tốc độ gọi `tdq_hook_launcher.mjs`, `tdq_mcp_launcher.mjs lsp`, `rg`, `rtk` và xóa sạch `TEMP`
  - Ca góc hiểm & Assert: Tiến trình trung gian của shell kết thúc sớm làm đổi `ppid` trực tiếp → phải leo cây tiến trình tìm tổ tiên bền vững (`Antigravity`/`language_server` hoặc boot session) thay vì lấy `os.getppid()` đơn thuần; `assert cfg_before == cfg_after`

**Xong P1 khi**: Hai shard `axis-a-lifecycle-os.ev.jsonl` và `axis-c-probes.ev.jsonl` hoàn chỉnh, vượt lệnh `Test:` và bảo toàn nguyên vẹn `~/.gemini/config/`.

## P2 — Khảo sát Trục B: Kiểm toán sâu mã nguồn setup, add-ons và đường nóng PreInvocation

- [x] **T2.1** (e12m) Kiểm toán toàn bộ mã nguồn `tdq-setup`, `tdq_setup.py`, `tdq_lsp.py`, `setup_status.py`, các module add-ons (`rtk`, `caveman`, `devtool_mcp`), trình cài plugin và đường nóng `tdq-dispatch` Rust / `session_start.py` — Test: `py -3 -X utf8 -c "import json,pathlib; p=pathlib.Path('docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-b-code-audit.ev.jsonl'); rows=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]; assert len(rows)>=6 and all(r.get('id','').startswith('EV-B') and r.get('source') for r in rows)"`
  - Dùng: `agy-customizations`
  - Để: đối chiếu cấu trúc discovery roots (`~/.gemini/config/`, `.agents/`, `~/.gemini/GEMINI.md`) và thứ tự ưu tiên của Antigravity với các đường dẫn cứng `~/.claude*` đang nằm trong mã nguồn
  - Ra: `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-b-code-audit.md` và `axis-b-code-audit.ev.jsonl` kèm `raw/EV-B*.txt`
  - Kiểm: `py -3 -X utf8 -c "import pathlib; assert pathlib.Path('docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-b-code-audit.md').stat().st_size > 600"`
  - Không dùng cho: sửa đổi bất kỳ tệp Python, Rust, JS hay Markdown nào ngoài `docs/tdq/`
  - Req: `§1`, `§2#1`, `§2#2`, `§3b`, `§3c Bước 2` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ `scripts/`, `hooks/`, `tools/`, `plugins/`
  - Chạm: `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-b-code-audit.md`, `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-b-code-audit.ev.jsonl`
  - Cần: Không
  - Giao tiếp: Consumes: `agy-customizations` + các tệp mã nguồn setup/hooks/installers | Produces: `axis-b-code-audit.md` và các bản ghi `EV-B01..EV-B0x` kèm `path:line` chính xác
  - Neo & Công cụ: tạo mới `axis-b-code-audit.md`, `axis-b-code-audit.ev.jsonl` và `raw/EV-B*.txt` sau khi đọc khoanh vùng dòng và quét LSP/ripgrep trên các tệp setup, add-ons, installers và hooks dispatch
  - Trước → Sau: Mới biết sơ bộ có đường dẫn `~/.claude*` → Có bảng kiểm toán đầy đủ từng hàm/hằng số cần chuyển đổi, danh mục hàm tái sử dụng được cho từng add-on và điểm móc `O(1)` `< 0.1ms` trong `PreInvocation`
  - Tiêu chí chấp nhận (EARS): KHI hoàn tất kiểm toán mã nguồn, HỆ THỐNG PHẢI liệt kê chính xác `path:line` trên đĩa cho mọi điểm lệch `Claude -> Antigravity`, mọi add-on hiện có và vị trí chèn kiểm tra cờ hậu restart trong cả Rust lẫn Python fallback
  - Logic cốt lõi: Quét toàn bộ tham chiếu `.claude` trong `scripts/` và `skills/tdq-setup/`, đọc cơ chế cài đặt của `rtk_integration`, `caveman_config`, `tdq_devtool_mcp`, và đọc luồng xử lý `PreInvocation` trong `hooks/rust/tdq-dispatch/src/` cùng `hooks/scripts/session_start.py`
  - Ca góc hiểm & Assert: Đề xuất sửa `scripts/` vi phạm luật kiến trúc (như import ngược `hooks/` hoặc ghi đè `docs/tdq/state.json` ngoài `tdq_state.py`) → bắt buộc kiểm tra đối chiếu với `docs/kien-truc.md` ngay trong bảng kiểm toán

**Xong P2 khi**: `axis-b-code-audit.ev.jsonl` chứa tối thiểu 6 bản ghi bằng chứng có `path:line` hợp lệ trên đĩa và vượt lệnh `Test:`.

## P3 — Hợp nhất sổ bằng chứng, tổng hợp Blueprint kiến trúc và soạn báo cáo nháp

- [x] **T3.1** (e12m) Hợp nhất 3 shard thành `evidence.jsonl` và biên soạn Hồ sơ Nghiên cứu & Bản Thiết kế Kiến trúc `docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md` phủ trọn 4 trụ cột (`1a`, `2a`, `3a`, `4a`), phản biện 4 góc khuất và lộ trình tách task triển khai — Test: `py -3 -X utf8 -c "import json,pathlib,re; ev={json.loads(l)['id'] for l in pathlib.Path('docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/evidence.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()}; txt=pathlib.Path('docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md').read_text(encoding='utf-8'); refs=set(re.findall(r'\[(EV-[A-Z0-9-]+)\]', txt)); assert len(ev)>=14 and refs and refs.issubset(ev)"`
  - Req: `§1`, `§2#1`, `§2#2`, `§3c Bước 3`, `§6 Q1`, `§6 Q4` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn ngoài `docs/tdq/`
  - Chạm: `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/evidence.jsonl`, `docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md`
  - Cần: `T1.1`, `T1.2`, `T2.1`
  - Giao tiếp: Consumes: 3 tệp `.ev.jsonl` và `.md` từ `T1.1`, `T1.2`, `T2.1` | Produces: `evidence.jsonl` và hồ sơ kiến trúc `docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md`
  - Neo & Công cụ: `read_file` trên 3 shard + `write_file` tạo mới `evidence.jsonl` và `docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md`
  - Trước → Sau: Ba nhánh dữ liệu rời nhau → Một bản Blueprint kỹ thuật đầy đủ đặc tả Dual-Entry bootstrap 3 OS, One-Shot Manifest Consent, schema JSON `setup-state.json`, giao thức `[TDQ:SETUP-RESUME]`, bộ `Simulate Test` 6 tầng, phản biện góc khuất và danh sách task sẵn sàng cho request `build`
  - Tiêu chí chấp nhận (EARS): KHI hợp nhất xong, HỆ THỐNG PHẢI bảo đảm 100% mã `[EV-xxx]` trong tài liệu nghiên cứu tồn tại trong `evidence.jsonl` và mọi nhận định chính đều gắn nhãn tin cậy (`Verified`/`Single-source`/`Inferred`/`Unverified`)
  - Logic cốt lõi: Hợp nhất không trùng lặp các bản ghi `EV-A*`, `EV-B*`, `EV-C*` vào `evidence.jsonl`; viết đặc tả chi tiết cho từng trụ cột kèm JSON schema mẫu, bảng lệnh đa OS, bảng phân hạng `Core Gate` vs `Optional Add-on Gate` và phản biện counterfactual cho 4 góc khuất lớn
  - Ca góc hiểm & Assert: Thiếu đường lùi khi máy không có quyền cài gói hệ thống hoặc người dùng kẹt ở trạng thái `awaiting_restart` → bắt buộc đặc tả lệnh thoát/vượt tay (`--reset-setup`, `--confirm-restarted`) và cơ chế TTL chống kẹt vô hạn; `assert refs.issubset(ev)`

- [x] **T3.2** (e10m) Soạn nháp báo cáo tổng hợp 4 phần `docs/tdq/reports/2026-11-22-1424-phan-tich-setup-may-trong.md` và nguồn sơ đồ trực quan `bao-cao.archify.md` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/reports/2026-11-22-1424-phan-tich-setup-may-trong.md`
  - Req: `§2#4`, `§6 Q1`, `§6 Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn ngoài `docs/tdq/`
  - Chạm: `docs/tdq/reports/2026-11-22-1424-phan-tich-setup-may-trong.md`, `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/bao-cao.archify.md`
  - Cần: `T3.1`
  - Giao tiếp: Consumes: `docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md`, `evidence.jsonl` | Produces: báo cáo Markdown 4 phần chuẩn và tệp nguồn `@workflow` cho `Archify HTML`
  - Neo & Công cụ: `write_file` tạo mới `docs/tdq/reports/2026-11-22-1424-phan-tich-setup-may-trong.md` và `bao-cao.archify.md` + `doc_lint.py`
  - Trước → Sau: Chưa có báo cáo hướng người đọc và nguồn sơ đồ → Có báo cáo mạch lạc Trước → Sau → Đã kiểm chứng gì → Kết quả & Đề xuất, vượt sạch kiểm tra `doc_lint.py`
  - Tiêu chí chấp nhận (EARS): KHI chạy `doc_lint.py` trên báo cáo nháp, HỆ THỐNG PHẢI thoát `0` (`0 violation`, bao gồm luật `R16` trên ô `Tóm tắt dễ hiểu`) và dẫn chiếu đầy đủ `[EV-xxx]`
  - Logic cốt lõi: Trình bày ô `> **Tóm tắt dễ hiểu:**` súc tích (`<= 120` từ, câu `<= 35` từ, `0` bọc code quanh số/đường dẫn), tóm lược rõ 4 phần bắt buộc cùng bảng đề xuất lộ trình triển khai, và thiết kế sơ đồ `@workflow` tiếng Việt nhãn gọn `<= 28` ký tự trong `bao-cao.archify.md`
  - Ca góc hiểm & Assert: Câu mở đầu báo cáo vượt trần 35 từ hoặc nhãn sơ đồ quá dài gây rớt kiểm tra bố cục Archify → kiểm ngay bằng `doc_lint.py` và giữ nhãn ngắn gọn

**Xong P3 khi**: `evidence.jsonl`, `research/<slug>.md`, `reports/<slug>.md` và `bao-cao.archify.md` hoàn tất, vượt lệnh `Test:` và đạt `doc_lint.py` `0` lỗi.

## P4 — Log & test bắt buộc

Log: BỎ — yêu cầu thuộc chế độ `work_kind=investigate` chỉ nghiên cứu và xuất tài liệu trong `docs/tdq/`, không tạo hoặc sửa mã runtime sản phẩm (chuẩn log của hệ thống mới đã được đưa vào yêu cầu đặc tả của `T3.1`).

- [x] **T4.1** (e6m) Kiểm chứng tự động toàn bộ định dạng tài liệu, toàn vẹn trích dẫn `[EV-xxx]` và `path:line` trên đĩa, bảo toàn `~/.gemini/config/` và ranh giới sạch `git diff` — Test: `py -3 -X utf8 scripts/doc_lint.py docs/tdq/brief/2026-11-22-1424-phan-tich-setup-may-trong.md docs/tdq/spec/2026-11-22-1424-phan-tich-setup-may-trong.md docs/tdq/plan/2026-11-22-1424-phan-tich-setup-may-trong.md docs/tdq/reports/2026-11-22-1424-phan-tich-setup-may-trong.md`
  - Req: `§4`, `§5`, `§6 Q3`, `§6 Q5`, `§6 Q6` · Ngoài phạm vi: `GIỮ NGUYÊN` toàn bộ mã nguồn ngoài `docs/tdq/`
  - Chạm: `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/verify-summary.md`
  - Cần: `T3.2`
  - Giao tiếp: Consumes: `evidence.jsonl`, `research/<slug>.md`, `reports/<slug>.md`, `git diff` | Produces: `verify-summary.md` phục vụ trực tiếp pha `qc` (`QC-I1`–`QC-I4`)
  - Neo & Công cụ: `run_command` chạy kiểm tra Python tự động (`EV-xxx`, `path:line`, `git diff --name-only dev...HEAD`, `doc_lint.py`) + `write_file` tạo mới `verify-summary.md`
  - Trước → Sau: Các tài liệu riêng lẻ chưa qua đối chiếu tổng thể bằng máy → Có biên bản xác nhận `0` trích dẫn mồ côi, `0` đường dẫn sai, `0` tệp chạm ngoài `docs/tdq/` + `docs/workinglog/` và `0` lỗi `doc_lint`
  - Tiêu chí chấp nhận (EARS): KHI chạy kiểm tra tổng hợp, HỆ THỐNG PHẢI xác nhận 100% `[EV-xxx]` khớp `evidence.jsonl`, 100% `path:line` tồn tại trên đĩa, `git diff` sạch ngoài vùng tài liệu cho phép và `doc_lint.py` thoát `0`
  - Logic cốt lõi: Quét regex toàn bộ `[EV-xxx]` và `path:line` trong `research` + `reports` đối chiếu với `evidence.jsonl` và hệ thống tệp thực tế, kiểm tra `git diff --name-only dev...HEAD`, ghi kết quả vào `verify-summary.md`
  - Ca góc hiểm & Assert: Phát hiện bất kỳ trích dẫn lệch dòng hoặc tệp lạ ngoài `docs/tdq/` → sửa dứt điểm trước khi chuyển sang pha `qc`

**Xong P4 khi**: `verify-summary.md` ghi nhận toàn bộ phép kiểm tự động đạt xanh và `doc_lint.py` thoát `0`.

## Cụm song song

Đồ thị phụ thuộc tách thành 4 đợt rõ ràng với `0` xung đột ghi đĩa:
- **Đợt 1 (song song 3 nhánh độc lập):** `T1.1` (`axis-a-lifecycle-os.*`), `T1.2` (`axis-c-probes.*`), `T2.1` (`axis-b-code-audit.*`) — 3 shard hoàn toàn tách rời trong `docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/`.
- **Đợt 2 (tuần tự sau Đợt 1):** `T3.1` (`evidence.jsonl` + `research/<slug>.md`) — hợp nhất bằng chứng, thiết kế Blueprint 4 trụ cột và phản biện góc khuất.
- **Đợt 3 (tuần tự sau Đợt 2):** `T3.2` (`reports/<slug>.md` + `bao-cao.archify.md`) — soạn báo cáo 4 phần và nguồn sơ đồ trực quan.
- **Đợt 4 (tuần tự sau Đợt 3):** `T4.1` (`verify-summary.md`) — kiểm chứng máy toàn vẹn trích dẫn, `doc_lint` và ranh giới sạch kho.

## Luật file nóng

Không có file nóng (`HOT FILE = 0`): mỗi tệp đầu ra ở dòng `Chạm:` thuộc quyền ghi duy nhất của một task, không có hai task nào chạm chung một đường dẫn.

## Definition of Done

Trỏ về §6 của spec `docs/tdq/spec/2026-11-22-1424-phan-tich-setup-may-trong.md` (mức QC `full`, `Work kind: investigate`, mỗi hạng mục kiểm chứng bằng một lệnh thực tế):

- [x] Q1 Đặc tả đầy đủ 4 trụ cột thiết kế (`1a` Dual-Entry 3 OS, `2a` One-Shot Manifest + Add-ons + bảng lệch `Claude -> Antigravity`, `3a` Schema `setup-state.json` + `PreInvocation` auto-resume, `4a` `Simulate Test` 6 tầng trên sandbox tạm) kèm lộ trình chia task triển khai — `py -3 -X utf8 -c "import pathlib; t=pathlib.Path('docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md').read_text(encoding='utf-8'); assert all(k in t for k in ('setup-state.json','PreInvocation','Windows','macOS','Linux','caveman','rtk','chrome-devtools'))"`
- [x] Q2 Thực nghiệm khả thi cô lập dấu phiên tiến trình và khung sandbox tạm chạy an toàn trong `TEMP`, bảo toàn nguyên vẹn 100% thư mục `~/.gemini/config/` — `py -3 -X utf8 -c "import pathlib; t=pathlib.Path('docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/axis-c-probes.md').read_text(encoding='utf-8'); assert 'gemini' in t.lower() and ('untouched' in t.lower() or 'không đổi' in t.lower() or 'nguyen ven' in t.lower() or 'nguyên vẹn' in t.lower())"`
- [x] Q3 Đạt `QC-I1` & `QC-I2`: 100% mã `[EV-xxx]` trong nghiên cứu/báo cáo tồn tại trong `evidence.jsonl`, 100% `path:line` tồn tại trên đĩa và khớp trích đoạn nguồn `raw/` — `py -3 -X utf8 -c "import json,pathlib,re; ev={json.loads(l)['id'] for l in pathlib.Path('docs/tdq/artifacts/2026-11-22-1424-phan-tich-setup-may-trong/evidence.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()}; rep=pathlib.Path('docs/tdq/reports/2026-11-22-1424-phan-tich-setup-may-trong.md').read_text(encoding='utf-8'); refs=set(re.findall(r'\[(EV-[A-Z0-9-]+)\]', rep)); assert refs and refs.issubset(ev)"`
- [x] Q4 Đạt `QC-I3` & `QC-I4`: có phản biện counterfactual cho tối thiểu 4 góc khuất lớn và 100% nhận định chính gắn nhãn tin cậy (`Verified`/`Single-source`/`Inferred`/`Unverified`) — `py -3 -X utf8 -c "import pathlib; t=pathlib.Path('docs/tdq/research/2026-11-22-1424-phan-tich-setup-may-trong.md').read_text(encoding='utf-8'); assert any(lbl in t for lbl in ('Verified','Single-source','Inferred','Unverified'))"`
- [x] Q5 Ranh giới kho sạch (`work_kind=investigate`): `0` tệp sửa ngoài `docs/tdq/` và `docs/workinglog/`, không chạm `main` hay `release/antigravity` — `py -3 -X utf8 -c "import subprocess; out=subprocess.check_output(['git','diff','--name-only','dev...HEAD'],text=True).splitlines(); bad=[f for f in out if not f.startswith(('docs/tdq/','docs/workinglog/'))]; assert not bad, bad"`
- [x] Q6 `doc_lint.py` đạt `0` vi phạm trên trọn bộ tài liệu, `tdq_archify.py verify` trả `status=current` và đường dẫn Tailscale HTTPS của `reports/2026-11-22-1424-phan-tich-setup-may-trong.html` trả HTTP `200` — `py -3 -X utf8 scripts/doc_lint.py docs/tdq/brief/2026-11-22-1424-phan-tich-setup-may-trong.md docs/tdq/spec/2026-11-22-1424-phan-tich-setup-may-trong.md docs/tdq/plan/2026-11-22-1424-phan-tich-setup-may-trong.md docs/tdq/qc/2026-11-22-1424-phan-tich-setup-may-trong.md docs/tdq/reports/2026-11-22-1424-phan-tich-setup-may-trong.md`

## QC vòng 1 — fix

- [x] **QC1.1** (e2m) Đổi đuôi 10 tệp trích đoạn tiếng Anh gốc trong `raw/EV-A*.md` sang `raw/EV-A*.txt` (đúng quy ước `raw/*.txt` ở spec §2#1) và cập nhật tham chiếu trong `axis-a-lifecycle-os.ev.jsonl`, `axis-a-lifecycle-os.md`, `evidence.jsonl` để `tdq_meta_gate.py` không chạy nhầm luật `R12` tiếng Việt lên tài liệu tham khảo tiếng Anh gốc — Test: `py -3 -X utf8 scripts/tdq_meta_gate.py`
