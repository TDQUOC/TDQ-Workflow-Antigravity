# Nghiên cứu: Độ chi tiết Plan và Thiết kế Đặc tả cho Model Coding Bậc thấp trong Agentic Workflows
Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> Ngày nghiên cứu: 2026-11-19 · Phạm vi: Khảo sát thực nghiệm bên ngoài (benchmarks, papers, engineering postmortems) về kiến trúc Strong Planner + Small/Low-Tier Executor, điểm gãy của over-specification, cấu trúc task-card tối ưu pass@1/token, và các mô thức harness hiện đại để hiệu chỉnh thiết kế `tdq-plan` / `tdq-implementer`.

---

## Tóm tắt Điều hành (Executive Synthesis)

1. **Tách Reasoning (Architect/Planner mạnh) khỏi Execution (Editor/Worker nhỏ) mở khóa biên chất lượng lớn nhất — nhưng KHÔNG phải bằng cách nhồi toàn bộ code hay văn xuôi dài vào plan.**
   - Thực nghiệm **Skeleton Coding** (`arXiv:2610.38214v1`) chứng minh đặc tả **cấu trúc** (file layout + function signatures + local contracts + global invariants) đẩy pass rate của model nhỏ (`GPT-5.6 Luna`) từ `67% -> 90%` trên SCBench và `21.1% -> 79.5%` trên SDDBench — chỉ còn kém model mạnh nhất (`GPT-5.6 Sol`) `5.0–8.2` điểm phần trăm nhưng chi phí triển khai thấp hơn **15–26 lần**. Trong khi đó, đặc tả thuần hành vi (behavioral prose) chỉ tăng tối đa `9.4` điểm phần trăm.
   - **Aider Architect/Editor** chứng minh tách tư duy và chỉnh sửa tạo đột phá chi phí/chất lượng: `o1-preview` + `o1-mini`/`DeepSeek` đạt `85.0%` SOTA (so với `79.7%` solo); `DeepSeek R1` (Architect) + `Claude 3.5 Sonnet` (Editor) đạt `64.0%` Polyglot SOTA (so với `56.9%` R1 solo và `51.6%` Sonnet solo) với chi phí rẻ hơn **14 lần** so với `o1` (`$13.29` vs `$186.50`).
2. **Model nhỏ cực kỳ nhạy với Over-Specification và Mật độ Ràng buộc (Instruction Density).**
   - **IFScale** (`arXiv:2507.11538v1`, Distyl AI) chỉ ra 3 đường cong suy giảm theo số lượng chỉ thị đồng thời (`10 -> 500`): model reasoning mạnh chịu **Threshold Decay** (ổn định tới ~150–200 chỉ thị), model flagship chịu **Linear Decay**, còn **model nhỏ/nhẹ (`Haiku`, `Flash`, `Mini`, Llama nhỏ) chịu Exponential Decay** — sụp nhanh ngay ở mật độ thấp, rơi về ngưỡng `7–15%` theo cơ chế **bỏ sót (omission)** và **primacy bias**.
   - **Context Rot** (Chroma 2025 trên 18 model; Liu et al. TACL 2024; Du et al.) chứng minh độ chính xác giảm dần rất sớm trước giới hạn cửa sổ ngữ cảnh (~113K tokens hoặc `<50%` window đã mất vùng giữa, `>50%` mất vùng đầu), đồng thời **Laban et al. 2025** chỉ ra hội thoại multi-turn thiếu đặc tả ngay từ đầu làm giảm trung bình `39%` hiệu năng (`-15%` aptitude, `+112%` unreliability).
   - **Anthropic Harness Design** và **Birgitta Böckeler (martinfowler.com)** cảnh báo: nếu Planner cố đặc tả chi tiết kỹ thuật quá vụn (line numbers, code cứng toàn bộ), chỉ một giả định sai ở Planner sẽ **cascade** lỗi xuống mọi task downstream, tạo plan drift và khiến model nhỏ hoặc **phớt lờ** hoặc **làm theo một cách máy móc sai ngữ cảnh**.
3. **Cấu trúc Task-Card Tối ưu ("Goldilocks Spec") cho Model Bậc thấp = Structural Skeleton + Local Contract + Locked Test Oracle + Scoped Context.**
   - Đạt tỷ số `pass@1 / token` cao nhất nhờ: (a) **Contract-first** (tên file đích chính xác, symbol/signature, input/output types, invariants cục bộ, đường dẫn thay thế rõ ràng), (b) **Test-first locked oracle** (test viết trước hoặc assertion cụ thể + lệnh verify cố định, cấm sửa/xóa test), (c) **Ngữ cảnh cô lập per-task** (fresh subagent + AST/skeleton rút gọn, không mang lịch sử task trước), và (d) **Không nhồi số dòng dễ cũ (stale line numbers) hoặc quy tắc toàn cục dạng văn xuôi** (đẩy quy tắc toàn cục sang linter/script kiểm tra tự động).

---

## Góc nhìn 1: Kiến trúc Strong Planner + Weak/Small Executor trong Coding Agents

### Query
- `Aider architect editor benchmark strong planner weak small executor coding LLM SWE-bench Haiku Flash accuracy`
- `Aider DeepSeek R1 architect Claude Sonnet editor polyglot benchmark cost savings percentage`
- Trích xuất trực tiếp: `https://aider.chat/2024/09/26/architect.html`, `https://arxiv.org/html/2610.38214v1`

### Sources / URLs
- Aider Blog (Sep 2024) — *Separating code reasoning and editing*: https://aider.chat/2024/09/26/architect.html
- Aider Blog (Jan 2025) — *R1+Sonnet set SOTA on aider's polyglot benchmark*: https://aider.chat/2025/01/24/r1-sonnet.html
- Skeleton Coding (arXiv preprint) — *Skeleton Coding: Program Structure as a Specification for Agents*: https://arxiv.org/html/2610.38214v1
- Dissecting SWE-Bench Leaderboards (arXiv:2506.17208v2): https://arxiv.org/html/2506.17208v2
- LLMKube FinOps / Aider Polyglot Analysis: https://llmkube.com/blog/m5-max-aider-polyglot-and-finops
- Scale SWE-Bench Pro Leaderboard: https://labs.scale.com/leaderboard/swe_bench_pro
- Vals AI SWE-bench Verified Leaderboard: https://www.vals.ai/benchmarks/swebench

### Key Findings
- **Aider Architect/Editor (Code Editing Benchmark, Sep 2024):**
  - Tách 2 vai trò: **Architect** tập trung giải bài toán và mô tả hướng sửa; **Editor** chỉ tập trung chuyển mô tả thành thao tác sửa mã nguồn đúng định dạng.
  - Bảng điểm thực nghiệm đối chiếu Solo Baseline vs Architect/Editor:
    - `o1-preview` (solo baseline): `79.7%` → ghép với `o1-mini` (whole): **`85.0%`** (+5.3 pp); ghép với `DeepSeek` (whole): **`85.0%`** (+5.3 pp); ghép với `claude-3.5-sonnet` (diff): **`82.7%`** (+3.0 pp).
    - `claude-3.5-sonnet` (solo): `77.4%` → tự tách Architect/Editor với `DeepSeek`: **`78.9%`** (+1.5 pp); với `claude-3.5-sonnet`: **`80.5%`** (+3.1 pp).
    - `gpt-4o` (solo): `71.4%` → ghép `DeepSeek` làm Editor: **`74.4%`** (+3.0 pp).
- **Aider Polyglot Benchmark (Jan 2025 — chi phí & độ chuẩn edit format):**
  - `DeepSeek R1` (Architect) + `Claude 3.5 Sonnet` (Editor) đạt **`64.0%`** (100.0% đúng edit format) với tổng chi phí **`$13.29`**, vượt cả `o1` high solo (`61.7%`, `$186.50` — **rẻ hơn 14×**), `R1` solo (`56.9%`, `$5.42`, +7.1 pp), và `Sonnet` solo (`51.6%`, `$14.41`, +12.4 pp).
  - **Lưu ý phản chứng quan trọng từ chính Aider:** khi model reasoning đời sau (`o1` chính thức) đã mạnh về edit format, ghép thêm Editor không phải lúc nào cũng vượt solo. Lợi ích lớn nhất xuất hiện khi **tách tải nhận thức** giữa model suy luận mạnh (hoặc rẻ về thinking) và model nhỏ/rẻ chuyên áp edit.
- **Skeleton Coding (`arXiv:2610.38214v1`) — Tác động trực tiếp lên model nhỏ:**
  - Khi cung cấp đặc tả cấu trúc kèm global invariants, model nhỏ **`GPT-5.6 Luna`** tăng vọt từ **`67% -> 90%`** trên SCBench (+23 pp) và từ **`21.1% -> 79.5%`** trên SDDBench (+58.4 pp).
  - Khoảng cách giữa model nhỏ và model đầu bảng (`GPT-5.6 Sol`) thu hẹp xuống chỉ còn **`5.0–8.2` điểm phần trăm**, trong khi chi phí thực thi thấp hơn **15–26 lần**.
- **Hệ sinh thái SWE-bench (Multi-model & Hierarchical Agents):**
  - Nghiên cứu phân tích bảng xếp hạng SWE-Bench (`arXiv:2506.17208v2`) ghi nhận nhiều hệ thống top đầu kết hợp đa tầng model (ví dụ `Claude 4 Sonnet + o4-mini` đạt `74.4%` Verified; `Claude 3.5 Haiku + Sonnet + Gemini 2.5 Pro` đạt `49%` Lite; kiến trúc **HyperAgent** gom suy luận cao cấp về `Planner`, ủy thác 3 child agent `Navigator`, `Editor`, `Executor` qua hàng đợi bất đồng bộ).
  - Tuy nhiên trên các bài khó như **SWE-Bench Pro**, khoảng cách model tự chạy (solo) giữa đầu bảng (`Claude Opus 4.6`: `51.9%`, `GPT-5.4`: `59.1%`) và model nhỏ (`Claude 4.5 Haiku`: `39.45%`, `Gemini 3 Flash`: `34.63%`, `Gemma 3 27B`: `11.38%`) vẫn rất rộng (`12–40` pp).
  - **Nhạy cảm với Edit Format & Harness ở model nhỏ:** Thử nghiệm của LLMKube chỉ ra `Devstral-Small-2-2512` đạt `81.7%` trên HumanEval+, nhưng rơi xuống **`4%`** ở định dạng `diff` và **`8%`** ở định dạng `whole` trên Aider Polyglot — chênh lệch **20×** chỉ do định dạng chỉnh sửa và harness! Model nhỏ chịu phạt cực nặng nếu phải vừa giải bài toán vừa tuân thủ định dạng patch phức tạp.

### Implications for TDQ Workflow
- Với TDQ (`tdq-spec`/`tdq-plan` chạy trên model mạnh, `tdq-implementer` có thể hạ xuống `flash`/`haiku`/`mini`), **đừng bắt model nhỏ tự thiết kế kiến trúc hay tự suy đoán phạm vi file**.
- Phần việc nặng về suy luận (phân rã module, định nghĩa interface/signature, bất biến dữ liệu, danh sách file tạo/sửa, thứ tự phụ thuộc) **phải giải quyết dứt điểm ở Planner mạnh**.
- Khi hạ model cho `tdq-implementer`, cần lưu ý **khả năng áp edit/tool call** của model đó (ví dụ `edit_file` target nhỏ, chính xác theo anchor symbol thay vì diff dài nhiều block phức tạp) vì lỗi định dạng edit ở model nhỏ có thể phá hỏng toàn bộ lợi ích của plan tốt.

---

## Góc nhìn 2: Các Chế độ Lỗi của Over-Specification (Plan Quá Chi Tiết / Quá Dài)

### Query
- `LLM coding agent over-specification plan drift context rot instruction dilution lost in the middle small model accuracy`
- `Chroma Context Rot benchmark small model Haiku Flash mini accuracy degradation Laban LLMs Get Lost Multi-Turn`
- `"Curse of Instructions" OR "IFScale" LLM instruction following density dilution small model Haiku Flash mini benchmark`
- `coding agent plan over-specification stale line numbers plan drift rigid pseudocode hurts execution LLM benchmark`
- `Birgitta Böckeler martinfowler spec-driven development Kiro spec-kit over-specification instructions ignored`

### Sources / URLs
- IFScale (Distyl AI, Jul 2025) — *How Many Instructions Can LLMs Follow at Once?*: https://arxiv.org/html/2507.11538v1
- Philippe Laban et al. (May 2025) — *LLMs Get Lost in Multi-Turn Conversation*: https://www.prompthub.us/blog/why-llms-fail-in-multi-turn-conversations-and-how-to-fix-it · https://www.linkedin.com/posts/philippe-laban-b5a59b66_new-paper-out-today-llms-get-lost-in-activity-7327738186141417472-2k9K
- Context Rot Synthesis (Chroma 2025, Liu et al. TACL 2024, Du et al.): https://upsolve.ai/blog/context-rot · https://www.tinyfish.ai/blog/context-rot · https://tmls.nyc/research/context-engineering · https://redis.io/blog/context-rot
- Birgitta Böckeler (Oct 2025, martinfowler.com / birgitta.info) — *Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl*: https://birgitta.info/posts/spec-driven.html · https://www.sofokus.com/ai-glossary/spec-driven-development
- Augment Code — *How to Write Living Specs for AI Agent Development*: https://www.augmentcode.com/guides/living-specs-for-ai-agent-development
- Heym Engineering Audit (1,133 commits / 117 days) — *Spec Driven Development: What Our Agents Ignored*: https://heym.run/blog/spec-driven-development
- SlopCodeBench (arXiv:2603.24755v1) — *Benchmarking How Coding Agents Degrade Over Long-Horizon Iterative Tasks*: https://arxiv.org/html/2603.24755v1

### Key Findings
- **1. Suy giảm theo Hàm Mũ dưới Mật độ Chỉ thị Cao (Instruction Dilution — IFScale `arXiv:2507.11538v1`):**
  - Đánh giá 20 model trên 10→500 chỉ thị đồng thời: ngay cả model frontier tốt nhất chỉ đạt **`68%`** ở mật độ tối đa.
  - Phát hiện **3 dạng đường cong suy giảm**:
    - *Threshold Decay* (model reasoning mạnh như `o3`, `Gemini Pro`): giữ gần hoàn hảo đến ~150–200 chỉ thị rồi mới rơi.
    - *Linear Decay* (model flagship như `GPT-4.1`, `Claude Sonnet`): giảm tuyến tính đều.
    - *Exponential Decay* (**model nhỏ/nhẹ: `Haiku`, `Flash`, `Mini`, open-weights nhỏ**): **sụp dốc rất sớm ngay ở mật độ thấp**, rơi xuống đáy `7–15%`.
  - Cơ chế lỗi dịch chuyển từ *sửa đổi sai (modification)* sang **bỏ quên hoàn toàn (omission)** dưới tải nhận thức cao, kèm **primacy bias** (ưu tiên chỉ thị đầu, bỏ quên phần sau).
- **2. Context Rot & Lost-in-the-Middle (Chroma 2025; Liu et al. 2023/2024; Du et al.):**
  - Trên cả 18 frontier models, độ chính xác trượt giảm đều rất sớm trước giới hạn token (ở bài kiểm tra hội thoại ~113K tokens — chỉ ~1/10 cửa sổ 1M).
  - **Tác động vị trí (U-shaped curve):** thông tin nằm ở giữa ngữ cảnh tụt hiệu năng **>30%**; khi cửa sổ lấp đầy `<50%`, model mất phần giữa; khi `>50%`, model bắt đầu quên cả phần đầu.
  - **Tác động độ dài thuần túy (Du et al.) & nhiễu (Chroma):** ngay cả khi model truy xuất đúng đoạn cần thiết và xóa toàn bộ token nhiễu thành khoảng trắng, **bản thân độ dài input vẫn làm suy giảm suy luận**. Chỉ 1 đoạn distractor gần giống đã giảm độ chính xác rõ rệt, và 4 distractor nhân bội thiệt hại.
  - **Hàm ý trực tiếp cho plan dài:** Nhét toàn bộ plan 20 task + code mẫu đầy đủ + tài liệu tham khảo vào cùng 1 prompt của model nhỏ chính là tự bơm "distractor" đẩy ràng buộc quan trọng vào vùng chết giữa cửa sổ.
- **3. Cascade Error & Plan Drift từ Chi tiết Kỹ thuật Cứng (Anthropic; Böckeler; Heym):**
  - **Anthropic (`harness-design-long-running-apps`):** Cảnh báo rõ lý do Planner không được đặc tả chi tiết kỹ thuật quá vụn từ đầu: *"if the planner tried to specify granular technical details upfront and got something wrong, the errors in the spec would cascade into the downstream implementation."*
  - **Birgitta Böckeler (martinfowler.com) & Kent Beck:** Thực nghiệm Kiro/spec-kit cho thấy đặc tả quá dày (ví dụ **16 acceptance criteria cho một bug nhỏ**) gây 2 lỗi đối nghịch đồng thời: (a) agent **phớt lờ** nhiều mục trong rừng Markdown (thậm chí đọc phần mô tả class có sẵn trong research rồi **code trùng lặp lại toàn bộ class đó**!), và (b) agent **tuân thủ quá máy móc** (overboard) theo điều khoản hiến pháp/kế hoạch đến mức phá cấu trúc. Kent Beck chỉ ra giả định sai của heavy upfront spec: mặc định rằng *không có gì mới được học ra trong lúc code*.
  - **Stale Line Numbers & Brittle Verbatim Code:** Trong đánh giá thực tế `obra/superpowers` (`lobehub.com/skills/obra-superpowers-writing-plans`), nhúng mã triển khai đầy đủ (complete implementation code) cho mọi bước làm plan phình to, tốn chi phí bảo trì và nhanh chóng lệch (stale) ngay khi Task 1 sửa số dòng hoặc đổi chi tiết chữ ký mà Task 3 phụ thuộc vào. Tương tự, **Augment Code** ghi nhận *static specs* trôi một chiều tích tụ drift qua từng vòng sinh mã.
- **4. "The Rule That Died" — Ranh giới giữa Văn xuôi và Công cụ Kiểm chứng (Heym Audit):**
  - Phân tích **1,133 commits trong 117 ngày**: quy tắc toàn cục dạng văn xuôi (*"file max 300 lines"*) tồn tại qua cả 17 bản sửa spec nhưng vẫn bị vi phạm ở **31% file (85/272 file, có file phình quá 4,500 dòng)** vì không một edit đơn lẻ nào tự nhận thấy mình vi phạm thuộc tính tổng hợp.
  - Ngược lại, **3 quy tắc đạt 100% tuân thủ** đều có đặc điểm: (1) chỉ đích danh đường dẫn file/component, (2) nêu rõ đích đến thay thế (đừng chỉ cấm "không làm X", phải nói "đặt vào thư mục Y"), và (3) kiểm chứng cục bộ được ngay trong phạm vi 1 màn hình edit.
- **5. Multi-Turn Anchoring & Degradation (Laban et al. 2025; SlopCodeBench):**
  - **Laban et al. (May 2025):** Khi yêu cầu bị chia mảnh qua nhiều lượt thiếu rõ ràng (sharded multi-turn) so với đặc tả gọn đầy đủ trong 1 lượt (`FULL`), hiệu năng 15 LLM hàng đầu giảm trung bình **`39%`** (`-15%` aptitude, **`+112%` unreliability**). Khi gộp đủ thông tin (`CONCAT`), điểm hồi phục về **`95.1%`** của `FULL` (model nhỏ như `Claude 3 Haiku`, `Llama 3.1 8B` tụt sâu hơn một chút: `86–92%`). Nguyên nhân: agent chốt giải pháp quá sớm và bám chặt giả định sai của chính mình.
  - **SlopCodeBench (`arXiv:2603.24755v1`):** Prompt kiểu "anti-slop" hay "plan-first" chỉ nâng chất lượng khởi đầu; qua nhiều vòng mở rộng lặp lại trên chính mã của mình, sự bào mòn kiến trúc (structural erosion) vẫn quay lại nếu thiếu rào chắn cấu trúc và kiểm chứng độc lập.

### Implications for TDQ Workflow
- **Quy tắc mật độ tối đa cho model nhỏ:** Một Task Card nạp cho `tdq-implementer` (nhất là `flash`/`haiku`/`mini`) phải giới hạn nghiêm ngặt mật độ ràng buộc (khuyến nghị **≤ 5–7 ràng buộc cục bộ có thể kiểm chứng ngay trong task**; không bơm toàn bộ `spec.md` hay toàn bộ `plan.md` của các task khác vào context của worker).
- **Cấm số dòng cứng (hardcoded line numbers) làm neo duy nhất:** Thay bằng **tên file chính xác + tên symbol (class/function/method)** và ranh giới thay đổi; chỉ ghi số dòng như gợi ý tham khảo khi cần, hoặc bắt buộc worker xác định lại qua `read_file`/`LSP`.
- **Không dùng văn xuôi để ép thuộc tính toàn cục:** Những luật như `<= 50 dòng/hàm`, `không dead code`, `coverage`, `format` phải kiểm bằng linter/script/QC tự động thay vì lặp đi lặp lại trong prose của mọi task card.
- **Tránh vòng hỏi-đáp phân mảnh trong lúc implement:** Toàn bộ thông tin quyết định kết quả của 1 task phải được **đóng gói hoàn chỉnh (self-contained, single-shot contract)** ngay từ đầu task để tránh hố `-39%` của sharded multi-turn.

---

## Góc nhìn 3: Cấu trúc Task-Card & Đặc tả Thực thi Tối ưu (Pass@1 trên Mỗi Token)

### Query
- `coding agent specification structure contract-first interface signature test oracle vs pseudocode pass@1 benchmark`
- Trích xuất trực tiếp: `https://arxiv.org/html/2610.38214v1`

### Sources / URLs
- Skeleton Coding (`arXiv:2610.38214v1`) — *Program Structure as a Specification for Agents*: https://arxiv.org/html/2610.38214v1
- 52 AI Coding Benchmarks (DEV Community, empirical study): https://dev.to/greg_c6450ed3e296e7/we-ran-52-ai-coding-benchmarks-heres-every-uncomfortable-thing-we-found-d72
- Augment Code — *Spec + TDD: The Combination That Actually Produces Shippable AI Code*: https://www.augmentcode.com/guides/spec-tdd-shippable-ai-generated-code
- O'Reilly Radar — *Why AI Coding Agents Still Need Clear Specs*: https://www.oreilly.com/radar/why-ai-coding-agents-still-need-clear-specs
- Contract-First Development (Cole Medin Knowledge Base): https://github.com/coleam00/cole-medin-knowledge-base/blob/main/concepts/contract-first.md
- ProjDevBench (`arXiv:2602.01655v1`) — *Benchmarking AI Coding Agents on End-to-End Project Development*: https://arxiv.org/html/2602.01655v1
- Last Secure Code Benchmark (LSCBench review): https://dev.to/gabrielanhaia/coding-agents-pass-up-to-91-of-tasks-in-a-new-benchmark-at-most-25-are-also-secure-1oib
- Spec-Driven Development: Giving AI Coding Agents a Contract, Not a Guess: https://www.linkedin.com/pulse/spec-driven-development-giving-ai-coding-agents-contract-8ua2f

### Key Findings
- **1. Structural Specification (Skeleton + Contracts + Invariants) Đè Bẹp Behavioral Prose (`Skeleton Coding`, `arXiv:2610.38214v1`):**
  - So sánh trực tiếp giữa **Behavioral Specs** (mô tả hành vi, ví dụ I/O, thậm chí có cả binary oracle để truy vấn) và **Structural Specs** (bộ khung file + chữ ký hàm/signatures + local contracts + global invariants):
    - Trên **SCBench**: Structural specs nâng pass rate trung bình từ **`72% -> 89%`** (+17 pp).
    - Trên **SDDBench**: Structural specs nâng pass rate trung bình từ **`29.0% -> 74.2%`** (+45.2 pp), trong khi **behavioral specs tốt nhất chỉ tăng tối đa `9.4` điểm phần trăm**.
    - Trên **ProgramBench** (ngay cả khi agent được cấp full oracle binary — tức đặc tả hành vi đầy đủ 100%): thêm skeleton có **local contracts** vẫn tăng relative pass rate thêm **`+10.9%`** (`64.0% -> 70.9%`); nâng lên skeleton có **global invariants** giảm test error **`27.0%` tương đối** (`36.0% -> 26.3%`).
  - **Tác động kép lên Chất lượng Mã (Code Erosion):** Đặc tả bằng **signature + ranh giới hàm** giảm độ bào mòn mã (*code erosion*) từ `0.66 -> 0.56` (SCBench) và `0.41 -> 0.24` (SDDBench), đồng thời giảm verbosity. Ngược lại, **đặc tả thuần hành vi lại làm tăng code erosion** lên `0.73` và `0.43`!
  - **Khảo sát độ chi tiết theo lát cắt (Nested Detail Levels):** Bài báo thử rút gọn tài liệu kiến trúc qua 5 tầng (*components → state → collaborations → layout → per-file sketches*) và thử giữ lại `25% / 50% / 75%` local contracts xếp hạng theo độ phức tạp hàm (callable complexity) — khẳng định chiến lược **tập trung đặc tả sâu vào các hàm/boundary có độ phức tạp cao** thay vì trải đều chữ nghĩa vào code boilerplate.
- **2. Contract-First + AST Compression + Cấm Retry Mù (52 AI Coding Benchmarks):**
  - **Viết CONTRACT trước** cho mọi task chạm `>= 3` file: tốn chỉ `~$0.15` để sinh contract nhưng **tiết kiệm `47–54%` chi phí toàn task**, hoàn vốn ngay từ lần chạy đầu.
  - **Nén ngữ cảnh file bằng AST extraction (chỉ giữ signatures/interfaces):** giảm **`91%` token** với **0% suy giảm chất lượng**.
  - **Retry loops làm tụt chất lượng:** vòng tự sửa (retry) không có hợp đồng/kiểm chứng rõ làm chất lượng rơi từ **`9/10 -> 6/10`** và tốn chi phí **`2×`** vì model viết lại cả file và làm rụng mất những đoạn đang đúng.
  - **Contract tốt thay thế Review đắt đỏ:** `Sonnet + CONTRACT tốt` đã đạt `9.8/10`, không cần thêm vòng review bằng Opus khi hợp đồng đầu vào đủ sắc nét.
- **3. Test Oracle & Chống Tự Xác Nhận (Spec + TDD; Kent Beck; LSCBench; ProjDevBench):**
  - Kent Beck cảnh báo: *"The genie doesn't want to do TDD. It wants to write the code and then write tests that pass."* Nếu để model yếu tự suy diễn cả code lẫn test từ văn xuôi mơ hồ, nó tạo ra **self-confirming tests** (test chỉ xác nhận bug mà chính nó vừa viết).
  - **LSCBench:** Các coding agent pass tới **`91%`** bài test chức năng nhưng tối đa chỉ **`25%`** pass bài test bảo mật vì spec chỉ mô tả happy-path chức năng và không nêu rõ ràng buộc an ninh/misuse cases.
  - **ProjDevBench (`arXiv:2602.01655v1`):** `42%` lỗi đến từ sai logic/edge-case (`wrong answer`), `14%` từ sai độ phức tạp thuật toán (`TLE`). Mức sụp đổ khi đi từ sửa repo có sẵn sang xây từ đầu rất mạnh ở các hệ thống yếu cấu trúc (`Sonnet 4.5 + Copilot`: `71.10 -> 36.63`; `Gemini CLI`: `74.57 -> 35.53`).
  - **O'Reilly Radar:** Trong pipeline đa agent (`Agent A -> Agent B`), độ mơ hồ ở contract bị khuếch đại qua từng tầng (*compounding drift*). Vì vậy điểm hòa vốn của đặc tả dịch mạnh về phía **strongly-typed handoff contract** cho công việc xác định (CRUD, API, refactor có boundary rõ), trong khi công việc khám phá (exploratory/research) nên giữ khung biên (boundaries) thay vì khóa bước chi tiết.

### Implications for TDQ Workflow
- **Công thức Artifact đạt ROI cao nhất cho Task-Card của `tdq-plan`:**
  1. **Target & Scope Boundary:** đường dẫn file chính xác (tạo mới / sửa / cấm đụng) + `Non-goals`.
  2. **Structural Skeleton (Contract-First):** chữ ký hàm/class/type/CLI flag chính xác (`signature` + `input/output contract` + `error/edge-case contract`) + **Global/Local Invariants** ngắn gọn (thay thế đoạn văn xuôi dài và thay thế việc chép nguyên thân hàm).
  3. **Concrete Before/After Example (1 ví dụ mini nếu có transform/protocol):** 1 cặp input→output mẫu cụ thể cho case khó/biên.
  4. **Locked Test Oracle (Red → Green):** tên file test, danh sách test case cụ thể (happy path + edge case + negative/security case) và **lệnh chạy kiểm chứng cố định** (proving command) kèm luật *test ratchet* (không được xóa/nới assertion để làm xanh test).
  5. **Reuse / Reference Pointers (AST-level):** liệt kê rõ hàm/helper hiện có phải tái sử dụng (`path:symbol`) để ngăn model nhỏ tự bịa bản sao trùng lặp (lỗi Böckeler gặp phải ở `spec-kit`).
- **Phân bổ độ sâu theo độ phức tạp (Adaptive Granularity):** Tập trung viết local contract kỹ ở các hàm/nhánh logic phức tạp nhất hoặc điểm nối giữa nhiều file (`>= 3` file), còn boilerplate đơn giản chỉ cần signature + pointer.

---

## Góc nhìn 4: Mô thức Agentic Workflow Hiện đại về Tách Reasoning khỏi Execution

### Query
- `Anthropic Building Effective Agents Effective harnesses for long-running agents spec-driven development superpowers coding workflow`
- `obra superpowers writing-plans subagent-driven-development coding agent plan granularity exact file paths complete code`
- `"Anthropic" "Building Effective Agents" orchestrator-workers evaluator-optimizer workflow patterns`
- Trích xuất trực tiếp: `https://www.anthropic.com/research/harness-design-long-running-apps`

### Sources / URLs
- Anthropic Engineering — *Building Effective Agents* (Orchestrator-Workers, Evaluator-Optimizer): https://www.anthropic.com/research/building-effective-agents
- Anthropic Engineering — *Effective harnesses for long-running agents*: https://www.anthropic.com/research/effective-harnesses-for-long-running-agents
- Anthropic Engineering — *Harness design for long-running apps*: https://www.anthropic.com/research/harness-design-long-running-apps
- Anthropic Engineering — *Scaling Managed Agents: Decoupling the brain from the hands*: https://www.anthropic.com/research/managed-agents
- Addy Osmani — *Long-running Agents* & *How to write a good spec for AI agents*: https://addyosmani.com/blog/long-running-agents · https://addyo.substack.com/p/how-to-write-a-good-spec-for-ai-agents
- obra/superpowers — *writing-plans* & *subagent-driven-development*: https://github.com/obra/superpowers · https://www.verdent.ai/guides/what-is-superpowers-ai-coding-framework · https://lobehub.com/skills/obra-superpowers-writing-plans · https://github.com/obra/superpowers/issues/1120

### Key Findings
- **1. Tiến hóa 3 Thế hệ Harness của Anthropic:**
  - **Thế hệ 1 — Building Effective Agents:** Tách rõ *workflows* (vòng điều khiển xác định bằng code) và *agents*. Hai mẫu cốt lõi cho coding: **Orchestrator-Workers** (Planner phân rã động và giao subtask) + **Evaluator-Optimizer** (tách người sinh và người chấm độc lập theo rubric/test). Nguyên tắc vàng: *"find the simplest solution possible, and only increase complexity when needed."*
  - **Thế hệ 2 — Effective Harnesses for Long-Running Agents:** Tách **Initializer Agent** (chạy 1 lần dựng môi trường, `init.sh`, `feature-list.json`) và **Coding Agent** (mỗi phiên chỉ làm **1 feature tăng dần**, chạy test, ghi `claude-progress.txt`, commit sạch). Đặt **Test Ratchet** (cấm xóa/sửa test đang fail). Cốt lõi: *"state lives outside the agent's context — the agent is amnesiac, the filesystem isn't."*
  - **Thế hệ 3 — Planner + Generator + Evaluator Sprint Contract (`harness-design-long-running-apps` & `managed-agents`):**
    - **Planner** chỉ viết đặc tả cấp sản phẩm & kiến trúc/deliverables ở mức cao — **chủ đích KHÔNG khóa chi tiết cài đặt vụn từ đầu** để tránh lỗi dây chuyền (cascade error).
    - Trước mỗi sprint/task, **Generator và Evaluator đàm phán/chốt Sprint Contract** (chi tiết triển khai cục bộ + hành vi kiểm thử được) — tức áp dụng **Just-In-Time (JIT) granularity** thay vì chi tiết hóa cứng toàn bộ ngay từ bước 0.
    - **Nguyên lý "Harness Assumptions Expire":** Mọi thành phần trong harness đều mã hóa một giả định về *điều model hiện tại chưa tự làm được*. Ví dụ: `Sonnet 4.5` mắc *"context anxiety"* (tự kết thúc sớm khi sắp đầy context) nên bắt buộc phải reset context giữa phiên; nhưng sang `Opus 4.5` hiện tượng này biến mất, biến cơ chế reset cứng thành "dead weight". **Hệ quả ngược lại cũng đúng:** khi hạ xuống model nhỏ (`Haiku`/`Flash`/`Mini`), những giả định harness có thể lược bỏ ở `Opus` lại trở thành **bắt buộc** (context isolation, cấu trúc task nhỏ, kiểm chứng cưỡng bức).
- **2. Đối lập & Tổng hợp với `obra/superpowers` (`writing-plans` + `subagent-driven-development`):**
  - **Điểm mạnh đã chứng minh của Superpowers:**
    - Chia nhỏ cực sắc thành bite-sized tasks (`2–5 phút/task`) trong git worktree cô lập, mỗi task chạy bằng **fresh subagent** (chống context rot triệt để).
    - Kỷ luật **Red-Green-Refactor TDD** nghiêm ngặt + **Two-stage Review** (Stage 1: Spec compliance → Stage 2: Code quality).
    - Giả định đối tượng đọc plan là *"một lập trình viên không có ngữ cảnh về codebase"* → buộc Planner làm lộ toàn bộ giả định ngầm ngay ở pha rẻ tiền (text) trước khi đụng code.
  - **Điểm yếu thực tế được cộng đồng báo cáo (Issue `#1120` & LobeHub Reviews):**
    - Viết **complete implementation code** trong mọi task của plan làm file plan quá dài, khó review, nhanh bị stale khi repo đổi giữa chừng.
    - Bắt buộc vòng lặp `Implementer -> Spec Reviewer -> Fix -> Re-review -> Quality Reviewer -> Fix -> Re-review` với mọi agent đều **cold-start** gây lãng phí khổng lồ cho các task cơ học đơn giản (ví dụ tạo file 5 dòng đã cho sẵn nội dung). Issue `#1120` kiến nghị phân tầng theo độ phức tạp (*tiering*): gộp 1 pass review hoặc xử lý trực tiếp với task cơ học, dành full loop cho task có quyết định thiết kế / tích hợp.
- **3. Ba Tầng Biên Giới của Addy Osmani (Three-Tier Boundaries):**
  - Đưa thẳng vào spec/plan 3 danh mục rõ ràng cho agent: **Always** (bắt buộc làm, ví dụ chạy test command X), **Ask First / Escalate** (khi gặp mâu thuẫn với thực tế codebase thì dừng báo Planner, không tự bịa), **Never** (cấm đụng file ngoài scope, cấm sửa test để làm xanh, cấm thêm dependency ngoài plan).

### Implications for TDQ Workflow
- TDQ đang đứng ở vị trí rất đẹp để tổng hợp điểm mạnh của cả **Anthropic** (Planner cấp kiến trúc + Sprint/Task Contract vừa đủ + State trên disk + Harness thích nghi theo bậc model) và **Superpowers** (Fresh subagent per task + Worktree isolation + Red-Green TDD + Explicit paths), đồng thời **tránh được cả hai thái cực chết người**:
  - Tránh thái cực **Under-spec** (plan quá chung chung kiểu "implement feature X" khiến model nhỏ tự đoán kiến trúc và rơi vào hố `-39%` hoặc drift).
  - Tránh thái cực **Over-spec cứng** (nhồi full verbatim code + line numbers dễ stale + 50 ràng buộc văn xuôi khiến model nhỏ dính *Exponential Decay* của IFScale và *Cascade Error* của Anthropic).

---

## Ma trận Khuyến nghị Thiết kế cho TDQ (`tdq-plan` & `tdq-implementer`)

### 1. Điều chỉnh Độ chi tiết Plan theo Bậc Model Thực thi (Model-Tier Adaptive Plan)

| Thành phần trong Task Card | Executor Mạnh (`Opus` / `Pro` / `GPT-5.x`) | Executor Bậc trung (`Sonnet` / `Mid`) | Executor Bậc thấp (`Haiku` / `Flash` / `Mini` / Small OSS) |
| :--- | :--- | :--- | :--- |
| **Kích thước 1 Task** | 1 module/vertical slice (2–5 file) | 1–3 file, 1 hành vi rõ | **1 lát cắt mỏng (1–2 file, 1–3 hàm, ≤ 150 LOC thay đổi)** |
| **Neo vị trí (Anchors)** | Tên file + tên symbol chính | Tên file + symbol + điểm gọi (`callers`) | **Đường dẫn file chính xác + tên symbol chính xác + symbol tái sử dụng (`reuse`)** (KHÔNG dựa vào line numbers cố định) |
| **Đặc tả Logic** | Deliverable + invariants + edge cases | Structural skeleton (signatures + contracts) | **Structural Skeleton đầy đủ**: chữ ký hàm/type, input/output contract, bảng edge-case/error ngắn, 1 ví dụ I/O cho case khó; **KHÔNG viết full verbatim body** trừ boilerplate/schema/regex cực dễ sai |
| **Mật độ ràng buộc cục bộ** | Thoải mái (hỗ trợ tốt) | ≤ 10 ràng buộc/task | **Bắt buộc ≤ 5–7 ràng buộc cục bộ** (chống Exponential Decay của IFScale); ràng buộc toàn cục giao cho linter/test script |
| **Test Oracle (Red → Green)** | Spec test scenario + proving command | Test case list + proving command | **Test file đích + danh sách test case cụ thể (input → expected + 1 negative/security case) + lệnh chạy cố định + Test Ratchet** |
| **Ngữ cảnh nạp cho Worker** | Plan + file liên quan | Task card + file liên quan (AST summary cho file phụ) | **Fresh subagent chỉ nhận ĐÚNG 1 Task Card + danh sách file cần đọc tối thiểu** (cấm nhồi toàn bộ `spec.md` hay lịch sử các task trước) |
| **Cơ chế Escalate (Stop-the-Line)** | Tự xử lý sai lệch nhỏ | Hỏi khi đổi public interface | **Bắt buộc dừng & trả về `BLOCKED` cho Planner** nếu thực tế file/symbol lệch contract thay vì tự chế workaround |

### 2. Năm Quy tắc "Nên làm / Cấm làm" Rút ra từ Thực nghiệm

1. **NÊN viết Structural Skeleton thay vì Prose dài hoặc Full Code:** Ưu tiên `file path` + `function/class signature` + `local contract` + `global invariants` (`Skeleton Coding`: +23 đến +58 pp trên model nhỏ, giảm code erosion). Chỉ đưa snippet ngắn cho *contract/schema/regex/wire-format* dễ sai cú pháp; **tránh** chép cả thân hàm dài vì dễ gây cascade error và stale drift.
2. **NÊN tách rạch ròi "Luật cục bộ trong Task" và "Luật toàn cục trong Tooling":** Theo audit 1,133 commits của Heym, chỉ đặt vào Task Card các quy tắc đánh giá được ngay trong 1 màn hình edit (chỉ rõ tên file + nơi đặt thay thế). Mọi chuẩn về số dòng, lint, type, dead code, security scan phải kiểm bằng lệnh tự động / QC gate.
3. **NÊN dùng Just-In-Time (JIT) Plan Reconciliation giữa các sóng (waves):** Thay vì khóa chết chi tiết triển khai của Task 8 trước khi Task 1 chạy, giữ `plan.md` ở mức **contract & skeleton ổn định**; nếu Task trước buộc phải đổi signature, cập nhật lại contract trước khi phát cho worker sau (Living Spec / Sprint Contract của Anthropic).
4. **CẤM vòng retry mù khi model nhỏ fail test:** Thực nghiệm 52 benchmarks cho thấy retry lặp mù làm tụt chất lượng (`9->6/10`) và tốn `2×` chi phí. Với model nhỏ trong TDQ, giới hạn **tối đa 1–2 lần sửa có chẩn đoán mới**; nếu vẫn fail → leo thang (escalate) lên model mạnh hơn hoặc trả về Planner chỉnh contract.
5. **CẤM quy trình review nặng giống nhau cho mọi độ khó (Anti-Ceremony Tiering):** Học từ `obra/superpowers#1120` và Böckeler: tách rõ task cơ học/đơn giản (gộp 1 pass verify tự động + check nhanh) khỏi task logic/tích hợp (full TDD + independent QC review) để không đốt context và latency vô ích.
