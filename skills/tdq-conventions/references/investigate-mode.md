# Investigation Mode (`work_kind=investigate`)
<!-- muc-luc-dong:
  Purpose and routing=10-24 · Scoping and planning=25-39 · Fan-out breakeven tiers=40-52 ·
  Shard ledger and checkpoint=53-68 · Debug RCA vs Bugfix=69-80 · Evidence QC (QC-I1..I4)=81
-->

Applies when `work_kind=investigate` covers research, codebase analysis, audit, RCA-only debugging, and architecture reporting. Source rules stay lean here to protect token ceilings across core skill files.

## Purpose and routing

- Keep `build` for product code edits; assign `work_kind=investigate` at `init --kind investigate` for non-code investigation and reporting work.
- `PHASE_TABLE` (`11` rows) remains unchanged; `tdq_state.py` routes `investigate` instructions dynamically via `INVESTIGATE_PHASE_ROWS` and prints `· kind:inv` inside `next_headline`.
- Pre-approval Archify previews (`spec-preview` and `quick-flow`) are waived when `work_kind=investigate`; render Archify HTML once at `report`.
- Mid-flight conversion from `investigate` to product code edits is locked behind `tdq_state.py escalate-to-build --by "<user words>"`; raw `set work_kind=build` is blocked.
- Diagnostic Python scripts authored under `docs/tdq/artifacts/<slug>/` or `docs/tdq/bench/<slug>/` are exempt from code failsafe `QC-F1` unless diffs exit `docs/tdq/`.

## Scoping and planning (`analyze`, `spec`, `plan`)

- Keep pre-implement phases (`analyze` / `quick_analyze`, `spec`, `plan`) strictly shallow: identify entry points, platform health, confirmed facts, and 2–4 falsifiable candidate hypotheses.
- Save deep reading, multi-query search, RCA falsification, and full synthesis exclusively for phase `implement`.
- Full `investigate` specs omit artificial `§2b` product module boundaries (`rule_r10` exempt when header sets `Work kind: investigate`) and non-benchmark thresholds (`r14_loi` exempt).
- Express `quick + investigate` mini-plans may expand up to `<= 65` lines while declaring independent shards and falsifiable checks.
- Combine `main|subagent` execution choice cleanly at `plan` approval without offering disabled `codex`.

## Fan-out breakeven tiers (`implement` Collect)

Based on the `45%` single-agent saturation ceiling (`2512.08296v3`) and diminishing-returns stop rules:

| Tier | Condition | Execution Shape | Tool Budget & Early Stop |
|---|---|---|---|
| **Tier 0 (Zero-Fanout SAS)** | `<= 1` independent branch or `< 4` files | `mode=main`, `0` subagents | `<= 12` tool calls total |
| **Tier 1 (Narrow)** | `2` disjoint investigation axes | `2` `no_worktree` workers (`flash` / `inherit`) | `<= 8` calls/branch |
| **Tier 2 (Standard)** | `3–4` disjoint axes (`TRAN_SONG_SONG=4`) | Hub-and-spoke centralized shards | `<= 12` calls/branch; stop after `2` empty queries |
| **Tier 3 (Deep / `ultra`)** | `<= 5` broad audit/QC shards | Centralized fan-out (`inherit` / `pro` Red-Team) | Warn at `12`, hard cap `20`; `2` empty queries -> stop |

## Shard ledger, `scoped-write`, and Rust Burden Checkpoint

- Investigation workers (`tdq-explorer`, `tdq-debugger`, `tdq-reviewer`) receive `Worktree: none` (`worktree_required: false`) and `scoped-write` restricted solely to `docs/tdq/artifacts/<active_slug>/` (never `evidence*`, `trial_*.json`, `rec_*.json`) or flat `docs/tdq/research/<active_slug>*.md`.
- `tdq-security-reviewer` stays `100%` `[TDQ:READONLY]` (deny-first before role allowlist); Python and Rust `tdq-dispatch` enforce identical canonical ancestor checks plus `cmd /c` and `[IO.File]` guards.
- Workers write locally into disjoint `<task>.md` and optional `<task>.ev.jsonl` shards (`kind: hypothesis | tried | evidence`), then run `tdq_team.py evidence add --claim-file ... --excerpt-file ...` or let the leader run `tdq_team.py evidence merge` at the barrier.
- All updates to `evidence.jsonl` and `blackboard_record` acquire `with_ntfs_lock`; `evidence.jsonl` is the immutable append-only source of truth.
- Rust keeps `<0.5ms` `has_range` fast-path (`pre_tool_use.rs:444`) while incrementing per-`sid` Weighted Burden (`checkpoint-<sid>.json`: `+3` read/extract/crawl/browser, `+2` grep/search/LSP, `+1` read-only bash). At `score >= 40`, Rust queues `[TDQ:DOC]` once without adding a 23rd AGY code.
- `[TDQ:ANCHOR]` stays static pointer-only (no seconds timestamp, `< 600` chars) to preserve KV-cache across multiple `/compact` cycles and `resume` events.

## Debug-RCA (`Point-of-Commitment`) vs Two-Stage Bugfix

- `tdq-debugger` MUST separate the **Manifestation Step** (where failure surfaces) from the **Point-of-Commitment Step** (earliest wrong assumption/branch) and pass at least `1` Counterfactual Falsification Test before ranking root causes.
- Localized bugs (`<= 2` suspect modules, clear repro) enter `work_kind=build` directly; multi-layer ambiguous bugs run a short `investigate` Micro-Spike (`<= 10m`) first, then transition cleanly via `tdq_state.py escalate-to-build`.

## Draft report and Evidence QC (`QC-I1..I4`)

- Phase `Write` inside `implement` drafts directly into `docs/tdq/reports/<slug>.md` before `qc` so phase `report` only finalizes checks, renders Archify HTML once, and verifies Tailscale delivery (`<= 120s`).
- Execute dual-track grounding verification strictly in `L1 -> L4 -> L2` order:
  - `QC-I1` (`L1/L4` `0` LLM): `100%` `[EV-xxx]` IDs exist in `evidence.jsonl`; `100%` cited `path:line` bounds exist on disk; `0` unbackticked placeholders; `git diff --name-only` confirms scope.
  - `QC-I2` (`L2` Focused Grounding): inspect exact `(Claim <-> Disk line or docs/tdq/artifacts/<slug>/raw/<ev_id>.txt)` pairs against source text (`0` ALCE F6 hallucination, independent of `tdq_ccr` LRU eviction).
  - `QC-I3` (Red-Team / Counterfactual Pass): challenge claims with opposing evidence and excluded edge cases (`<= 5` shards at `ultra`).
  - `QC-I4` (Confidence Labeling): tag every major finding `Verified`, `Single-source`, `Inferred`, or `Unverified`; fix or downgrade failing claims inline.
- **Code failsafe:** Any modified file outside `docs/tdq/` automatically re-enables full `QC-F1` + `QC-F4`.
