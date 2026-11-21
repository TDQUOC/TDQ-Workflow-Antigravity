# Thiết kế Trước vs Sau — Triển khai Trọn bộ 3 Đợt Kiến trúc `work_kind=investigate` (V2) {#tong-quan}

@meta locale=vi

Chuyển đổi toàn bộ TDQ Workflow (`scripts/`, `hooks/`, `hooks/rust/tdq-dispatch`, `skills/`, `agents/`, `tools/patches/`, `plugins/tdq-workflow-agy/`) từ kiến trúc đơn luồng `build` sang kiến trúc V2 hỗ trợ `work_kind=investigate`, bảo mật `scoped-write` 5 tầng, Shard + Leader-Merge chống `/compact`, bộ đếm gánh nặng Rust theo `sid` giữ nguyên `<0.5ms`, và bộ kiểm chứng `QC-I1..I4`.

## Trước cập nhật: Luồng build duy nhất, mù MCP/range & đứt gãy compact {#truoc-cap-nhat}

@workflow id=wf-before title="Hiện trạng Trước V2: Đơn luồng build & điểm mù"
| don_luong | State chỉ có build, mất mốc implement | backend |
| mu_checkpoint | pre_tool_use L444 bỏ qua range, mù MCP | security |
| khoa_cung | READONLY chặn explorer/debugger | messagebus |
| qc_thua_bug | 2x Archify, R10/R14 cứng, QC chạy 4,315 tests | frontend |
| don_luong > mu_checkpoint |
| mu_checkpoint > khoa_cung |
| khoa_cung > qc_thua_bug |

Hiện trạng ép `24.1%` ca thuần điều tra đi qua quy trình `build`: mất `49.9%` median thời gian ở tiền-implement, thiếu kho lưu vết Shard + Leader-Merge, bỏ sót `resume`/`mode` trên Rust `tdq-dispatch`, và chạy dư `4,315` test code ở `qc`.

## Sau cập nhật: Đợt 1–3 Hoàn thiện V2 Python ↔ Rust ↔ AGY {#sau-cap-nhat}

@workflow id=wf-after title="Kiến trúc Sau V2: 3 Đợt triển khai đồng bộ"
| dot1_core | Đợt 1: State, Lint, EN mode & miễn Preview | external |
| dot2_sec | Đợt 2: Shard-Merge, Deny-first & Burden sid | security |
| dot3_plugin | Đợt 3: Prompt POC, Compiler AGY & 4-ca E2E | backend |
| dot1_core > dot2_sec |
| dot2_sec > dot3_plugin |

Sau khi hoàn thành cả `3` đợt: `tdq_state.py` phân tách `work_kind=investigate` và vá `_cli_approve`; `scoped-write` bảo mật 5 tầng đồng bộ Python/Rust (`tdq-security-reviewer` đọc `100%`, vá `cmd /c` + `[IO.File]`); Rust giữ `<0.5ms` `has_range` kèm Weighted Burden `>=40` tái sử dụng mã `"DOC"` (`22` mã AGY); toàn bộ test parity, `doc_lint`, `token_budget` (`<3,500`) và `agy.EXE plugin validate --strict` PASS hoàn toàn.
