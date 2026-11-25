# Evidence Log — 2026-11-25-1439-paperclip-tdq-integration-sim

| # | ID | Shard | Claim | Source | Confidence |
|---|---|---|---|---|---|
| 1 | `44fcdddd506d` | `s1` | Paperclip hang doi 4 tang Person > Work > Recovery va OLDEST_DISPATCH_SHARE chong bo doi sau 60 phut | `C:/Users/admin/Documents/paperclip/doc/heartbeat-internals.md:59-97` | `high` |
| 2 | `457d1f633f62` | `s1` | tdq_worktree_registry.py khoa so worktree voi 7 truong va 6 ly do chan kem lenh giai toa cu the | `scripts/tdq_worktree_registry.py:25-95` | `high` |
| 3 | `596107efb02e` | `s1` | tdq_state.py save() chi canh bao khi updated_at lech va van ghi de, chua co multi-session lock | `scripts/tdq_state.py:579-597` | `high` |
| 4 | `8592d1befc8d` | `s1` | tdq_team.py gioi han 4 nhanh song song (TRAN_SONG_SONG=4) va co AST TCAS detect_tcas_collision | `scripts/tdq_team.py:99-685` | `high` |
| 5 | `8daca69ba8c6` | `s1` | Paperclip automaticRunBrakes la circuit breaker 3 pha ngat khi >=12 luot >=80% loi trong 10 phut hoac 5 refusal | `C:/Users/admin/Documents/paperclip/server/src/services/recovery/automatic-run-brake.ts:8-32` | `high` |
| 6 | `b55f0ac994d7` | `s1` | Paperclip checkout() dung transaction DB khoa atomic checkoutRunId va executionRunId, tu choi blocker chua xong | `C:/Users/admin/Documents/paperclip/server/src/services/issues.ts:12783-12916` | `high` |
| 7 | `ba07e59af908` | `s1` | tdq_state.py chi co 8 phase chuan va 2 work_kind (build, investigate) | `scripts/tdq_state.py:82-100` | `high` |
| 8 | `d76883f3ba1a` | `s1` | agy_stop_gate.py doi chieu SHA-256 tren dia va ha streak MAX_STREAK=3 khi plan_sha khong doi | `hooks/scripts/agy_stop_gate.py:14-56` | `high` |
| 9 | `0377c980f231` | `s2` | Paperclip skills-catalog tach bundled/optional kem 3 muc trust_level (markdown_only, assets, scripts_executables) | `C:/Users/admin/Documents/paperclip/doc/skills-and-teams-catalog.md:84-146` | `high` |
| 10 | `17d337e3ae59` | `s2` | investigate-mode.md quy dinh QC-I1..I4 va mien preview/2b giup giam phinh ma van giu ky luat chung | `plugins/tdq-workflow-agy/skills/tdq-conventions/references/investigate-mode.md:10-58` | `high` |
| 11 | `25e4451bc94f` | `s2` | TDQ co INVESTIGATE_PHASE_ROWS tach rieng khoi PHASE_TABLE de giu nguyen build khi mo rong loai cong viec | `scripts/tdq_state.py:1797-1825` | `high` |
| 12 | `3ee5c0f3f917` | `s2` | Paperclip dinh nghia 12 AGENT_ROLES tach roi khoi title/capabilities va template huong dan rieng | `C:/Users/admin/Documents/paperclip/packages/shared/src/constants.ts:53-82` | `high` |
| 13 | `7921aa072f03` | `s2` | edit_gate.py va stop_gate.py bao ve luong code TDQ qua TDQ:APPROVE, TDQ:TICK, TDQ:TEAM va QUY_TAC_NGON_NGU | `hooks/scripts/edit_gate.py:1-54` | `high` |
| 14 | `b5890600c7f6` | `s2` | TDQ skill_router.py la KhoBM25 stdlib ho tro tieng Viet khong dau va camelCase nhung moi la prototype chua noi hook | `scripts/skill_router.py:1-86` | `high` |
| 15 | `e81989a5e51c` | `s2` | Paperclip cam chuc danh ceo/manager tu suy ra quyen thue/duyet neu thieu cap quyen tuong minh | `C:/Users/admin/Documents/paperclip/skills/paperclip-create-agent/SKILL.md:15-28` | `high` |
| 16 | `320ec188d2a9` | `s3` | Paperclip agent chay theo nhip heartbeat ngan, moi lan thuc giac nap lai issue summary, comment batch va bat buoc X-Paperclip-Run-Id | `C:/Users/admin/Documents/paperclip/skills/paperclip/SKILL.md:10-31` | `high` |
| 17 | `342b3fd669d4` | `s3` | Paperclip khoa cung Antigravity ACPX chi chay tren darwin + arm64, chua co target Windows | `C:/Users/admin/Documents/paperclip/server/src/services/native-runtime/acpx-qualification.ts:5-24` | `high` |
| 18 | `3e7aa4dd449b` | `s3` | agy_pretooluse_gate.py chi chan 2 luat shell co dinh (nhanh cam va ghi state.json), chua co MCP policy hay quarantine | `hooks/scripts/agy_pretooluse_gate.py:1-56` | `high` |
| 19 | `5b0d134135a8` | `s3` | tdq-workflow-agy dong goi native da HDH (Windows/macOS/Linux) khong can DB server va boc Caveman/RTK gon nhe | `README-Antigravity.md:1-25` | `high` |
| 20 | `642dbc026abe` | `s3` | Paperclip Plugin UI chay dang same-origin JS khong sandbox iframe va chua san sang cai dong cho cloud | `C:/Users/admin/Documents/paperclip/doc/plugins/PLUGIN_SPEC.md:15-35` | `high` |
| 21 | `6d4c00eed673` | `s3` | Paperclip MCP Gateway danh gia rui ro read/write/destructive va tu dong quarantine tool moi xuat hien | `C:/Users/admin/Documents/paperclip/doc/MCP-ACCESS-GOVERNANCE.md:213-230` | `high` |
| 22 | `968ec32977a4` | `s3` | Paperclip budgets.ts thuc thi hard_stop trong DB transaction for(update), gan pauseReason=budget | `C:/Users/admin/Documents/paperclip/server/src/services/budgets.ts:365-390` | `high` |
| 23 | `a22d6a034353` | `s3` | Paperclip package.json yeu cau Node>=24.11, pnpm 9.15.4 va 11 patchedDependencies | `C:/Users/admin/Documents/paperclip/package.json:109-128` | `high` |
| 24 | `bddb62961afe` | `s3` | token_budget.py cua TDQ la khoa hash tinh cap 3500 token cho file luat .md trong CI, chua chan chi tieu runtime | `scripts/token_budget.py:1-49` | `high` |
| 25 | `e79c1da5f2ab` | `s3` | Paperclip local_trusted khong chan duoc tien trinh con truy cap ngam loopback tren Windows | `C:/Users/admin/Documents/paperclip/doc/DEPLOYMENT-MODES.md:81-87` | `high` |
| 26 | `981a164cf0ca` | `s4` | SIM-4 va SIM-5 xac nhan 12/12 bat bien TDQ giu nguyen (0 hoi quy), cach ly 2/2 tool MCP moi va dinh tuyen 8/8 prompt qua 4 Domain Pack (5/5 disk gates); SIM-6 do Pattern-Native p50=0.367ms, p95=0.428ms voi 0 dependency moi | `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/sim-results.json:64-123` | `high` |
| 27 | `9fdc25e30293` | `s4` | Bo simulate test SIM-1..SIM-6 dat 6/6 PASS (TDQ_LOG=1/0 chuan): O_EXCL lease giam duplicate claim tu 61 xuong 0 (0.328ms) va hoi phuc 2/2 crash; aging dua task cu tu slot 20 len 4 (aging_share_hits=1), chan 1 chay som; breaker+hard_stop chan lo ngan sach tu +$2.2 ve $0.0 | `docs/tdq/artifacts/2026-11-25-1439-paperclip-tdq-integration-sim/sim/sim-results.json:1-63` | `high` |
