# Hướng dẫn Cài đặt `setupfully tdq-workflow` trên Máy mới (Antigravity)

File này dùng độc lập để sao chép sang máy mới (Windows, macOS hoặc Linux), trỏ thẳng về repository trực tuyến chính thức và thiết lập đầy đủ hệ sinh thái `TDQ-Workflow-Antigravity` trên Google Antigravity không cần quyền Admin (`0 sudo`).

> **Cách dùng nhanh nhất trên máy mới:** Mở Google Antigravity ở bất kỳ thư mục nào. Gửi nội dung file này cho Agent và nhắn: **"Làm theo file instruction này để cài đặt và setup fully tdq-workflow từ GitHub về máy mới."**

---

## Thông tin nguồn chính thức (Git Online)

- **Repository URL:** `https://github.com/TDQUOC/TDQ-Workflow-Antigravity.git`
- **Nhánh chứa bộ cài + mã nguồn đầy đủ (`bootstrap` + `setupfully`):** `dev`
- **Nhánh phát hành plugin gọn (`plugin.json` ở gốc):** `release/antigravity`
- **Thư mục chuẩn trên máy mới:** `~/.local/share/tdq-workflow-antigravity` (Windows: `%USERPROFILE%\.local\share\tdq-workflow-antigravity`)

---

## Quy tắc dành cho AI Agent thực hiện trên máy mới

1. **Xác nhận người dùng:** Việc người dùng giao file hướng dẫn này kèm yêu cầu cài đặt tương đương đã cấp quyền thiết lập ở user-space (`0 sudo`, không ghi đè file ngoài phạm vi plugin/tool user và `~/.gemini/`). Nếu máy chưa có `git`, hỏi hoặc chạy đúng lệnh user-space bên dưới theo OS.
2. **Không dùng đường dẫn cứng máy cũ:** Tuyệt đối không giữ path `C:\Users\admin\...`; dùng biến môi trường `%USERPROFILE%` / `$HOME` và `${PLUGIN_ROOT}` / `${PLUGIN_DATA}`.
3. **Không sửa trạng thái dự án khác:** Chỉ thao tác trên bản clone `~/.local/share/tdq-workflow-antigravity`, bản cài plugin ở `~/.gemini/config/plugins/tdq-workflow-agy`, dữ liệu ở `~/.gemini/antigravity/plugin_data/tdq-workflow-agy`, và ghim toàn cục `~/.gemini/GEMINI.md`.

---

## Giai đoạn 0 — Kiểm tra tối thiểu & Tải repo từ GitHub

### Windows (PowerShell — không cần Admin)
```powershell
# 1. Cài Git user-space nếu máy chưa có
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    winget install --id Git.Git --exact --silent --accept-package-agreements --accept-source-agreements --scope user
}

# 2. Clone nhánh dev về thư mục chuẩn
$tdqRepo = Join-Path $env:USERPROFILE ".local\share\tdq-workflow-antigravity"
if (Test-Path (Join-Path $tdqRepo ".git")) {
    git -C $tdqRepo pull --ff-only
} else {
    git clone --branch dev https://github.com/TDQUOC/TDQ-Workflow-Antigravity.git $tdqRepo
}
Set-Location $tdqRepo
```

### macOS / Linux (Bash/Zsh — `0 sudo` trừ khi thiếu `git` hệ thống)
```bash
# 1. Đảm bảo máy đã có git (macOS: xcode-select --install hoặc brew install git; Ubuntu/Debian: sudo apt-get install -y git)
git --version

# 2. Clone nhánh dev về thư mục chuẩn
TDQ_REPO="$HOME/.local/share/tdq-workflow-antigravity"
if [ -d "$TDQ_REPO/.git" ]; then
  git -C "$TDQ_REPO" pull --ff-only
else
  git clone --branch dev https://github.com/TDQUOC/TDQ-Workflow-Antigravity.git "$TDQ_REPO"
fi
cd "$TDQ_REPO"
```

---

## Giai đoạn 1 — Chạy Gate-0 Bootstrap, Cài Plugin & `setupfully`

Script bootstrap tự động dò và cài công cụ nền ở user-space (`fnm` + Node.js LTS `>= 18`, `uv` + Python 3, `agy` CLI nếu thiếu), đẩy `~/.local/bin` lên trước WindowsApps Stubs, chạy `scripts/tdq_setup_probe.mjs`, cài gói `plugins/tdq-workflow-agy`, bật plugin, rồi gọi nối `scripts/tdq_setup.py --setupfully`.

### Windows (PowerShell)
```powershell
# Chạy Gate-0 + setupfully (-Yes cho phép cài uv/fnm/agy user-space không dừng hỏi lại)
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -Yes
```

### macOS / Linux
```bash
chmod +x ./scripts/bootstrap.sh
./scripts/bootstrap.sh --yes
```

**Nếu `agy` CLI chưa có sẵn hoặc `agy plugin install` gặp lỗi, cài plugin bằng fallback từ bản clone:**
```powershell
# Windows
py -3 -X utf8 .\tools\install_agy_plugin.py
py -3 -X utf8 .\scripts\tdq_setup.py --setupfully --json
```
```bash
# macOS / Linux
python3 -X utf8 ./tools/install_agy_plugin.py
python3 -X utf8 ./scripts/tdq_setup.py --setupfully --json
```

**Tùy chọn mở rộng (chỉ chạy nếu người dùng cần):**
- Lưu key Tavily Search vào `secrets.env` riêng tư (tùy chọn):
  `py -3 -X utf8 scripts/tdq_setup.py --set-tavily-key "<TAVILY_API_KEY>"` (Linux/macOS dùng `python3`).
- Plugin `chrome-devtools`: mở thẻ Marketplace trong Antigravity hoặc dùng bảng gợi ý plugin nếu cần test trình duyệt.

---

## Giai đoạn 2 — Khởi động lại Antigravity & Hậu kiểm 6 tầng (`setupfully` hoàn tất)

1. Sau khi `tdq_setup.py --setupfully` báo `status="awaiting_restart"` và đặt cờ `setup-pending.flag`, **đóng hoàn toàn Google Antigravity rồi mở lại**.
2. Mở một cuộc trò chuyện mới bất kỳ và gửi một tin ngắn (ví dụ `"hi"` hoặc `"kiểm tra setup"`):
   - Hook `PreInvocation` sẽ phát hiện thay đổi `Host Session Fingerprint` sau khởi động lại và phát thẻ `[TDQ:SETUP]`.
3. Agent (hoặc người dùng) chạy kiểm chứng 6 tầng khép kín (`T1`–`T6` trong sandbox tự dọn `tdq_sim_*`):
   ```powershell
   # Windows
   py -3 -X utf8 "$env:USERPROFILE\.local\share\tdq-workflow-antigravity\scripts\tdq_setup.py" --post-restart-verify --json
   py -3 -X utf8 "$env:USERPROFILE\.local\share\tdq-workflow-antigravity\scripts\tdq_lsp.py" check
   ```
   ```bash
   # macOS / Linux
   python3 -X utf8 "$HOME/.local/share/tdq-workflow-antigravity/scripts/tdq_setup.py" --post-restart-verify --json
   python3 -X utf8 "$HOME/.local/share/tdq-workflow-antigravity/scripts/tdq_lsp.py" check
   ```
4. **Kiểm tra live end-to-end trong Antigravity (khi cần xác nhận đầy đủ 100%):**
   - Gọi 1 tra cứu `lsp` (`find_symbol` hoặc `find_references`) trên workspace bất kỳ.
   - Gọi 1 subagent `tdq-explorer` kiểm chứng luồng phân quyền và hook subagent.

---

## Tiêu chí Đạt (Done When)

- `agy plugin list --json` hiển thị `tdq-workflow-agy` đã bật (`enabled: true`).
- `--post-restart-verify --json` trả `"core_gate": "PASS"` và `"status": "verified"`, đồng thời xóa `setup-pending.flag`.
- `tdq_lsp.py check` thoát mã `0`; `agent-lsp`, `rg`, `rtk`, Node `tdq_mcp_launcher.mjs` (Caveman), `archify` và `~/.gemini/GEMINI.md` (`< 24.000` bytes) đều sẵn sàng.
- Không báo lỗi nếu thiếu `TAVILY_API_KEY` hoặc `chrome-devtools` (tự động ghi nhận ở `optional_gate`).

---

## Cập nhật sau này từ máy mới

Khi repo online `https://github.com/TDQUOC/TDQ-Workflow-Antigravity.git` có phiên bản mới:
```powershell
# Windows
git -C "$env:USERPROFILE\.local\share\tdq-workflow-antigravity" pull --ff-only
py -3 -X utf8 "$env:USERPROFILE\.local\share\tdq-workflow-antigravity\tools\install_agy_plugin.py"
py -3 -X utf8 "$env:USERPROFILE\.local\share\tdq-workflow-antigravity\scripts\tdq_setup.py" --setupfully --json
```
```bash
# macOS / Linux
git -C "$HOME/.local/share/tdq-workflow-antigravity" pull --ff-only
python3 -X utf8 "$HOME/.local/share/tdq-workflow-antigravity/tools/install_agy_plugin.py"
python3 -X utf8 "$HOME/.local/share/tdq-workflow-antigravity/scripts/tdq_setup.py" --setupfully --json
```
Rồi khởi động lại Antigravity để hệ thống tự chạy `--post-restart-verify`.
