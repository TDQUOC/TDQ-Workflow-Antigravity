# Thiết kế MVP 4 Trụ cột Nâng cấp Agent TDQ (Antigravity 2.0) {#tong-quan}

@meta locale=en

So sánh kiến trúc hệ thống agent trước và sau khi triển khai MVP `4` trụ cột ưu tiên Google Antigravity 2.0 (`6` module `M1`–`M6`).

## 1. Hiện trạng v0.102.0: Lệch Model, 3 Agent Mồ Côi & Hở Cổng {#truoc-cap-nhat}

@workflow id=wf-before title="Trước cập nhật: ghim flash/pro, 3/6 mồ côi, hở shell và lệch schema"
| dispatch | Gọi 1 implementer | external |
| compile | AGY ép flash/pro | security |
| guard | Hở python -c / >= | messagebus |
| exit | 2 schema lệch nhau | backend |
| dispatch > compile | Mất LSP & effort |
| compile > guard | Chặn nhầm QC write |
| guard > exit | Không hậu kiểm |

Hiện trạng chỉ kích hoạt `tdq-implementer` thường xuyên, `ultra` giới hạn `1` QC và thiếu hậu kiểm khi subagent thoát.

## 2. Sau cập nhật (M1–M2): Cấu hình Plugin, 8 Agent & Packet V2 {#sau-m1-m2}

@workflow id=wf-m1-m2 title="M1-M2: tdq-config.json, thang Gemini 4, 8 agent và Packet V2+"
| plan_cfg | Plan Model/Effort | external |
| cfg_json | tdq-config.json | backend |
| team8 | 6+2 agent & caller | messagebus |
| pkt_bb | Packet V2 + Board | security |
| plan_cfg > cfg_json | 3.8 Flash->4 Carbon |
| cfg_json > team8 | Ultra max 5 QC |
| team8 > pkt_bb | 1 JSON + đa ngôn ngữ |

Tất cả agent về mặc định `inherit`, có bảng phân bổ model/effort trong Plan và truyền đủ Mini-Spec qua Packet V2+.

## 3. Sau cập nhật (M3–M4): Hook AGY/Claude, Rust & Scoped QC {#sau-m3-m4}

@workflow id=wf-m3-m4 title="M3-M4: Vá command_parser.rs, mở hẹp docs/tdq/qc/ và hậu kiểm thoát"
| pre_post | Pre/PostToolUse | external |
| role_reg | Đăng ký role ID | backend |
| rust_fix | Vá >= & python -c | security |
| stop_chk | Stop/SubagentStop | messagebus |
| pre_post > role_reg | Lưu sessions.json |
| role_reg > rust_fix | Mở hẹp docs/tdq/qc/ |
| rust_fix > stop_chk | Ghi telemetry role |

Trên Antigravity, hậu kiểm chạy bằng `PostToolUse` và `Stop` thật; trên Claude Code chạy chung qua `SubagentStop`.

## 4. Sau cập nhật (M5–M6): Build AGY Parity & Ultra QC Song Song {#sau-m5-m6}

@workflow id=wf-m5-m6 title="M5-M6: Build plugins/tdq-workflow-agy, test parity và QC song song"
| cargo_b | Build Rust Win | backend |
| agy_bld | Build plugin AGY | security |
| parity | Test 8 agent+shell | messagebus |
| ultra_qc | QC song song <= 5 | external |
| cargo_b > agy_bld | Giữ < 24KB & AST |
| agy_bld > parity | 0 lỗi hồi quy |
| parity > ultra_qc | Hỗ trợ unlimited |

Bản plugin biên dịch sạch trong repo (không đụng `~/.gemini`), vượt trọn bộ unit, smoke, runtime và QC song song.
