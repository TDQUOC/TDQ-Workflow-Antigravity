# Kết quả Thực nghiệm Simulate Test (`SIM-1`–`SIM-6`)

> Thực thi cô lập trong sandbox tạm tại `2026-11-25T16:04:17+07:00` · Python `3.13.15` · Platform `win32` · Tổng kịch bản PASS: `6/6`.

| Kịch bản | Mục tiêu kiểm chứng | Baseline (Hiện trạng TDQ) | Proposed (Tích hợp Paperclip Pattern) | Kết quả |
|---|---|---|---|---|
| **SIM-1** | Atomic Lock + Lease TTL (8 luồng, 2 crash) | `61` claim trùng · `2` task kẹt chết | `0` claim trùng · `2/2` task tự hồi phục (`0.328 ms`) | **PASS** |
| **SIM-2** | 4-Tier Priority + 60m Aging + `blockedBy` | Task cũ đợi tới lượt `20` · `3` wake trùng | Task cũ chạy ngay lượt `4` · `1` wake duy nhất · `0` lỗi sớm | **PASS** |
| **SIM-3** | Circuit Breaker + Budget `hard_stop` | Đốt `21` lượt lỗi · lố ngân sách `+$2.2` | Ngắt ở lượt `12`, refusal ngắt tại streak `5` · chi `$4.8` (`+$0.00` vượt trần) | **PASS** |
| **SIM-4** | Bảo toàn `12` bất biến TDQ + MCP Quarantine | `12/12` bất biến · `0/2` tool lạ bị chặn | `12/12` bất biến (`0` hồi quy) · `2/2` tool lạ cách ly (`0.0009 ms`) | **PASS** |
| **SIM-5** | `4` Domain Packs + định tuyến BM25 | Chỉ có `2` kind · `4/4` nhóm phi-code lệch cổng | `4` Domain Pack · `8/8` khớp prompt · Code Build bảo toàn `100%` | **PASS** |
| **SIM-6** | Đo độ trễ `Pattern-Native` vs `Hybrid Bridge` | TDQ không đo tổng chuỗi lock+budget+policy | `Pattern-Native`: `p50=0.367 ms`, `p95=0.428 ms`, `0` dep mới vs Bridge cần PG + `11` patch | **PASS** |

## Kết luận thực nghiệm rút ra từ `SIM-1..SIM-6`

- **Tính khả thi & ổn định (`SIM-1`–`SIM-3`):** Khả thi hoàn toàn bằng Python stdlib (`0` thư viện mới). Atomic `O_EXCL` lockfile + TTL dập tắt triệt để race claim và treo worker; aging fairness đưa task cũ lên xử lý trong `<= 4` lượt; circuit breaker + `hard_stop` chặn lố ngân sách về `$0.00`.
- **Bảo toàn chất lượng TDQ (`SIM-4`–`SIM-5`):** Kiểm tra trực tiếp `12/12` bất biến trên các file thật của repo (`tdq_state.py`, `tdq_team.py`, `agy_stop_gate.py`, `edit_gate.py`, `token_budget.py`) đạt `0` hồi quy. Domain Pack đa lĩnh vực giữ nguyên 100% bộ cổng khắt khe cho `code-build`.
- **Chọn kiến trúc tối ưu (`SIM-6`):** Trên Windows + Antigravity, `Pattern-Native` có độ trễ p95 chỉ vài mili-giây nên thắng tuyệt đối cho lõi (`P0`–`P1`). `Hybrid Bridge` chỉ phù hợp làm add-on `P2` tùy chọn chạy trong Docker/WSL2.
