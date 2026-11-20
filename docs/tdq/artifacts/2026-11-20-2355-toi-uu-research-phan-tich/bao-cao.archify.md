# Báo cáo Phân tích Thực nghiệm, Red-Team & Đề xuất Kiến trúc V2 (`work_kind=investigate`) {#tong-quan}

@meta locale=vi

Tổng quan kết quả: Kiểm chứng thực nghiệm trên 174 bản ghi lịch sử khẳng định nhận định tiền-implement bị phình (`49.9%` vs `12.7%` median ở `investigate — full`); thực thi trọn vẹn 2 vòng Collect → V1 → Red-Team 3 chiều (`A · B · C`) → Hội tụ Đề xuất Hoàn chỉnh V2 vá `100%` `9` cụm nhược điểm (`ND-1`–`ND-9`, truy vết từ `17/17` mã Red-Team) và xác minh `29` bằng chứng `EV-xxx` cùng kỷ luật `0` tệp mã nguồn bị chạm.

## 1. Trước request: Luồng build ép phân tích vào tiền-implement & mất mạch khi compact {#truoc-request}

@workflow id=bao-cao-truoc title="1. Trước request: Luồng build ép nặng tiền-implement"
| chi_mot_luong | Chỉ có 1 luồng build | external |
| phinh_tien_impl | Tiền-impl 49.9% (424L + 2x HTML) | backend |
| mu_checkpoint | Mù MCP & range pre_tool_use.rs | security |
| qc_thua_bug | QC-F1 chạy 4,315 tests; bug im=0s | messagebus |
| chi_mot_luong > phinh_tien_impl |
| phinh_tien_impl > mu_checkpoint |
| mu_checkpoint > qc_thua_bug |

Trên `42/174` (`24.1%`) ca thuần điều tra (`33` research/analysis/audit + `9` debug/scan), nhóm `investigate — full` (`N=25`) tốn median `1,888s` (`49.9%`) tiền-implement so với `780s` (`12.7%`) ở `implement`, chịu double Archify (`2.88 MB`), mù checkpoint trên MCP web/đọc theo dải, và bị `QC-F1` ép chạy `4,315` tests (`1,283s`) dù sửa `0` dòng code.

## 2. Sau request: Đề xuất Hoàn chỉnh V2 — Trọng tâm vào Implement & Vá 100% Red-Team {#sau-request}

@workflow id=bao-cao-sau title="2. Sau request: Kiến trúc V2 sau Red-Team 3 chiều"
| triage_nhe | M1: work_kind=investigate (miễn Preview) | external |
| gate_breakeven | M5: Tier 0 SAS >45% & Two-Stage Bugfix | messagebus |
| rust_shard_sec | M2-M4: Shard+Merge, Rust Burden, Deny-first | backend |
| qc_bang_chung | M5-M6: QC-I1..I4 & Failsafe ngoài docs/tdq/ | security |
| triage_nhe > gate_breakeven |
| gate_breakeven > rust_shard_sec |
| rust_shard_sec > qc_bang_chung |

Kiến trúc V2 chuyển trọng tâm điều tra sâu sang `implement` với `6` trụ cột (`M1`–`M6`) đã vá kín `ND-1`–`ND-9`: giữ `<0.5ms` fast-path Rust (`pre_tool_use.rs:444`) kèm bộ đếm Weighted Burden `>=40` theo `sid` tái sử dụng mã `"DOC"`, Shard + Leader-Merge qua `--claim-file` + `with_ntfs_lock`, bảo mật `scoped-write` Deny-first (giữ `tdq-security-reviewer` đọc `100%`, canonicalize `ancestors()` + chặn `cmd /c`/`[IO.File]`), Tier 0 Zero-Fanout SAS (`>45%`), Two-Stage Bugfix (`escalate-to-build`), miễn double Archify ở `_archify_gate`, cô lập script `.py` ở `docs/tdq/bench/<slug>/` và quy trình `QC-I1..I4` đối chiếu đĩa thô chống ALCE F6.

## 3. Đã test gì: Điều tra song song, Red-Team A · B · C & Đối chiếu nguồn trên đĩa {#da-test}

@workflow id=bao-cao-kiem-tra title="3. Đã test gì: Quy trình 2 vòng + Kiểm chứng QC-I1..I4"
| wave1_collect | T1.1-T1.3: 174 timing + Code + 29 URL | external |
| wave2_v1 | T2.1-T2.2: 18 EV + Đề xuất V1 (M1-M6) | messagebus |
| wave3_redteam | T3.1-T3.3: Red-Team A/B/C (17 ND) | security |
| wave4_qc_v2 | T4.1-T5.1: V2 + 248 path:line + Q1-Q6 | backend |
| wave1_collect > wave2_v1 |
| wave2_v1 > wave3_redteam |
| wave3_redteam > wave4_qc_v2 |

Thực hiện đầy đủ `T1.1`–`T5.1` theo `mode=subagent` (`TRAN_SONG_SONG=3` mỗi wave `no_worktree`), kiểm chéo `248` trích dẫn `path:line` trên đĩa, đối chiếu trực tiếp `5` điểm nóng nguồn (`timing.jsonl`, `tdq_state.py`, `pre_tool_use.rs`, `bash_gate.py`/`tdq_team.py`, `gate_guidance.json`/`token-budget.json`), chạy `doc_lint.py` và kiểm tra `git status`/`git diff dev` + plugin ngoài repo `~/.gemini/`.

## 4. Kết quả test: Pass 6/6 DoD, 0 lỗi path:line / F6 / doc_lint & Zero-Code-Touch {#ket-qua}

@workflow id=bao-cao-ket-qua title="4. Kết quả test: Xác minh thực tế Q1–Q6"
| ev_and_v1 | Q1-Q2: 29 EV + 4 V1 (M1-M6) PASS | external |
| redteam_and_line | Q3-Q4: 17 ND + 248 path:line 0 F6 | backend |
| lint_and_html | Q5: doc_lint 0 + Archify + HTTP 200 | messagebus |
| zero_code_touch | Q6: 0 code ngoài docs/ bị chạm | security |
| ev_and_v1 > redteam_and_line |
| redteam_and_line > lint_and_html |
| lint_and_html > zero_code_touch |

Kết quả xác minh: `Q1` đạt `29` `EV-xxx`; `Q2` đủ `4` tệp V1 phủ `173`/`174` bản ghi + `M1`–`M6`; `Q3` đủ `3` tệp Red-Team (`5` `ND-A*`, `6` `ND-B*`, `6` `ND-C*`); `Q4` xác minh `100%` trích dẫn `path:line` hợp lệ trên đĩa (`0` missing/OOB, `0` F6 qua đối soát trực tiếp); `Q5` `doc_lint.py` `0` vi phạm & truy vết `100%` `ND-1`..`ND-9` + `Archify` current + Tailscale HTTP `200`; `Q6` `0` tệp code ngoài `docs/` bị chạm (`git diff dev` sạch code) · Giới hạn: request `docs`-only nên mã nguồn chạy được chưa sửa, đã bàn giao lộ trình `3` đợt code cho request kế tiếp.
