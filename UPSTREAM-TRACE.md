# THÔNG TIN NGUỒN GỐC & KHẢ NĂNG TRUY VẾT UPSTREAM (UPSTREAM TRACEABILITY)
**Tài liệu truy vết phiên bản từ TDQ-Workflow gốc sang TDQ-Workflow-Antigravity**

---

## 1. THÔNG TIN PHIÊN BẢN GỐC (UPSTREAM BASE)

Kho mã nguồn này được fork và phát triển độc lập nhằm tối ưu hóa toàn diện cho **Google Antigravity 2.0 / Gemini**, đồng thời nâng cấp độ tin cậy đa nền tảng (Windows/NTFS/Linux/macOS).

* **Repository Gốc:** `https://github.com/TDQUOC/TDQ-Workflow.git`
* **Nhánh Gốc:** `dev`
* **Commit SHA Gốc:** `b423ee062ef90e0b3c2bb6f0b480cb9d784a1417` (`b423ee06`)
* **Tiêu đề Commit Gốc:** `docs(report): bind and publish Archify report manifest for 2026-11-11-0230`
* **Phiên Bản Gốc Tại Thời Điểm Fork:** `0.97.0` (kế thừa từ bump version `112e9945`)
* **Thời Điểm Fork Gốc:** `2026-11-11T02:30:00+07:00`

---

## 2. THÔNG TIN REPOSITORY ĐỘC LẬP NÀY (TDQ-WORKFLOW-ANTIGRAVITY)

* **Repository Hiện Tại:** `https://github.com/TDQUOC/TDQ-Workflow-Antigravity.git`
* **Nhánh Mặc Định / Phát Hành (Release Branch):** `main`
* **Nhánh Phát Triển (Development Branch):** `dev`
* **Release Tag:** `v0.102.0`
* **Plugin ID & Bundle Bản Địa:** `tdq-workflow-agy` tại `plugins/tdq-workflow-agy/` (chuẩn Antigravity 2.0 Plugin Specification)

---

## 3. CÁC HẠNG MỤC CẢI TIẾN & KHÁC BIỆT CHÍNH SO VỚI GỐC

Toàn bộ các cải tiến dưới đây đã vượt qua bộ kiểm thử **pytest đầy đủ (0 failed)**, **15/15 gates Antigravity**, và **portable CLEAN**:

1. **Bộ Đóng Gói Native Antigravity Plugin (`plugins/tdq-workflow-agy/`):**
   - Đạt chuẩn `agy plugin validate --strict --json` với **0 error / 0 warning**.
   - Cung cấp đủ **6 agents**, **6 hooks**, **3 mcpServers** (lsp, chrome-devtools, tavily-primary), **10 rules** (2-tier), và **12 skills** (75 files, khôi phục đủ cả 2 browser skills).
2. **Hệ Thống Dual-Protocol Hooks (`hooks/scripts/_common.py`):**
   - Hỗ trợ đầy đủ Protojson: `toolCall`, `workspacePaths` (xử lý URI `file:///`), `injectSteps`, `lastUserInput`, `terminationReason`.
   - Đăng ký và đồng bộ danh mục **24 mã nhắc nhở `[TDQ:*]`**.
3. **Các Bản Vá Lỗi P0 Nghiêm Trọng:**
   - **EC-02:** Sửa `remind()` không thoát sớm (`sys.exit(0)`) trong `edit_gate.py`, bảo vệ tuyệt đối cổng cấm sửa ngoài vùng `[TDQ:VUNG]` và kiểm tra stale plan.
   - **NEW-04:** Sửa tokenizer trong `scripts/search_rules.py` không báo lỗi `malformed` oan khi gặp đường dẫn Windows có `\"` ở cuối (`"C:\path\""`), đồng thời bảo toàn chuỗi JSON POSIX.
   - **EC-10:** Xử lý xung đột ghi đồng thời trên NTFS Windows (trước đây mất 29.1% dòng log `.tdq-turn.jsonl`) bằng cơ chế retry lockfile đa nền tảng và phân vùng per-session.
   - **NEW-01:** Sửa `scripts/tdq_finish.py` lỗi `.strip()` cắt xén ký tự đầu tên file; hỗ trợ tiếng Việt qua `git status -z` và `core.quotepath=false`.
   - **NEW-05:** Sửa `scripts/tdq_state.py` lỗi dính BOM UTF-8 `\ufeff` từ PowerShell 5.1 và lỗi ghi đè atomic file trên Windows.
   - **EC-03 / EC-05 / EC-06:** Cơ chế nhận diện subagent tự động, tránh vòng lặp vô hạn ở `stop_gate.py` và chặn subagent sửa code ngoài `.tdq-worktrees/`.
4. **Khả Năng Tương Thích Đa Nền Tảng (Windows PS 5.1 + NTFS + macOS/Linux):**
   - Tự động nhận diện lệnh Python (`py -3` trên Windows, `python3` trên POSIX).
   - Hệ thống con I/O UTF-8 (`scripts/utf8_io.py`) chống crash `cp1252` trên 18+ scripts CLI.
   - Bổ sung `core.longpaths=true` trong `scripts/tdq_team.py`.
5. **Dynamic Tool Unwrapping Cho LSP:**
   - Tự động unwrap `call_mcp_tool` để kiểm soát đầy đủ 65 tools của `agent-lsp.exe` khi AI gọi gián tiếp.
6. **Tối Ưu Ngân Sách Token (Luật R13):**
   - Tách bảng định tuyến sang `skills/tdq-build/references/team-mode-tra-cuu.md` để giữ `team-mode.md` dưới ngưỡng 3.500 tokens.

---

## 4. HƯỚNG DẪN CÀI ĐẶT BẢN PHÁT HÀNH USER-LEVEL TRÊN MÁY KHÁC

Bản phát hành này được thiết kế để **cài đặt trực tiếp vào cấp tài khoản người dùng (User-Level)** tại `~/.gemini/config/plugins/tdq-workflow-agy` (tự động nhận diện trên mọi workspace).

### Cách 1: Cài Đặt User-Level 1 Lệnh (One-Click Installer — Khuyên dùng)
```bash
git clone https://github.com/TDQUOC/TDQ-Workflow-Antigravity.git
cd TDQ-Workflow-Antigravity

# Trên Windows (PowerShell / CMD):
.\install.ps1
# hoặc: py -3 install.py

# Trên macOS / Linux:
./install.sh
# hoặc: python3 install.py

# Cập nhật nhanh khi repo có bản phát hành mới:
.\install.ps1 -Update
# hoặc: py -3 install.py --update
# hoặc trên macOS / Linux: ./install.sh --update
```
*Script tự động copy plugin vào `~/.gemini/config/plugins/tdq-workflow-agy`, điều chỉnh lệnh runtime tương thích với OS, chạy `agy plugin validate` xác nhận 0 lỗi và tự động kích hoạt plugin.*

### Cách 2: Cài Đặt User-Level Qua CLI Antigravity (`agy`)
```bash
git clone https://github.com/TDQUOC/TDQ-Workflow-Antigravity.git
agy plugin install ./TDQ-Workflow-Antigravity/plugins/tdq-workflow-agy
agy plugin enable tdq-workflow-agy
```
> *Lưu ý:* `agy plugin install` cài bản sao từ thư mục cục bộ và chưa tự động đồng bộ từ URL Git từ xa, vì vậy hãy chạy `install.py --update` (`.\install.ps1 -Update` / `./install.sh --update`) khi cập nhật lên phiên bản mới.

### Cách 3: Plugin Discovery (`plugins.json`) ở Cấp Global hoặc Workspace
Clone kho mã nguồn hoặc thêm submodule vào dự án của bạn:
```bash
git clone https://github.com/TDQUOC/TDQ-Workflow-Antigravity.git
```
Khai báo trong `~/.gemini/config/plugins.json` (cấp toàn cục người dùng) hoặc `.agents/plugins.json` tại thư mục gốc dự án:
```json
{
  "entries": [
    { "path": "./TDQ-Workflow-Antigravity/plugins" }
  ]
}
```

---

## 5. QUY TRÌNH ĐỒNG BỘ CẬP NHẬT TỪ UPSTREAM GỐC (FUTURE SYNC WORKFLOW)

Khi bản gốc `TDQ-Workflow` có các tính năng hoặc bản cập nhật mới trên nhánh `dev`, hãy thực hiện đồng bộ theo các bước an toàn sau:

```bash
# 1. Thêm remote upstream nếu chưa có
git remote add upstream https://github.com/TDQUOC/TDQ-Workflow.git

# 2. Lấy dữ liệu mới nhất từ upstream
git fetch upstream dev

# 3. Kiểm tra các commit mới của upstream
git log dev..upstream/dev --oneline

# 4. Tạo nhánh đồng bộ xuất phát từ dev
git checkout dev
git checkout -b sync/upstream-update

# 5. Merge nhánh dev của upstream
git merge upstream/dev

# 6. Chạy 4 Trụ Cột Kiểm Định chất lượng
# Trụ cột 1: Full Pytest Suite
py -3 -B -m pytest tests/ -n auto -q --tb=short

# Trụ cột 2: 15 Antigravity Gates
py -3 -B tools/run_full_verification.py

# Trụ cột 3: Portable Generator & Check
py -3 -B scripts/build_portable.py --sinh-agy --dich "$TEMP/tdq_sync_check/tdq-workflow"
agy plugin validate "$TEMP/tdq_sync_check/tdq-workflow" --strict --json
py -3 -B scripts/tdq_checkportable.py --root "$TEMP/tdq_sync_check/tdq-workflow" check

# Trụ cột 4: Linters & Token Budget
py -3 -B scripts/doc_lint.py skills agents rules
py -3 -B scripts/token_budget.py --kiem

# 7. Merge về dev, sau đó merge sang main và gắn Tag phiên bản mới
git checkout dev
git merge sync/upstream-update
git checkout main
git merge dev
git tag -a vX.Y.Z -m "Release vX.Y.Z: Sync updates from upstream commit <SHA>"
git push origin main dev --tags
```
