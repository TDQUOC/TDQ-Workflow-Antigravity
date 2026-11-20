#!/usr/bin/env python3
"""Tests for T1.1: Plan V2+ parser isolation, stable assignment SHA, and `packet` command."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.dirname(TESTS_DIR)
SCRIPTS = os.path.join(GOC, "scripts")
for _p in (TESTS_DIR, SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tdq_state  # noqa: E402
import tdq_team  # noqa: E402
import tdq_ten_lenh  # noqa: E402

TRUONG_PROMPT = ["TASK:", "CỤM:", "BASE:", "WORKTREE:", "VÙNG FILE:", "TEST:", "TRẢ VỀ:"]


def _write(root, rel_path, content):
    full = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full


def _run_team(cwd, *args, env=None):
    full_env = dict(os.environ)
    full_env["TDQ_PROJECT_DIR"] = cwd
    if env is not None:
        full_env.update(env)
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "tdq_team.py"), *args],
        cwd=cwd,
        env=full_env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestDocPlanV2Isolation(unittest.TestCase):
    """doc_plan isolates Chạm:/Tham chiếu:/Sinh ra:, skips code fences, supports ROOT_FILES."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def _parse(self, plan_text):
        path = _write(self.cwd, "docs/tdq/plan/2026-11-20-test.md", plan_text)
        return tdq_team.doc_plan(path)

    def test_task_defaults_new_attributes(self):
        t = tdq_team.Task("T1.1", " ", "P1")
        self.assertEqual(t.tham_chieu, [])
        self.assertEqual(t.sinh_ra, [])
        self.assertEqual(t.nhan_loai, "")

    def test_isolates_cham_tham_chieu_sinh_ra_and_other_sections(self):
        plan = """# PLAN — test

## P1 — core
- [ ] **T1.1** (e10m) Update `scripts/ignore_in_title.py` — Test: `py -3 -m unittest tests/test_x.py`
  - Req: `spec/foo.md` §2
  - Chạm: `scripts/a.py`
  - Tham chiếu: `scripts/ref.py` (`helper_fn`)
  - Sinh ra: `docs/out.md`
  - Trước → Sau: `scripts/old.py` -> `scripts/new.py`
  - Neo & Công cụ: `Edit` on `scripts/anchor_only.py`
"""
        tasks = self._parse(plan)
        self.assertEqual(len(tasks), 1)
        t = tasks[0]
        self.assertEqual(t.vung_file, ["scripts/a.py"])
        self.assertIn("scripts/ref.py", t.tham_chieu)
        self.assertEqual(t.tham_chieu, ["scripts/ref.py"])
        self.assertEqual(t.sinh_ra, ["docs/out.md"])

    def test_multiline_sections_and_continuation_lines(self):
        plan = """# PLAN — test

## P1 — core
- [ ] **T1.1** (e10m) Multi-line sections — Test: `pytest -q`
  - Chạm:
    - `scripts/a.py`
    - `scripts/b.py`,
      `scripts/c.py`
  - Tham chiếu:
    - `scripts/ref1.py` (`fn1`)
    - `scripts/ref2.py` (`fn2`)
  - Sinh ra:
    - `docs/out1.md`
    - `docs/out2.md`
  - Logic cốt lõi:
    1. Keep `scripts/should_not_leak.py` untouched.
"""
        t = self._parse(plan)[0]
        self.assertEqual(t.vung_file, ["scripts/a.py", "scripts/b.py", "scripts/c.py"])
        self.assertEqual(t.tham_chieu, ["scripts/ref1.py", "scripts/ref2.py"])
        self.assertEqual(t.sinh_ra, ["docs/out1.md", "docs/out2.md"])

    def test_root_files_whitelist_accepted_in_cham(self):
        plan = """# PLAN — test

## P1 — core
- [ ] **T1.1** (e5m) Update root config — Test: `pytest -q`
  - Chạm: `CLAUDE.md`, `AGENTS.md`, `Cargo.toml`, `pyproject.toml`, `package.json`, `pyrightconfig.json`, `not_whitelisted.txt`, `T1.1`
"""
        t = self._parse(plan)[0]
        self.assertEqual(
            t.vung_file,
            ["CLAUDE.md", "AGENTS.md", "Cargo.toml", "pyproject.toml", "package.json", "pyrightconfig.json"],
        )

    def test_code_fences_backtick_and_tilde_ignored(self):
        plan = """# PLAN — test

```markdown
## P9 — fake phase
- [ ] **T9.9** (e5m) Fake task in fence — Test: `pytest`
  - Chạm: `scripts/fence_outer.py`
```

## P1 — real
- [ ] **T1.1** (e5m) Real task — Test: `pytest`
  - Chạm: `scripts/real.py`
  - Logic cốt lõi:
    ```markdown
    - Chạm: `scripts/fence_backtick.py`
    ```
    ~~~markdown
    - Chạm: `scripts/fence_tilde.py`
    ~~~
  - Cần: T1.0
"""
        tasks = self._parse(plan)
        self.assertEqual([t.ma for t in tasks], ["T1.1"])
        self.assertEqual(tasks[0].phase, "P1")
        self.assertEqual(tasks[0].vung_file, ["scripts/real.py"])

    def test_legacy_fallback_without_cham_label(self):
        plan = """## P1 — a
- [ ] **T1.1** (e10m) Sửa bộ đọc, mô tả dài nên ngắt dòng và đường dẫn rơi xuống
  dòng sau: `scripts/tdq_team.py` — Test: x
"""
        t = self._parse(plan)[0]
        self.assertEqual(t.vung_file, ["scripts/tdq_team.py"])

    def test_nhan_loai_labels(self):
        plan = """## P1 — labels
- [ ] **T1.1** (e5m) Uniform Mechanical Sweep on docs — Test: `pytest`
  - Chạm: `scripts/a.py`
- [ ] **T1.2** (e5m) Sync cycle (dong-bo-chu-ky) — Test: `pytest`
  - Chạm: `scripts/b.py`
- [ ] **T1.3** (e5m) Fix tdq_team.py sweep command bug — Test: `pytest`
  - Chạm: `scripts/c.py`
- [ ] **T1.4** (e5m) Implement linter rule — Test: `pytest`
  - Chạm: `scripts/d.py`
  - Trước → Sau: adds Uniform Mechanical Sweep check
- [ ] **T1.5** (e5m) Explicit child label — Test: `pytest`
  - Chạm: `scripts/e.py`
  - Loại: Uniform Mechanical Sweep
"""
        tasks = self._parse(plan)
        self.assertEqual(tasks[0].nhan_loai, "sweep")
        self.assertEqual(tasks[1].nhan_loai, "dong-bo-chu-ky")
        self.assertEqual(tasks[2].nhan_loai, "")
        self.assertEqual(tasks[3].nhan_loai, "")
        self.assertEqual(tasks[4].nhan_loai, "sweep")


class TestTaskRefExpansion(unittest.TestCase):
    """_TASK_REF matches T1, T2.1a, T2A.1, QC1, QC1.1."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_doc_phu_thuoc_recognizes_t1_t2_1a_and_qc1_1(self):
        plan = """## P1 — work
- [ ] **T1** (e5m) Base — Test: `pytest`
  - Chạm: `scripts/a.py`
- [ ] **T2.1a** (e5m) Variant — Test: `pytest`
  - Chạm: `scripts/b.py`
  - Cần: T1
- [ ] **QC1.1** (e5m) Verify — Test: `pytest`
  - Chạm: `scripts/c.py`
  - Cần: T1, T2.1a
"""
        path = _write(self.cwd, "docs/tdq/plan/2026-11-20-refs.md", plan)
        tasks = tdq_team.doc_plan(path)
        deps = tdq_team.doc_phu_thuoc(tasks)
        self.assertEqual(deps["T1"], set())
        self.assertEqual(deps["T2.1a"], {"T1"})
        self.assertEqual(deps["QC1.1"], {"T1", "T2.1a"})


class TestAssignmentShaStability(unittest.TestCase):
    """Anchor/ref/delta edits keep plan_assignment_sha stable and prevent false stale warnings."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.slug = "2026-11-20-sha-stable"
        self.plan_rel = f"docs/tdq/plan/{self.slug}.md"
        self.addCleanup(self.tmp.cleanup)

    def test_anchor_and_ref_and_delta_edits_do_not_change_sha(self):
        base_plan = """# PLAN — stable sha

## P1 — work
- [ ] **T1.1** (e5m) Alpha — Test: `pytest -q`
  - Chạm: `scripts/alpha.py`
  - Dùng: `tdq-build`
  - Để: keep contract tracked
- [ ] **T1.2** (e5m) Beta — Test: `pytest -q`
  - Chạm: `scripts/beta.py`
  - Cần: T1.1
  - Vị trí neo: `scripts/beta.py:10-20`
  - Neo & Công cụ: `Edit` on `scripts/beta.py` (`L10-20`)
  - Tham chiếu:
    - `scripts/alpha.py` (`alpha_fn`)
  - CONTRACT-DELTA: none
"""
        p1 = _write(self.cwd, self.plan_rel, base_plan)
        sha_before, mode1 = tdq_team.tinh_sha_projection(tdq_team.doc_plan(p1))
        self.assertEqual(mode1, "explicit")

        edited_plan = (
            base_plan
            .replace("`scripts/beta.py:10-20`", "`scripts/beta.py:42-88`")
            .replace("`L10-20`", "`L42-88`")
            .replace("- `scripts/alpha.py` (`alpha_fn`)", "- `scripts/alpha.py` (`alpha_fn`, `alpha_two`)")
            .replace("CONTRACT-DELTA: none", "CONTRACT-DELTA: updated-note")
        )
        p2 = _write(self.cwd, self.plan_rel, edited_plan)
        sha_after, mode2 = tdq_team.tinh_sha_projection(tdq_team.doc_plan(p2))
        self.assertEqual(mode2, "explicit")
        self.assertEqual(sha_before, sha_after)

        # Contract fields like `Để:` still invalidate SHA.
        contract_changed = edited_plan.replace("keep contract tracked", "different contract")
        p3 = _write(self.cwd, self.plan_rel, contract_changed)
        sha_contract, _ = tdq_team.tinh_sha_projection(tdq_team.doc_plan(p3))
        self.assertNotEqual(sha_before, sha_contract)

    def test_canh_bao_lach_luat_uses_kiem_tra_stale_in_explicit_mode(self):
        plan = """# PLAN — explicit

## P1 — work
- [ ] **T1.1** (e5m) Alpha — Test: `pytest -q`
  - Chạm: `scripts/alpha.py`
  - Vị trí neo: `L1-10`
- [ ] **T1.2** (e5m) Beta — Test: `pytest -q`
  - Chạm: `scripts/beta.py`
  - Cần: T1.1
"""
        _write(self.cwd, self.plan_rel, plan)
        tdq_state.save(
            self.cwd,
            {
                "active_request": self.slug,
                "lane": "full",
                "phase": "implement",
                "implement_mode": "subagent",
                "plan_file": self.plan_rel,
            },
        )
        rc, out, err = _run_team(self.cwd, "assign")
        self.assertEqual(rc, 0, out + err)

        # Edit checkbox and anchor line after assign — explicit mode is NOT stale!
        updated = plan.replace("- [ ] **T1.1**", "- [>] **T1.1**").replace("`L1-10`", "`L20-40`")
        _write(self.cwd, self.plan_rel, updated)
        finding = tdq_team.canh_bao_lach_luat(self.cwd, "scripts/alpha.py")
        self.assertIsNotNone(finding)
        self.assertEqual(finding["kieu"], "da-giao-thieu-nhanh")
        self.assertEqual(finding["ma"], "T1.1")


class TestPacketCommand(unittest.TestCase):
    """tdq_team.py packet command registration, Symbol-Span, ref signatures, invariants, logs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.slug = "2026-11-20-packet-test"
        self.plan_rel = f"docs/tdq/plan/{self.slug}.md"
        self.addCleanup(self.tmp.cleanup)

    def test_packet_registered_in_bang_doi_ten_lenh_and_help(self):
        self.assertEqual(tdq_ten_lenh.BANG_DOI_TEN["tdq_team.py"].get("packet"), "packet")
        self.assertIn("packet", tdq_team.LENH)
        rc, out, err = _run_team(self.cwd, "--help")
        self.assertEqual(rc, 0, err)
        self.assertIn("packet", out)

    def _seed_sample_repo(self):
        _write(
            self.cwd,
            "scripts/target.py",
            "\n".join([
                "# line 1",
                "def before_one():",
                "    return 1",
                "",
                "# boundary_before_1",
                "# boundary_before_2",
                "def compute_value(alpha, beta=2):",
                '    """Compute scaled value."""',
                "    total = alpha + beta",
                "    return total * 3",
                "# boundary_after_1",
                "# boundary_after_2",
                "",
                "def after_one():",
                "    return 9",
                "",
            ]),
        )
        _write(
            self.cwd,
            "scripts/ref.py",
            "\n".join([
                "def build_ref_item(name: str, count: int = 1) -> dict:",
                '    """Reference helper."""',
                '    secret = "SECRET_REF_BODY_DO_NOT_INCLUDE"',
                "    return {'name': name, 'count': count, 'secret': secret}",
                "",
            ]),
        )
        _write(
            self.cwd,
            "docs/kien-truc.md",
            "\n".join([
                "# Architecture",
                "",
                "## Luật gọi",
                "",
                "- Rule 1: `scripts/` must NOT import `hooks/`.",
                "- Rule 2: Only `scripts/tdq_state.py` writes `docs/tdq/state.json`.",
                "- Rule 3: New code lives in `scripts/` or `hooks/`.",
                "- Rule 4: `tests/` may import all layers.",
                "- Rule 5: Keep stdout English.",
                "",
            ]),
        )

    def test_packet_md_outputs_7_fields_symbol_span_ref_sig_and_max_3_invariants(self):
        self._seed_sample_repo()
        plan = """# PLAN — packet test

## P1 — impl
- [ ] **T1.1** (e10m) Update `compute_value` — Test: `py -3 -m unittest tests/test_target.py -v`
  - Chạm: `scripts/target.py`
  - Tham chiếu: `scripts/ref.py` (`build_ref_item`)
  - Neo & Công cụ: `Edit` on `scripts/target.py` at `compute_value()` (`L7-10`)
"""
        plan_path = _write(self.cwd, self.plan_rel, plan)
        rc, out, err = _run_team(self.cwd, "packet", "T1.1", "--plan", plan_path, "--format", "md")
        self.assertEqual(rc, 0, out + err)
        for field in TRUONG_PROMPT:
            self.assertIn(field, out)
        self.assertIn("def compute_value(alpha, beta=2):", out)
        self.assertIn("return total * 3", out)
        # 3 boundary lines around compute_value (lines 4..6 and 11..13)
        self.assertIn("# boundary_before_1", out)
        self.assertIn("# boundary_after_2", out)
        # Reference signature only (1-line signature, body excluded)
        self.assertIn("def build_ref_item(name: str, count: int = 1) -> dict:", out)
        self.assertNotIn("SECRET_REF_BODY_DO_NOT_INCLUDE", out)
        # Up to 3 invariants from docs/kien-truc.md
        inv_count = sum(1 for r in ("Rule 1:", "Rule 2:", "Rule 3:", "Rule 4:", "Rule 5:") if r in out)
        self.assertGreaterEqual(inv_count, 1)
        self.assertLessEqual(inv_count, 3)

    def test_packet_large_function_over_120_lines_emits_read_exact(self):
        body = ["def big_func(x):"] + [f"    x += {i}" for i in range(1, 130)] + ["    return x", ""]
        _write(self.cwd, "scripts/big.py", "\n".join(body))
        plan = """# PLAN — big fn

## P1 — impl
- [ ] **T1.1** (e10m) Edit `big_func` — Test: `pytest`
  - Chạm: `scripts/big.py`
  - Neo & Công cụ: `Edit` on `scripts/big.py` at `big_func()`
"""
        plan_path = _write(self.cwd, self.plan_rel, plan)
        rc, out, err = _run_team(self.cwd, "packet", "T1.1", "--plan", plan_path)
        self.assertEqual(rc, 0, out + err)
        self.assertIn("READ-EXACT: scripts/big.py:1-131", out)
        self.assertNotIn("    x += 65", out)

    def test_packet_more_than_2_files_emits_read_exact(self):
        for idx in (1, 2, 3):
            _write(self.cwd, f"scripts/f{idx}.py", f"def fn_{idx}():\n    return {idx}\n")
        plan = """# PLAN — 3 files

## P1 — impl
- [ ] **T1.1** (e10m) Touch 3 files — Test: `pytest`
  - Chạm: `scripts/f1.py`, `scripts/f2.py`, `scripts/f3.py`
  - Neo & Công cụ: `fn_1`, `fn_2`, `fn_3`
"""
        plan_path = _write(self.cwd, self.plan_rel, plan)
        rc, out, err = _run_team(self.cwd, "packet", "T1.1", "--plan", plan_path)
        self.assertEqual(rc, 0, out + err)
        self.assertIn("READ-EXACT: scripts/f3.py:1-2", out)

    def test_packet_json_format_and_unknown_task_exit_1(self):
        self._seed_sample_repo()
        plan = """# PLAN — json

## P1 — impl
- [ ] **T1.1** (e5m) Update `compute_value` — Test: `pytest`
  - Chạm: `scripts/target.py`
  - Tham chiếu: `scripts/ref.py` (`build_ref_item`)
"""
        plan_path = _write(self.cwd, self.plan_rel, plan)
        rc, out, err = _run_team(self.cwd, "packet", "T1.1", "--plan", plan_path, "--format", "json")
        self.assertEqual(rc, 0, out + err)
        data = json.loads(out)
        self.assertEqual(data["task_id"], "T1.1")
        for field in ("TASK", "CỤM", "BASE", "WORKTREE", "VÙNG FILE", "TEST", "TRẢ VỀ"):
            self.assertIn(field, data["prompt_fields"])
        self.assertTrue(data["symbol_spans"])
        self.assertTrue(data["reference_signatures"])
        self.assertLessEqual(len(data["invariants"]), 3)

        rc_bad, _out_bad, err_bad = _run_team(self.cwd, "packet", "T99.9", "--plan", plan_path)
        self.assertEqual(rc_bad, 1)
        self.assertNotIn("Traceback", err_bad)
        self.assertIn("T99.9", err_bad)

    def test_packet_tdq_log_default_on_and_muted_with_0(self):
        self._seed_sample_repo()
        plan = """# PLAN — log

## P1 — impl
- [ ] **T1.1** (e5m) Update `compute_value` — Test: `pytest`
  - Chạm: `scripts/target.py`
"""
        plan_path = _write(self.cwd, self.plan_rel, plan)
        rc_on, _out_on, err_on = _run_team(self.cwd, "packet", "T1.1", "--plan", plan_path)
        self.assertEqual(rc_on, 0, err_on)
        self.assertRegex(err_on, r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\]")

        rc_off, _out_off, err_off = _run_team(
            self.cwd, "packet", "T1.1", "--plan", plan_path, env={"TDQ_LOG": "0"}
        )
        self.assertEqual(rc_off, 0, err_off)
        self.assertEqual(err_off.strip(), "")

    def test_unbackticked_section_paths_extracted_without_leaking_backtick_cmd_or_urls(self):
        plan = """# PLAN — legacy bare paths

## P1 — work
- [ ] **T1.1** (e5m) Add add(a, b) — Test: `pytest tests/test_calc.py`
  - Chạm: src/calc.py, tests/test_calc.py, CLAUDE.md
  - Tham chiếu: scripts/ref.py (`build_ref`), https://example.com/guide.html
- [ ] **T1.2** (e5m) Missing cham line — Test: `pytest tests/test_calc.py`
"""
        p = _write(self.cwd, self.plan_rel, plan)
        tasks = {t.ma: t for t in tdq_team.doc_plan(p)}
        self.assertEqual(tasks["T1.1"].vung_file, ["src/calc.py", "tests/test_calc.py", "CLAUDE.md"])
        self.assertEqual(tasks["T1.1"].tham_chieu, ["scripts/ref.py"])
        self.assertEqual(tasks["T1.2"].vung_file, [])


class TestHandoffPacketV2AndBlackboard(unittest.TestCase):
    """Unified handoff validation, Mini-Spec + multi-lang packet spans, and shared blackboard."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.slug = "2026-11-20-t21-test"
        self.plan_rel = f"docs/tdq/plan/{self.slug}.md"
        self.addCleanup(self.tmp.cleanup)

    def test_root_files_includes_tdq_config_json(self):
        self.assertIn("tdq-config.json", tdq_team.ROOT_FILES)

    def test_validate_handoff_payload_accepts_valid_and_rejects_bad(self):
        good = {
            "task_id": "T2.1",
            "status": "done",
            "files": ["scripts/tdq_team.py"],
            "test_result": "pytest -> 10 passed",
            "branch": "team/test/t2.1",
            "merge_ready": True,
            "tick_ready": True,
            "notes": "scripts/tdq_team.py:2206 — _build_packet_payload — unified schema",
        }
        ok, errs = tdq_team.validate_handoff_payload(good)
        self.assertTrue(ok, errs)
        self.assertEqual(errs, [])

        bad_missing = {"task_id": "T2.1", "status": "done"}
        ok_m, errs_m = tdq_team.validate_handoff_payload(bad_missing)
        self.assertFalse(ok_m)
        self.assertTrue(errs_m)

        bad_long = dict(good, notes="x" * 1501)
        ok_l, errs_l = tdq_team.validate_handoff_payload(bad_long)
        self.assertFalse(ok_l)
        self.assertTrue(any("1500" in e for e in errs_l))

    def test_parse_handoff_from_text_parses_7line_and_json_cli(self):
        text_7line = "\n".join([
            "TASK: T2.1",
            "STATUS: done",
            "FILES: scripts/tdq_team.py, tests/test_team_packet_v2.py",
            "TEST: py -3 -X utf8 -m unittest tests.test_team_packet_v2 -> 12 passed",
            "BRANCH: team/demo/t2.1 | COMMIT: abc1234 | MERGE-READY: yes",
            "TICK-READY: yes",
            "NOTES: scripts/tdq_team.py:2206 — _build_packet_payload — added Mini-Spec",
        ])
        parsed = tdq_team.parse_handoff_from_text(text_7line)
        ok, errs = tdq_team.validate_handoff_payload(parsed)
        self.assertTrue(ok, errs)
        self.assertEqual(parsed["files"], ["scripts/tdq_team.py", "tests/test_team_packet_v2.py"])

        rc_ok, out_ok, err_ok = _run_team(self.cwd, "validate-handoff", "--text", text_7line, "--json")
        self.assertEqual(rc_ok, 0, out_ok + err_ok)
        rc_bad, _out_bad, _err_bad = _run_team(self.cwd, "validate-handoff", "--text", '{"task_id":"T1"}')
        self.assertEqual(rc_bad, 1)

    def test_packet_extracts_minispec_and_ts_rust_ps1_spans(self):
        _write(
            self.cwd,
            "src/widget.ts",
            "\n".join([
                "export function helperBefore() { return 1; }",
                "export interface WidgetConfig { name: string; }",
                "export async function computeWidget(cfg: WidgetConfig): Promise<number> {",
                "  const base = cfg.name.length;",
                "  return base * 2;",
                "}",
            ]),
        )
        _write(
            self.cwd,
            "src/lib.rs",
            "\n".join([
                "pub fn unused_helper() -> i32 { 0 }",
                "pub fn handle_pre_tool(input: &str) -> bool {",
                "    !input.is_empty()",
                "}",
            ]),
        )
        _write(
            self.cwd,
            "scripts/check.ps1",
            "function Invoke-Check {\n    param($Name)\n    return $Name\n}\n",
        )
        plan = """# PLAN — multi lang packet

## P1 — core
- [ ] **T1.1** (e10m) Update `computeWidget` and `handle_pre_tool` — Test: `pytest -q`
  - Req: `§2#2` · Ngoài phạm vi: `GIỮ NGUYÊN` chữ ký cũ của `unused_helper`
  - Chạm: `src/widget.ts`, `src/lib.rs`, `scripts/check.ps1`
  - Tiêu chí chấp nhận (EARS): KHI truyền config hợp lệ, HỆ THỐNG PHẢI trả về số > 0.
  - Logic cốt lõi: tính độ dài tên nhân 2 và kiểm input không rỗng.
  - Ca góc hiểm & Assert: Input rỗng trả false · `assert computeWidget({name: "a"}) == 2`
"""
        plan_path = _write(self.cwd, self.plan_rel, plan)
        rc, out, err = _run_team(self.cwd, "packet", "T1.1", "--plan", plan_path)
        self.assertEqual(rc, 0, out + err)
        for token in ("Req:", "GIỮ NGUYÊN:", "EARS:", "RANH GIỚI:", "TỰ KIỂM:"):
            self.assertIn(token, out)
        self.assertIn("`src/widget.ts` :: `computeWidget`", out)
        self.assertIn("`src/lib.rs` :: `handle_pre_tool`", out)
        self.assertIn("READ-EXACT: scripts/check.ps1:1-4", out)

    def test_blackboard_record_read_and_escalation(self):
        tdq_team.blackboard_record(
            self.cwd, "T2.1", "failed", "first syntax break",
            slug=self.slug, role="tdq-implementer", error="SyntaxError at line 12",
        )
        tdq_team.blackboard_record(
            self.cwd, "T2.1", "failed", "second compile break",
            slug=self.slug, role="tdq-implementer", error="TypeError at line 18",
        )
        board = tdq_team.blackboard_read(self.cwd, self.slug)
        self.assertEqual(len(board["entries"]), 2)
        esc = tdq_team.suggest_escalation(self.cwd, self.slug, "T2.1")
        self.assertIsNotNone(esc)
        self.assertEqual(esc["recommended_agent"], "tdq-build-resolver")
        self.assertEqual(esc["failures"], 2)

        rc, out, err = _run_team(self.cwd, "blackboard", "read", "--slug", self.slug, "--json")
        self.assertEqual(rc, 0, out + err)
        cli_board = json.loads(out)
        self.assertEqual(len(cli_board["entries"]), 2)

    def test_is_artifact_only_paths_no_worktree_and_handoff_schema(self):
        self.assertTrue(tdq_team.is_artifact_only_paths([
            f"docs/tdq/artifacts/{self.slug}/t1.md",
            f"docs/tdq/research/{self.slug}-notes.md",
        ]))
        self.assertFalse(tdq_team.is_artifact_only_paths(["docs/tdq/artifacts/s/../state.json"]))
        self.assertFalse(tdq_team.is_artifact_only_paths([]))
        self.assertFalse(tdq_team.is_artifact_only_paths([f"docs/tdq/artifacts/{self.slug}/t1.md", "scripts/tdq_state.py"]))

        inv_plan = f"""# PLAN — inv no_worktree

## P1 — Investigate
- [ ] **T1.1** (e5m) Research hotspot — Test: `py -3 -c "print('ok')"`
  - Chạm: `docs/tdq/artifacts/{self.slug}/t1.md`
  - Worktree: no_worktree
"""
        plan_path = _write(self.cwd, self.plan_rel, inv_plan)
        tdq_state = __import__("tdq_state")
        st = tdq_state.default_state()
        st.update({
            "active_request": self.slug,
            "lane": "full",
            "plan_file": self.plan_rel,
            "phase": "implement",
            "implement_mode": "subagent",
            "spec_approved": True,
            "plan_approved": True,
            "work_kind": "investigate",
        })
        tdq_state.save(self.cwd, st)

        rc_a, out_a, err_a = _run_team(self.cwd, "assign")
        self.assertEqual(rc_a, 0, out_a + err_a)
        map_path = tdq_team.duong_ban_do(self.cwd, self.slug)
        with open(map_path, encoding="utf-8") as fh:
            ban_do = json.load(fh)
        self.assertFalse(ban_do["tasks"]["T1.1"].get("worktree_required", True))
        self.assertIsNone(tdq_team.canh_bao_lach_luat(self.cwd, f"docs/tdq/artifacts/{self.slug}/t1.md"))

        rc_p, out_p, err_p = _run_team(self.cwd, "packet", "T1.1", "--plan", plan_path, "--format", "json")
        self.assertEqual(rc_p, 0, out_p + err_p)
        pkt = json.loads(out_p)
        self.assertIs(pkt.get("worktree_required"), False)

        rc_o, out_o, err_o = _run_team(self.cwd, "open", "T1.1")
        self.assertEqual(rc_o, 0, out_o + err_o)
        self.assertIn("no_worktree", out_o.lower())
        self.assertFalse(os.path.isdir(os.path.join(self.cwd, ".tdq-worktrees", self.slug, "t1.1")))

        ok_h = {
            "task_id": "T1.1",
            "status": "done",
            "files": [f"docs/tdq/artifacts/{self.slug}/t1.md"],
            "test_result": "ok",
            "branch": "no_worktree",
            "merge_ready": False,
            "tick_ready": True,
            "worktree_required": False,
            "notes": "Shard written cleanly",
        }
        valid, errs = tdq_team.validate_handoff_payload(ok_h, project=self.cwd)
        self.assertTrue(valid, errs)
        bad_bool = dict(ok_h, worktree_required="nope")
        self.assertFalse(tdq_team.validate_handoff_payload(bad_bool, project=self.cwd)[0])
        bad_extra = dict(ok_h, extra_field=1)
        self.assertFalse(tdq_team.validate_handoff_payload(bad_extra, project=self.cwd)[0])

    def test_evidence_add_claim_file_merge_render_and_ntfs_concurrency(self):
        import threading
        claim_dir = os.path.join(self.cwd, "docs", "tdq", "artifacts", self.slug)
        os.makedirs(claim_dir, exist_ok=True)
        errs = []

        def worker(idx):
            try:
                claim_p = os.path.join(claim_dir, f"claim_{idx}.txt")
                with open(claim_p, "w", encoding="utf-8") as fh:
                    fh.write(f"Phát hiện #{idx}: đường dẫn `src/mod_{idx}.py` > 0 & an toàn")
                rc, out, err = _run_team(
                    self.cwd,
                    "evidence", "add",
                    "--slug", self.slug,
                    "--shard", f"T{idx}",
                    "--claim-file", claim_p,
                    "--source", f"src/mod_{idx}.py:{10 + idx}",
                    "--confidence", "high",
                    "--role", "tdq-explorer",
                )
                if rc != 0:
                    errs.append(f"evidence add {idx} failed: {out}{err}")
                # Concurrent writes into shared evidence.jsonl and shared blackboard
                tdq_team.evidence_add(
                    self.cwd,
                    slug=self.slug,
                    shard="",
                    claim=f"Direct shared claim #{idx}",
                    source=f"src/shared_{idx}.py:{idx}",
                    confidence="medium",
                    role="tdq-debugger",
                )
                tdq_team.blackboard_record(
                    self.cwd, f"T{idx}", "done", f"Concurrent note {idx}", slug=self.slug,
                )
            except Exception as exc:
                errs.append(repr(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)
        self.assertEqual(errs, [])

        board = tdq_team.blackboard_read(self.cwd, self.slug)
        self.assertEqual(len(board["entries"]), 6)

        rc_m, out_m, err_m = _run_team(self.cwd, "evidence", "merge", "--slug", self.slug, "--json")
        self.assertEqual(rc_m, 0, out_m + err_m)
        merged_info = json.loads(out_m)
        self.assertEqual(merged_info["count"], 12)

        ev_jsonl = os.path.join(claim_dir, "evidence.jsonl")
        with open(ev_jsonl, encoding="utf-8") as fh:
            ev_rows = [json.loads(ln) for ln in fh if ln.strip()]
        self.assertEqual(len(ev_rows), 12)

        log_md = os.path.join(claim_dir, "evidence-log.md")
        self.assertTrue(os.path.isfile(log_md))
        with open(log_md, encoding="utf-8") as fh:
            md1 = fh.read()
        self.assertIn("Phát hiện #0", md1)

        rc_r, out_r, err_r = _run_team(self.cwd, "evidence", "render", "--slug", self.slug)
        self.assertEqual(rc_r, 0, out_r + err_r)
        with open(log_md, encoding="utf-8") as fh:
            md2 = fh.read()
        self.assertEqual(md1, md2)


if __name__ == "__main__":
    unittest.main()
