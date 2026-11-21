# Report template
<!-- muc-luc-dong:
  Table of contents=7-13 · The execution steps=14-101 · The report shape=102-154 ·
  Check before presenting=155
-->

## Table of contents

- The execution steps
- The report shape
- Thời gian
- Check before presenting

## The execution steps

This is the whole of Part C of [SKILL.md](../SKILL.md) — moved here so the skill body does not
carry this branch on every call. On entering phase `report` you **must** read all four steps
below before writing the report; working from memory is banned.

<!-- doc-lint: allow R1 -->
7. Write `docs/tdq/reports/<slug>.md` — in the user's document language, with NO hard line
   limit; ~10-20 lines recommended. Write in plain, accessible language so any reader can
   understand it (`đơn giản, dễ hiểu`, `trực quan, đầy đủ thông tin`), explicitly stating:
   (1) before-request state/flow (`Trước request (trạng thái/flow)`),
   (2) after-request state/flow (`Sau request (trạng thái/flow)`),
   (3) what was tested (`Đã test gì`), and
   (4) actual test results (`Kết quả test`). Template: section `## The report shape` in this file.
   The timing table is **mandatory**: run `tdq_timing.py show` and paste the whole table into the
   report; never estimate the numbers yourself.

7b. **Both lanes** write the paired visual report `docs/tdq/reports/<slug>.html` from actual
   task, DoD, QC, output and limit evidence via [Archify lifecycle](archify-lifecycle.md),
   visually presenting the before/after state & flow, what was tested, and actual test results.
   Render with `--evidence-kind working-tree` for uncommitted sources (or `committed` for a verified clean revision); CLI has no `actual` evidence kind. Render and verify AFTER all Markdown edits: gate `set phase=idle` blocks if report manifest is missing or not current (unless bypassed via `--bo-qua-archify`). Verify before linking; unavailable/stale output gets a disclosed text fallback.

8. Close the books: tick the leftover boxes of BOTH kinds — the task boxes in each phase AND
   the Definition of Done boxes — change the plan header to HOÀN THÀNH, then run <!-- i18n-allow: canonical status value -->
   `tdq_finish.py --files <edited files> --log "<report summary>"` (working log + graphify).
   The two kinds are counted separately, and the DoD one is the one that gets forgotten: QC
   signs off every item while the boxes stay `[ ]`. Hook `Stop` reminds with `[TDQ:DOD]`
   when the books close on an open box, but the reminder is a net, not a substitute — tick
   as each item passes.

9. Present the report in chat (verbatim, or a short summary plus the path).

10. **Ask the user whether to commit** — mandatory; never commit the final result on your own
    (the single exception: an unblocking commit during build under the Hard rules, which must
    be listed in the report). Merge it with step 9 into ONE block following
    [user-facing-block.md](../../tdq-conventions/references/user-facing-block.md):
    <!-- i18n-allow: chat block written in the default document language -->
    ```
    Mọi thứ của <tên việc> đã hoàn tất, kiểm sạch và sẵn sàng để bạn chốt. Tóm tắt ngắn gọn:

    1. Trước và sau request có gì khác?

    - **Trước đây:** <trạng thái/vướng mắc cũ>.
    - **Sau khi làm xong:** <thay đổi cốt lõi>:
      - **<Ý chính 1>:** <tác dụng, số liệu ngắn>.
      - **<Ý chính 2>:** <tác dụng>.
    - **Đã test & Kết quả:** <kiểm gì, số đạt/lỗi>.

    Xem đầy đủ tại: `docs/tdq/reports/<slug>.md`

    ---

    **Bạn có muốn tôi commit phần thay đổi này không?**

    ➤ Trả lời: nhắn "commit" (tôi commit, không push) hoặc "chưa" (giữ nguyên chỗ làm việc) · Góp ý: nhắn trực tiếp

    ---
    ```
    User agrees → a message describing the change, containing NO "generated with …", NO
    "Co-Authored-By: Claude Code...", and no AI trailer; branch named per the conventions.

11. **Merge the request branch back** — this happens on BOTH answers, so long as state holds a
    `nhanh_request`. The branch was opened at step 3b of `tdq-intake`; leaving it behind is what
    used to breed orphan branches.
    - `"commit"` → commit on the request branch first (dirty ở `docs/**`, `*.md`, `logs/**`, `*.log`, `graphify-out/**` được tự động add/commit cùng hoặc mang theo, không cần hỏi). Then:
      ```
      git switch <nhanh_goc>
      git merge --no-ff <nhanh_request>
      git branch -d <nhanh_request>
      ```
    - `"chưa"` → no new commit, but everything ALREADY committed on the request branch still
      merges back with the same three commands. What is not committed lives in the working tree
      and would be dragged along by `git switch`, so run `git status --porcelain` first: dirty but
      ONLY docs/logs/graphify (`docs/**`, `*.md`, `logs/**`, `*.log`, `graphify-out/**`) → switch and carry them along;
      ANY other dirty file (code trong `scripts/`, `src/`, `hooks/`, `tests/`...) → STOP, print them, ask
      the user, and do not switch. Same shape as the dirty-repo rule at step 3b.
    - Merge conflict, or `git branch -d` refuses → do NOT force. Report it and ask the user.
    - Then clear the three keys:
      ```
      python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tdq_state.py" set loai_request=null nhanh_goc=null nhanh_request=null
      ```
    No `nhanh_request` in state (tier `nhỏ`, or a project with no git) → skip this step entirely.

Done when: the report is written, the user has been asked about the commit, and the request
branch has been merged back into `nhanh_goc`.
Next step: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tdq_state.py" set phase=idle`
(or `reset` when the user wants the slate wiped for a new request).

## The report shape

(deliberate repetition — the original is step 7 of `## The execution steps` in this file.)

`docs/tdq/reports/<slug>.md` — in the user's document language, with NO hard line limit.
Keep wording simple, clear, visual, and complete (`đơn giản, dễ hiểu`, `trực quan, đầy đủ thông tin`) for every reader following [user-facing-block.md](../../tdq-conventions/references/user-facing-block.md).
Lead with a `Tóm tắt nhanh` blockquote. Explain Before → After → Result cleanly across readable sub-bullets instead of packing facts onto middle-dot (`·`) lines. Draw behavior and command highlights from `Dev Behavior QC Card` in `docs/tdq/qc/<slug>.md`, and paste verbatim `tdq_timing.py show` output (hiding all-unavailable host columns while preserving JSON v2).

<!-- i18n-allow: report template written in the default document language -->
```markdown
# REPORT — <tên việc> (`<slug>` · lane <lane> · mode <mode> · <n> task tick đủ)

Soul: chất lượng > runtime > context cost · luật gốc: skills/tdq-conventions/references/soul.md

> **Tóm tắt nhanh:** <2–3 câu: trước vướng gì → sau sửa gì → kết quả thật>.

**Trước request (trạng thái/flow):** <trạng thái và luồng trước khi sửa, dễ hiểu>
**Sau request (trạng thái/flow):** <luồng mới ngắn gọn, tách ý con bên dưới nếu cần>
- **<Ý chính 1>:** <tác dụng và con số chính>
- **<Ý chính 2>:** <tác dụng>
**Đã test gì:** <kịch bản, vùng chạm và lệnh kiểm>
**Kết quả test:** <số pass/skip/fail, đo thực tế trước → sau, QC PASS x/y DoD>
**Đầu ra:** <file chính> · **Archify HTML:** `docs/tdq/reports/<slug>.html` · Backup: <đường dẫn nếu có>
**Giới hạn:** <việc chưa làm và ảnh hưởng, hoặc "không có">
**Lệch spec chờ duyệt:** <Qn · ngưỡng → đo · phương án — hoặc "không có">
**Git:** <chưa commit / commit đã tạo>

## Thời gian

<dán nguyên output của `tdq_timing.py show`, gồm bảng timing v2, quality và chú thích nguồn>

## Thân PR (soạn sẵn)

**Tóm tắt:** <thay đổi gì, vì sao — 1–2 câu>
**Trước/Sau:** <link HTML Trước/Sau đã duyệt, hoặc "không có — <lý do>">
**Đã kiểm:** <lệnh test/QC + kết quả thật, mỗi lệnh một dòng>
**Rủi ro hồi quy:** <luồng cũ nào có thể bị ảnh hưởng và test nào đang giữ nó>
```

**PR body is drafted, never sent.** The report carries the `Thân PR (soạn sẵn)` block for the <!-- i18n-allow: canonical section name -->
user to paste; the workflow never opens the PR itself.

**Spec deviations ride on the commit question.** When `tdq_state.py lech list` shows pending
items, the closing block asks, before the commit question, one line per deviation: approve
(`lech duyet <id> --by "<words>"`) or reject (`lech bac <id> --by "<words>"`). A rejected one
becomes a fix task in the plan and the request goes back with `set phase=implement`.

**Wall clock** includes approval waits. V2 reports API latency, host tool wait, confirmed
background jobs, their observed union and unattributed time, each with quality and reason.
Intervals overlap: do not add those columns. Unattributed time is not evidence of user idle
or model compute; `model_giay` is null. Preserve partial/unavailable labels and source scope.
V1 timing and step-audit gaps remain **legacy assistant-gap estimates**, not model time.

## Check before presenting

- No hard cap; 10-20 lines recommended, as short as possible without dropping an item.
- Every number comes from real output, never an estimate. A measurement distorted by conditions
  gets said plainly in the "Kết quả" line. <!-- i18n-allow: canonical line name of the report -->
- The "Giới hạn" line must not be left empty <!-- i18n-allow: canonical line name of the report --> while work remains unfinished — tell the truth, hide
  nothing.
- `tdq_state.py get lsp_bo_qua` not null → the request opened past the LSP gate of `init`: the
  "Giới hạn" line <!-- i18n-allow: canonical line name of the report --> quotes its `ly_do` and
  `module`, so work built on grep alone never reads as a normal request.
- End by asking the user whether they want a commit (asked in chat, not written into the file).
