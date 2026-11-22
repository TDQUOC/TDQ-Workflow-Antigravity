# BÁO CÁO — Nghiên cứu custom marketplace GitHub, sẵn sàng Git và cơ chế auto-update của Antigravity

Ngày: 2026-11-22 · Mã yêu cầu: 2026-11-22-0821-research-marketplace-va-update (6/6 task tick đủ)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Google Antigravity không hỗ trợ custom marketplace GitHub kiểu danh mục riêng mà chỉ nhận kho chính hãng hoặc cài trực tiếp URL repo. Kho mã nguồn hiện tại chưa sẵn sàng đưa lên GitHub cho cộng đồng đa hệ điều hành vì còn cứng đường dẫn Windows và thiếu đồng bộ nhánh. Khi cài plugin từ Git remote, Antigravity không lưu địa chỉ nguồn nên không tự kiểm tra hay tự cập nhật phiên bản mới. Báo cáo tổng hợp đầy đủ bằng chứng kiểm chứng cùng phương án xử lý theo thứ tự ưu tiên mà không sửa mã nguồn.

## 1. Trước request (trạng thái/flow)

Trước khi điều tra, hệ thống chưa có tài liệu kiểm chứng chính thức về khả năng phân phối plugin Antigravity qua GitHub:

- Chưa rõ Antigravity có hỗ trợ khai báo custom marketplace từ GitHub (như `@ten-marketplace` của Claude Code hay Codex `.agents/plugins/marketplace.json`) hay không.
- Trong repo có nhiều adapter song song (`.agents/plugins.json`, `.agents/plugins/marketplace.json`, `.claude-plugin/`, `plugins/tdq-workflow-agy/`) nhưng chưa đối chiếu tính sẵn sàng khi đẩy lên GitHub công khai cho cộng đồng Windows, macOS và Linux.
- Chưa xác định khi cài plugin trỏ về Git remote thì Antigravity có tự kiểm tra phiên bản mới và auto-update hay không.

## 2. Sau request (trạng thái/flow)

Kết quả kiểm chứng từ tài liệu sống `antigravity.google` (tới CLI `v1.5.12` / App `v2.34.0`), thử nghiệm cô lập `agy v1.4.12` và kiểm toán toàn bộ cấu hình repo trả lời dứt khoát cả 3 câu hỏi (đều ở mức tin cậy `Verified`):

- **Câu 1 — Antigravity có hỗ trợ Custom Marketplace từ GitHub không? KHÔNG (`Verified` `[EV-A01]`, `[EV-A08]`):** Antigravity chỉ hỗ trợ tên marketplace duy nhất `antigravity-plugins-official` (`Error: unknown marketplace` với tên riêng); không có lệnh thêm/update marketplace như Claude Code. Tuy nhiên Antigravity **CÓ** 3 con đường cài từ Git: (a) cài thẳng URL/subpath GitHub qua `agy plugin install https://github.com/<owner>/<repo>[/tree/<branch>/<path>]` (`[EV-A02]`, `[EV-A10]`), (b) nạp cấp Workspace khi clone repo chứa `.agents/plugins/` hoặc `.agents/plugins.json` trỏ đường dẫn nội bộ repo (`[EV-A05]`), và (c) nộp đơn đăng ký Google Marketplace (`https://forms.gle/2EX5RFYPoJe1UgxR9`) (`[EV-A03]`).
- **Câu 2 — Project này đã sẵn sàng đưa lên GitHub cho cộng đồng đa OS chưa? CHƯA (`Verified` `[EV-A11]`, `[EV-B01]`–`[EV-B07]`):** Gói `plugins/tdq-workflow-agy/` đã vượt `agy plugin validate --strict` (`0` lỗi `[EV-A12]`), nhưng còn 6 khoảng trống chặn phát hành công khai:
  - `mcp_config.json` đóng cứng đường dẫn cá nhân Windows `C:\Users\admin\...`, `npx.cmd` và `--userDataDir=C:/Users/admin/...` (`[EV-B01]`).
  - `hooks.json` đóng cứng `bin\tdq-dispatch.exe`, làm lỗi toàn bộ 6 hook trên macOS/Linux (`sh -c`), binary chưa đặt trong `scripts/` để giữ quyền `0755`, và `rules/AGENTS.md` dùng `py -3` (`[EV-A04]`, `[EV-B02]`).
  - Nhị phân `tdq-dispatch-linux-x86_64` và `tdq-dispatch-darwin-arm64` còn kẹt ở bản cũ `d74393da` (`2026-11-21`), chậm hơn `.exe` (`f1e7fcfb`, `2026-11-22`), CI chưa tự đồng bộ vào repo và thiếu `x86_64-apple-darwin` (`[EV-B03]`).
  - Remote `origin` trỏ mặc định vào `main`, nhưng `scripts/build_portable.py:69-70` lại loại `plugins/`, `tools/`, `.agents/plugins.json` khỏi `main`, làm lệnh cài URL gốc `https://github.com/TDQUOC/TDQ-Workflow-Antigravity` rơi nhầm sang `.claude-plugin/` (`tdq-workflow`, mất `10 rules`, `3 mcpServers` và hỏng hooks `[EV-A11]`, `[EV-B04]`).
  - Adapter 3 host lệch tên/URL (`tdq-workflow` vs `tdq-workflow-agy`, trỏ `TDQUOC/TDQ-Workflow` cũ `[EV-B05]`), và `dev`/`main` cục bộ chưa đồng bộ lên `origin` (hơn `25` và `62` commit `[EV-B06]`).
- **Câu 3 — Trỏ về Git remote có auto-check & auto-update khi có version mới không? KHÔNG (`Verified` `[EV-A06]`, `[EV-A08]`, `[EV-A09]`, `[EV-A10]`):** Chỉ **Marketplace plugin** chính thức mới ghi `"installedFrom"` trong `config.json` để so khớp cache `.zip` trên `gstatic.com` và tự cập nhật. Khi cài từ GitHub URL, `agy` chỉ `git clone --depth 1` vào `%TEMP%`, chép tĩnh không giữ `.git`, không ghi URL/nhánh/SHA vào `config.json` hay `import_manifest.json` và không có lệnh `agy plugin update`; muốn lên bản mới phải chạy lại `agy plugin install <url>` (hoặc `git pull` nếu dùng cấp Workspace `.agents/plugins.json`).
- **Phương án đề xuất (`P0` → `P2`):** (1) Khử đường dẫn `C:\Users\admin` trong `agy_manifests.py`, (2) đổi `hooks.json` sang wrapper đa OS đặt trong `scripts/`, đồng bộ CI binary 3 OS và đưa manifest Antigravity lên nhánh phát hành chuẩn, (3) nộp Antigravity Marketplace (`https://forms.gle/2EX5RFYPoJe1UgxR9`) nếu muốn auto-update chính chủ hoặc thêm kiểm tra phiên bản nhẹ bất đồng bộ TTL `<= 1.5s`, (4) chuẩn hóa metadata 3 host và đồng bộ `origin`. Chi tiết tại [tài liệu nghiên cứu](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/research/2026-11-22-0821-research-marketplace-va-update.md).

## 3. Đã test gì

- Thu thập và lưu trữ đầy đủ các trang tài liệu `.md` chính thức từ `https://antigravity.google` (`llms.txt`, `plugins.md`, `marketplace.md`, `build-plugins.md`, `customization-discovery.md`, `hooks.md`, `changelog.md`, `schemas/v1/plugin.json`, `cli/reference.md`, `settings.md`, `enterprise.md`) cùng built-in skills (`antigravity-guide`, `plugin`, `agy-customizations`).
- Chạy thực nghiệm cách ly `agy v1.4.12` (`validate`, `install` cục bộ, `install` từ URL GitHub gốc và subpath `.../tree/dev/plugins/tdq-workflow-agy`, `disable`, `enable`, `list --json`, `@custom-mp`, `link`) với `USERPROFILE`/`HOME` trỏ `tempfile.TemporaryDirectory()` và kiểm tra đối chiếu toàn bộ 371 tệp ở `~/.gemini/config/` trước–sau.
- Kiểm toán tĩnh cấu hình adapter, bộ dựng/cài đặt, `.github/workflows/`, cây nhánh `dev`/`main`/`origin` và kiểm tra tính hợp nhất của 19 bằng chứng trong `evidence.jsonl` cùng phản biện counterfactual (`QC-I1`–`QC-I4`).

## 4. Kết quả test

- **`T1.1` (Docs chính thức Antigravity):** `PASS` (`7` bằng chứng `EV-A01`–`EV-A07`, HTTP `200` trên mọi mirror `.md` và JSON schema).
- **`T1.2` (Thực nghiệm cách ly `agy`):** `PASS` (`5` bằng chứng `EV-A08`–`EV-A12`, `REAL_HOME_UNTOUCHED: True` ở mọi lượt chạy; xác nhận `validate --strict plugins/tdq-workflow-agy` đạt `0 findings` còn `validate .` thất bại ở gốc repo).
- **`T2.1` (Kiểm toán repo đa OS & Git):** `PASS` (`7` bằng chứng `EV-B01`–`EV-B07`, đối chiếu trực tiếp dòng tệp và `git ls-tree`/`git log` thực tế).
- **`T3.1` & `T4.1` (Sổ bằng chứng, phản biện & ranh giới kho):** `PASS` (`19/19` mã `[EV-xxx]` hợp nhất và truy vết khớp `evidence.jsonl`, `doc_lint` `0` lỗi, `0` tệp sửa ngoài `docs/tdq/` và `docs/workinglog/`, nhánh `main` và `~/.gemini/` giữ nguyên vẹn).

## Đầu ra

- **Sổ bằng chứng & shard:** `docs/tdq/artifacts/2026-11-22-0821-research-marketplace-va-update/{evidence.jsonl,axis-a-docs.*,axis-a-cli.*,axis-b-repo.*,raw/*,verify-summary.md}`
- **Tài liệu nghiên cứu chi tiết:** [research/2026-11-22-0821-research-marketplace-va-update.md](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/research/2026-11-22-0821-research-marketplace-va-update.md)
- **Tài liệu quy trình & QC:** [spec](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/spec/2026-11-22-0821-research-marketplace-va-update.md), [plan](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/plan/2026-11-22-0821-research-marketplace-va-update.md), [phiếu QC](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/qc/2026-11-22-0821-research-marketplace-va-update.md)
- **Archify HTML:** `docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.html`
- **Giới hạn:** Máy đang chạy kiểm chứng là Windows 11 với `agy v1.4.12` (trong khi tài liệu trực tuyến phản ánh CLI tới `v1.5.12` / App `v2.34.0`); hành vi thực tế của binary macOS/Linux được kiểm chứng qua kiểm toán CI/script/chỉ dẫn chính thức `sh -c` thay vì chạy trực tiếp trên máy Mac/Linux. Yêu cầu không sửa mã nguồn (`work_kind=investigate`); `eval: chưa kích hoạt (opt-in)`.
- **Lệch spec chờ duyệt:** không có
- **Git:** Nhánh `docs/research-marketplace-va-update` (tách từ `dev`), chỉ chứa tài liệu/bằng chứng mới trong `docs/tdq/` và `docs/workinglog/`, chưa commit/merge.

## Thời gian

```text
Request `2026-11-22-0821-research-marketplace-va-update` · lane full · opened at 2026-11-22T08:27:38+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 1s | 1 |
| analyze | 5 min | 1 |
| spec | 1 min | 1 |
| plan | 7 min | 1 |
| mode | 28s | 1 |
| implement | 15 min | 1 |
| qc | 2 min | 1 |
| report | 14s | 1 |
| Total | 31 min |  |

Model compute time is unavailable (`model_giay=null`). API includes network/provider latency; tool time is host wait. Observed metrics may overlap; unattributed time is not assumed user/model time.
Transcript attribution: project_window. Complete covers selected supported observations only.
Host metrics unavailable (5 hidden: api_request_seconds, tool_call_seconds, background_job_seconds, observed_union_seconds, unattributed_seconds): no_usable_source, no_usable_observations, wall_minus_observed_union;no_usable_observations

## Agent Role Telemetry

| Role | Runs | First pass | Rate | Retries | Avg elapsed | Models |
|---|---|---|---|---|---|---|
| self | 7 | 7 | 100% | 0 | — | — |
| tdq-qc-tester | 6 | 6 | 100% | 0 | — | — |
| tdq-implementer | 2 | 2 | 100% | 0 | — | — |
```

## Thân PR (soạn sẵn)

**Tóm tắt:** Nghiên cứu và kiểm chứng toàn diện ba vấn đề khi phân phối TDQ Workflow trên Google Antigravity qua GitHub: hỗ trợ custom marketplace, mức sẵn sàng đa OS của repo và cơ chế auto-update. Kết luận rõ Antigravity không hỗ trợ custom marketplace GitHub mà chỉ nhận kho chính hãng hoặc cài URL GitHub tĩnh không auto-update, đồng thời lập danh sách 6 khoảng trống và phương án xử lý ưu tiên.

**Trước/Sau:** Xem sơ đồ trực quan tại `docs/tdq/reports/2026-11-22-0821-research-marketplace-va-update.html`.

**Đã kiểm:**
- Thử nghiệm cách ly `agy v1.4.12` (`validate`, `install` GitHub root & subpath, `@custom-mp`, `link`) bảo toàn 100% 371 tệp `~/.gemini/config/`
- Kiểm tra toàn vẹn `19/19` bằng chứng `[EV-xxx]` trong `evidence.jsonl`, `doc_lint.py` (`0` lỗi) và `git diff` không chạm ngoài `docs/tdq/`

**Rủi ro hồi quy:** Không có rủi ro hồi quy mã nguồn vì yêu cầu thuộc `work_kind=investigate`, không chỉnh sửa mã chạy, manifest, `~/.gemini/` hay nhánh `main`.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-22-0821-research-marketplace-va-update.manifest.json -->
<!-- manifest_digest: ec26e706240eae43574dad281386ab376c42d7de87d4d8d6374195a5e8ca73cb -->
<!-- tdq-archify-binding:end -->