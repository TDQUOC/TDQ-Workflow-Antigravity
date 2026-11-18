# Trước/Sau — Tối ưu hiệu năng lõi hook, chuyển sang chỉ dẫn 4 phần & dọn cổng (R1+R2+R3) {#tong-quan}

@meta locale=en

Hiện trạng: gói Antigravity mở `2–3` tiến trình `py -3` mỗi sự kiện (`PreInvocation` `449,5 ms`). Nó gọi `git` lặp lại ở mọi bước model và chặn nhầm nhiều lệnh hợp lệ. Thiết kế mới gộp còn `1` tiến trình `dispatch.py` qua `python -X utf8`. Mốc lượt dùng `transcriptPath` giúp bỏ qua `git` giữa lượt, và `overwrite` tự sửa tham số thiếu.

## Trước: Đa tiến trình py -3, gọi git lặp và chặn cứng cộc lốc {#truoc}

@workflow id=hook-kien-truc-truoc title="Hiện trạng: Spawn rời rạc qua py -3, chạy git lặp và deny cộc lốc"
| agy_ev_old | Sự kiện AGY | external |
| multi_py | 2-3 tiến trình py -3 | messagebus |
| git_repeat | 3 lệnh git + xóa sổ | backend |
| hard_deny | Chặn SEARCH/LSP/TICK | security |
| agy_ev_old > multi_py | 56ms/spawn |
| multi_py > git_repeat | 449ms/call |
| git_repeat > hard_deny | 196 deny |

Mỗi bước gọi model đều chạy lại `turn_snapshot` và bơm lặp `"same as last turn"` (`2,33M` ký tự). Trong khi đó, lệnh PowerShell `@'...'@` hoặc `start_lsp` thiếu `language_id` bị chặn cộc lốc.

## Sau: 1 Dispatcher python -X utf8, mốc lượt chuẩn và chỉ dẫn 4 phần {#sau}

@workflow id=hook-kien-truc-sau title="Thiết kế mới: 1 dispatch.py, mốc transcriptPath và chỉ dẫn 4 phần"
| agy_ev_new | Sự kiện AGY | external |
| dispatch_one | 1 dispatch.py (python) | messagebus |
| fast_turn | Mốc lượt + cache root | backend |
| smart_gate | 9 chặn, 2 sửa, thẻ 4 phần | security |
| agy_ev_new > dispatch_one | <=100-150ms |
| dispatch_one > fast_turn | 0 git ở bước 2+ |
| fast_turn > smart_gate | user_markdown |

Bước giữa lượt nhận diện qua `USER_INPUT` cuối trong `transcriptPath` và tốn `0` lệnh `git`. Cổng `TDQ:LSP` tự dò ngôn ngữ `O(1)` rồi bọc vào `Arguments` trong `overwrite`.

## Phân luồng xử lý 22 cổng trong dispatch.py {#phan-luong}

@workflow id=luong-phan-loai-cong title="Luồng quyết định in-process của dispatch.py trên Antigravity 2.0"
| tool_in | Payload stdin | external |
| router_in | Phân loại cổng? | messagebus |
| hard_9 | 9 cổng an toàn: deny | security |
| auto_2 | LSP/SUBAGENT: overwrite | backend |
| soft_12 | 12 cổng + SEARCH lần 1 | frontend |
| tool_in > router_in | |
| router_in > hard_9 | APPROVE/GIT/TEAM |
| router_in > auto_2 | sửa Arguments/Workspace |
| router_in > soft_12 | allow + thẻ 4 phần |

Ở `implement`/`qc`, `TDQ:SEARCH` cho phép lần đầu kèm thẻ nhắc 4 phần. Nó chỉ chặn nếu tái phạm grep mù lần 2 liên tiếp. Bản gốc Claude/Codex được giữ tương thích (`1a`), và `~/.gemini` không bị ghi đè (`4b`).
