# Quy trình Bump Version 0.103.0, Build 3-OS Rust, Release & Cập nhật Antigravity Local {#tong-quan}

@meta locale=en

Đối chiếu hiện trạng lệch phiên bản trên `dev`/`main`/`~/.gemini/` với kiến trúc đồng bộ `0.103.0` (`5` module `M1`–`M5`) qua SSH build 3 hệ điều hành, dọn sạch máy test, phát hành `main` và cài đặt Antigravity user-level.

## 1. Hiện trạng (Trước): Lệch phiên bản, Rust 0.101.0 & Plugin Local Cũ {#truoc-cap-nhat}

@workflow id=wf-truoc-release title="Trước: Manifest 0.102.0, Cargo/AGY 0.101.0, main v0.100.0 & CHANGELOG 480 dòng"
| dev_drift | Dev 0.102.0 + 3 đợt mới | external |
| changelog_cap | CHANGELOG 480/500 dòng | backend |
| rust_skew | Cargo 0.101.0 + tàn dư SSH | security |
| local_old | main v0.100.0 · AGY 0.101.0 | messagebus |
| dev_drift > changelog_cap | Thiếu release notes 3 đợt |
| changelog_cap > rust_skew | Rủi ro vượt trần R6 |
| rust_skew > local_old | Lệch Windows/Linux/Mac/GEMINI.md |

Hiện trạng đang tồn tại `4` độ lệch đồng thời: nhánh `dev` ghim `0.102.0` dù đã gộp `4 trụ cột agent`, `investigate V2` và `trình bày ngắn gọn`, `CHANGELOG.md` sát trần `480/500` dòng, `Cargo.toml` và plugin AGY live còn ở `0.101.0` (kèm binary Linux/macOS cũ `11/19` và tàn dư `/home/ubuntu/tdq-dispatch` trên máy SSH), còn `main` dừng ở `v0.100.0` và `~/.gemini/GEMINI.md` thiếu luật trình bày mới.

## 2. Bước 1–2 (M1 & M2): Đồng bộ 0.103.0, Tách Archive & Build Rust 3 OS {#sau-m1-m2}

@workflow id=wf-m1-m2-release title="M1-M2: Bump manifest/README, tách CHANGELOG và build + test Rust 3 OS"
| m1_docs | Bump 0.103.0 & Archive 0.60-61 | external |
| win_rust | Windows cargo build + clippy | backend |
| ssh_linux | SSH ubuntu-100-95 musl static-pie | security |
| ssh_mac | SSH mbair Mach-O ARM64 + dọn sạch | messagebus |
| m1_docs > win_rust | Giữ CHANGELOG < 500 dòng |
| win_rust > ssh_linux | Cập nhật Cargo.toml 0.103.0 |
| ssh_linux > ssh_mac | Dọn /tmp & /home/ubuntu/tdq* |

Tách `0.61.0`–`0.60.0` sang `CHANGELOG-archive-3.md` trước khi thêm mục `0.103.0` để `CHANGELOG.md` an toàn dưới trần `500` dòng; sau đó biên dịch mới nhị phân Rust trên cả Windows, Ubuntu (`musl`) và macOS (`ARM64`), chạy test simulation rồi xóa sạch toàn bộ thư mục tạm và tàn dư cũ trên 2 máy SSH.

## 3. Bước 3–4 (M3 & M4): Đóng gói Plugin AGY, Release `main` & Cài Local {#sau-m3-m4}

@workflow id=wf-m3-m4-release title="M3-M4: Build plugin AGY, kiểm full QC, xuất main/tag và cập nhật ~/.gemini/"
| m3_build | Build plugins/tdq-workflow-agy 0.103.0 | backend |
| full_qc | Full pytest + agy validate --strict | security |
| git_rel | Merge dev -> --sinh-main + tag v0.103.0 | external |
| local_agy | install.py + sync GEMINI.md TDQ:TOOLS | messagebus |
| m3_build > full_qc | Đóng gói 3 nhị phân native |
| full_qc > git_rel | 0 failed · giữ local chưa push |
| git_rel > local_agy | Giữ Caveman/RTK · không chạm Claude |

Sau khi đóng gói `plugins/tdq-workflow-agy/` (`v0.103.0`) và vượt qua kiểm định `full` QC + `agy plugin validate --strict`, nhánh được gộp về `dev`, xuất nhánh `main` sạch tại local bằng `--sinh-main` kèm tag `v0.103.0`, rồi cài cập nhật cho riêng Antigravity (`~/.gemini/config/plugins/tdq-workflow-agy` và `~/.gemini/GEMINI.md`) mà không chạm `~/.claude/` hay `~/.codex/`.
