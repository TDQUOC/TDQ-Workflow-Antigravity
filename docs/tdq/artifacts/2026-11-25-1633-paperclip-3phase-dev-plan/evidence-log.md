# Evidence Log — 2026-11-25-1633-paperclip-3phase-dev-plan

| # | ID | Shard | Claim | Source | Confidence |
|---|---|---|---|---|---|
| 1 | `0616cb0c1fbe` | `s1` | agy_dispatch.py dispatches PreToolUse in-process and routes _is_mcp_tool through lsp_gate.py | `tools/patches/agy_dispatch.py:136-168` | `high` |
| 2 | `1879901cb273` | `s1` | hooks/scripts/_common.py provides with_ntfs_lock using Windows msvcrt.locking LK_NBLCK with 200 attempts backoff | `hooks/scripts/_common.py:466-519` | `high` |
| 3 | `27411db5b47c` | `s1` | tdq_timing.py maintains timing.jsonl and telemetry logs with TDQ_LOG=0 toggle cleanly hosting runtime budget counters | `scripts/tdq_timing.py:33-53` | `high` |
| 4 | `3209613d4046` | `s1` | tdq_state.save uses atomic replace and warns overwriting anyway without a cross-process sidecar lock | `scripts/tdq_state.py:579-597` | `high` |
| 5 | `3c67a9ede986` | `s1` | Rust tdq-dispatch lock.rs keeps .lock anchor files on disk using File::try_lock to prevent Python create/unlink races | `hooks/rust/tdq-dispatch/src/lock.rs:1-86` | `high` |
| 6 | `4582617658f5` | `s1` | tdq_team.py chia_dot orders waves with TRAN_SONG_SONG=4 and detect_tcas_collision AST analysis without 3-tier aging or blockedBy | `scripts/tdq_team.py:594-685` | `high` |
| 7 | `680ff293a2d4` | `s1` | test_rust_dispatch_parity.py asserts len(codes) == 23 all_agy_codes from tools/patches/gate_guidance.json | `tests/test_rust_dispatch_parity.py:46-54` | `high` |
| 8 | `6f8f80aeae90` | `s1` | tdq_config.py resolves DEFAULT_CONFIG via env > project > plugin precedence from tdq-config.json | `scripts/tdq_config.py:30-94` | `high` |
| 9 | `aa71d3c3ceee` | `s1` | default_state pins schema_version=6, work_kind and load backfills/keeps unknown keys without breaking callers | `scripts/tdq_state.py:259-268` | `high` |
| 10 | `f75253b39ff2` | `s1` | Rust pre_tool_use.rs handle_mcp_tool routes mcp_* calls in parallel with Python lsp_gate.py | `hooks/rust/tdq-dispatch/src/events/pre_tool_use.rs:723-765` | `high` |
| 11 | `4e175fc25b1b` | `s2` | test_build_portable.py pins APPROVED_RUNTIME_MODULES in manifest and release branch tree assertions | `tests/test_build_portable.py:37-45` | `high` |
| 12 | `5d2c69ff2fcf` | `s2` | la_duong_dan_release preserves scripts/ subdirectories except scripts/samples/, allowing scripts/defaults/ to ship onto main | `scripts/build_portable.py:635-655` | `high` |
| 13 | `7212c05fe18b` | `s2` | token_budget.py enforces hard TRAN_TOKEN = 3500 cap across skills/*/references/**/*.md via SHA-256 lockfile | `scripts/token_budget.py:40-50` | `high` |
| 14 | `b01dbd39e180` | `s2` | tdq_state.py _cli_escalate_to_build enforces Zero-Downgrade Lock upgrading investigate to build with audit trail and plan reset | `scripts/tdq_state.py:3026-3101` | `high` |
| 15 | `ba161e7dac2d` | `s2` | KhoBM25 prototype in skill_router.py performs BM25 ranking in stdlib Python but is not yet wired into any intake flow | `scripts/skill_router.py:141-205` | `high` |
| 16 | `f04c4142ab16` | `s2` | build_portable.py RELEASE_EXCLUDE_SCRIPTS currently omits skill_router.py from main branch unless removed during P1 | `scripts/build_portable.py:76-81` | `high` |
| 17 | `f9b6f2d10c0c` | `s2` | i18n_check.py enforces 3-layer language separation across .py .md .json .txt files under skills hooks scripts | `scripts/i18n_check.py:33-55` | `high` |
| 18 | `fdfb84511245` | `s2` | build_agy_plugin.py recursively copies scripts skills agents tdq-config.json then runs verify_staged_bundle byte and token checks | `tools/build_agy_plugin.py:301-337` | `high` |
| 19 | `0080d4ab0cb5` | `s3` | tests/test_ntfs_concurrency.py proves 8 spawned processes write 320 JSONL events on Windows NTFS with zero data loss | `tests/test_ntfs_concurrency.py:1-38` | `high` |
| 20 | `0cc059920b10` | `s3` | Previous integration-blueprint.md defines 3 phases P0-P2, sample contracts, and 6 DO-NOT-COPY Paperclip exclusions | `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/integration-blueprint.md:1-100` | `high` |
| 21 | `2945577b6f04` | `s3` | tdq_test.py cmd_vung_cham skips cleanly when only docs change and cmd_tron_bo runs full suite at QC | `scripts/tdq_test.py:840-878` | `high` |
| 22 | `3b8239a918d9` | `s3` | tests/test_skill_router.py locks 22 benchmark queries across easy/medium/hard Vietnamese prompts for KhoBM25 accuracy | `tests/test_skill_router.py:38-70` | `high` |
| 23 | `4f5daae5671a` | `s3` | tdq_test.py nhanh_goc_mac_dinh defaults base branch to dev and collects changed files for blast-radius test selection | `scripts/tdq_test.py:559-592` | `high` |
| 24 | `81b26479b3d7` | `s3` | docs/kien-truc.md forbids scripts/ importing hooks/, restricts state file writes to tdq_state.py, and places new code in scripts/ or hooks/ | `docs/kien-truc.md:19-30` | `high` |
| 25 | `8296e3f382cd` | `s3` | tests/test_state.py pins single-line CLI output and atomic state writes compatible with schema_version=6 | `tests/test_state.py:25-85` | `high` |
| 26 | `8a81b5bbd05c` | `s3` | tdq_finish.py chains khoa-token lint worklog dong-so phase archify graphify in one TDQ_LOG-aware command | `scripts/tdq_finish.py:309-345` | `high` |
