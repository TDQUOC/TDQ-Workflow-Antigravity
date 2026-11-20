# Research: Kiến trúc Subagent & Multi-Agent trong các Workflow/Package Lớn

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

## 1. Truy vấn & Nguồn chính

Ghi chú failover công cụ tìm kiếm trong phiên phân tích này:

- `tavily-primary` thành công 2/6 truy vấn (`BMAD-METHOD / OpenHands / SWE-agent / Aider / Cline / Roo Code` và `MAST / multi-agent failures`).
- 4/6 truy vấn `tavily-primary` còn lại lỗi hạn mức keyless: `You reached the daily keyless Tavily limit... Retry after: 2112s / 734s / 1453s / 725s`.
- Đã kích hoạt `search_web` đúng 1 lần theo failover được cấp phép để phủ phần Claude Code, `obra/superpowers`, Anthropic và Cognition.
- Các chủ đề `affaan-m/everything-claude-code`, `LangGraph`, `CrewAI`, `OpenAI Codex` và trích xuất sâu `tavily_extract` bị chặn bởi hạn mức trên nên không suy diễn.

Bảng tổng hợp truy vấn, nguồn URL đã kiểm chứng và điểm cốt lõi:

| Cụm chủ đề | Truy vấn / Kênh | Nguồn URL chính thức & bài viết | Điểm cốt lõi rút ra |
|---|---|---|---|
| Claude Code Subagents & Teams | `search_web` failover | https://code.claude.com/docs/en/sub-agents | `disallowedTools` trừ quyền thừa; `isolation: worktree` cô lập nhánh Git. |
| Claude Code Agent Teams | `search_web` failover | https://code.claude.com/docs/en/agent-teams | Teams chạy ngang hàng với task list chung và nhắn tin trực tiếp. |
| Worktree Isolation & Guide | `search_web` failover | https://claude-world.com/tutorials/s12-worktree-isolation/ | Chặn ghi ngược về checkout chính ở tầng hệ thống tệp. |
| `obra/superpowers` | `search_web` failover | https://github.com/obra/superpowers | Kỹ năng tự kích hoạt, brainstorming/spec trước code, TDD red-green-refactor, review theo task. |
| `BMAD-METHOD` | `tavily_search` (advanced) | https://www.augmentcode.com/guides/bmad-method-ai-development | v6 gồm 12+–19+ vai trò SDLC và story files chống trôi ngữ cảnh. |
| `BMAD` Scale-Adaptive | `tavily_search` (advanced) | https://diegorodrigo.dev/en/2026/04/06/bmad-in-practice-the-complete-ai-agent-development-workflow | Tách rõ `Full Method` nhiều agent với `Quick Flow` một Solo Dev. |
| `OpenHands / SWE-agent / Aider` | `tavily_search` (advanced) | https://www.llms.blog/posts/autonomous-coding-agent-harnesses-in-production-comparing-openhands-swe-agent-aider-and-cline | Event stream append-only, CodeAct, Docker sandbox, Tree-sitter repo map, JSON trace. |
| `Roo Code / Cline` | `tavily_search` (advanced) | https://openweightthoughts.com/top-open-source-ai-coding-agents-2026-openhands-aider-cline-roo-code-swe-agent-p | Chế độ tách biệt, ước lượng chi phí, ngưỡng dừng auto-approve. |
| Anthropic Effective Agents | `search_web` failover | https://www.anthropic.com/research/building-effective-agents | Bắt đầu từ single-agent kèm eval; chỉ mở multi-agent khi tách ngữ cảnh rõ. |
| Cognition Multi-Agents | `search_web` failover | https://cognition.com/blog/dont-build-multi-agents | Chia nhỏ thiếu phối hợp làm vỡ context window và nhân lỗi dây chuyền. |
| MAST Failure Taxonomy | `tavily_search` (advanced) | https://www.alphaxiv.org/abs/2503.13657 | 1.642 trace, 14 lỗi gồm Specification 41,8%, Misalignment 36,9%, Verification 21,3%. |
| Thực hành & Observability | `tavily_search` (advanced) | https://www.splunk.com/en_us/blog/artificial-intelligence/multi-agent-system-failures.html | Lỗi thiếu trace phân tán; mỗi bước handoff tốn thêm 100–500 ms. |

## 2. Mẫu thiết kế nổi bật từ các dự án lớn

### 2.1. Anthropic Claude Code Subagents & Agent Teams

- **Cắt quyền tối thiểu bằng `disallowedTools`:** Subagent mặc định kế thừa công cụ từ phiên chính. Khai báo `disallowedTools` trong YAML frontmatter loại bỏ shell nguy hiểm hoặc quyền ghi dư thừa.
- **Cô lập ghi tệp bằng `isolation: worktree`:** Mỗi subagent chạy trên checkout và nhánh Git tạm thời tách biệt. Hệ thống tệp chặn ghi ngược ngoài phạm vi khi chạy song song.
- **Phân tách mô hình Subagents vs Agent Teams:** Subagent truyền thống đi theo cây phân cấp và chỉ trả tóm tắt lên cha. Agent Teams dùng task list chung để peer trao đổi trực tiếp.
- **Khớp cấu hình `effort` và `model`:** Tài liệu nội bộ `subagent-tuning.md` ghi nhận plugin subagent bỏ qua `permissionMode`, `mcpServers`, `hooks` ở frontmatter. Riêng `effort` cố định theo vai trò còn `model` chỉnh theo lệnh gọi.

### 2.2. `obra/superpowers`

- **Quy trình bắt buộc theo kỹ năng ghép nối:** Không chạy một prompt tự do. Bộ skill tự kích hoạt theo pha gồm brainstorming, viết spec, TDD red-green-refactor và debug 4 pha.
- **Phát triển hướng subagent kèm review tích hợp:** Tác vụ lớn được băm thành task cô lập cho subagent xử lý. Mỗi task hoàn tất đều đi qua bước code review gắn sẵn.

### 2.3. `bmad-code-org/BMAD-METHOD` (v6)

- **Định tuyến thích ứng quy mô (Scale-Adaptive):** Phân loại sớm thay đổi lớn (`Full Method`) và thay đổi nhỏ (`Quick Flow`). Nhánh nhỏ để một Solo Dev xử lý trọn vòng, tránh cồng kềnh.
- **Chống trôi ngữ cảnh qua tài liệu sống:** Các quyết định kiến trúc và ràng buộc được đóng gói vào PRD, architecture doc và story file. Vai trò sau đọc file chuẩn thay vì đoán từ chat cũ.
- **Đăng ký workflow động (`BMad Builder`):** Module mới tự đăng ký quan hệ thứ tự vào hệ thống help. Agent biết rõ bước kế tiếp trong chuỗi 50+ workflow.

### 2.4. `OpenHands`, `SWE-agent`, `Aider`, `Cline` và `Roo Code`

- **Event Stream & CodeAct (`OpenHands 1.5`):** Mọi hành động và quan sát đi qua luồng sự kiện append-only dưới bộ điều phối trung tâm. Agent thực thi trong container/VM cô lập thay vì máy host.
- **Reproducible Trace & ACI (`SWE-agent 1.2`):** Thiết kế giao diện Agent-Computer Interface gọn cho LLM. Hệ thống xuất JSON trace tái lập được để chấm eval và soi hồi quy.
- **Bản đồ mã nguồn & Commit nguyên tử (`Aider 0.78`):** Dùng Tree-sitter lập bản đồ cấu trúc kho mã giúp tiết kiệm token. Mọi sửa đổi gắn kèm commit Git nguyên tử dễ hoàn tác.
- **Chốt chặn chi phí & Chế độ quyền (`Roo Code` / `Cline`):** Tách rõ mode `Plan`/`Act` hoặc `Code`/`Architect`/`Ask`/`Debug`. Đặt ngưỡng tối đa lượt auto-approve trước khi buộc dừng hỏi người dùng.

## 3. Phân loại lỗi Multi-Agent & Nguyên tắc phòng tránh

Nghiên cứu MAST (Cemri et al., UC Berkeley, arXiv:2503.13657) phân tích 1.642 execution trace trên 7 framework và chỉ ra 14 dạng lỗi thuộc 3 nhóm chính:

| Nhóm lỗi MAST | Tỷ lệ | Dạng lỗi nổi bật đo được | Biện pháp phòng tránh thực chứng |
|---|---|---|---|
| Specification & Design | 41,77% | Lặp bước `FM-1.3` (17,14%); lệch suy luận-hành động (13,98%); ngại hỏi làm rõ (11,65%). | Viết spec đo lường được; quy định điều kiện dừng tường minh; chặn vòng lặp vô hạn. |
| Inter-Agent Misalignment | 36,94% | Rơi ngữ cảnh khi handoff; xung đột đầu ra; sai lệch định dạng trao đổi. | Dùng gói handoff có schema cứng; truyền story/context file thay tóm tắt mơ hồ. |
| Task Verification Failures | 21,30% | Dừng non `FM-3.1` (6,2%); bỏ kiểm tra (8,2%); kiểm tra sai vẫn duyệt (9,1%). | Kiểm chứng đa tầng gồm unit, tích hợp và đối chiếu lại yêu cầu gốc. |

Bốn nguyên tắc phòng tránh bổ sung từ Anthropic, Cognition và thực tế vận hành (`agentswarms.fyi`, `splunk.com`, `r/AI_Agents`):

1. **Chống lỗi "đã làm nhưng chưa ghi nhận" (Real-but-unrecorded done):** Subagent chạy xong nhưng không cập nhật trạng thái chung khiến planner sau lập lại việc cũ. Handoff chỉ hợp lệ khi đồng bộ state đích.
2. **Chống suy giảm độ tin cậy theo chuỗi:** Một chuỗi 20 bước với độ tin cậy 95% mỗi bước chỉ thành công khoảng 36%. Phải giữ chuỗi ngắn và thêm cổng kiểm tra trung gian.
3. **Ưu tiên Single-Agent + Context Engineering trước Swarm:** Cognition cảnh báo tách nhiều agent rời rạc làm đứt mạch ngữ cảnh và khó debug. Anthropic khuyến nghị chỉ dùng multi-agent khi cần cô lập ngữ cảnh thật sự.
4. **Observability & Ngân sách độ trễ:** Mỗi bước handoff tốn 100–500 ms. Cần trace chuẩn hóa và đo eval so sánh đối chứng trước khi giữ một route mới.

## 4. Ánh xạ gợi ý nâng cấp cho 6 agent TDQ Workflow

Đối chiếu trực tiếp từ 6 tệp `plugins/tdq-workflow-agy/agents/tdq-*.md` và `subagent-tuning.md`:

### 4.1. `tdq-implementer` (hiện dùng `model: flash`, 5 tools gồm `edit_file`, `write_file`)

- **Nâng cấp mô hình mặc định:** `subagent-tuning.md` yêu cầu `inherit` với effort `high` nhưng tệp agent đang đặt `model: flash`. Cần trả về `inherit` hoặc nâng tier cho task sửa logic phức tạp.
- **Siết biên công cụ & worktree:** Bổ sung `disallowedTools` tường minh và kiểm chứng cứng vùng `VÙNG FILE` trước ghi. Không chỉ dựa vào nhắc nhở bằng văn bản.
- **Đồng bộ hoàn tất & Review tích hợp:** Gắn bước đối chiếu trạng thái `tdq_team.py` chống lỗi real-but-unrecorded done. Áp dụng mẫu `obra/superpowers` tự kiểm unit và self-review trước khi trả `MERGE-READY: yes`.

### 4.2. `tdq-build-resolver` (hiện dùng `model: flash`, có `write_file` và `run_command`)

- **Thu hẹp quyền ghi & ngưỡng tự dừng:** Agent chỉ sửa tối đa dưới 5 dòng nhưng lại mang cả `write_file`. Nên bỏ `write_file` và thêm ngưỡng dừng theo bước kiểu Roo Code.
- **Chuẩn hóa trace khi `blocked`:** Bổ sung trích đoạn chẩn đoán tái lập được kiểu `SWE-agent` khi gặp lỗi kiến trúc sâu. Điều này giúp agent cha tránh lặp lại vòng sửa vô ích `FM-1.3`.

### 4.3. `tdq-qc-tester` (hiện dùng `model: inherit`, 3 tools read-only + `run_command`)

- **Kiểm chứng đa tầng chống duyệt nhầm (9,1% MAST):** Chuyển từ soát bảng DoD đơn tuyến sang 3 tầng: unit test, tích hợp liên module và đối chiếu ngược yêu cầu gốc trong spec.
- **Xuất trace kiểm chứng tái lập:** Mọi lần chạy failed hoặc edge case cần lưu log/JSON trace vào `docs/tdq/qc/<slug>.md`. Giảm rủi ro `FM-3.1` báo `PASS` non khi chưa chạy đủ biên lỗi.

### 4.4. `tdq-refactor-cleaner` (hiện dùng `model: inherit`, 5 tools gồm `edit_file`, `write_file`)

- **Tăng cường phân tích cấu trúc & commit nguyên tử:** Kết hợp kiểm tra `find_references` với bản đồ phụ thuộc AST/Tree-sitter kiểu Aider trước khi xóa symbol. Mỗi cụm xóa nên đi kèm bước regression riêng.
- **Cắt quyền tạo file mới:** Dọn dead code hiếm khi cần `write_file`. Thu hẹp quyền hoặc đặt giới hạn số file chạm giúp tránh tác dụng phụ ngoài phạm vi.

### 4.5. `tdq-reviewer` (hiện dùng `model: inherit`, có `read_file`, `run_command`)

- **Giảm bề mặt lệnh shell:** Tệp agent ghi chỉ đọc nhưng vẫn cấp `run_command` và phụ thuộc hook `bash_gate.py`. Nên thay bằng công cụ đọc/LSP thuần hoặc khai báo `disallowedTools` rõ ràng.
- **Chặn lỗi spec 41,8% ngay từ cổng duyệt:** Áp dụng bộ kiểm định tính hoàn chỉnh theo chuẩn BMAD gồm điều kiện dừng, ngưỡng đo lường và ngữ cảnh đầu vào của từng task.

### 4.6. `tdq-security-reviewer` (hiện dùng `model: pro`, có `read_file`, `run_command`)

- **Siết đặc quyền kiểm toán viên (Least Privilege):** Auditor chỉ đọc không nên giữ `run_command` không giới hạn. Hãy tách riêng scanner read-only hoặc danh sách lệnh cho phép cố định.
- **Schema handoff & Truy vết kiểm toán:** Chuẩn hóa payload JSON/Markdown chặt chẽ khi trả `BLOCKED` hoặc `CLEAN`. Kết hợp log trace có timestamp để chứng minh phạm vi tệp đã kiểm toán thực tế.

### 4.7. Nâng cấp chung cấp điều phối hệ thống

- **Định tuyến thích ứng & Eval đối chứng:** Giữ tách biệt rạch ròi `quick` vs `full` như BMAD. Mọi nâng cấp prompt hoặc route agent phải đo qua bộ eval tái lập trace kiểu `SWE-agent` trước khi giữ lại.
- **Bảng trạng thái & Trace thống nhất:** Đồng bộ kết quả của cả 6 agent vào một event stream / state chuẩn hóa của `tdq_team.py`. Loại bỏ hoàn toàn tình trạng rơi ngữ cảnh ở bước handoff.
