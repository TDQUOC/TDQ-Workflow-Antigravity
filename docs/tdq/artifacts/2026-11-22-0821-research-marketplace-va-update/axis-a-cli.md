# Shard Trục A2 — Thực nghiệm cách ly `agy` CLI (`v1.4.12`) & Cơ chế lưu trữ (T1.2)

Ngày thu thập: 2026-11-22 · Skill nạp: `plugin` (`SKILL.md` L121–309) + `agy-customizations/docs/plugins.md` & `json_configs.md`

## Chứng minh bảo toàn môi trường người dùng

- Chụp snapshot toàn bộ 371 tệp trong `C:\Users\admin\.gemini\config\` trước và sau mọi lệnh thử nghiệm bằng `USERPROFILE`/`HOME` trỏ `tempfile.TemporaryDirectory()`.
- Kết quả mọi lượt chạy (`raw/agy_probe_2.txt:143`, `raw/agy_probe_3.txt:236`): **`REAL_HOME_UNTOUCHED: True`** (`0` tệp bị thêm, xóa hay đổi `mtime`/kích thước trong `~/.gemini/config/`).

## Kết quả thực nghiệm & Bằng chứng (`raw/agy_probe_2.txt`, `raw/agy_probe_3.txt`)

1. **[EV-A08] Không hỗ trợ custom marketplace tên riêng qua `@marketplace`:**
   - `agy plugin install tdq-workflow-agy@custom-mp` thất bại (`ec=1`, `Error: unknown marketplace: custom-mp`, `agy_probe_3.txt:207-208`).
   - `agy plugin link antigravity-plugins-official firebase` và `link custom-mp ...` đều thất bại (`ec=1`, `Error: unknown marketplace: ...`, `agy_probe_3.txt:209-210`).
2. **[EV-A09] Kho Official Marketplace mới có metadata theo dõi phiên bản:**
   - Cache cục bộ nằm tại `~/.gemini/antigravity-cli/cache/marketplaces/{antigravity-plugins-official,antigravity-plugins-partners}/{marketplace.json,meta.json}`, phân phối qua archive `.zip` kèm `sha256` trên `gstatic.com` (`agy_probe_3.txt:56-97`).
   - Trong `~/.gemini/config/config.json` thật trên máy (`L1-55`), chỉ 7 plugin Official Marketplace mới có khóa `"installedFrom": {"id": ..., "marketplace": "antigravity-plugins-official", "version": ...}`; còn `tdq-workflow-agy` chỉ có `{"enabled": true}` (`L52-54`).
3. **[EV-A10] Cài qua URL GitHub subpath hoạt động tốt nhưng KHÔNG lưu nguồn để auto-update:**
   - Khi chạy `agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity/tree/dev/plugins/tdq-workflow-agy`, `agy` gọi `git clone --depth 1 --branch dev ...` vào thư mục tạm `%TEMP%\plugin-install-*` rồi chép phần plugin vào `.gemini/config/plugins/tdq-workflow-agy` (`agy_probe_2.txt:17-26`). Không giữ thư mục `.git/`.
   - Trong môi trường cách ly sau khi cài từ GitHub URL: `import_manifest.json` (`agy_probe_2.txt:116-142`) chỉ ghi `{"name": "tdq-workflow-agy", "source": "antigravity", "importedAt": "...", "components": [...]}` — **không hề lưu URL GitHub, tên nhánh hay commit SHA**; `config.json` (`agy_probe_3.txt:211-218`) không ghi `installedFrom`. Chạy lại cùng lệnh cài (`reinstall_gh_subpath_dev`) thì thay thế thủ công và in `(replaced existing installation)` (`agy_probe_2.txt:95-104`).
4. **[EV-A11] Trỏ thẳng URL gốc GitHub (`https://github.com/TDQUOC/TDQ-Workflow-Antigravity`) bị nhận nhầm thành Claude Code plugin:**
   - `agy plugin validate --json .` thất bại (`ec=1`): báo thiếu `plugin.json` tại gốc hoặc `.antigravity-plugin/`, phát hiện repo giống Claude Code plugin (`agy_probe_3.txt:102-122`).
   - Thực tế chạy `agy plugin install https://github.com/TDQUOC/TDQ-Workflow-Antigravity` (và `/tree/main`) kéo bản `.claude-plugin` (`0.98.0` trên `origin` hiện tại), chuyển đổi sai tên thành `tdq-workflow`, mất sạch `10 rules` + `3 mcpServers` và sinh 2 khóa hook lỗi `["description", "hooks"]` (`agy_probe_2.txt:9-58,105-112`).
5. **[EV-A12] Gói con `plugins/tdq-workflow-agy/` đạt chuẩn Antigravity native:**
   - `agy plugin validate --strict --json plugins/tdq-workflow-agy` thoát `0`, `"findings": []`, nhận đủ `12 skills, 8 agents, 10 rules, 3 mcpServers, 6 hooks` (`agy_probe_3.txt:123-138`).
