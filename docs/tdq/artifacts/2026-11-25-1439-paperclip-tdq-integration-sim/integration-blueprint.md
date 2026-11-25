# Bản thiết kế Tích hợp Tối ưu — Paperclip Pattern vào `TDQ-Workflow-Antigravity`

> Tài liệu này tổng hợp kết quả sàng lọc `4` tiêu chí cứng + tùy chọn add-on (`2a+c`), đối chiếu `27` bằng chứng mã nguồn và kết quả `SIM-1..SIM-6` (`9fdc25e30293`, `981a164cf0ca`). Cam kết `5b`: giữ nguyên `100%` hành vi và kỷ luật cốt lõi của `TDQ-Workflow`.

## 1. Bảng Điểm Sàng lọc Cơ chế (`4` Tiêu chí cứng + Add-on `2a+c`)

| Cơ chế Paperclip đánh giá | Đủ 4 tiêu chí lõi? | Kết quả `SIM` liên quan | Phân nhóm triển khai | Bằng chứng |
|---|---|---|---|---|
| **Atomic Claim Lock (`O_EXCL`) + Lease TTL** | Đạt `4/4` (`0` hồi quy, `0` DB, `0.328 ms`) | `SIM-1`: `61 -> 0` claim trùng, hồi phục `2/2` crash | **P0 — Lõi ổn định** | `596107efb02e`, `b55f0ac994d7`, `9fdc25e30293` |
| **3-Tier Priority Queue + 60m Aging + `blockedBy`** | Đạt `4/4` (`0` hồi quy, stdlib Python) | `SIM-2`: slot `20 -> 4` (aging kích hoạt `1` lần), chặn `1` chạy sớm, `1` wake duy nhất | **P0 — Lõi ổn định** | `8592d1befc8d`, `44fcdddd506d`, `9fdc25e30293` |
| **3-State Circuit Breaker (`closed/open/half_open`)** | Đạt `4/4` (`0` dep mới, ngắt tự động) | `SIM-3`: ngắt burst tại lượt `12`, refusal streak `5` | **P0 — Lõi ổn định** | `d76883f3ba1a`, `8daca69ba8c6`, `9fdc25e30293` |
| **Runtime Budget `hard_stop` (Soft 80% / Hard 100%)** | Đạt `4/4` (gắn vào `tdq_timing`/`tdq_state`) | `SIM-3`: dừng ở `$4.80`, vượt trần `$0.00` (Baseline `+$2.20`) | **P0 — Lõi ổn định** | `bddb62961afe`, `968ec32977a4`, `9fdc25e30293` |
| **MCP Policy Matrix + Changed-Tool Quarantine** | Đạt `4/4` (`0.0009 ms`/check, `0` hồi quy hook) | `SIM-4`: cách ly `2/2` tool lạ, giữ `12/12` bất biến TDQ | **P0 — Lõi ổn định** | `3e7aa4dd449b`, `6d4c00eed673`, `981a164cf0ca` |
| **`Domain Pack` + nối `skill_router.py` BM25** | Đạt `4/4` (mẫu `investigate-mode`, giữ `5b`) | `SIM-5`: `4` gói ngành, `8/8` khớp prompt, `5/5` cổng code trên đĩa giữ nguyên | **P1 — Mở rộng đa lĩnh vực** | `25e4451bc94f`, `b5890600c7f6`, `981a164cf0ca` |
| **Hybrid Bridge (`TDQ <-> Paperclip` Docker/WSL2)** | Trượt tiêu chí #2 cho lõi (cần PG + `11` patch) | `SIM-6`: chậm hơn, không chạy `Antigravity` Windows | **P2 — Add-on tắt mặc định** | `342b3fd669d4`, `a22d6a034353`, `981a164cf0ca` |
| **Postgres nhúng / `same-origin UI` / `local_trusted`** | Trượt tiêu chí bảo mật & độ gọn | Đánh giá kiến trúc `S3`–`S4` | **CẤM sao chép** | `e79c1da5f2ab`, `a22d6a034353`, `642dbc026abe`, `320ec188d2a9` |

## 2. Lộ trình Tích hợp `3` Pha & Danh mục File Dự kiến Chạm (`3a`)

### Pha `P0` — Gia cố Ổn định Điều hành `Phase`/`Task` & Bảo mật Cửa ngõ (`Pattern-Native`)

- **Mục tiêu:** Chặn race ghi state, tự giải phóng task treo, chống bỏ đói, ngắt vòng lặp đốt token và cách ly tool MCP nguy hiểm với độ trễ `p95 = 0.428 ms` (`981a164cf0ca`).
- **File TDQ dự kiến tạo mới / nâng cấp (ở request `feature` sau):**
  1. `scripts/tdq_lease.py` (mới): Cấp và thu hồi khóa `docs/tdq/runtime/leases/<task>.lock.json` qua `os.O_CREAT | os.O_EXCL` kèm `lease_expires_at` và `owner_run_id`.
  2. `scripts/tdq_state.py` (nâng cấp nhỏ): Bổ sung kiểm lock phiên trước khi ghi `save()` (`596107efb02e`), thêm trường `run_brake` (`closed/open/half_open`) và `budget_cap`.
  3. `scripts/tdq_team.py` (nâng cấp `chia_dot` & `wave`): Giữ nguyên `detect_tcas_collision` (`8592d1befc8d`), bổ sung xếp hạng 3 tầng (`Person > Work > Recovery`), `OLDEST_DISPATCH_SHARE = 4` (`44fcdddd506d`), cạnh `blockedBy` động và `idempotencyKey`.
  4. `hooks/scripts/agy_pretooluse_gate.py` & `hooks/scripts/bash_gate.py` (nâng cấp): Nạp bảng `docs/tdq/mcp-policy.json` (chính sách `allow/ask/deny` và SHA-256 `changed-tool quarantine`), giữ nguyên `2` luật shell cũ (`3e7aa4dd449b`).
  5. `tools/patches/` & `plugins/tdq-workflow-agy/` (build sync): Chạy `tools/build_agy_plugin.py` để đồng bộ bản vá sang bundle Antigravity.

### Pha `P1` — Khung `Domain Pack` Đa lĩnh vực Giữ Nguyên Kỷ luật Code (`5b`)

- **Mục tiêu:** Mở rộng từ 2 nhánh `build`/`investigate` sang kiến trúc `Domain Pack` linh hoạt cho `Nghiên cứu/Phân tích`, `PM/BA/Nội dung` và `Vận hành/Checklist`, đồng thời khóa cứng nhánh `code-build`.
- **File TDQ dự kiến tạo mới / nâng cấp:**
  1. `docs/tdq/domains/*.json` (mới): Kho `4` manifest chuẩn (`code-build`, `research-rca`, `pm-ba-content`, `ops-checklist`) kèm trường `base_kind`, `role_profile`, `skills_required`, `qc_gates` và `trust_level` (`0377c980f231`).
  2. `scripts/skill_router.py` (nâng cấp từ prototype): Nối `KhoBM25` (`b5890600c7f6`) vào bước phân loại đầu vào của `tdq-intake` để gợi ý Domain Pack + top-K skill theo prompt tiếng Việt/Anh.
  3. `skills/tdq-intake/SKILL.md` & `scripts/doc_lint.py` (nâng cấp): Thêm cờ `--domain <pack>` với khóa **Zero-Downgrade Lock** — mọi sửa đổi chạm code sản phẩm bên ngoài `docs/` tự động ép chuyển về `code-build` + `QC-F1..F4` (`17d337e3ae59`, `7921aa072f03`).

### Pha `P2` — Add-on Tùy chọn `Hybrid Bridge` (`Tắt mặc định`, chạy Docker/WSL2)

- **Mục tiêu:** Dành riêng cho đội chạy Paperclip Server trên Linux/Docker/WSL2 muốn đẩy các ticket kỹ thuật phức tạp sang TDQ xử lý sâu mà không ảnh hưởng người dùng TDQ chuẩn.
- **File dự kiến tạo mới:** `scripts/tdq_paperclip_bridge.py` (script thủ công / webhook receiver một chiều, chỉ chạy khi biến cấu hình `tdq-config.json` bật `"paperclip_bridge": true`; mặc định `false`).

## 3. Hợp đồng Dữ liệu Mẫu cho `P0` và `P1` (`3a`)

### A. Mẫu Lease Lock & Circuit Breaker (`docs/tdq/runtime/leases/<task>.lock.json`)

```json
{
  "schema_version": 1,
  "task_id": "T1.1",
  "owner_run_id": "run_20261125_w3",
  "acquired_at": "2026-11-25T15:50:00+07:00",
  "expires_at_epoch": 1795597200.0,
  "blocked_by": ["T0.1"],
  "idempotency_key": "claim:2026-11-25:T1.1:v1"
}
```

### B. Mẫu Domain Pack Manifest (`docs/tdq/domains/pm-ba-content.json`)

```json
{
  "domain_id": "pm-ba-content",
  "base_kind": "investigate",
  "role_profile": "pm",
  "trust_level": "markdown_only",
  "allows_code_edits": false,
  "escalate_on_code_touch": "code-build",
  "required_qc_gates": ["ears_criteria", "r16_plain_summary", "doc_lint_zero_errors", "archify_current"],
  "keywords_vi_en": ["prd", "user story", "ba", "tai lieu", "noi dung", "release announcement"]
}
```

### C. Mẫu MCP Policy & Quarantine (`docs/tdq/mcp-policy.json`)

```json
{
  "schema_version": 1,
  "default_effect": "allow",
  "deny_always_beats_allow": true,
  "quarantine_new_write_or_destructive": true,
  "rules": [
    { "domain": "pm-ba-content", "tool": "*_delete*", "effect": "deny" },
    { "domain": "*", "tool": "*_publish*", "effect": "ask" }
  ],
  "known_tool_signatures": {
    "chrome-devtools.take_snapshot": "sha256:read_safe",
    "tdq-lsp.find_references": "sha256:read_safe"
  }
}
```

## 4. Danh mục Tuyệt đối `CẤM` Sao chép từ Paperclip (`3a`)

1. **Cấm thay `state.json` bằng PostgreSQL nhúng (`a22d6a034353`):** Không kéo theo 192 schema Drizzle và 11 bản vá `pnpm` vào TDQ.
2. **Cấm mở chế độ `local_trusted` không xác thực trên Windows (`e79c1da5f2ab`):** Windows không có cách ly cây tiến trình trên loopback.
3. **Cấm nạp UI mở rộng kiểu `same-origin JS` (`PLUGIN_SPEC.md:23`):** Mọi giao diện trực quan phải giữ qua Archify HTML tĩnh hoặc sandbox riêng.
4. **Cấm dùng Adapter Antigravity `ACPX` của Paperclip làm đường chạy Windows (`342b3fd669d4`):** Khóa cứng `darwin-arm64`, kém xa `tdq-workflow-agy` native (`5b0d134135a8`).
5. **Cấm chạy cron heartbeat rỗng tốn token (`SKILL.md`):** TDQ chỉ kích hoạt tiến trình theo bước của request hoặc event thật (`blockedBy` / user input).
6. **Cấm gỡ bỏ `detect_tcas_collision`, `Red -> Green` hay `Verify-by-Effect` SHA-256 (`8592d1befc8d`, `d76883f3ba1a`):** Tuyệt đối giữ nguyên lời cam kết `5b`.
