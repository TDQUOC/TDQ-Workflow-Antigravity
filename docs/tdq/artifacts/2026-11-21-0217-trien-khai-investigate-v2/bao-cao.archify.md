# Báo cáo Triển khai Trọn bộ 3 Đợt Kiến trúc `work_kind=investigate` V2 {#tong-quan}

@meta locale=vi

Tổng quan kết quả: Triển khai đồng bộ vào mã nguồn thật (`scripts/`, `hooks/`, `hooks/rust/tdq-dispatch/`, `skills/`, `agents/`, `tools/patches/`, `plugins/tdq-workflow-agy/`, `tests/`) toàn bộ `3` đợt (`M1`–`M6`) theo Spec đã duyệt, hoàn thành `8/8` task gốc (`T1.1`–`T4.1`), `2` vòng sửa `QC1.1`–`QC1.2`, và đạt **PASS** trọn bộ `4,632` kiểm thử (`4,596 passed, 36 skipped, 0 failed`), Rust `29 passed` + `0` clippy warning, `agy.exe plugin validate --strict` (`findings: []`) cùng biên bản ký độc lập của `tdq-qc-tester`.

## 1. Trước request: Đơn luồng `build`, mù `range`/MCP & thiếu `scoped-write` {#truoc-request}

@workflow id=bao-cao-truoc title="1. Trước request: Luồng build đơn điệu & điểm mù V1"
| don_luong | State chỉ có build, bug _cli_approve im=0s | external |
| thieu_shard | Chưa có evidence shard-merge & NTFS lock | backend |
| khoa_cung | READONLY chặn cứng explorer/debugger; canonical 1 cấp | security |
| mu_burden | pre_tool_use.rs bỏ qua range, mù MCP & resume/mode | messagebus |
| don_luong > thieu_shard |
| thieu_shard > khoa_cung |
| khoa_cung > mu_burden |

Trước khi thực hiện request: mọi tác vụ điều tra bị ép đi qua luồng `build` (R10/R14 cứng, 2 lần Archify, `_cli_approve` bỏ quên ghi mốc `implement`), `tdq_team.py` chưa có `evidence add/merge/render` hay `worktree_required: false`, `edit_gate`/`pre_tool_use.rs` chưa tách `tdq-security-reviewer` khỏi nhóm điều tra (`cmd /c` và `[IO.File]` còn lọt), Rust `tdq-dispatch` bỏ qua đọc theo dải dòng và chưa đếm Weighted Burden theo `sid`, và chưa có bộ test đối kháng Python ↔ Rust + mô phỏng `4` ca (`1056`, `1457`, `1346`, `1953`).

## 2. Sau request: Đợt 1–3 Hoàn thiện V2 Python ↔ Rust ↔ AGY {#sau-request}

@workflow id=bao-cao-sau title="2. Sau request: Kiến trúc V2 đồng bộ 3 đợt"
| dot1_state | M1+M5: work_kind, R10/R14, escalate, EN mode | external |
| dot2_sec | M2-M4: Evidence Shard, 5-layer Deny-first & Burden sid | security |
| dot3_plugin | M6: Agents POC, Rust .exe & plugin validate strict | backend |
| e2e_sim | T4.1: Parity Python<->Rust & 4-ca tmp_path PASS | messagebus |
| dot1_state > dot2_sec |
| dot2_sec > dot3_plugin |
| dot3_plugin > e2e_sim |

Sau khi hoàn thành request: `tdq_state.py` phân nhánh sạch `work_kind=investigate`, vá `ghi_moc_phase` & `escalate-to-build`, miễn Double Archify và giữ nguyên `PHASE_TABLE == 11`; `doc_lint`/`tdq_plan_scaffold`/`tdq_bench` miễn có điều kiện `R10`/`R14` và tách `docs/tdq/bench/<slug>/*.py`; `tdq_team.py` hỗ trợ `evidence add|merge|render` (`--claim-file`, khóa NTFS/POSIX `O_EXCL` không phụ thuộc `fcntl`) và `no_worktree`; Python + Rust `tdq-dispatch.exe` áp dụng bảo mật `scoped-write` `5` tầng Deny-first kèm Weighted Burden `>=40` theo `sid` (`[TDQ:DOC]`, giữ nguyên `22` mã AGY) trong khi vẫn bảo toàn `Hot PreToolUse (Direct)` `14.76 ms`; bundle `plugins/tdq-workflow-agy/` được compile mới và chứng nhận `--strict`.

## 3. Đã test gì: 2 vòng Fix QC1.1–QC1.2, Toàn bộ Suite `4,632` Test & Kiểm Độc lập {#da-test}

@workflow id=bao-cao-kiem-tra title="3. Đã test gì: Quy trình 5 Wave, Fix QC & Independent QC"
| waves_impl | Waves 1-5: 8 task merge sach, 0 open worktree | external |
| tronbo_fix | QC1.1 (sys.path) + QC1.2 (10 module do -> 228 passed) | backend |
| tronbo_2 | tdq_test.py tron-bo lan 2: 4,632 tests (222 modules) | messagebus |
| qc_tester | tdq-qc-tester doc lap: 18 parity probes + TDQ_LOG=0 | security |
| waves_impl > tronbo_fix |
| tronbo_fix > tronbo_2 |
| tronbo_2 > qc_tester |

Trong quá trình kiểm chứng: sửa dứt điểm xung đột `sys.path`/`sys.modules` khi ghép suite (`QC1.1`), sau lượt `tron-bo` thứ nhất phát hiện `10` module đỏ (`_ntfs_lock` dùng `fcntl`, `worktree_required` dư khi `True`, `session_start` mất chuỗi O10/MCP-First, `doc_index`/`luat-hien-co.md`, `test_agent_upgrade_mvp` `SubagentStop` và `APPROVED_RELEASE_DOCS`) đã vá sạch tại `QC1.2` (`5e513558`), rồi chạy lại trọn bộ `tdq_test.py tron-bo --workers 1 --fresh --reuse off` (`2/3`), đo benchmark độ trễ Rust, chạy `cargo test && cargo clippy`, `agy.exe plugin validate --strict`, và để subagent `tdq-qc-tester` kiểm tra chéo độc lập mọi mục `Q1`–`Q6` & `QC-F1`–`QC-F4`.

## 4. Kết quả test: Pass 6/6 DoD, 4,596/4,632 Passed (0 Failed) & Đủ Giới hạn Thực tế {#ket-qua}

@workflow id=bao-cao-ket-qua title="4. Kết quả test: Chứng nhận QC PASS & Tailscale HTTP 200"
| dod_q1_q4 | Q1-Q4: 29 Rust tests, clippy 0, validate findings=[] | backend |
| dod_q5_f1 | Q5+QC-F1: tron-bo 4,596 passed, 36 skipped, 0 fail | messagebus |
| latency_ok | Hot PreToolUse Direct 14.35-14.76 ms (<=25 ms), 22 AGY | external |
| safe_scope | Q6: ~/.gemini/ giu moc 11/19; chi build Windows .exe (1a/2a) | security |
| dod_q1_q4 > dod_q5_f1 |
| dod_q5_f1 > latency_ok |
| latency_ok > safe_scope |

Kết quả thực tế: `Q1` `211 passed` + `investigate-mode.md = 1,783` tokens (`<= 3,000`) + `66` file `<= 3,500` tokens (`i18n_check 0` lỗi); `Q2` `99 passed, 1 skipped` (`WinError 1314` symlink, `mklink /J` PASS) + `18/18` probe độc lập `py == rust`; `Q3` `89 passed` + `Hot PreToolUse (Direct)` `14.35 ms` (`tdq-qc-tester` đo `14.76 ms`, chuẩn `<= 25.0 ms`) + `22` mã AGY; `Q4` `cargo test` `29 passed` + `clippy` `0` warning + `agy plugin validate --strict` `findings: []` + `--dry-run` exit `0`; `Q5` `tron-bo` `4,596 passed, 36 skipped, 0 failed, 2,891 subtests` (`1,279.01s`, `bo_sot=0`) + `TDQ_LOG=0` im `100%`; `Q6` `C:\Users\admin\.gemini\config\plugins\tdq-workflow-agy` chưa bị ghi đè (`2a`), binary Linux/macOS giữ bản prebuilt (`1a`), `QC-F2..F4` PASS, `tdq-qc-tester` ký **PASS everything**.
