# RESEARCH — Tách Scoping/Planning nhẹ khỏi Heavy Execution trong Research, Phân tích, Debug & Báo cáo
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

- Ngày thực hiện: 2026-11-20
- Công cụ: `tdq-workflow-agy_tavily-primary:tavily_search` (4 truy vấn, `search_depth=advanced`) + `tavily_extract` (4 URL trọng tâm)
- Mục tiêu: Thu thập best practices sản xuất (production) về việc tách pha **scoping/planning nhẹ** khỏi pha **thực thi nặng (heavy execution)** và thiết kế **QC dựa trên bằng chứng / red-team** cho các tác vụ phi-code (Research, Phân tích, Debug/RCA, Báo cáo) để áp dụng vào TDQ Workflow.

---

## Truy vấn 1: Anthropic Multi-Agent Research System (Orchestrator-Worker, Planning vs Execution & CitationAgent)

- **Query**: `Anthropic multi-agent research system orchestrator worker planning scoping subagents citation agent`
- **Nguồn đã đối chiếu**:
  - `https://theaiengineer.substack.com/p/how-anthropic-built-multi-agent-deep` (Anthropic's Multi-Agent Research Architecture Explained)
  - `https://www.swarms.ai/blog/advanced-research-anthropic-multi-agent-research-system` (AdvancedResearch: An Open-Source Implementation)
  - `https://fountaincity.tech/resources/blog/anthropic-multi-agent-blueprint-production` (Anthropic's Multi-Agent Blueprint in Production)
  - `https://blog.bytebytego.com/p/how-anthropic-built-a-multi-agent` (How Anthropic Built a Multi-Agent Research System)
  - `https://www.zenml.io/llmops-database/building-a-multi-agent-research-system-for-complex-information-tasks` (ZenML LLMOps Database — Anthropic 2025)
  - `https://www.youtube.com/watch?v=0HljLKVdtjo` (Anthropic: How to Build Multi Agent Systems)

### Dữ kiện chính (Key Facts)
1. **Kiến trúc 4 chặng tách bạch (Orchestrator-Worker + Citation Pass)**:
   - Chặng 1 (Lead Planner): phân tích yêu cầu, lập chiến lược/kế hoạch điều tra và **lưu kế hoạch vào bộ nhớ ngoài (external memory)** trước khi chạy sâu để không mất định hướng khi context dài.
   - Chặng 2 (Parallel Subagents): Lead spawn 3–5 subagent chạy song song (mỗi subagent tự chạy nhiều tool call song song). Mỗi subagent có context window cô lập và nhận giao việc chặt gồm 4 phần: **(a) mục tiêu rõ, (b) định dạng đầu ra, (c) hướng dẫn tool/nguồn ưu tiên, (d) ranh giới nhiệm vụ (task boundaries)** để tránh chồng lấn hoặc mở rộng vô hạn.
   - Chặng 3 (Synthesis & Replan): subagent trả kết quả cô đọng (qua kho lưu trữ chung thay vì chat dài); Lead tổng hợp và quyết định dừng hay mở thêm vòng mới.
   - Chặng 4 (CitationAgent độc lập): đọc **tài liệu nguồn thô (raw documents)** song song với **bản nháp báo cáo cuối** để gắn/đối chiếu trích dẫn từng luận điểm.
2. **Chống hiện tượng "game of telephone" (tam sao thất bản)**:
   - Khi một agent vừa viết báo cáo vừa tự gắn citation sau nhiều lớp tóm tắt từ subagent, agent thường tái dựng nguồn từ trí nhớ và gắn sai. Tách riêng `CitationAgent` đọc trực tiếp raw evidence + draft giải quyết lỗi này.
3. **Số đo hiệu năng & chi phí (Cost/Benefit Guardrail)**:
   - Multi-agent (Opus 4 làm lead + Sonnet 4 làm subagents) vượt single-agent Opus 4 tới **+90.2%** trên bộ eval nội bộ và giảm **~90% thời gian** cho câu hỏi phức tạp.
   - Tuy nhiên, chi phí token gấp **~15x** tương tác chat thông thường (lượng token giải thích ~80% phương sai hiệu năng). Multi-agent chỉ có lời khi bài toán **tách được thành các hướng độc lập song song**; nếu tác vụ phụ thuộc tuần tự/ngữ cảnh gắn chặt thì không nên ép fan-out.
   - Cần quy tắc **scale effort to query complexity** (định mức số subagent & số lượt tool theo độ khó) để tránh lỗi "spawn 50 subagents cho một câu hỏi 1 dòng".

### Bài học hành động cho TDQ Workflow
- **Tách Planning khỏi Execution**: trong pha `analyze`/`spec`/`plan` cho Research/Phân tích, Lead chỉ lập chiến lược + lưu plan ra artifact (`spec`/`plan`) và định mức công sức (số nhánh, ngân sách tool), tuyệt đối không chạy fan-out sâu khi user chưa duyệt phạm vi.
- **Chuẩn hóa Brief giao việc cho Worker**: mọi lệnh gọi subagent trong pha thực thi phải ghi rõ 4 trường bắt buộc (objective, output format, tool/source boundary, out-of-scope boundary).
- **Kho bằng chứng ngoài (External Evidence Store)**: worker ghi raw evidence/citations ra file (vd. `docs/tdq/research/...` hoặc CCR store) và chỉ trả digest `<= 1,500 chars` về Lead; pha QC/Citation đọc trực tiếp raw evidence để kiểm chéo thay vì tin bản tóm tắt truyền tay.

---

## Truy vấn 2: OpenAI Deep Research, Gemini Unified Intent-Planning & LangGraph Open Deep Research

- **Query**: `deep research agent architecture clarifying questions scoping plan-and-execute LangGraph OpenAI`
- **Nguồn đã đối chiếu**:
  - `https://www.langchain.com/blog/open-deep-research` (LangChain — Open Deep Research)
  - `https://zylos.ai/research/2026-04-21-deep-research-agent-architectures` (Zylos Research — Deep Research Agent Architectures)
  - `https://note.com/repkuririn7/n/nec531ce04f09?hl=en` (LangChain Open Deep Research Architecture Breakdown)
  - `https://www.youtube.com/watch?v=agGiWUpxkhg` (LangChain Open Deep Research Walkthrough)
  - `https://www.splunk.com/en_us/blog/learn/deep-research-agents.html` (Deep Research Agents with Plan-and-Execute & Evals)
  - `https://medium.com/@tahirbalarabe2/architecting-autonomous-deep-research-agents-with-langgraph-76f487ded907` (Autonomous Deep Research Agents with LangGraph)

### Dữ kiện chính (Key Facts)
1. **Ba mô hình Scoping trước khi chạy sâu**:
   - **Planning-Only** (Grok DeepSearch, H2O, Manus): tự lập plan và chạy ngay không hỏi user -> nhanh ra search đầu tiên nhưng rủi ro cao bị lệch hướng phân rã.
   - **Intent-to-Planning** (OpenAI Deep Research): luôn hỏi **clarifying questions** về phạm vi, định dạng mong muốn và ràng buộc trước khi khởi chạy vòng nghiên cứu -> giảm mạnh lãng phí compute/token do đi sai nhánh phụ.
   - **Unified Intent-Planning** (Gemini Deep Research): tiến xa hơn bằng cách **xuất trình nguyên Research Plan có thể chỉnh sửa được** để user duyệt/sửa trước khi thực thi.
2. **Chuẩn 3 pha của LangGraph Open Deep Research (`Scope -> Research -> Write`)**:
   - **Phase 1 — Scope** gồm 2 bước nhẹ: (1) *User Clarification* (thu thập ngữ cảnh còn thiếu), (2) *Brief Generation* (viết `Research Brief` chuẩn hóa lưu vào state làm kim chỉ nam xuyên suốt pha Research và Write).
   - **Phase 2 — Research**: Supervisor đọc `Research Brief`, quyết định có song song hóa được không rồi giao sub-topics cho sub-agents có context cô lập. Cuối vòng, mỗi sub-agent tự chạy 1 bước nén để lọc bỏ nhiễu (trang web rác, tool call lỗi) và trả câu trả lời kèm trích dẫn sạch.
   - **Phase 3 — Write**: Writer LLM nhận toàn bộ findings đã lọc cùng `Research Brief` để soạn báo cáo nhất quán.
3. **Kiểm soát ngân sách thực thi & bảo toàn Citation khi nén**:
   - Các hệ thống production đều đặt **execution budgets cứng** (OpenAI Deep Research: ~30–60 search calls, 120–150 page fetches, 150–200 reasoning loops; Step-DeepResearch: **tối đa 3 vòng error-reflection** cho mỗi sub-task để chặn vòng lặp sửa sai vô hạn; Splunk/LangGraph Plan-and-Execute: bắt buộc có explicit completion criteria và recursion limit, nhắc replanner không trả lại bước đã xong).
   - **Bảo toàn Citation Provenance khi nén (Context Folding)**: Step-DeepResearch và Mind2Report dùng lớp quản lý bộ nhớ có **ID duy nhất + nội dung chưng cất + liên kết nguồn gốc** để nén context mà không làm rụng link nguồn.
   - **Mid-flight interruption & Async Checkpoints**: cho phép cập nhật/điều hướng giữa chừng dựa trên state đã checkpoint thay vì hủy làm lại từ đầu.

### Bài học hành động cho TDQ Workflow
- **Áp dụng Unified Intent-Planning cho TDQ**: pha `analyze` chỉ chạy **lightweight probe** (đủ hiểu bối cảnh, không cày sâu) + phỏng vấn làm rõ (clarifying questions) -> khóa **Research/Analysis Brief** (trong `spec`) -> chốt **Execution Plan** (danh sách nhánh, nguồn dự kiến, ngân sách tool/subagent, tiêu chí dừng, định dạng báo cáo) rồi **STOP chờ user duyệt** trước khi vào pha thực thi nặng.
- **Tách riêng pha `Write/Synthesize` khỏi pha `Collect`**: tránh để một lượt vừa thu thập thô vừa viết báo cáo cuối; gom toàn bộ findings đã khử nhiễu (kèm evidence IDs) vào một bước tổng hợp chuyên biệt.
- **Giới hạn vòng lặp & ngân sách tường minh trong Plan**: mỗi task trong plan cho Research/Phân tích nên có `budget` (số truy vấn/trang mục tiêu) và `max 3 error-reflection retries` + `completion criteria` rõ ràng để không bị trôi phạm vi hoặc lặp vô hạn.

---

## Truy vấn 3: Agentic SWE Debugging & Automated RCA Pipelines (Triage/Hypothesis Planning vs Deep RCA)

- **Query**: `agentic SWE debugging investigation pipeline triage hypothesis root cause analysis planning execution`
- **Nguồn đã đối chiếu**:
  - `https://www.augmentcode.com/guides/root-cause-analysis-ai-agents` (How Root Cause Analysis AI Agents Work in Production — Augment Code)
  - `https://resolve.ai/glossary/what-is-automated-rca` (What is Automated Root Cause Analysis — Resolve AI)
  - `https://www.databricks.com/blog/how-databricks-uses-ai-accelerate-incident-investigation` (How Databricks Uses AI to Accelerate Incident Investigation)
  - `https://community.cadence.com/cadence_blogs_8/b/artificial-intelligence/posts/agentic-ai-for-design-verification-and-debug` (Agentic AI for Design Verification and Debug — Cadence)
  - `https://chipagents.ai/blogs/scaling-autonomous-root-cause-analysis-regression-triage` (Scaling Autonomous RCA for Regression Triage — ChipAgents)
  - `https://mcpmarket.com/tools/skills/bug-triage-investigation` (Bug Triage & Investigation Skill Pattern)

### Dữ kiện chính (Key Facts)
1. **Phân biệt rạch ròi Triage (nhẹ) với Deep RCA (nặng)**:
   - **Triage**: ưu tiên, khoanh vùng subsystem/file nghi vấn, tách biệt **sự thật đã xác nhận (confirmed facts)** với **giả thuyết (hypotheses)**, xác minh khả năng tái hiện (reproducibility) và loại trừ "cá trích đỏ" (red herrings — vd. Databricks AI SRE chạy *platform health checks* ngay đầu để loại lỗi hạ tầng trước khi kỹ sư mất 30 phút debug code ứng dụng).
   - **Deep RCA**: coi debug là **bài toán tìm kiếm trên nhiều giả thuyết song song** (ChipAgents, Resolve AI, LATS-RCA), không chốt vội câu trả lời đầu tiên. Duy trì tập giả thuyết ứng viên, thu thập bằng chứng ủng hộ **và bằng chứng bác bỏ (for and against)** cho từng giả thuyết rồi xếp hạng theo độ tin cậy.
2. **Single-agent trộn planning + execution dễ bị nông**:
   - Theo tổng hợp của Augment Code, khi một LLM đơn lẻ vừa lập kế hoạch vừa thực thi RCA, mô hình có xu hướng sinh một đoạn văn phi cấu trúc cố giải quyết mọi thứ một lượt, mất khả năng lặp và tinh chỉnh giả thuyết.
   - Giải pháp production kết hợp 2 mẫu: **Modality-specific specialists** (agent chuyên logs, metrics, traces, code/diff với tool boundary riêng) + **Progressive discovery** (Azure SRE Agent: mỗi bước đi tiếp dựa trên phát hiện của bước trước thay vì kịch bản cứng).
3. **4 cơ chế kiểm soát chất lượng RCA ở production (Augment Code & Databricks)**:
   - **Scope restriction**: khóa mỗi agent vào 1 modality/vai trò xác thực.
   - **Stored evidence**: lưu bằng chứng điều tra ra ngoài trạng thái suy luận tạm của LLM; nhúng bằng chứng bấm-mở-được (click-to-verify) để kỹ sư tự kiểm chứ không phải "tin lời agent" (Databricks).
   - **Adversarial verification**: kiểm thử phản chứng (counterfactual review) đối với kết luận trước khi xuất báo cáo.
   - **Confidence routing**: kết luận có độ tin cậy thấp được định tuyến cho con người duyệt thay vì hành động tự động.
4. **Chuỗi vòng lặp đầy đủ không đứt gãy (Cadence / ChipAgents)**:
   - `Understand & Plan -> Triage -> Parallel Hypothesis Investigation (Debug/RCA) -> Evidence Convergence -> [Fix] -> Reverify -> Next Action`.

### Bài học hành động cho TDQ Workflow
- **Debug/RCA lane phải tách 2 chặng rõ**:
  - Chặng `analyze` (Triage nhẹ): thu thập triệu chứng, check sức khỏe môi trường để loại red herrings, lập bảng **Confirmed Facts vs Candidate Hypotheses (2–4 giả thuyết)** và chọn chiến lược điều tra/tái hiện -> trình user duyệt hướng điều tra (đặc biệt khi debug sâu có nguy cơ tốn thời gian hoặc cần quyền môi trường).
  - Chặng `implement/investigate` (Deep RCA nặng): kiểm chứng từng giả thuyết có cả **evidence ủng hộ + tiêu chí bác bỏ (falsification criteria)**, cập nhật progressive discovery vào Evidence Log ngoài hội thoại, cuối cùng xếp hạng nguyên nhân gốc kèm **confidence score + chuỗi bằng chứng kiểm chứng được (`file:line`, log, repro output)**.
- Không cho phép nhảy thẳng vào kết luận nguyên nhân gốc hay sửa code khi chưa có tối thiểu 1 bước kiểm phản chứng (vì sao các giả thuyết khác bị loại).

---

## Truy vấn 4: Evidence-Based Verification, Fact-Checking & Red-Team QC cho Báo cáo Phi-Code

- **Query**: `LLM agent report verification citation verification fact-checking red-team grounding quality control`
- **Nguồn đã đối chiếu**:
  - `https://hidekazu-konishi.com/entry/llm_output_verification_patterns.html` (LLM Output Verification Patterns — Grounding, Self-Verification, Cross-Model Review & Citation Enforcement)
  - `https://www.dataiku.com/blog/grounding-verification-in-ai` (Grounding Verification in AI: LLM Techniques and Metrics)
  - `https://www.alphaxiv.org/abs/2310.13549` (The Perils & Promises of Fact-checking with LLMs)
  - `https://arxiv.org/html/2608.23811v1` (Generating Biomedical Fact-Checking Reports with RL-Enhanced Agentic Search — BioCheck Agent)
  - `https://www.nature.com/articles/s41598-026-41862-z` (Multi-agent Systems and Credibility-based Scoring in Fact-Checking — Scientific Reports)
  - `https://parallel.ai/articles/ai-fact-checking-api` (AI Fact Checking API: Verify Claims With Cited Answers)

### Dữ kiện chính (Key Facts)
1. **Kiểm chứng cấp mệnh đề nguyên tử (Atomic Claim-Level Verification — FActScore)**:
   - Một báo cáo dài chứa hàng chục mệnh đề pha trộn; chấm điểm toàn cục cả bài là vô dụng cho việc sửa lỗi.
   - **FActScore** (Min et al.) tách báo cáo thành các **mệnh đề nguyên tử (atomic facts)** rồi kiểm độc lập từng mệnh đề trước nguồn bằng chứng -> xác định chính xác *câu nào sai* để **sửa phẫu thuật (surgical repair)** thay vì viết lại toàn bộ.
2. **Chuẩn đo Citation 2 chiều (ALCE) & Lỗi nguy hiểm nhất — Failure Type F6**:
   - Đánh giá trích dẫn bắt buộc đo cả **Citation Recall** (mọi luận điểm cần bằng chứng đều có trích dẫn?) và **Citation Precision** (đoạn trích dẫn có *thực sự chứng minh* luận điểm gắn kèm không?).
   - **Failure Type F6**: trích dẫn có URL/nguồn *hoàn toàn có thật*, nhưng nội dung nguồn **không chứng minh** cho mệnh đề được gắn. Đây là lỗi nguy hiểm nhất vì lọt qua mọi bộ check chỉ kiểm tra "link có sống / có citation hay không".
3. **Kiến trúc kiểm chứng nhiều lớp & Ngưỡng từ chối (Threshold Gating)**:
   - **4 lớp grounding (Dataiku)**: (1) RAG/retrieval có nguồn, (2) Post-generation fact-checking đối chiếu claim vs retrieved passages (vd. Google Check Grounding API trả support score + byte-offset attribution), (3) Claim-level scoring hiệu quả chi phí (vd. **MiniCheck** / **AlignScore** cho bài toán kiểm từng câu bằng model nhẹ), (4) Human-in-the-loop với miền rủi ro cao.
   - Khi support score dưới ngưỡng -> tự động từ chối và chuyển nhánh xử lý: truy xuất lại, gắn nhãn `"cannot verify"`, hoặc leo thang human review.
4. **Giới hạn của Self-Verification & Vai trò của Adversarial / Multi-Agent Review**:
   - Tự kiểm duyệt (self-critique) mà **không có bằng chứng bên ngoài hoặc góc nhìn độc lập** có độ tin cậy kém hơn nhiều so với kiểm chứng có grounding.
   - Các khung đa tác nhân như **MADR** (tranh biện lặp với vai trò khác nhau) và **DelphiAgent** (nhiều chuyên gia độc lập đánh giá nguồn riêng biệt, nhân `factuality {-1, +1} * confidence [0,1]`) giúp chống hiện tượng **overconfidence** (tự tin thái quá) của một agent đơn lẻ.
5. **Tín hiệu độ không chắc chắn (Uncertainty Signaling)**:
   - Báo cáo chất lượng cao (DeepResearch Bench / Zylos) phải phân tầng độ chắc chắn rõ ràng: **High confidence** (nhiều nguồn độc lập xác nhận), **Medium/Single-source** (1 nguồn duy nhất), **Contested/Unverified** (nguồn mâu thuẫn hoặc chưa kiểm chứng được — ghi rõ thay vì che lấp bằng giọng văn quả quyết).

### Bài học hành động cho TDQ Workflow
- **Chuẩn hóa `tdq-qc-tester` cho nhánh phi-code (Evidence & Red-Team QC)** thay vì ép tiêu chí unit-test phần mềm:
  1. **Atomic Claim Audit**: trích các luận điểm cốt lõi (số liệu, mốc thời gian, quan hệ nhân quả, khuyến nghị kiến trúc) trong báo cáo/kết quả phân tích.
  2. **Citation Precision & Recall (chống lỗi F6)**: đọc lại raw evidence đã lưu (URL/snippet/file:line/log) để xác nhận nguồn *thực sự ủng hộ* đúng mệnh đề gắn kèm — không chỉ kiểm sự tồn tại của link.
  3. **Red-Team / Counterfactual Pass**: một pass độc lập đóng vai phản biện đi tìm (a) bằng chứng bị bỏ sót, (b) nguồn mâu thuẫn, (c) giả thuyết thay thế chưa bị bác bỏ, (d) kết luận suy diễn vượt quá bằng chứng.
  4. **Uncertainty & Gap Disclosure**: bắt buộc mọi báo cáo phi-code phân loại rõ `Verified (multi-source / direct probe)` vs `Single-source / Inferred` vs `Unverified / Open gap`; bất kỳ claim nào dưới ngưỡng grounding phải sửa phẫu thuật hoặc hạ cấp/gỡ bỏ trước khi PASS QC.

---

## Tổng hợp Kiến trúc đề xuất cho TDQ Workflow (4 nhóm tác vụ phi-code & điều tra)

| Tầng / Pha TDQ | Nguyên tắc cốt lõi (từ bằng chứng) | Research & Báo cáo | Phân tích (Kiến trúc/Hệ thống) | Debug / RCA |
| :--- | :--- | :--- | :--- | :--- |
| **1. Lightweight Scoping (`analyze` -> `spec`)** | **Intent-to-Planning / Unified Intent-Planning** (OpenAI, Gemini, LangGraph): chỉ probe nhẹ đủ thấy địa hình, hỏi rõ câu hỏi làm đổi kết quả, lưu `Brief` + `Confirmed vs Unknown`. | Probe 1–2 nguồn/cấu trúc để hiểu thuật ngữ; chốt câu hỏi nghiên cứu, phạm vi nguồn, định dạng báo cáo, độ sâu. | Đọc bề mặt (LSP symbols / entrypoints / docs) thay vì audit toàn repo ngay; chốt mục tiêu phân tích & tiêu chí đánh giá. | **Triage nhẹ**: tái hiện tối thiểu, kiểm infra/env để loại red herrings, tách *Confirmed Facts* vs *2–4 Candidate Hypotheses*. |
| **2. Plan Gate (`plan` -> duyệt)** | **Effort Scaling & Explicit Budgets** (Anthropic, Step-DeepResearch): khai báo rõ nhánh song song (chỉ fan-out khi thực sự độc lập), tool budget, max 3 error-reflection loops, exit criteria; STOP chờ user duyệt. | Danh sách sub-questions độc lập, nguồn/tool cho từng nhánh, giới hạn số query/URL, khung mục lục báo cáo. | Danh sách trục phân tích (vd. hiệu năng, bảo mật, phụ thuộc), phạm vi file/module, cách đối chứng thực tế. | Ma trận kiểm chứng từng giả thuyết (bằng chứng cần thu + **tiêu chí bác bỏ** cho mỗi giả thuyết). |
| **3. Heavy Execution (`implement` / `execute`)** | **Orchestrator-Worker + Isolated Context + External Evidence Store** (Anthropic, LangGraph, Augment): giao việc đủ 4 trường, mỗi worker cô lập context, lưu raw evidence kèm ID/URL ra disk, trả digest ngắn; tách bước `Collect` khỏi bước `Write`. | Chạy subagent song song theo sub-questions -> lưu raw notes/URLs -> bước `Write` tổng hợp báo cáo theo Brief. | Chạy phân tích sâu (LSP refs, Graphify blast radius, đo benchmark/probe thật) -> lưu bảng bằng chứng `file:line` -> tổng hợp trade-offs. | Chạy modality/hypothesis probes (logs, traces, code diff, repro test) -> lưu evidence log -> hội tụ nguyên nhân gốc + confidence score. |
| **4. Independent QC (`qc`)** | **CitationAgent + FActScore + ALCE (chống F6) + Red-Team Counterfactual** (Anthropic, Konishi, Dataiku, Augment, MADR): agent độc lập đọc **raw evidence + draft**, kiểm từng atomic claim, phản biện giả thuyết đối lập, gán nhãn độ chắc chắn. | Kiểm Citation Precision & Recall (chống F6), kiểm mâu thuẫn giữa các nguồn, gắn nhãn độ tin cậy, sửa phẫu thuật claim lỗi. | Kiểm mỗi nhận định có `file:line` hoặc kết quả đo thực tế, red-team các giả định ẩn/trade-off bị bỏ sót. | Counterfactual check (chứng minh vì sao các giả thuyết khác sai), kiểm chuỗi bằng chứng tái hiện được, confidence routing nếu chưa chốt 100%. |

### Lưu ý chống over-engineering (Guardrails)
1. **Không ép Multi-Agent cho mọi việc**: multi-agent tốn ~15x token (Anthropic). Chỉ spawn nhiều worker khi có >= 2 nhánh/modality thực sự độc lập; việc tuyến tính hoặc quy mô nhỏ giữ single-agent nhưng vẫn giữ kỷ luật **Scope nhẹ -> Plan duyệt -> Execute có Evidence Store -> QC độc lập**.
2. **Bảo toàn Provenance là bắt buộc**: bất kỳ bước nén/CCR/tóm tắt nào giữa worker và Lead đều phải giữ nguyên `evidence_id` / `URL` / `file:line` để `CitationAgent`/QC đối chiếu trực tiếp với nguồn gốc, tuyệt đối không chấm điểm từ trí nhớ tóm tắt.
3. **Fail-Closed về độ chắc chắn**: không đủ bằng chứng thì ghi rõ `Unverified / Cần kiểm thêm` thay vì bịa nguồn hoặc viết giọng khẳng định (chặn F6 ngay ở cổng QC).
