# Quy trình Sửa Lỗi Subagent Tools Registry & Phát hành `0.103.1` {#tong-quan}

@meta locale=en

Đối chiếu hiện trạng `8/8` subagent `tdq-workflow-agy` lỗi registry `call_mcp_tool` ở `0.103.0` với bản vá chuẩn Antigravity 2.0, test khóa âm tính, rebuild Rust 3 OS song song và phát hành `0.103.1`.

## 1. Trước khi sửa: `8/8` subagent lỗi registry & lặp chuỗi `write_file` {#truoc-khi-sua}

@workflow id=wf-truoc-fix title="Trước: 8/8 subagent gãy khi gọi invoke_subagent ở Antigravity 2.0"
| commit_old | Commit 4859058b thêm 4 tool | external |
| front_bad | 8/8 agents chứa call_mcp_tool | backend |
| validate_miss | validate bỏ qua trường tools | security |
| runtime_crash | invoke_subagent lỗi registry | messagebus |
| commit_old > front_bad | Kèm grep_search, list_dir |
| front_bad > validate_miss | Test cũ khóa nhầm contract |
| validate_miss > runtime_crash | Nổ khi dựng executor |

Commit `4859058b` gán `call_mcp_tool`, `grep_search`, `find_by_name`, `list_dir` vào `skills_and_agents.py`, còn `tdq-explorer.md` lặp `write_file`, khiến cả `8/8` subagent không dựng được executor dù `agy plugin validate` báo đạt.

## 2. Bản vá M1–M3: Tool chuẩn Antigravity, Test Âm Tính & Rust `0.103.1` 3 OS {#ban-va-m1-m3}

@workflow id=wf-sau-m1-m3 title="M1-M3: Tool chuẩn Antigravity, Test âm tính & Rust 0.103.1 trên 3 OS"
| fix_tools | Chuẩn hóa 8 agent | external |
| neg_test | Test cấm tool lỗi | backend |
| ver_bump | Bump 0.103.1 docs | security |
| rust_3os | Rust Win + 2 SSH OS | messagebus |
| fix_tools > neg_test | Red-Green giữ hooks |
| neg_test > ver_bump | Sửa tdq-explorer |
| ver_bump > rust_3os | Dọn sạch 0 rác SSH |

Đưa danh sách tool về đúng chuẩn `migrate-agent-settings/SKILL.md` (`read_file`, `edit_file`, `write_file`, `run_command`, `manage_task`, `search_web`, `send_message`), khóa test âm tính, giữ nguyên `hooks/` cho agent chính, rồi đồng bộ `0.103.1` và biên dịch lại Rust `3` OS.

## 3. Hoàn tất M4–M5: QC `6` Worker, Cài `~/.gemini/` & Release `main` + `v0.103.1` {#hoan-tat-m4-m5}

@workflow id=wf-sau-m4-m5 title="M4-M5: Build AGY, tron-bo 6 worker, cài ~/.gemini/ & xuất main v0.103.1"
| agy_build | Build plugin AGY 0.103.1 | backend |
| xdist_qc | tron-bo 6 worker + strict | security |
| install_live | Cài ~/.gemini/ giữ Caveman | external |
| release_main | Merge dev -> main + v0.103.1 | messagebus |
| agy_build > xdist_qc | 0 failed · bo_sot=0 · Q1-Q6 |
| xdist_qc > install_live | ~/.claude nguyên · gọi thử |
| install_live > release_main | Chỉ local, không git push |

Sau khi đóng gói và chạy trọn bộ kiểm thử `6` worker với `0` lỗi, cài bản `0.103.1` ra `~/.gemini/` giữ nguyên Caveman/RTK, kiểm gọi subagent và xuất nhánh local `main` kèm tag `v0.103.1`.
