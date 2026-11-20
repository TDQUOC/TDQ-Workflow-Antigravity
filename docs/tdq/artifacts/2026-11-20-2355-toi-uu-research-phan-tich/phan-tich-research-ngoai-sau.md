# Nghiên cứu Chuyên sâu Bên ngoài — Bộ nhớ Bền qua `/compact`, Điểm hòa vốn Multi-Agent & Xác minh Hai luồng Tiết kiệm Chi phí (T1.3)

Request: `2026-11-20-2355-toi-uu-research-phan-tich`  
Soul: chất lượng > runtime > context cost · luật gốc: `skills/tdq-conventions/references/soul.md`

> Tài liệu này mở rộng **vượt ra ngoài** báo cáo nền `docs/tdq/research/2026-11-20-2355-toi-uu-research-phan-tich.md` trên 3 khoảng trống mở: (1) kiến trúc bộ nhớ & checkpointing sống sót qua nhiều lần `/compact` liên tiếp, (2) ngưỡng định lượng hòa vốn fan-out đa tác tử & cơ chế dừng sớm chống vòng lặp tốn tiền, và (3) triển khai thực dụng Dual-Track Verification (FActScore / ALCE F6 / Counterfactual RCA) trong công cụ lập trình mà không nhân đôi chi phí. Mọi luận điểm và số liệu dưới đây đều gắn trực tiếp với các URL đã trích xuất và đọc trong phiên T1.3.

---

## 1. Nhật ký Truy vấn & Kiểm chứng Nguồn

### 1.1. Truy vấn tìm kiếm đã chạy

1. **MCP `tdq-workflow-agy_tavily-primary:tavily_search`** (`search_depth="advanced"`, `max_results=8`):
   - **Query 1 (Thành công):** `Manus "Context Engineering for AI Agents" filesystem KV-cache append-only compaction`
   - **Query 2 (Thành công):** `Anthropic multi-agent research system diminishing returns stopping criteria subagent effort scaling budget`
   - **Query 3–6 (Đụng giới hạn daily keyless Tavily — `Retry after: 1599s–1615s`, chuyển fallback sang `search_web` theo quy trình):**
     - `Anthropic "effective harnesses for long-running agents" context compaction claude-progress.txt`
     - `LangGraph OpenHands Cursor checkpointing context compaction external memory long-running agents`
     - `"Towards a Science of Scaling Agent Systems" Google MIT multi-agent vs single-agent breakeven token latency`
     - `MiniCheck FActScore ALCE citation verification cost reduction lightweight entailment`
2. **Fallback `search_web` (tổng 13 truy vấn bổ sung)** để thay thế 4 query bị rate-limit và xác định exact canonical URLs cho `tavily_extract`:
   - Tìm bài gốc Anthropic harnesses/context engineering, OpenHands Context Condenser (`docs.openhands.dev`, `arXiv:2511.03690`), Cursor (`dynamic-context-discovery`, `self-summarization`), Google/MIT (`arXiv:2512.08296`, `research.google/blog`), `MiniCheck` (`arXiv:2404.10774`), `ALCE` (`arXiv:2305.14627`), Anthropic Cookbooks (`research_lead_agent.md`, `research_subagent.md`, `citations_agent.md`), và Counterfactual RCA (`CausalFlow`, `Causal Agent Replay`).

### 1.2. Danh sách URL đã trích xuất trực tiếp (`tavily_extract`) & Sàng lọc

- **Chủ đề 1 — Compact-Resilient Agent Memory & Checkpointing (12 nguồn sơ cấp):**
  1. `https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents`
  2. `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents`
  3. `https://www.anthropic.com/news/context-management`
  4. `https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus`
  5. `https://rlancemartin.github.io/2025/10/15/manus`
  6. `https://www.zenml.io/llmops-database/context-engineering-for-production-ai-agents-at-scale`
  7. `https://cursor.com/blog/dynamic-context-discovery`
  8. `https://cursor.com/blog/self-summarization`
  9. `https://www.openhands.dev/blog/openhands-context-condensensation-for-more-efficient-ai-agents`
  10. `https://docs.openhands.dev/sdk/guides/context-condenser`
  11. `https://arxiv.org/abs/2511.03690` (`https://arxiv.org/html/2511.03690v2`)
  12. `https://langchain-ai.github.io/langgraph/concepts/persistence/`
- **Chủ đề 2 — Effort Scaling, Breakeven & Early-Stopping Budgets (7 nguồn sơ cấp):**
  13. `https://www.anthropic.com/research/multi-agent-research-system`
  14. `https://raw.githubusercontent.com/anthropics/claude-cookbooks/main/patterns/agents/prompts/research_lead_agent.md`
  15. `https://raw.githubusercontent.com/anthropics/claude-cookbooks/main/patterns/agents/prompts/research_subagent.md`
  16. `https://fountaincity.tech/resources/blog/anthropic-multi-agent-blueprint-production`
  17. `https://arxiv.org/abs/2512.08296` (`https://arxiv.org/html/2512.08296v3`)
  18. `https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/`
  19. `https://docs.openhands.dev/sdk/guides/metrics`
- **Chủ đề 3 — Cost-Effective Dual-Track Verification & Counterfactual RCA (10 nguồn sơ cấp):**
  20. `https://hidekazu-konishi.com/entry/llm_output_verification_patterns.html`
  21. `https://platform.claude.com/docs/en/build-with-claude/citations`
  22. `https://raw.githubusercontent.com/anthropics/claude-cookbooks/main/patterns/agents/prompts/citations_agent.md`
  23. `https://arxiv.org/abs/2305.14251` (FActScore)
  24. `https://arxiv.org/abs/2305.14627` (ALCE)
  25. `https://arxiv.org/abs/2404.10774` (`https://arxiv.org/html/2404.10774v2` — MiniCheck)
  26. `https://www.bespokelabs.ai/blog/hallucinations-fact-checking-entailment-and-all-that-what-does-it-all-mean`
  27. `https://huggingface.co/bespokelabs/Bespoke-MiniCheck-7B`
  28. `https://arxiv.org/abs/2605.25338` (CausalFlow)
  29. `https://arxiv.org/abs/2606.08275` (`https://arxiv.org/html/2606.08275v1` — Causal Agent Replay / CAR)

> **Kiểm soát chất lượng nguồn (tự chặn F6):** Hai URL do `search_web` gợi ý là `https://arxiv.org/abs/2510.05321` (thực chất là bài toán Vehicle Routing LP Rounding, không phải VeriCite) và `https://blog.langchain.com/context-management-for-deep-agents/` (trả HTTP 404) đã bị **loại bỏ** sau khi kiểm bằng `tavily_extract`.

---

## 2. Chủ đề 1 — Compact-Resilient Agent Memory & Checkpointing qua nhiều lần `/compact`

Báo cáo nền đã nêu ý tưởng lưu `plan` và `evidence` ra đĩa. Tuy nhiên, bài toán khó thực sự ở production là: **khi một phiên chạy qua 2–3 lần `/compact` hoặc reset context liên tiếp, làm sao bảo toàn 100% provenance (mọi nguồn, lỗi đã thử, giả thuyết đã loại) mà không biến post-compact prompt anchor thành một khối phình to làm cạn attention budget hoặc phá KV-cache?**

### 2.1. Tổng hợp cơ chế từ 5 hệ thống sản xuất

1. **Anthropic Long-Running Harness (`effective-harnesses-for-long-running-agents`, `effective-context-engineering-for-ai-agents`, `news/context-management`)**
   - **Tách `Initializer` khỏi `Incremental Agent` & JSON hoá tiến độ:** Dùng 2 artifact cốt lõi ngoài chat: `claude-progress.txt` (log append những gì vừa xong, lỗi gặp phải, bước tiếp theo) và `feature_list.json` (từng item gắn cờ `"passes": false/true`). Anthropic chọn **JSON thay vì Markdown** cho danh sách tính năng vì model ít có xu hướng ghi đè hoặc sửa bậy cấu trúc JSON so với Markdown.
   - **Nghi thức khởi động sau reset/compact (Boot Ritual):** Mọi phiên mới đều chạy chuỗi tối thiểu: `pwd` → đọc `git log` + `claude-progress.txt` → đọc `feature_list.json` chọn đúng 1 mục tiếp theo → chạy smoke test qua `init.sh` trước khi đụng code mới (tránh cộng dồn lỗi trên nền trạng thái hỏng ngầm).
   - **Compaction 2 tầng trên Claude Developer Platform:**
     - *Tầng nhẹ (Reversible-like Context Editing):* tự động xoá tool calls/results cũ đã dùng xong mà giữ nguyên luồng hội thoại. Trên benchmark tìm kiếm 100 lượt, context editing giảm **84% lượng token tiêu thụ**; kết hợp thêm client-side file-based **Memory tool** nâng hiệu năng tác vụ agentic search **+39%** so với baseline (riêng context editing đóng góp **+29%**).
     - *Tầng nặng (Summarization + Top-5 Files):* nén lịch sử bằng tóm tắt giữ lại quyết định kiến trúc, bug chưa giải quyết và chi tiết triển khai, cộng thêm **5 file truy cập gần nhất** + truy xuất "just-in-time" qua pointer (đường dẫn file, query đã lưu, URL).

2. **Manus Context Engineering (`manus.im/blog/...`, `rlancemartin.github.io/2025/10/15/manus`, `zenml.io/...`)**
   - **Kinh tế KV-Cache quyết định cấu trúc bộ nhớ:** Tỷ lệ token đầu vào/đầu ra ở agent là **~100:1**; trên Claude Sonnet, token hit KV-cache có giá **0.30 USD/MTok** so với **3.00 USD/MTok** không hit (**chênh 10x**). Vì vậy context phải **append-only**, serialize JSON xác định (key order cố định), không đặt timestamp tới giây ở prefix hệ thống, và dùng **logit masking theo FSM** (theo prefix tên tool như `browser_`, `shell_`) thay vì thêm/xoá định nghĩa tool động giữa chừng.
   - **Phân biệt rạch ròi Compaction (khả nghịch) vs Summarization (bất khả nghịch):**
     - *Dual representation:* Mọi tool call/observation có bản `full` (ghi xuống filesystem sandbox) và bản `compact` (chỉ giữ pointer: path file, URL, hoặc query).
     - *3 ngưỡng giám sát:* Hard limit (vd. 1M) → Pre-rot threshold (**128K–200K**, nơi độ chính xác suy giảm) → Compaction trigger. Khi chạm trigger, Manus chỉ **compact 50% tool calls cũ nhất**, giữ nguyên các tool calls gần nhất ở dạng đầy đủ để duy trì few-shot hành vi chuẩn.
     - *Summarization theo schema chỉ chạy khi compaction hết dư địa:* Trước khi tóm tắt, dump toàn bộ raw trajectory log thành file trên đĩa để sau này vẫn `grep` lại được; bản tóm tắt bắt buộc điền theo **schema cố định** (`files modified`, `user goals`, `current state`) và vẫn giữ nguyên vài tool calls cuối cùng.
   - **Bài học xương máu về `todo.md` & Error Retention:**
     - Manus từng dùng `todo.md` để "recite" mục tiêu vào cuối context chống *lost-in-the-middle*, nhưng đo được **~1/3 tổng số hành động** bị lãng phí chỉ để cập nhật file todo → chuyển sang tách Planner + Executor subagents với output schema ràng buộc (`submit results`).
     - **"Keep the wrong stuff in":** Giữ lại các tool call lỗi và stack trace trong context (thay vì xoá sạch dấu vết khi retry) giúp model cập nhật prior để không lặp lại đúng đường cụt.

3. **Cursor (`dynamic-context-discovery`, `self-summarization`)**
   - **Đưa Chat History thành file truy vấn được hậu compaction (`dynamic-context-discovery`):** Sau khi context đạt ngưỡng hoặc user tóm tắt thủ công, Cursor cấp cho agent **tham chiếu tới file chat history thô** thay vì coi summary là duy nhất — nếu summary làm rụng chi tiết, agent tự `grep`/`tail` lại đúng đoạn hội thoại cũ.
   - **Sync MCP & Terminal thành file:** Đồng bộ mô tả MCP tool vào từng thư mục theo server (chỉ đưa tên tool vào static prompt) giúp **giảm 46.9% tổng token của agent** trong các phiên gọi MCP (A/B test có ý nghĩa thống kê). Long shell/MCP outputs ghi ra file cho agent `tail`/`rg` thay vì truncate mù gây mất dữ liệu.
   - **Self-Summarization bằng RL (`self-summarization`):** Thay vì prompt tóm tắt dài hàng nghìn token sinh ra bản tóm tắt >5,000 tokens, Cursor huấn luyện Composer tự tóm tắt theo trigger cố định (thử nghiệm ở **40k** và **80k** tokens) xuống còn **~1,000 tokens** theo khung 5 phần (`User goal`, `What was implemented`, `Errors / fixes`, `What's still broken / to do`, `Paths`). Kết quả trên CursorBench: **giảm 50% lỗi do compaction** trong khi dùng **1/5 số token** và tái sử dụng KV-cache.

4. **OpenHands SDK (`openhands-context-condensensation`, `docs.openhands.dev/.../context-condenser`, `arXiv:2511.03690v2`)**
   - **Immutable Append-Only Event Sourcing + Stateless `CondensationEvent`:** Toàn bộ lịch sử gốc (`MessageEvent`, `ActionEvent`, `ObservationEvent`, `AgentErrorEvent`) được ghi bất biến xuống `LocalFileStore`. Khi context vượt ngưỡng (`max_size`), `LLMSummarizingCondenser` **không sửa lịch sử cũ** mà append thêm một `CondensationEvent` (`CondensationSummaryEvent`) đánh dấu danh sách event ID được thay thế. Trước mỗi lượt gọi LLM, tầng projection dựng view gồm: `keep_first` events đầu (system prompt + yêu cầu gốc) + summary + các event gần nhất.
   - **Amortized Prompt Caching:** Chỉ kích hoạt condensation theo chu kỳ khi vượt ngưỡng giúp dồn chi phí xây lại prefix KV-cache trên nhiều lượt, biến chi phí mỗi lượt từ **bình phương ($O(T^2)$) xuống tuyến tính ($O(T)$)**: đạt tới **2x giảm API cost mỗi lượt**, giữ tốc độ phản hồi ổn định và tỷ lệ giải SWE-bench Verified nhỉnh hơn (**54% vs 53%** baseline).
   - **Chi phí I/O gần như bằng 0:** Đo trên **433 hội thoại SWE-Bench Verified (39,870 events)** qua `LocalFileStore`, storage tăng tuyến tính và **crash recovery hoàn tất dưới 20 ms** ngay cả với phiên dài nhất (358 events); kiến trúc V1 event-sourced giảm **61% lỗi hệ thống (system-attributable failures)** so với V0.

5. **LangGraph Persistence (`langchain-ai.github.io/langgraph/concepts/persistence/`)**
   - Tách **Checkpointer** (state graph theo `thread_id`, snapshot sau mỗi superstep bằng `SqliteSaver`/`PostgresSaver` cho fault tolerance, time-travel, HITL interrupt) khỏi **Store** (key-value liên-thread cho tri thức bền vững).
   - Cảnh báo 2 lỗi vận hành thực tế: (a) **Checkpoints phình vô hạn** nếu không có chính sách dọn/prune theo retention; (b) **Subgraph namespace isolation** khiến parent graph không tự thấy state cập nhật bên trong subgraph trừ khi ghi qua `Store` hoặc propagate checkpoint lên parent.

### 2.2. Bảng đối chiếu cơ chế sống sót qua 2–3 lần `/compact`

| Hệ thống | Nguồn chân lý ngoài chat (External State) | Cơ chế chống mất chi tiết qua 2–3x `/compact` | Bảo vệ KV-Cache & Giữ Anchor gọn | Rủi ro còn tồn tại |
|---|---|---|---|---|
| **Anthropic Harness** | `claude-progress.txt`, `feature_list.json`, `git log`, Memory tool | Không dồn hết vào chat; phiên mới đọc lại JSON/progress + 5 file gần nhất | Context editing dọn stale tool results trước khi buộc summarize (**-84% tokens**) | `feature_list.json` quá dài hoặc không test e2e bằng tool vẫn báo sai |
| **Manus** | Sandbox filesystem (`full` tool output + pre-summary trajectory log) | Reversible compaction (giữ path/URL/query); schema-based summary + `grep` raw log | Append-only, deterministic JSON, không đổi tool list động (**10x** cache savings) | Cập nhật `todo.md` thủ công ngốn ~1/3 action nếu không tách planner |
| **Cursor** | Chat history log files, terminal session files, MCP tool folders | Trả pointer tới **file chat history thô** sau tóm tắt để agent tự `rg` lại | Sync MCP vào folder (**-46.9% tokens**); Composer self-summary gọn ~1,000 tokens (**-50% lỗi**) | Summarization prompt thủ công nặng (>5,000 tokens) dễ làm mất tín hiệu nếu không có raw pointer |
| **OpenHands SDK** | `LocalFileStore` event log bất biến + `CondensationEvent` | Raw events không bao giờ bị xoá; `keep_first` ghim mục tiêu gốc vĩnh viễn | Amortized condensation theo batch giữ prefix cache, recovery **<20 ms** (358 events) | Cần theo dõi chi phí LLM phụ (`usage_id="condenser"`) trong budget chung |
| **LangGraph** | `SqliteSaver`/`PostgresSaver` Checkpointer + `Store` | Replay/time-travel theo checkpoint `thread_id`; tri thức xuyên thread ở `Store` | Tách short-term thread state khỏi cross-thread `Store` | Checkpoint DB phình to nếu thiếu retention; subgraph tách namespace |

### 2.3. Áp dụng trực tiếp cho TDQ Workflow

- **Hiện trạng đã có trong repo:** `session_start.py` (root `L349-410`; plugin `L358-410`) đã có `[TDQ:ANCHOR]` khi `source in ("compact", "resume")` kèm giới hạn head cap `12 dòng / 600 chars` (`render_next(..., compact=True)`), và `tdq_ccr.py` đã hỗ trợ offload payload `> 32 KB` (`CCR_MIN_BYTES = 32768`). Tuy nhiên `phan-tich-kien-truc-codebase.md` chỉ ra 2 lỗ hổng:
  1. `pre_invocation.rs:157` ở Rust hot-path chỉ check `source == "compact"` mà bỏ qua `source == "resume"`.
  2. `read_gate.py` (`docs/tdq/.tdq-read.jsonl`) bị `pre_tool_use.rs:444-463` bypass mỗi khi gọi `read_file` có `StartLine/EndLine`, nên không đếm được tích luỹ context/tokens để nhắc checkpoint, và chưa có **Append-only Evidence Ledger (`evidence.jsonl`)** chuẩn cho các pha điều tra/research.
- **Khuyến nghị thiết kế (không làm phình `[TDQ:ANCHOR]`):**
  1. **Append-only Evidence & Progress Ledger ngoài chat (`docs/tdq/artifacts/<slug>/evidence.jsonl` hoặc `.tdq-runtime/evidence/<slug>.jsonl`):** Mỗi bằng chứng (`EV-001`, `EV-002`...) chỉ ghi một dòng JSONL bất biến (kiểu OpenHands Event Sourcing + Manus dual representation: `id`, `source_ref` như `URL` hoặc `file:line`, `ccr_or_raw_path`, `claim_excerpt`, `status`, `turn_ts`). Không bao giờ sửa dòng cũ — muốn bác bỏ hoặc đính chính chỉ append event mới (`"status": "refuted"`).
  2. **Giữ `[TDQ:ANCHOR]` dưới ngưỡng `<= 600 chars` bằng Pointer-Only Index:** Thay vì nhồi nội dung bằng chứng vào `[TDQ:ANCHOR]` sau mỗi `/compact`, chỉ ghim **3 con trỏ + 2 bộ đếm**: `ledger=docs/tdq/artifacts/<slug>/evidence.jsonl`, `latest_ev=EV-014 (verified=10, contested=2, failed_hypotheses=2)`, `raw_transcript=<path>` (mô hình Cursor history-as-file). Khi sống sót qua 2–3 lần `/compact`, model luôn biết nơi `grep` toàn bộ provenance thô với chi phí anchor ~2–3 dòng!
  3. **Mẹo JSON cho bảng checklist/hypotheses:** Học Anthropic (`feature_list.json`), mọi bảng trạng thái giả thuyết/nhiệm vụ đòi hỏi cập nhật trạng thái (`pending`/`verified`/`refuted`) qua nhiều lần compact nên có bản máy đọc JSON/JSONL đi kèm hoặc trường trạng thái rõ ràng để chống model vô tình xoá/sửa nhầm dòng Markdown khi tóm tắt lại.

---

## 3. Chủ đề 2 — Adaptive Effort Scaling, Điểm hòa vốn Multi-Agent Fan-Out & Ngân sách Dừng Sớm

Báo cáo nền đã ghi nhận con số từ Anthropic (+90.2% hiệu năng với chi phí ~15x token) và quy tắc 1 / 2–4 / 10+ subagents. Nghiên cứu sâu ở T1.3 bổ sung **bằng chứng định lượng đối chứng từ Google Research / DeepMind / MIT (`arXiv:2512.08296v3`)** cùng **prompt thực chiến trong `anthropics/claude-cookbooks`** để trả lời câu hỏi sống còn: **chính xác khi nào fan-out có lời, khi nào lỗ nặng cả tiền lẫn độ chính xác, và làm sao chặn runaway loop?**

### 3.1. Bằng chứng định lượng về điểm hòa vốn & nghịch lý "More Agents" (`arXiv:2512.08296v3`)

Nhóm Google Research, Google DeepMind và MIT đánh giá có kiểm soát **260 cấu hình** (bản mở rộng từ 180 cấu hình trên blog Google Research), chuẩn hoá tool/prompt/ngân sách tính toán qua **6 benchmarks** (*Finance-Agent*, *BrowseComp-Plus*, *PlanCraft*, *Workbench*, *SWE-bench Verified*, *Terminal-Bench*), **3 họ model** (OpenAI GPT, Google Gemini, Anthropic Claude) và **5 kiến trúc chuẩn**:

| Chỉ số thực nghiệm (`arXiv:2512.08296v3`) | Single-Agent (SAS) | Independent | Decentralized | Centralized | Hybrid |
|---|---:|---:|---:|---:|---:|
| **Success Rate trung bình** | 0.466 | 0.370 | 0.477 | 0.463 | 0.452 |
| **Số lượt trung bình (Turns)** | 7.2 (±2.1) | 11.4 (±3.2) | 26.1 (±7.5) | 27.7 (±8.1) | 44.3 (±12.4) |
| **Coordination Overhead (%)** | **0%** | 58% | 263% | 285% | **515%** |
| **Message Density** | 0.00 | 0.00 | 0.41 | 0.39 | 0.24 |
| **Redundancy (trùng lặp)** | 0.00 | 0.48 (±0.09) | 0.50 (±0.06) | 0.41 (±0.06) | 0.46 (±0.04) |
| **Efficiency (Success / Overhead)** | **0.466** | 0.234 | 0.132 | 0.120 | 0.074 |
| **Error Amplification (khuếch đại lỗi)** | **1.0x** | **17.2x** | 7.8x | **4.4x** | 5.1x |
| **Success / 1,000 tokens** | **67.7** | 42.4 | 23.9 | 21.5 | **13.6** |

Từ bảng số liệu trên, 4 ngưỡng ra quyết định cốt lõi rút ra cho mọi hệ thống agentic:

1. **Ngưỡng bão hoà năng lực (Capability Saturation Ceiling — `45%`):**
   - Mô hình hồi quy mixed-effects chứng minh hiệu ứng bão hoà năng lực (xác nhận dưới cả cluster-robust inference lẫn hiệu chỉnh Holm–Bonferroni): **khi Single-Agent baseline đã đạt trên ~45% accuracy, việc thêm phối hợp đa tác tử cho lợi suất giảm dần hoặc âm.**
   - Minh chứng trực tiếp trên **SWE-bench Verified** (tác vụ coding thực tế): Single-Agent đạt trung bình **0.522** (vượt 45%), dẫn tới **TẤT CẢ các biến thể Multi-Agent đều thua Single-Agent**: Hybrid **0.511**, Centralized **0.506**, Decentralized **0.494**, Independent **0.444**. Lý do: phần lớn lỗi là phối hợp chia sẻ ngữ cảnh và đồng bộ state làm phân mảnh ngân sách token lý luận.
2. **Độ dốc theo cấu trúc tác vụ (`+80.8%` vs `-70.0%`):**
   - **Tác vụ phân rã song song thật sự** (*Finance-Agent* — tách độc lập doanh thu, cấu trúc chi phí, đối thủ): Centralized tăng tới **+80.8%** (+80.9% trong bản blog 180 cấu hình) so với Single-Agent.
   - **Tác vụ lập kế hoạch tuần tự ràng buộc chặt** (*PlanCraft*): Mọi kiến trúc Multi-Agent đều **tụt từ −39% đến −70%** vì giao tiếp giữa agent ăn hết token budget lý luận mà không song song hoá được bước phụ thuộc.
   - Mô hình dự báo của nhóm Google/MIT (cross-validated $R^2 = 0.513$ ở bộ 180 cấu hình; $R^2 = 0.373$–$0.413$ trên toàn bộ 6 benchmark) chọn đúng kiến trúc tối ưu cho **87%** cấu hình chưa thấy dựa trên mật độ tool và mức độ phân rã.
3. **Thuế phối hợp Tool (`Tool-Coordination Trade-Off`):**
   - Trên môi trường nhiều tool (vd. *Workbench* với **16+ tools**), việc chia nhỏ tác vụ khiến mỗi subagent tiêu tốn tỷ lệ lớn token cho lời gọi giao tiếp và lặp lại các lệnh tra cứu tool trùng khớp (**41%–50% redundancy** across MAS!). Trong khi đó trên *Terminal-Bench* (chỉ 2 tools, SAS mean `0.344 < 45%`), Centralized cũng tụt xuống `0.278` do chi phí điều phối nặng hơn lợi ích chia nhánh.
4. **Khuếch đại lỗi theo Topology (`17.2x` vs `4.4x`):**
   - **Independent MAS** (chạy song song không có khâu tổng hợp/kiểm định trung tâm) khuếch đại lỗi trace-level tới **17.2x**.
   - **Centralized MAS** (hub-and-spoke có orchestrator đóng vai "nút cổ chai kiểm chứng") nén mức khuếch đại lỗi xuống **4.4x** — nhưng cái giá là **285% overhead** và hiệu suất mỗi 1K token tụt **>3x** (`67.7 → 21.5`).

### 3.2. Ngưỡng ngân sách, Early-Stopping & Chống Runaway Loop (Anthropic Cookbook + OpenHands)

Kiểm trực tiếp prompt nguồn mở của Anthropic (`research_lead_agent.md` & `research_subagent.md`) và thực nghiệm vận hành của Fountain City & OpenHands cho thấy cách chặn đốt token ngoài kiểm soát:

1. **Ma trận Effort Scaling 4 bậc của Anthropic (`research_lead_agent.md` + `research_subagent.md`):**
   - **Bậc 1 — Straightforward:** **1 subagent** (hoặc không fan-out), `< 5` tool calls cho câu hỏi đơn giản (`5` cho vừa).
   - **Bậc 2 — Standard complexity:** **2–3 subagents**, mỗi subagent `5–10` tool calls.
   - **Bậc 3 — Medium complexity (mặc định):** **3–5 subagents** (default `3`), mỗi subagent `~10` tool calls (tránh >10).
   - **Bậc 4 — High complexity:** **5–10 subagents (trần cứng: tối đa 20)**; mỗi subagent tối đa **15** tool calls.
   - **Trần cứng bắt buộc ở Subagent (`research_subagent.md`):** Hệ thống đặt **hard kill tại 20 tool calls và ~100 sources** — prompt nhắc subagent khi chạm **15 tool calls hoặc 100 sources** phải lập tức dừng thu thập và gọi `complete_task`.
2. **Tiêu chí dừng sớm theo Lợi suất Giảm dần (`Decreasing-Returns Early Stopping`):**
   - Cả Lead lẫn Subagent đều mang luật dừng tường minh: *"when you have reached the point where further research has diminishing returns and you can give a good enough answer to the user, STOP FURTHER RESEARCH and do not create any new subagents."*
   - **Chống lặp truy vấn vô ích:** Cấm subagent chạy lại y nguyên query cho cùng tool khi không ra kết quả mới (`research_subagent.md`); ép chuyển góc/query rộng hơn (`< 5 từ`) hoặc dừng báo open gap.
3. **Hard Budget Circuit Breaker cấp phiên (`Fountain City` + `OpenHands Metrics`):**
   - Fountain City chỉ ra điểm mù của bản thiết kế Anthropic: thiếu **per-run cost ceilings**, **circuit breakers** chống subagent đệ quy hoặc tool trả payload quá khổ, và **model pinning** (ghim model nhỏ/rẻ hơn ở tầng worker thay vì chạy frontier model đồng loạt).
   - OpenHands SDK (`docs.openhands.dev/sdk/guides/metrics`) cài `max_budget_per_run` kiểm tra sau **mỗi step** trên **tổng chi phí cộng dồn của MỌI LLM** (gồm cả `usage_id="agent"` và `usage_id="condenser"` qua `ConversationStats`) — vượt trần lập tức dừng bằng `MaxBudgetReached` (`execution_status="error"`).

### 3.3. Áp dụng trực tiếp cho TDQ Workflow

- **Hiện trạng trong repo:** `tdq_team.py` đặt `TRAN_SONG_SONG = 4` (khớp vùng tối ưu 3–5 nhánh của Anthropic) và chỉ dispatch khi không đụng `vung_file` / TCAS collision; `tdq_bench.py` mô phỏng kế hoạch; `AGY invoke_subagent` chọn model `inherit | flash_lite | flash | pro`. Tuy nhiên `phan-tich-kien-truc-codebase.md` phát hiện:
  - `tdq_team._finalize_tasks` không đưa `- Sinh ra: docs/...` vào `vung_file`, làm các task research/artifact bị `quyet_dinh_task` gán nhầm `("tu_lam", "vung-khoa")` và tính tuần tự trong `tdq_bench.py` (`chen`)!
  - Chưa có **Breakeven Gate** kiểm định trước khi fan-out trong `analyze` / `plan` / `qc`, và chưa có **per-subagent tool/turn ceiling + diminishing-returns stop** nhất quán cho các agent điều tra.
- **Khuyến nghị thiết kế cho TDQ Workflow:**
  1. **Quy tắc Fan-Out Breakeven 3 câu hỏi (trước khi sinh >= 2 subagents):** Dựa trên phát hiện `45% saturation` + `285% overhead` + `tool-coordination trade-off` của Google/MIT (`2512.08296v3`) và `15x` token cost của Anthropic:
     - Chỉ fan-out khi **cả 3 điều kiện cùng đúng**: (a) Có `>= 2` nhánh **độc lập không cần trung gian của nhau** (breadth-first hoặc distinct modality), (b) Tổng dung lượng đọc/tìm kiếm vượt ngưỡng làm loãng 1 context window (hoặc cần cross-check độc lập ở QC), và (c) Tác vụ không phải sequential planning / sửa code phụ thuộc chặt trên cùng 1–2 file (vốn là vùng SAS thắng MAS `0.522 vs 0.444–0.511`).
     - Giữ **Centralized Hub-and-Spoke** (1 Leader tổng hợp + kiểm chứng, tối đa `TRAN_SONG_SONG = 4` worker đồng thời) để ghìm hệ số khuếch đại lỗi ở mức `~4.4x` thay vì `17.2x` của Independent mesh; không cho subagent tự đẻ subagent đệ quy tuỳ tiện.
  2. **Định mức Effort Tier & Early-Stop cho Subagents trên AGY (`flash_lite`/`flash`/`pro`/`inherit`):**
     - Gắn rõ 3 tier trong brief giao việc (`Straightforward`: 1 subagent, `<= 5` calls; `Standard`: 2–3 subagents, `<= 10` calls/nhánh; `Deep`: 3–4 subagents wave, `<= 15` calls/nhánh, hard stop khi 2 lượt tìm kiếm liên tiếp không ra fact/source mới = **diminishing returns**).
     - Phân tầng model chủ động: dùng `flash` cho subagent thu thập/quét diện rộng có schema trích xuất chặt (hoặc `browser` vốn đã mặc định `flash`), giữ `inherit`/`pro` cho Lead tổng hợp, `tdq-reviewer` và `tdq-qc-tester` đối chứng phản biện.
  3. **Sửa phân loại artifact task trong `tdq_team.py` / `tdq_bench.py`:** Để `- Sinh ra:` khai báo rõ output file riêng biệt không đè nhau được công nhận là `vung_file` tách biệt (cho phép wave song song như T1.1/T1.2/T1.3 thay vì bị mô phỏng đẩy hết vào `tu_lam` tuần tự).

---

## 4. Chủ đề 3 — Dual-Track Verification Tiết Kiệm Chi Phí (FActScore / ALCE F6 / Counterfactual RCA)

Báo cáo nền đã nêu khái niệm `FActScore`, `ALCE` (Precision vs Recall), lỗi **F6** (link thật nhưng không chứng minh claim), và phản chứng (`Counterfactual`). Vấn đề kỹ thuật cốt lõi ở T1.3 là: **làm sao kiểm chứng từng claim ở cấp độ nguyên tử + chặn F6 + chạy Counterfactual RCA trong developer tooling mà KHÔNG nhân đôi chi phí token & thời gian chạy?**

### 4.1. Kiến trúc 5+1 lớp theo chi phí & Triệt tiêu F6 từ cấu trúc (`hidekazu-konishi.com`, Anthropic Citations, `FActScore`, `ALCE`)

1. **Nguyên lý "Chạy kiểm định rẻ & xác định trước, kiểm định xác suất sau" (`hidekazu-konishi.com`):**
   - Phân loại **6 kiểu lỗi (F1–F6)** vào **5 lớp máy (L1–L5) + Human**. Hai luật kiến trúc bắt buộc:
     - **L5 (Cross-Model Judge) KHÔNG bao hàm L1 (Structural):** Dùng LLM-as-a-judge tốn tiền để bắt lỗi thiếu trường hoặc format sai là phản thiết kế. **L1 decidable** chạy trước 100%, reject ngay ở chi phí ~0 USD để L2–L5 không bao giờ chạy trên output hỏng cấu trúc.
     - **Tách riêng L2 (Grounding — bắt F2 & F6 precision) khỏi L4 (External Tool — bắt F1 & F5):** L2 *không thể phát hiện nguồn bị lỗi thời (F5) hoặc nguồn sai sẵn*; nó chỉ kiểm claim có được chứng minh bởi evidence kèm theo hay không. L4 (chạy compiler, test suite, LSP, `git`, CLI check) mới là lớp xác lập sự thật thực tại cho dev tooling.
     - **Độ mù của L3 Self-Verification & L5 Self-Preference:** `Chain-of-Verification` (`2309.11495`) chỉ hiệu quả khi câu hỏi xác minh được **cách ly hoàn toàn khỏi bản nháp** ("a verification step that can see the draft tends to ratify it"); tự sửa lỗi nội tại không có tín hiệu ngoài (`2310.01798`) có thể làm giảm chất lượng; và model tự chấm bài mình thiên vị rõ rệt (`2404.13076`). Do đó L5 chỉ thực sự đáng tiền khi dùng cho **F4 (Instruction compliance)** hoặc chạy **cross-family model**.
2. **Chặn F6 làm hai nửa: Structural Citation + Invariant Diff + Entailment Check:**
   - **Nửa 1 — Diệt trích dẫn bịa từ cấu trúc (Zero-Token Citation Metadata):** Anthropic Messages API (`platform.claude.com/docs/en/build-with-claude/citations`) khi bật `citations: {enabled: true}` trên `document` blocks trả về location index xác định (`char_location` 0-indexed cho text, `page_location` 1-indexed cho PDF, `content_block_location` cho custom blocks). Điểm tối ưu chi phí cực lớn: trường `cited_text` trả về **không tính vào output tokens** và cũng **không tính vào input tokens ở các lượt hội thoại sau**, đồng thời kết hợp được với `cache_control: ephemeral` trên document block.
     - *Lưu ý xung đột API (`hidekazu-konishi.com` §3.3 & §4.4):* Trên Anthropic API, bật `citations` không dùng chung được với `output_config.format` (JSON Schema enforcement — trả lỗi 400). Ba cách hoá giải thực chiến: (i) 2-pass (viết có citation trước → parse sang JSON sau), (ii) Citations + custom parser dòng `field: value` (chính docs Anthropic khuyên dùng), hoặc (iii) Schema enforcement + tự chạy Entailment checker (L2) ngoài.
   - **Nửa 2 — Chốt bất biến văn bản ở `CitationAgent` (`citations_agent.md`):** Trong cookbook thực tế của Anthropic, bước gắn citation dùng một kiểm tra định lượng **deterministic 0-LLM**: tách toàn bộ tag citation khỏi `<exact_text_with_citation>` rồi so chuỗi thuần 1:1 với `<synthesized_text>` gốc — **chỉ cần khác 1 khoảng trắng là reject ngay**, đảm bảo CitationAgent không bao giờ viết lại hay bịa thêm luận điểm khi đang gắn nguồn!

### 4.2. Thực thi Atomic Entailment rẻ hơn >400x & Không cần nhân đôi LLM Calls (`MiniCheck`, `Bespoke-MiniCheck-7B`)

- **Nút thắt chi phí của FActScore truyền thống (`arXiv:2305.14251`):** Tách từng đoạn văn thành hàng chục atomic facts bằng LLM rồi lại gọi frontier LLM (GPT-4) chấm từng fact chống lại corpus làm chi phí tăng vọt (dù chính FActScore tự động đã giảm chi phí từ `$26K` human eval cho 6,500 generations xuống còn `<2%` sai số so với người).
- **Bước nhảy chi phí của MiniCheck (`arXiv:2404.10774v2`, `bespokelabs.ai`, `huggingface.co/bespokelabs/Bespoke-MiniCheck-7B`):**
  1. **Không cần bước gọi LLM tách atomic facts (`No Claim Decomposition Step`):** MiniCheck chứng minh trên benchmark hợp nhất **LLM-AggreFact** (11 bộ dữ liệu human-annotated) rằng **kiểm định thẳng ở mức từng câu (sentence-level) với model huấn luyện tổng hợp trên lỗi tinh vi** đạt độ chính xác ngang GPT-4 mà **bỏ luôn chi phí & độ trễ của pass LLM decompose**.
  2. **Rẻ hơn >400 lần so với GPT-4 (Table 3 & §6.2 trong `2404.10774v2`):** Trên toàn bộ test set LLM-AggreFact:
     - `MiniCheck-FT5` (Flan-T5-Large, **770M** params): chi phí quy đổi GPU cloud chỉ **$0.24** (ngang mức accuracy của GPT-4 ở vùng ~75% BAcc không cần tune ngưỡng), so với `T5-NLI-Mixed` (11B) tốn **$7.39** và rẻ hơn GPT-4 **>400x**.
     - `MiniCheck-Dbta` (DeBERTa-v3-Large, **355M** params) & `MiniCheck-Rbta` (RoBERTa-L, **355M**): chỉ **$0.20**.
     - `Bespoke-MiniCheck-7B` (chạy qua vLLM + **Automatic Prefix Caching / APC**): đạt thông lượng **>500 docs/phút** trên 1 GPU A6000 (48GB VRAM), trả ra cả nhãn nhị phân lẫn **soft support score `[0.0, 1.0]`** — cho phép định tuyến theo ngưỡng (pass / sửa phẫu thuật / hạ nhãn `"Unverified"` / escalate người) thay vì pass/fail mù.
  3. **Mẹo tối ưu bối cảnh cho Verifier (chống `Lost in the Middle` & `Prompt Injection`):** Không nhét cả bộ tài liệu vào checker; chỉ cấp **đúng snippet/evidence gắn với `EV-xxx` của câu đang kiểm** (vì `2307.03172` chứng minh model mất chính xác ở giữa context dài), đồng thời khóa output verifier thành enum/score hẹp để **chống Indirect Prompt Injection** từ văn bản web chưa tin cậy (`2302.12173`).

### 4.3. Counterfactual RCA trong Dev Tooling không phải Replay toàn bộ (`CausalFlow` & `Causal Agent Replay`)

- **Vì sao LLM-as-a-judge RCA thất bại nặng (`arXiv:2606.08275v1` — CAR):** Trên benchmark `Who&When`, SOTA LLM-judge quy trách nhiệm bước lỗi trong trajectory agent chỉ đạt **~14% step-level accuracy**! Nguyên nhân cốt lõi: **bước *thực thi* hành động hỏng (manifestation step) thường KHÔNG phải bước *quyết định* sai lầm (commitment step)**, và LLM đọc log tĩnh thường nhầm tương quan bề mặt thành nhân quả.
- **2 cơ chế Counterfactual RCA nhẹ hơn chạy lại từ đầu:**
  1. **Point-of-Commitment Rule + `do_resample` giới hạn (`CAR`, `2606.08275`):** Thay vì replay toàn bộ trajectory hay đánh giá mọi bước mù quáng, CAR định vị điểm chuyển pha (*point of commitment* — bước sớm nhất mà khi can thiệp `do()` và chạy tiếp cục bộ theo cùng policy sẽ làm dịch chuyển phân phối kết quả kèm **confidence interval**), kết hợp **budget-bounded Monte-Carlo Shapley** để chia tín dụng nhân quả khi 2 bước tương tác gây lỗi.
  2. **Minimal Counterfactual Edit (`CausalFlow`, `2605.25338`):** Mô hình hoá trace thành chuỗi bước phụ thuộc để tính *Causal Responsibility Score (CRS)* và tạo **bản sửa tối thiểu (minimal edit)** ngay tại bước có CRS cao nhất làm đảo ngược kết quả từ Fail → Pass, giảm thiểu *behavioral drift* và chi phí retry toàn cục.

### 4.4. Áp dụng trực tiếp cho Dual-Track Verification trong TDQ Workflow

Dựa trên ràng buộc thực tế của repo TDQ (từ `phan-tich-kien-truc-codebase.md` §5: root `skills/tdq-build/references/qc.md` đang **3,479 / 3,500 tokens — chỉ còn dư 21 tokens**, `SKILL.md` của `tdq-build` chỉ dư **2 dòng**; `invoke_subagent` hỗ trợ `flash_lite` / `flash` / `pro` / `inherit`):

1. **Track 1 (Deterministic L1 + Tool Oracle L4 — chạy trước, chi phí ~0 token LLM):**
   - Trong `doc_lint.py` / helper Python kiểm báo cáo (`evidence-lint` nhẹ trong code/script thay vì nhồi prompt dài):
     - Kiểm **Citation Recall & Structural Binding**: mọi luận điểm định lượng/kết luận bắt buộc mang tag `[EV-xxx]` hợp lệ có tồn tại trong `evidence.jsonl`, và mọi `file:line` / URL tham chiếu đều khớp whitelist đã đọc/trích xuất (chặn lỗi bịa `2510.05321` hoặc link 404 như `blog.langchain.com` ngay ở tầng deterministic trước khi gọi QC LLM!).
     - Áp dụng **Invariant Text Diff** kiểu Anthropic `citations_agent.md` nếu có pass bổ sung trích dẫn sau khi viết nháp.
2. **Track 2 (Focused Grounding L2 + Counterfactual Check — chi phí thấp, không đọc mù cả kho tài liệu):**
   - Thay vì bắt `tdq-qc-tester` đọc lại toàn bộ web/repo hoặc tự phán tổng quan, cấp cho `tdq-qc-tester` (hoặc một sub-pass `flash` chi phí rẻ cho L2 entailment trước khi `inherit`/`pro` làm L5 red-team) đúng cặp **(Atomic/Sentence Claim ↔ Snippet trích từ `EV-xxx` trong `evidence.jsonl`)**. Nhờ tính chất *localized premise* (bài học từ `MiniCheck` & `Lost in the Middle`), L2 chạy nhanh trên context hẹp, chi phí chỉ bằng **một phần nhỏ của bước Write/Analyze** chứ không nhân đôi chi phí hệ thống.
   - **Phân tầng Confidence Label bắt buộc đầu ra QC:** Mỗi claim trọng yếu gắn 1 trong 3 nhãn (tương đương soft score của Bespoke-MiniCheck): `Verified (L4/Multi-EV)`, `Single-Source / Inferred` (cần user lưu ý), hoặc `Contested / Unverified (F6-blocked)` → ép **Surgical Repair** (kiểu `FActScore` / `RARR`) sửa đúng câu đó thay vì viết lại cả báo cáo.
3. **Counterfactual Point-of-Commitment cho `tdq-debugger` (Debug/RCA lane):**
   - Bắt buộc `tdq-debugger` trong phân tích lỗi/RCA tách rõ **Manifestation Step** (nơi lỗi nổ ra) khỏi **Point-of-Commitment Step** (quyết định/trạng thái sớm nhất dẫn tới lỗi) và ghi kèm **Counterfactual Falsification Test** ("nếu đảo điều kiện X tại bước Y mà lỗi biến mất / vẫn giữ nguyên thì giả thuyết H1 đúng/sai") trước khi kết luận nguyên nhân gốc.
4. **Bảo vệ Token Budget (`R13`) khi tích hợp vào TDQ:**
   - Tuyệt đối không nhồi hướng dẫn mới vào `skills/tdq-build/references/qc.md` (dư 21 tokens) hay `skills/tdq-spec/references/spec-template.md` (dư 14 tokens). Đặt đặc tả chi tiết vào sibling file còn headroom rộng (như `qc-vong-fix.md` đang `536/3500`, `subagent-tuning.md` đang `1654/3500`, `context-budget.md` đang `2025/3500`) hoặc script kiểm deterministic `scripts/`.

---

## 5. Ma trận Tổng hợp Kiến trúc Đề xuất cho TDQ Workflow

| Trục tối ưu | Cơ chế cốt lõi đã kiểm chứng | Bằng chứng định lượng / thực chiến | Điểm chạm mục tiêu trong TDQ Repo |
|---|---|---|---|
| **1. Memory sống sót qua multi-`/compact`** | Append-only `evidence.jsonl` + Pointer-only `[TDQ:ANCHOR]` + JSON state flags | OpenHands `<20 ms` recovery (358 events), `-61%` lỗi hệ thống; Anthropic `-84%` token (`+39%` perf); Cursor `-50%` compaction error ở 1,000 tokens | `session_start.py` (`[TDQ:ANCHOR]`), `read_gate.py` & `pre_tool_use.rs:444` (range bypass), `tdq_ccr.py`, `skills/tdq-conventions/references/context-budget.md` |
| **2. Fan-out Breakeven & Budget Guardrails** | Centralized hub-and-spoke (`<=4` workers), ngưỡng bão hoà `45%`, diminishing-returns stop & per-run cap | Google/MIT (`2512.08296v3`): `>45%` MAS thua SAS (`0.522 vs 0.444–0.511`), Independent lỗi `17.2x` vs Centralized `4.4x`, Hybrid overhead `515%`; Anthropic cap `15–20` tool calls | `tdq_team.py` (`TRAN_SONG_SONG`, `- Sinh ra:` → `vung_file`), `tdq_bench.py`, `skills/tdq-conventions/references/subagent-tuning.md`, `skills/tdq-build/references/team-mode.md` |
| **3. Dual-Track Verification chống F6 & RCA sai** | L1 deterministic (`EV-xxx` + invariant diff) trước → L2 localized claim↔snippet (`flash` / MiniCheck-style) → L4 tool oracle + Point-of-Commitment RCA | MiniCheck `>400x` rẻ hơn GPT-4 (`$0.24`), `>500 docs/min`, bỏ bước LLM decompose; LLM-judge RCA tĩnh chỉ đạt `14%` trên `Who&When` (`CAR`) | `agents/tdq-qc-tester.md`, `agents/tdq-debugger.md`, `scripts/doc_lint.py` (tôn trọng headroom `qc.md` 21 tokens → dùng sibling `qc-vong-fix.md` hoặc validator script) |
