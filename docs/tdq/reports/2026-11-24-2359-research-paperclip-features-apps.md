# BÁO CÁO — Phân tích chi tiết chức năng và khả năng ứng dụng Paperclip

Ngày: 2026-11-25 · Mã yêu cầu: 2026-11-24-2359-research-paperclip-features-apps (6 task tick đủ)
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt dễ hiểu:** Trước khi khảo sát, bạn chỉ mới có kho mã nguồn Paperclip trên máy. Báo cáo này kiểm chứng từng trụ cột tính năng và sáu công cụ AI ưu tiên từ mã nguồn thật. Paperclip mạnh ở quản trị công ty AI, nhưng chưa chạy được Google Antigravity trên Windows. Hãy dùng Docker hoặc WSL2 khi chạy Paperclip, và chỉ học chọn lọc các cơ chế tốt cho TDQ.

## Tầng 1 — Bức tranh dễ hiểu cho người ra quyết định

**Trước request (trạng thái/flow):** Đã xác định tồn tại kho `C:/Users/admin/Documents/paperclip`, nhưng chưa kiểm chứng độ thật của tính năng, khả năng tương thích 6 công cụ AI ưu tiên và ranh giới ứng dụng với `TDQ-Workflow-Antigravity`.
**Sau request (trạng thái/flow):** Đã tổng hợp hồ sơ nghiên cứu toàn diện từ `28` bằng chứng mã nguồn (`evidence.jsonl`), `4` tài liệu phân tích chuyên sâu (`s1`–`s4`) và ma trận chấm điểm `3` hướng ứng dụng:

- **Paperclip là gì (nói dễ hiểu):** Hãy hình dung đây là "văn phòng điều hành công ty AI". Bạn không ngồi gõ lệnh lẻ từng bot nữa, mà xếp sơ đồ nhân sự (`Org Chart`), giao thẻ việc có khóa chống đụng hàng (`Task Manager`), đặt lịch tự chạy (`Routines`), cấp kỹ năng (`Skill Studio`) và khóa trần chi tiêu hàng tháng (`Budgets`).
- **Thứ nào đã làm tới nơi, thứ nào mới thử nghiệm (`H1`):** Lõi quản trị dùng PostgreSQL với `192` file schema Drizzle rất bài bản, có cả hợp đồng đầu ra băm SHA-256 (`completionContracts`) và cầu dao tự ngắt khi lỗi lặp (`automaticRunBrakes`). Ngược lại, `Cases`, `Chat Connectors` và `Memory Connectors` (Mem0, Zep, Supermemory, Cognee, Honcho) vẫn đang ẩn sau cờ thử nghiệm; `6` mục trên lộ trình như `MAXIMIZER MODE`, `Work Queues`, `Self-Organization`, `Auto Org Learning`, `Desktop App` và `BYO Ticket` hiện chưa có mã nguồn thực thi (`Planned`).
- **Sự thật về 6 công cụ AI ưu tiên trên máy Windows (`H2`):** `Claude Code`, `Codex`, `Gemini CLI`, `OpenCode` và `OpenClaw` đều có adapter chính thức dùng được ngay. Riêng **Google Antigravity chưa hỗ trợ Windows**: mã nguồn hiện khóa cứng nền tảng Apple Silicon (`darwin-arm64`), ẩn khỏi menu giao diện và chỉ là candidate chờ duyệt trên `paperclip_runner`.
- **Điểm mạnh lớn và cạm bẫy cần tránh (`H2`, `H3`):** Rất đáng khen ở `MCP Tool Gateway` (`Allowed / Ask first / Off`, tự cách ly tool mới thêm), `Secrets` theo phiên bản có che log và `hard_stop` ngân sách khóa cứng giao dịch. Tuy nhiên trên **Windows**, chế độ không đăng nhập (`local_trusted`) không chặn được tiến trình con của agent tự gọi loopback lên board, và tài liệu kỹ năng cảnh báo cấm dùng `pnpm paperclipai` với dữ liệu lạ vì lỗi chèn lệnh `/bin/sh`.
- **Tổng kết 3 hướng ứng dụng cho bạn (`H4`):**
  - **1. Dùng trực tiếp:** Chạy trong Docker hoặc WSL2 với chế độ `authenticated + private`, gắn trần ngân sách `hard_stop` cho `Claude Code`, `Codex`, `Gemini CLI`, `OpenClaw` và luôn gọi CLI bằng `npx paperclipai`. Không dùng `local_trusted` thuần trên Windows và chưa trông chờ chạy `Antigravity` trực tiếp.
  - **2. Nâng cấp `TDQ-Workflow-Antigravity`:** Học ngay **Circuit Breaker** kiểu `automaticRunBrakes` để ngắt wave subagent lỗi lặp, **MCP Policy + Changed-Tool Quarantine**, băm **Completion Contract SHA-256** và **Eval Matrix fail-closed**. Tuyệt đối không chép PostgreSQL nhúng và `11` bản vá pnpm để giữ sự gọn nhẹ Git-native.
  - **3. Cho dự án AI riêng:** Áp dụng mẫu **Atomic Task Checkout** (`checkoutRunId`), **Secrets binding + redaction**, và tách SDK plugin nhiều lớp — nhưng nhớ bọc Plugin UI trong iframe cô lập thay vì chạy `same-origin JS` như Paperclip hiện tại.

**Đã test gì:** Chạy kiểm chứng toàn diện `QC-I1..I4` (`Q1`–`Q5`) gồm: script Python rà `evidence.jsonl` và biên dòng thực trên đĩa, đối chiếu nguyên văn `12` lát cắt mã nguồn `L2`, kiểm `doc_lint.py`, kiểm tra `git status`/`git diff` cả hai repository, dựng và xác nhận Archify HTML cùng HTTP `200` trên Tailscale Serve.
**Kết quả test:** Đạt `5/5` cổng DoD (`Q1`–`Q5` PASS): `28/28` dòng bằng chứng hợp lệ và được trích dẫn đầy đủ, `0` placeholder hở, `12/12` đối chiếu nguyên văn khớp mã nguồn, `0` file mã nguồn bị sửa ở cả hai repo, `doc_lint.py` `0` vi phạm, Archify đạt `current` và URL Tailscale Serve trả HTTP `200`.
**Đầu ra:** Báo cáo tổng hợp này, ma trận chấm điểm `feature-and-application-matrix.md`, biên bản kiểm chứng `docs/tdq/qc/2026-11-24-2359-research-paperclip-features-apps.md`, `4` shard `s1`–`s4` và sổ `evidence.jsonl` (`28` bằng chứng). · **Archify HTML:** `docs/tdq/reports/2026-11-24-2359-research-paperclip-features-apps.html`
**Giới hạn:** Chỉ khảo sát mã nguồn tĩnh trên đĩa của `C:/Users/admin/Documents/paperclip` (`branch master`), không cài đặt hoặc khởi chạy server Paperclip nên chưa đo tải runtime thực địa; các dự báo ma sát vận hành trên Windows gắn nhãn `Inferred` dựa trên mã nguồn và tài liệu `Verified`.
**Lệch spec chờ duyệt:** không có
**Git:** chưa commit (đang trên nhánh `docs/research-paperclip-features-apps`, không có thay đổi nào ở mã nguồn hai repository)

---

## Tầng 2 — Hồ sơ Kiểm chứng Kỹ thuật & Dẫn chứng Chi tiết

### 1. Kết luận 4 giả thuyết nghiên cứu (`H1`–`H4`)

| Giả thuyết | Kết luận | Độ tin cậy | Bằng chứng gốc (`evidence.jsonl`) & Phản ví dụ / Giới hạn |
|---|---|---|---|
| **H1 (4 trụ cột vs thực tế)** | **Xác nhận có điều kiện** | `Verified` | Lõi control plane hoàn chỉnh (`192` schema Drizzle, atomic checkout, `completionContracts`, `automaticRunBrakes`, Skill Studio): `c4df6da485e1`, `675b0fde5eca`, `6ed72ebf2102`, `bebe66c2b40b`, `939a5d60eb24`. **Giới hạn:** `Memory` tắt mặc định (`851aed075830`), `Cases`/`Chat Connectors` nằm sau cờ experimental (`9808e627df4b`), và `6` mục `ROADMAP.md` chưa có mã sản phẩm (`7b601bcb0d2c`). |
| **H2 (Tương thích 6 agent & Bảo mật)** | **Xác nhận** | `Verified` | Có `16` builtin adapters (`4f327884e23c`); `Claude Code`, `Codex`, `Gemini CLI`, `OpenCode`, `OpenClaw` chạy chính thức (`040177970640`); MCP Policy + Quarantine (`2f2a03922807`), `hard_stop` ngân sách (`a8e553513c25`), Circuit Breaker (`738f669f4a36`), Secrets + Prompt Injection (`0b1938766c67`). **Phản ví dụ:** `Antigravity` bị khóa cứng `darwin-arm64` và chưa có bản Windows (`0cd7c9e55dee`, `c3f785b3a54d`); `local_trusted` trên Windows thiếu chặn process-tree qua loopback (`f106298288d2`); MCP Gateway V1 không chặn tiến trình tự gọi thẳng ngoài gateway (`2f2a03922807`). |
| **H3 (Hệ sinh thái & Triển khai thực chiến)** | **Xác nhận có điều kiện** | `Verified` / `Inferred` | Plugin SDK `1.0.0` đầy đủ (`bf1d1856adaf`), `9` cloud sandbox provider (`0569625de455`), `eval-kernel` (`17f1800f1c31`), Docker build cho Linux AMD64/ARM64 (`d0e96cdea61e`). **Rủi ro thực tế:** `install.sh` ưu tiên macOS/Linux/WSL2 (`b2223121bd7e`); Plugin UI chạy `same-origin JS` không iframe sandbox (`2bcfa6c78590`); phụ thuộc Node `>= 24.11` và `11` bản vá `pnpm` (`ec1f5f6fc365`); cấm dùng `pnpm paperclipai` cho text untrusted (`e519d1712f1d`). |
| **H4 (Đối chiếu TDQ & Tiềm năng ứng dụng)** | **Xác nhận** | `Verified` / `Inferred` | Hai hệ thống bổ trợ: Paperclip mạnh điều phối công ty đa agent liên tục; TDQ mạnh kỷ luật code từng request và hỗ trợ Antigravity native trên Windows (`486ed58ea0e8`, `480c1cafc303`, `7c2529a5c8a9`). Tách rõ danh sách áp dụng ngay, cân nhắc sau và mục cấm copy để tránh phình kiến trúc TDQ. |

### 2. Bảng tóm tắt ma trận ứng dụng theo 3 hướng (xem đầy đủ ở phụ lục)

| Hướng ứng dụng | Nên áp dụng ngay | Cân nhắc sau | Không nên học theo |
|---|---|---|---|
| **Dùng trực tiếp Paperclip** | Chạy Docker/WSL2 `authenticated + private`; gán `Claude/Codex/Gemini/OpenClaw` kèm `hard_stop`; dùng `npx paperclipai` | Bật thử `Cases`, `Chat Connectors`, `Memory Connectors` nội bộ | Dùng `local_trusted` mở trên Windows; chờ `Antigravity` bản native Windows hiện tại |
| **Nâng cấp `TDQ-Workflow-Antigravity`** | Circuit Breaker cho wave subagent (`738f669f4a36`); bảng MCP Policy + Quarantine (`2f2a03922807`); Completion Contract SHA-256 (`939a5d60eb24`) + Eval Matrix (`17f1800f1c31`) | Ngắt `hard_stop` chi phí theo request; Inline Document Annotation trên Archify HTML | Đem PostgreSQL nhúng và `11` bản vá `pnpm` sang TDQ (`ec1f5f6fc365`) |
| **Áp dụng cho dự án riêng** | Atomic Task Checkout (`6ed72ebf2102`); Secrets versioned + Redaction (`0b1938766c67`) | Tách Plugin SDK 5 lớp (`bf1d1856adaf`); Export/Import Portable ZIP | Dùng Plugin UI `same-origin JS` không sandbox iframe (`2bcfa6c78590`) |

### 3. Bản đồ tài liệu chi tiết kèm theo

- Phụ lục bảng chấm điểm `1–5` đầy đủ: `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/feature-and-application-matrix.md`
- Sổ bằng chứng hợp nhất (`28` dòng): `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/evidence-log.md` (`evidence.jsonl`)
- Shard `S1` (Kiến trúc & 4 trụ cột): `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s1.md`
- Shard `S2` (6 Agent, Bảo mật & Ngân sách): `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s2.md`
- Shard `S3` (Plugin, Sandbox, Cài đặt thực chiến): `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s3.md`
- Shard `S4` (Đối chiếu TDQ & Tách lọc): `docs/tdq/artifacts/2026-11-24-2359-research-paperclip-features-apps/s4.md`

## Thời gian

```text
Request `2026-11-24-2359-research-paperclip-features-apps` · lane full · opened at 2026-11-25T00:04:14+07:00

| Phase | Wall clock | Times entered |
|---|---|---|
| idle | 0s | 1 |
| analyze | 11 min | 1 |
| spec | 7 min | 1 |
| plan | 23 min | 1 |
| mode | 10h 01min | 1 |
| implement | 14 min | 1 |
| qc | 53s | 1 |
| Total | 10h 57min |  |

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

**Tóm tắt:** Tổng hợp nghiên cứu và đánh giá chi tiết toàn bộ chức năng, bảo mật, tương thích 6 agent ưu tiên và tiềm năng ứng dụng của Paperclip (đối chiếu với `TDQ-Workflow-Antigravity`). Không sửa mã nguồn ở cả hai repository.
**Trước/Sau:** https://unity-pc-rtx3060.tail99896.ts.net/vlog/tdq-workflow-agy/reports/2026-11-24-2359-research-paperclip-features-apps.html
**Đã kiểm:**
- Script Python `QC-I1`: `28/28` nguồn `path:line` tồn tại trong biên dòng, `28/28` ID trích dẫn khớp `evidence.jsonl`, `0` placeholder, `git diff` mã nguồn rỗng trên cả 2 repo (`PASS`)
- Đối chiếu `QC-I2..I3`: `12/12` lát cắt nguồn `L2` khớp nguyên văn và kiểm đủ `H1`–`H4` kèm phản ví dụ (`PASS`)
- `py -3 -X utf8 scripts/doc_lint.py` trên report, matrix và QC (`0 violation(s)`, `exit 0`)
- `py -3 -X utf8 scripts/tdq_archify.py verify` trả `status: current` và Tailscale Serve HTTP `200` (`PASS`)
**Rủi ro hồi quy:** không có — chỉ tạo tài liệu nghiên cứu trong `docs/tdq/`, `git diff` mã nguồn rỗng trên cả hai repository.
<!-- tdq-archify-binding:start -->
<!-- manifest: 2026-11-24-2359-research-paperclip-features-apps.manifest.json -->
<!-- manifest_digest: f04ae4d9ffb66a85d9d5fe838d71152c9dee6bbafeb621709e23e09d689a7888 -->
<!-- tdq-archify-binding:end -->