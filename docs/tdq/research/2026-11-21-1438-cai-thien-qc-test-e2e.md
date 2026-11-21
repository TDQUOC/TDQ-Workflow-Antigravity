# Nghiên cứu chuẩn ngành & plugin QA cho mô hình QC/E2E mới của TDQ

> **Tóm tắt dễ hiểu**
>
> - **Vấn đề ngành đang giải quyết:** Các pipeline kiểm thử nặng unit-test cô lập dễ rơi vào "mù mock" (unit pass nhưng ghép vào flow thật thì gãy), còn nếu dồn quá nhiều E2E cồng kềnh vào vòng lặp lập trình thì chậm, hay flaky và gây hội chứng "kêu sói" khiến dev bỏ qua lỗi.
> - **Đồng thuận chuẩn ngành 2025–2026:** Tách rạch ròi theo **chi phí – độ tin cậy – thời điểm chạy**: giữ vòng lặp dev siêu nhanh bằng kiểm thử theo tác động thay đổi (TIA / Risk-Based Smoke + Integration/Contract ít mock), chạy E2E trình duyệt bằng **Accessibility Tree Snapshot** (nhẹ token, locator ngữ nghĩa `getByRole`/ref thay CSS mong manh) và khóa cổng báo xong bằng quy tắc **"Evidence before claims"** (chỉ kết luận sau khi chạy lệnh và đọc exit code / output tươi).
> - **Giá trị trực tiếp cho TDQ:** Mô hình QC/E2E mới của TDQ nên bỏ checklist hàn lâm dài dòng để chuyển sang 3 lớp thực dụng: **(1) Planner tách Spec/Test Plan hành vi**, **(2) Fast Loop theo luồng chạm (TIA + Integration/Smoke)**, và **(3) Evidence-first Gate + Semantic Browser Snapshot**.

- **Request:** `2026-11-21-1438-cai-thien-qc-test-e2e`
- **Task:** `T1.3` (Research benchmark chuẩn ngành & QA plugin)
- **Thời gian thu thập:** `2026-11-21T15:13+07:00` – `2026-11-21T15:16+07:00`
- **Công cụ sử dụng:** `tdq-workflow-agy_tavily-primary` (`tavily_search`, `tavily_extract`) và `search_web` (fallback khi Tavily chạm hạn mức keyless hàng ngày `Retry after: 329s` / `1010s`).
- **Kho bằng chứng thô (raw extracts):**
  - [01-playwright-agents-and-mcp.txt](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/01-playwright-agents-and-mcp.txt)
  - [02-testing-trophy-pyramid-google-sizes.txt](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/02-testing-trophy-pyramid-google-sizes.txt)
  - [03-tia-risk-based-ci-gates.txt](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/03-tia-risk-based-ci-gates.txt)
  - [04-ai-qa-verification-and-browser-agents.txt](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/04-ai-qa-verification-and-browser-agents.txt)

---

## 1. Playwright Test Agents (`planner` / `generator` / `healer`) & Playwright MCP (`microsoft/playwright-mcp`)

### Truy vấn đã chạy
- `tavily_search`: `Playwright Test Agents planner generator healer microsoft playwright-mcp` (`2026-11-21T15:13:52+07:00`)
- `tavily_extract`: `https://playwright.dev/docs/test-agents` (`2026-11-21T15:14:12+07:00`)
- `search_web` (fallback khi Tavily hết hạn mức): `"microsoft/playwright-mcp" GitHub accessibility tree snapshot` & `"microsoft/playwright-mcp" "--caps" "browser_snapshot" "accessibility" tools list` (`2026-11-21T15:14:19+07:00`, `15:15:40+07:00`)

### Danh sách URL
- https://playwright.dev/docs/test-agents
- https://www.testmuai.com/blog/playwright-agents
- https://bug0.com/blog/playwright-mcp-changes-ai-testing-2026
- https://qaskills.sh/blog/mcp-for-qa-automation-guide-2026

### Trích đoạn chính
1. **Kiến trúc 3 agent tách vai rõ ràng** — nguồn `playwright.dev` ([01-playwright-agents-and-mcp.txt#L11-L17](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/01-playwright-agents-and-mcp.txt#L11-L17)):
   > "Playwright comes with three Playwright Test Agents out of the box: planner, generator and healer. These agents can be used independently, sequentially, or as the chained calls in the agentic loop."
   - **Planner** nhận yêu cầu + `seed.spec.ts` (khởi tạo fixtures, auth, global setup) → tự mở app thật và xuất Markdown test plan vào `specs/` ([L36-L59](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/01-playwright-agents-and-mcp.txt#L36-L59)).
   - **Generator** đọc `specs/*.md`, thao tác trực tiếp trên trình duyệt sống để **xác minh selector (`getByRole`) và assertion** rồi mới ghi mã test xác định (deterministic `.spec.ts`) vào `tests/` ([L67-L89](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/01-playwright-agents-and-mcp.txt#L67-L89)).
   - **Healer** chạy lại bước fail, kiểm tra UI hiện tại để vá locator/wait/data hoặc **skip test nếu đánh giá tính năng thật sự bị hỏng** ([L92-L107](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/01-playwright-agents-and-mcp.txt#L92-L107), [L145](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/01-playwright-agents-and-mcp.txt#L145)).
2. **Playwright MCP & Accessibility Tree Snapshots** — nguồn `bug0.com` & `search_web` ([01-playwright-agents-and-mcp.txt#L149-L174](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/01-playwright-agents-and-mcp.txt#L149-L174)):
   > "The open-source Playwright MCP server (@playwright/mcp npm package) exposes 25+ tools for browser control through structured, LLM-friendly APIs. No vision models required. No screenshot processing. Just accessibility tree snapshots."
   - Tool cốt lõi `browser_snapshot` trả về cây ngữ nghĩa (`role`, `name`, `state`, mã tham chiếu tạm `[ref=e5]`) thay vì ảnh pixel hoặc HTML thô, giúp agent dùng locator ổn định theo vai trò (`getByRole`), tiết kiệm token và chạy được trên model text thuần.
   - Các capability mở rộng (`vision`, `tracing`, `network`, `storage`, `devtools`) được bật chọn lọc qua `--caps=...` thay vì bật mặc định gây phình ngữ cảnh ([L174](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/01-playwright-agents-and-mcp.txt#L174)).

### Điểm rút ra cho mô hình QC/E2E mới của TDQ
- **Tách Planner khỏi Executor và xuất test xác định (deterministic):** TDQ không nên để AI vừa đoán flow vừa tự đánh dấu đạt bằng lời. Cần tách bước lập kịch bản hành vi (`specs/` / DoD theo luồng người dùng) khỏi bước chạy kiểm chứng thật trên môi trường đã seed sẵn (`seed` fixture).
- **Ưu tiên Accessibility Tree Snapshot hơn screenshot toàn trang:** Khi QC duyệt web app qua MCP, dùng snapshot ngữ nghĩa + ref để giảm chi phí token và tránh lỗi chọn nhầm CSS class động; chỉ bật screenshot/tracing/network khi debug lỗi thực tế.
- **Cảnh giác với vòng tự sửa (Healer):** Không để agent tự ý "chữa" assertion cho xanh giả; nếu chức năng hỏng thật phải fail hoặc đánh dấu chặn rõ ràng.

---

## 2. Testing Trophy (Kent C. Dodds), Practical Test Pyramid (Martin Fowler / Ham Vocke) & Google Test Sizes

### Truy vấn đã chạy
- `tavily_search`: `"Testing Trophy" "Kent C. Dodds" "Practical Test Pyramid" Martin Fowler Google "Test Sizes" Small Medium Large` (`2026-11-21T15:13:55+07:00`)
- `tavily_extract`: `https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications` (`2026-11-21T15:14:12+07:00`)
- `search_web` (fallback): `"Practical Test Pyramid" site:martinfowler.com`, `Google Testing Blog "Test Sizes" Small Medium Large`, `"Just Say No to More End-to-End Tests" 70/20/10` (`2026-11-21T15:14:22+07:00` – `15:15:12+07:00`)

### Danh sách URL
- https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications
- https://martinfowler.com/articles/practical-test-pyramid.html
- https://testing.googleblog.com/2010/12/test-sizes.html
- https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html
- https://web.dev/articles/ta-strategies
- https://bug0.com/knowledge-base/testing-pyramid

### Trích đoạn chính
1. **Testing Trophy & ROI theo độ giống hành vi thật** — nguồn `kentcdodds.com` ([02-testing-trophy-pyramid-google-sizes.txt#L79-L80](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/02-testing-trophy-pyramid-google-sizes.txt#L79-L80), [L148-L156](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/02-testing-trophy-pyramid-google-sizes.txt#L148-L156)):
   > "The more your tests resemble the way your software is used, the more confidence they can give you."
   > "Remember, it's all about getting a good return on your investment where 'return' is 'confidence' and 'investment' is 'time.'"
   - Kent C. Dodds phân biệt rõ: Unit test dùng cho đơn vị cô lập hoặc đã mock collaborator; **Integration test kiểm tra nhiều đơn vị phối hợp với nhau (ít mock hơn, ví dụ mock ở biên HTTP bằng MSW)**; E2E chạy hầu như không mock ([L75-L80](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/02-testing-trophy-pyramid-google-sizes.txt#L75-L80), [L101](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/02-testing-trophy-pyramid-google-sizes.txt#L101)).
   - Justin Searls được trích dẫn lại như kim chỉ nam chống tranh cãi hình học vô bổ ([L120](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/02-testing-trophy-pyramid-google-sizes.txt#L120)):
     > "People love debating what percentage of which type of tests to write, but it's a distraction. Nearly zero teams write expressive tests that establish clear boundaries, run quickly & reliably, and only fail for useful reasons. Focus on that instead."
2. **Practical Test Pyramid (Ham Vocke / Martin Fowler)** — nguồn `martinfowler.com` & `web.dev` ([02-testing-trophy-pyramid-google-sizes.txt#L254-L270](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/02-testing-trophy-pyramid-google-sizes.txt#L254-L270)):
   - Giữ 2 nguyên tắc cốt lõi từ Mike Cohn: **(1) Viết test ở nhiều mức độ chi tiết khác nhau; (2) Càng lên tầng cao càng phải viết ít test lại.**
   - Đưa vào **Contract Tests** (kiểm tra ranh giới giao tiếp API/dịch vụ) để không phải dựng môi trường E2E nặng nề chỉ để bắt lỗi lệch schema, đồng thời cảnh báo phản mẫu **"Test Ice Cream Cone"** (quá nhiều E2E chậm và dễ vỡ).
3. **Google Test Sizes (`Small` / `Medium` / `Large`) & Cảnh báo về E2E** — nguồn `testing.googleblog.com` ([02-testing-trophy-pyramid-google-sizes.txt#L272-L284](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/02-testing-trophy-pyramid-google-sizes.txt#L272-L284)):
   - Google phân loại theo **tài nguyên và ràng buộc chạy** thay vì tên gọi mơ hồ:
     - **Small:** 1 process, 1 thread, 1 máy; cấm network/DB/file system/sleep; hermetic, chạy ms–giây (~70–80%).
     - **Medium:** đa luồng, dùng DB/file cục bộ hoặc `localhost`, kiểm tra tương tác giữa các thành phần lân cận (~20%).
     - **Large:** không giới hạn tài nguyên/mạng/hệ thống thật, non-hermetic, chạy phút–giờ (~10%).
   - Mike Wacker (*Just Say No to More End-to-End Tests*) chỉ ra 3 lỗi chết người khi lạm dụng E2E: **vòng phản hồi chậm**, **khó debug vì tính chất hộp đen**, và **flakiness gây hội chứng "cry wolf"** khiến developer mất niềm tin vào kết quả fail.

### Điểm rút ra cho mô hình QC/E2E mới của TDQ
- **Chuyển trọng tâm từ "unit mock-heavy" sang "Integration + Contract + Focused E2E":** TDQ cần bắt buộc mỗi task không chỉ chứng minh hàm đơn lẻ chạy đúng với mock mà phải kiểm chứng biên giao tiếp thật (CLI subprocess, file I/O thật, DB/localhost endpoint thật — tức tầng `Medium` / Integration).
- **Giới hạn E2E (`Large`) ở đúng các luồng sống còn (critical journeys):** Giữ tỷ lệ E2E gọn, hermetic tối đa (dùng seed/fixture cô lập, tránh dùng chung state gây flaky) để QC không bị kẹt hàng chục phút hay gãy vặt.

---

## 3. Risk-Based Testing, Test Impact Analysis (TIA) & CI Staged Gates

### Truy vấn đã chạy
- `tavily_search`: `"Test Impact Analysis" OR "risk-based testing" "changed" E2E CI staged gates smoke regression pytest` (`2026-11-21T15:13:58+07:00`)

### Danh sách URL
- https://engineering.instawork.com/test-impact-analysis-the-secret-to-faster-pytest-runs-e44021306603
- https://totalshiftleft.com/blog/regression-testing-strategy-enterprise-guide
- https://circleci.com/blog/regression-testing-and-how-to-automate-it-with-ci
- https://realpython.com/ref/software-engineering-glossary/smoke-test
- https://www.minitap.ai/magazine/smoke-testing-vs-regression-testing
- https://www.cloudbees.com/blog/the-smoke-sanity-and-regression-testing-triad

### Trích đoạn chính
1. **Test Impact Analysis (TIA) với `pytest` + `Testmon`** — nguồn `engineering.instawork.com` ([03-tia-risk-based-ci-gates.txt#L8-L13](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/03-tia-risk-based-ci-gates.txt#L8-L13)):
   > "TIA works by analyzing the code changes in a pull request and identifying the tests that are impacted by these changes. It then runs only these affected tests, skipping the rest of the test suite. Testmon is a tool that implements TIA using coverage data and advanced techniques to map dependencies between code and tests."
   - Kết quả thực tế tại Instawork: **giảm một nửa thời gian chạy test trung vị (2x faster)** mà vẫn bám sát vùng code thay đổi.
2. **Risk-Based Selection & Tiered Execution** — nguồn `totalshiftleft.com` & `circleci.com` ([03-tia-risk-based-ci-gates.txt#L20-L37](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/03-tia-risk-based-ci-gates.txt#L20-L37)):
   - `totalshiftleft.com`: 60–70% công sức hồi quy bị lãng phí vào các bài test rủi ro thấp suốt 12 tháng không bắt lỗi nào; chọn test theo rủi ro bắt được **90% lỗi chỉ với 30% bộ test**, khi kết hợp 4 trụ cột (Risk-based, Tiered execution, TIA, Suite hygiene) có thể giảm **70% chu kỳ hồi quy**.
   - `circleci.com`: chia rõ **Unit regression** (cổng đầu tiên mỗi commit) → **Selective regression** (chọn module/luồng bị ảnh hưởng cho PR/nhánh nhỏ, kèm lưu ý rủi ro bỏ sót phụ thuộc ẩn nếu TIA không đủ chính xác) → **Complete regression** (chỉ chạy toàn bộ trước release lớn).
3. **Kỷ luật giữ Smoke Suite gọn & không flaky** — nguồn `realpython.com` & `minitap.ai` ([03-tia-risk-based-ci-gates.txt#L57-L77](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/03-tia-risk-based-ci-gates.txt#L57-L77)):
   > "Bloat. Smoke suites accrete tests until they take ten minutes to run and lose their fast-feedback value. The discipline is deletion. If a check does not gate the rest of the pipeline, it belongs in the full regression suite, not the smoke suite."
   > "Flakiness. A flaky test in the smoke suite is worse than no smoke suite at all, because it trains the team to retry-and-ignore the gate."
   - Pattern thực dụng trên Python: gắn marker `@pytest.mark.smoke` và chạy `pytest -m smoke --tb=short` làm cổng fail-fast trước khi tốn tài nguyên chạy full suite; nếu smoke fail thì dừng ngay.

### Điểm rút ra cho mô hình QC/E2E mới của TDQ
- **Phân tầng rõ 2 nhịp chạy cho QC TDQ:**
  - **Vòng lặp dev / task (`Quick / Affected Gate`):** Chỉ chạy `smoke` marker + các test/E2E thuộc **luồng bị chạm** (tra map thay đổi theo file/module hoặc `affected` từ dependency/Graphify), fail-fast trong vài chục giây tới vài phút.
  - **Cổng hợp nhất / thay đổi nền tảng (`Full Regression Gate`):** Chỉ kích hoạt full E2E hoặc full suite khi chạm lõi dùng chung, đổi schema/config toàn cục hoặc trước khi merge nhánh lớn.
- **Kỷ luật cắt tỉa Smoke Suite:** Mọi check flaky hoặc không có giá trị chặn pipeline phải bị loại khỏi vòng chạy nhanh, tránh tình trạng càng ngày bộ QC càng phình to thành 10+ phút.

---

## 4. AI QA / Coding-Agent Verification Plugins & Browser Agent Frameworks

### Truy vấn đã chạy
- `tavily_search`: `"browser-use" OR "browserbase/stagehand" OR "vercel-labs/agent-browser" AI browser testing verification` (`2026-11-21T15:14:02+07:00`)
- `tavily_extract`: `https://github.com/vercel-labs/agent-browser` (`2026-11-21T15:14:12+07:00`)
- `search_web` (fallback): `"obra/superpowers" "verification-before-completion" "Iron Law" "Red Flags" "Gate Function" verbatim`, `"browserbase/stagehand" act extract observe self-healing cache "browser-use"`, `"browser-use/browser-use" CDP DOM accessibility screenshot architecture python` (`2026-11-21T15:14:15+07:00` – `15:15:45+07:00`)

### Danh sách URL
- https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md
- https://github.com/vercel-labs/agent-browser
- https://github.com/browserbase/stagehand

### Trích đoạn chính
1. **`obra/superpowers` (`verification-before-completion`) — "Evidence before claims, always"** ([04-ai-qa-verification-and-browser-agents.txt#L266-L297](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/04-ai-qa-verification-and-browser-agents.txt#L266-L297)):
   > "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE"
   > "If you haven't run the verification command in this message, you cannot claim it passes."
   - **Gate Function 5 bước siêu gọn:** `1. IDENTIFY` (lệnh nào chứng minh điều này?) → `2. RUN` (chạy trọn vẹn, tươi mới) → `3. READ` (đọc full output, kiểm exit code và số lỗi) → `4. VERIFY` (output có khớp claim không?) → `5. ONLY THEN` mới được báo kết quả.
   - **Chống ảo giác & tin lời subagent mù quáng:** Bảng *Common Failures* quy định `Agent completed` đòi hỏi đối chiếu **VCS diff**, không tin câu tự báo `"success"`; `Bug fixed` đòi hỏi tái hiện **triệu chứng gốc pass**; `Red Flags` chặn ngay các từ mơ hồ (`"should"`, `"probably"`, `"seems to"`).
2. **`vercel-labs/agent-browser` — CLI Accessibility-Ref + Fail-Closed Click + Tích hợp Audit** ([04-ai-qa-verification-and-browser-agents.txt#L125-L199](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/04-ai-qa-verification-and-browser-agents.txt#L125-L199)):
   > "A click fails, instead of reporting success, when the target is hidden, disabled, outside the viewport, or covered by another element such as a consent banner. Dismiss the covering element, take a new snapshot, and retry."
   - Trình duyệt chạy qua daemon CDP giữ phiên mở giữa các lệnh CLI (`--session`); `snapshot` xuất cây accessibility gọn nhẹ với ref `@e1`; bắt buộc lấy snapshot mới sau mỗi lần DOM đổi; tích hợp sẵn nhóm lệnh kiểm chứng `diff`, `console`, `errors`, `trace`, `a11y`.
3. **`browserbase/stagehand` & `browser-use` — Lai giữa code xác định và AI tự phục hồi** ([04-ai-qa-verification-and-browser-agents.txt#L299-L314](file:///c:/Users/admin/Documents/Projects/TDQ-Workflow-Antigravity/docs/tdq/artifacts/2026-11-21-1438-cai-thien-qc-test-e2e/raw/04-ai-qa-verification-and-browser-agents.txt#L299-L314)):
   - **Stagehand** kết hợp code Playwright xác định với 3 primitive `act`, `extract` (ép schema Zod/Pydantic), `observe`, kèm **action caching** để tái chạy không tốn token và giữ độ ổn định khi DOM ít thay đổi.
   - **Browser Use** hợp nhất 3 kênh nhận thức qua CDP (`SimplifiedNode` DOM + `Accessibility.getFullAXTree` + screenshot có highlight thao tác) cho các luồng tự hành đa bước phức tạp.

### Điểm rút ra cho mô hình QC/E2E mới của TDQ
- **Áp dụng đúng "Gate Function 5 bước" thay cho checklist hành chính:** Thay vì bắt dev hoặc QC agent điền hàng chục mục lý thuyết, chỉ giữ một cổng cứng: mọi kết luận `PASS` phải đi kèm **lệnh đã chạy ở lượt hiện tại + exit code + triệu chứng/hành vi gốc pass + diff thực tế**; cấm hoàn toàn chữ `"có lẽ"` / `"should pass"` hoặc tin báo cáo chay từ subagent.
- **Fail-closed khi kiểm UI thật:** Hành động click/submit trên E2E phải kiểm tra trạng thái khả dụng (`visible`, `enabled`, không bị che) và đọc `console`/`errors` sau thao tác như cách `agent-browser` thiết kế.
- **Giữ E2E chạy theo cơ chế lai (Hybrid Deterministic + Semantic):** Dùng script xác định cho các bước lặp cố định và chỉ gọi semantic snapshot / AI repair khi cấu trúc UI thay đổi, có caching kết quả để vòng QC luôn nhanh.

---

## 5. Tổng hợp đối chiếu: Khung thiết kế đề xuất cho TDQ QC/E2E mới

| Trụ cột thiết kế | Chuẩn ngành tham chiếu | Điểm thay đổi cốt lõi cho TDQ |
| :--- | :--- | :--- |
| **1. Phạm vi & tỷ lệ kiểm thử** | Testing Trophy (`kentcdodds.com`), Practical Test Pyramid (`martinfowler.com`), Google Test Sizes (`testing.googleblog.com`) | Bớt dồn unit test mock nặng; đẩy trọng tâm vào **Integration / Contract test** (biên CLI, file, DB, API cục bộ) + số lượng ít nhưng sắc **Critical E2E (`Large`)** hermetic. |
| **2. Tốc độ & chọn vùng chạy** | TIA / `Testmon` (`instawork.com`), Tiered Gates (`circleci.com`, `totalshiftleft.com`), Smoke Discipline (`realpython.com`) | Chạy **Affected + Smoke (`<= vài phút`)** trên vòng lặp dev/task; dời **Full Regression** sang cổng merge/release hoặc khi chạm module lõi. Loại bỏ test flaky khỏi smoke. |
| **3. Cơ chế kiểm E2E trình duyệt** | Playwright Agents (`playwright.dev`), Playwright MCP (`bug0.com`), `agent-browser`, `stagehand` | Tách **Planner** (lập kịch bản luồng dùng thật) khỏi **Generator/Runner** (tạo/chạy kiểm chứng xác định); đọc UI bằng **Accessibility Tree Snapshot + ref** thay ảnh nặng token; kiểm thêm `console`/`errors` và fail-closed khi phần tử bị che. |
| **4. Kỷ luật bằng chứng QC** | `obra/superpowers` `verification-before-completion` | Bỏ các checklist học thuật rườm rà; áp dụng duy nhất **Iron Law + 5-step Gate Function**: định danh lệnh chứng minh → chạy tươi → đọc full output/exit code → đối chiếu diff/triệu chứng gốc → mới được báo `PASS`. |
