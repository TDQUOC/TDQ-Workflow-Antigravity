# Planner Rules (30 Invariants)

Apply these rules before, during, and after writing any TDQ plan. Detailed Per-Task Mini-Spec field templates live in [plan-template.md](plan-template.md).

## 1. Ground Before Drafting
1. Read target symbols, signatures, and call sites before writing a single task line — never invent file paths, symbol names, or line numbers from memory.
2. Inspect at least one related existing file or reference when drafting new modules or wiring interfaces.
3. Run `tdq_plan_scaffold.py --files <spec>` and `--refs <files>` (plus `--from-spec <spec>` on greenfield specs) to extract real AST + `§3c` anchors before writing Pass 2 details.
4. Keep prose in the user's `doc_lang`; keep code identifiers, CLI commands, and tool names verbatim.

## 2. Decomposition Thresholds (Split, Merge, Sweep)
5. Enforce Adaptive 3-Tier sizing: split monolithic tasks touching >300 LOC or mixing distinct concerns (e.g. parser vs CLI vs persistence); merge trivial 1-line edits in the same file unless isolated tests or ordering require separation.
6. Cap each task block at `<= 30` lines (`<= 35` hard limit enforced by `doc_lint` on post-cutoff plans); move shared constraints once to the top of the plan instead of repeating them per task.
7. Declare exactly one testable deliverable per task with concrete `Chạm:` paths — never split by arbitrary line ranges inside the same concern. <!-- i18n-allow -->
8. Use **Uniform Mechanical Sweep** (label `Uniform Mechanical Sweep`) only when editing `<= 6` homogeneous files following one identical pattern; use `dong-bo-chu-ky` when updating `<= 5` call sites after a signature change.
9. Escalate any `quick` lane code task touching `> 4` source files (excluding tests) to `full` lane before writing code.
10. Declare all parallel write conflicts upfront under `## Luật file nóng` and serialize via `Cần:` dependencies. <!-- i18n-allow -->

## 3. Contract-First & Ownership Map
11. For every plan with `>= 2` code tasks, open with shared `Ràng buộc toàn cục` and an `Ownership Map` table (`Contract | Owner Task & File | Consumers`) placed before `P1`. <!-- i18n-allow -->
12. Map every `§3c` contract/symbol and every `DÙNG` row in `spec §3b` to at least one owning task. <!-- i18n-allow -->
13. Write `Req: <spec sections>` and `Ngoài phạm vi:` (listing explicit `GIỮ NGUYÊN` invariants) in every full code task so an implementer never silently drops behavior or widens diffs. <!-- i18n-allow -->
14. Write `Giao tiếp: Consumes: ... | Produces: ...` with exact typed signatures or data schemas when tasks share interfaces. <!-- i18n-allow -->
15. Never assign two concurrent tasks in the same wave to edit overlapping files in `Chạm:`. <!-- i18n-allow -->

## 4. Zero-Ambiguity Banlist
16. Ban placeholders (`TBD`, `TODO`, `FIXME`, `...`, `etc.`, `"similar to"`, `"update as needed"`, `"tương tự"`, `"như cũ"`) anywhere in task specs, contracts, or assertions. <!-- i18n-allow -->
17. State exact edge cases and boundary inputs in `Ca góc hiểm & Assert:` (`empty`, `null`, `missing`, `invalid`). <!-- i18n-allow -->
18. State verifiable `EARS` acceptance criteria (`WHEN <trigger>, SYSTEM MUST <observable result>`) with concrete values or exit codes — never `"works correctly"` or `"handles errors"`.
19. Ban `ANTI-1` mocked-pass tests (patching away the system under test) and `ANTI-2` blind asserts (`assert True`, `assert x is not None`, `assert 1 == 1`) in `Test:` and `Tiêu chí:`. <!-- i18n-allow -->
20. Require `TDQ_LOG` timestamped logging (`TDQ_LOG=0` off) and real Red → Green test verification for every new or modified artifact.

## 5. Two-Pass Execution & 5-Question Semantic Self-Review
21. Always execute **Two-Pass Planning**: Pass 1 drafts header, `Ownership Map`, task DAG (`Chạm:`/`Cần:`/`Test:`), and runs `tdq_plan_scaffold.py --emit-cards`. <!-- i18n-allow -->
22. Pass 2 populates concise Per-Task Mini-Specs inside `30` lines/task using real anchors, then runs `--verify-plan`, `--check-wave`, and `doc_lint.py --pair`.
23. When fixing QC defects (`QCn.x`), draft compact `5`-field `R15-Compact` repair tasks instead of bloating or rewriting unrelated plan phases.
24. Keep references and `SKILL.md` pointers one-tier only: never create nested reference chains (`SKILL.md -> ref -> ref2`).
25. Answer ALL 5 **Semantic Self-Review** questions as PASS before presenting the plan to the user:
    - **Q1 (Isolation):** Can a lightweight subagent finish each task using ONLY its task card + declared files without searching unrelated modules?
    - **Q2 (Contracts):** Does every shared symbol or `§3c` signature have one clear owner in `Ownership Map` and matching `Consumes`/`Produces` types?
    - **Q3 (DAG & Waves):** Are all `Cần:` links acyclic and do same-wave tasks have disjoint `Chạm:` file sets? <!-- i18n-allow -->
    - **Q4 (Oracles):** Would each task's `Test:` and `Tiêu chí:` fail if the implementation returned a hardcoded dummy value? <!-- i18n-allow -->
    - **Q5 (Shape & Budget):** Are all code tasks within `<= 30` lines, exact header format `- [ ] **Tn.m** (eXm) ... — Test: ...`, and zero banned placeholders?
