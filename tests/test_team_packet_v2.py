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


if __name__ == "__main__":
    unittest.main()
