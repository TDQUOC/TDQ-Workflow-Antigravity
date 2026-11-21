# Báo cáo Sửa Lỗi Subagent Tools Registry & Phát hành `0.103.1` {#tong-quan}

@meta locale=en

Đối chiếu toàn bộ chuỗi sửa lỗi `call_mcp_tool` cho `8/8` subagent `tdq-workflow-agy`, khóa test âm tính, biên dịch Rust `3` OS và xác nhận gọi live `tdq-explorer` ở bản `0.103.1`.

## 1. Hiện trạng `0.103.0` và bản vá `0.103.1` {#hien-trang-va-ban-va}

@workflow id=wf-fix-summary title="Từ sự cố v0.103.0 tới bản vá tool chuẩn Antigravity v0.103.1"
| bad_01030 | 8 agent tool ao | external |
| fix_tools | Loc tool chuan | backend |
| neg_tests | Khoa test am | security |
| hooks_keep | Giu hook IDE | messagebus |
| bad_01030 > fix_tools | Bo 4 tool ao |
| fix_tools > neg_tests | 10 pass 59 sub |
| neg_tests > hooks_keep | 47 dong hook |

Loại `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir` khỏi `_READONLY_TOOLS`/`_WRITER_TOOLS` và sửa lặp `write_file` trong `tdq-explorer.md`, đồng thời khóa test âm tính và giữ nguyên `hooks/`.

## 2. Đóng gói Rust `3` OS và kiểm chứng toàn repo `0.103.1` {#dong-goi-va-qc}

@workflow id=wf-build-qc title="Build Rust 3 OS, dong goi AGY, tron-bo 6 worker va QC doc lap"
| rust_3os | Rust 3 OS 0.103.1 | external |
| agy_pkg | Goi AGY 0 loi | backend |
| tron_bo | 4605 pass 0 fail | security |
| qc_indep | QC Q1-Q6 PASS | messagebus |
| rust_3os > agy_pkg | 29 test, SSH 0 |
| agy_pkg > tron_bo | validate rong |
| tron_bo > qc_indep | SOLID va log ok |

Crate Rust `0.103.1` biên dịch thành công trên Windows, `ubuntu-100-95` (`musl`) và `mbair` (`ARM64`) với `0` tàn dư SSH, gói plugin sạch lỗi và trọn bộ `6` worker đạt `4.605 passed` (`0 failed`).

## 3. Cài `~/.gemini/` bảo toàn Caveman & chờ duyệt `T5.2` {#cai-dat-va-cho-commit}

@workflow id=wf-install-release title="Cai ~/.gemini/ 0.103.1, goi thu live va cho duyet T5.2"
| install_ag | Cai ~/.gemini/ | external |
| live_probe | tdq-explorer ok | backend |
| claude_safe | ~/.claude nguyen | security |
| wait_commit | Cho T5.2 main | messagebus |
| install_ag > live_probe | Caveman va RTK |
| live_probe > claude_safe | read va send ok |
| claude_safe > wait_commit | dev va v0.103.1 |

Bản `0.103.1` đã chạy thật trên Antigravity user-level, giữ nguyên Caveman/RTK và `~/.claude/`, xác minh gọi live `tdq-explorer` thành công và sẵn sàng thực thi `T5.2` khi người dùng duyệt `"commit"`.
