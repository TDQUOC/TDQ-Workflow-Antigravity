#!/usr/bin/env python3
"""Tests for T1.3: R15 V2+ linter (Per-Task Mini-Spec, Compact/Full, placeholders, ANTI-2, pair, R12)."""
import os
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

from helper import ROOT  # noqa: E402

SCRIPTS_DIR = os.path.join(ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import doc_lint  # noqa: E402

LINT_SCRIPT = os.path.join(SCRIPTS_DIR, "doc_lint.py")

SPEC_MIN = """# SPEC — Demo

Ngày: 2026-11-20 · Bản: 1.0 · Lane: full

## 2b. Ranh giới module

| Module | Vùng file | Phụ thuộc module | Đầu ra §2 nào |
|---|---|---|---|
| core | `src/app.py` | không | 1 |

## 3b. Năng lực & công cụ

| Skill | Nguồn | Phán quyết | Dùng ở đâu / Lý do loại |
|---|---|---|---|
| `tdq-build` | plugin:tdq-workflow | NỀN | workflow |

## 6. QC & Definition of Done

| # | Hạng mục kiểm | Điều kiện PASS |
|---|---|---|
| Q1 | App works | `pytest -q` exits 0 |
"""


def _full_task(
    code="T1.1",
    cham="`src/app.py`",
    req="- Req: `§2 #1` · Ngoài phạm vi: `GIỮ NGUYÊN` unrelated CLI flags",
    giao_tiep="",
    neo="- Neo & Công cụ: `Edit` on `src/app.py` (`run()`)",
    before_after="- Trước → Sau: Hiện `run()` returns None → Sau: returns dict",
    ears="- Tiêu chí chấp nhận (EARS): KHI call `run()`, HỆ THỐNG PHẢI return status dict",
    logic="- Logic cốt lõi:\n    1. Parse input dict.\n    2. Return status payload.",
    oracle="- Ca góc hiểm & Assert:\n    - Ca hiểm: empty dict input\n    - Tiêu chí: `assert run({})['ok'] is True`",
    test_cmd="`py -3 -m unittest tests/test_app.py`",
):
    parts = [f"- [ ] **{code}** (e10m) Implement core flow — Test: {test_cmd}"]
    for item in (req, f"  - Chạm: {cham}" if cham is not None else None, giao_tiep, neo, before_after, ears):
        if item:
            parts.append(item if item.startswith("  ") else f"  {item}")
    for block in (logic, oracle):
        if block:
            parts.append(block if block.startswith("  ") else f"  {block}")
    return "\n".join(parts)


def _wrap_plan(
    body,
    header="# PLAN — Demo\n\nNgày: 2026-11-20 · Lane: full",
    ownership=True,
    dod="- [ ] Q1 App — `py -3 -m unittest tests/test_app.py`",
):
    sections = [header]
    if ownership:
        sections.append(
            "## Ownership Map\n\n"
            "| Contract | Owner | Users |\n|---|---|---|\n"
            "| `run` | `src/app.py` | `T1.1` |"
        )
    sections.append(f"## P1 — Core\n\n{body}")
    sections.append("## Cụm song song\n\nMột cụm.")
    sections.append(f"## Definition of Done\n\n{dod}")
    return "\n\n".join(sections) + "\n"


def _compact_task(
    code="QC1.1",
    label="",
    cham="`src/app.py`",
    neo="- Vị trí neo: `src/app.py` (`run`)",
    before_after="- Trước → Sau: Old return → New return",
    logic="- Logic: Update return dict and verify status",
    oracle="- Tiêu chí: `assert run()['ok'] is True`",
    test_cmd="`py -3 -m unittest tests/test_app.py`",
):
    tag = f" {label}" if label else ""
    parts = [f"- [ ] **{code}** (e5m){tag} Fix check — Test: {test_cmd}"]
    for item in (f"  - Chạm: {cham}" if cham is not None else None, neo, before_after, logic, oracle):
        if item:
            parts.append(item if item.startswith("  ") else f"  {item}")
    return "\n".join(parts)


class PlanV2LinterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _write(self, rel_path, content):
        path = os.path.join(self.tmp.name, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def test_constants_and_tdq_plan_line_limit(self):
        self.assertEqual(doc_lint.SKILL_LINE_LIMITS["tdq-plan"], 132)
        self.assertEqual(doc_lint.R15_MOC, "2026-11-20")
        for ext in (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"):
            self.assertIn(ext, doc_lint.EXT_CAU_HINH)
        self.assertIn(".py", doc_lint.EXT_MA_NGUON)
        self.assertTrue(doc_lint.BANNED_PLACEHOLDERS)
        self.assertTrue(doc_lint.ANTI2_PATTERNS)

    def test_plan_sau_moc_helper(self):
        self.assertTrue(doc_lint._plan_sau_moc("docs/tdq/plan/2026-11-20-demo.md"))
        self.assertTrue(doc_lint._plan_sau_moc("2026-12-01-future.md"))
        self.assertFalse(doc_lint._plan_sau_moc("docs/tdq/plan/2026-11-19-old.md"))
        self.assertFalse(doc_lint._plan_sau_moc("docs/tdq/plan/p.md"))
        self.assertFalse(doc_lint._plan_sau_moc("plan-mau.md"))

    def test_r12_skips_numbered_steps(self):
        self.assertIsNone(doc_lint._r12_van_xuoi("  1. Initialize state and parse input args"))
        self.assertIsNone(doc_lint._r12_van_xuoi("12. Validate payload fields and return dict"))
        text = (
            "# Report\n\n"
            "This paragraph uses English prose without any Vietnamese diacritic marks at all.\n"
            "Second line continues the same English paragraph across multiple prose lines.\n"
            "Third line completes the non-Vietnamese prose block for language verification.\n"
        )
        path = self._write("docs/tdq/reports/2026-11-20-lang.md", text)
        errs = doc_lint.lint_file(path)
        self.assertTrue(any("[R12]" in e for e in errs), errs)

    def test_pre_cutoff_plan_preserves_legacy_r15_and_respects_fence(self):
        legacy_ok = _wrap_plan(
            "- [ ] **T1.1** (e5m) Legacy — Test: `pytest`\n"
            "  - Chạm: `src/app.py`\n"
            "  - Logic: simple update\n",
            header="# PLAN — Legacy\n\nNgày: 2026-11-15 · Lane: full",
            ownership=False,
        )
        p_ok = self._write("docs/tdq/plan/2026-11-15-legacy.md", legacy_ok)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(p_ok)), [])

        fenced = _wrap_plan(
            "- [ ] **T1.1** (e5m) Doc only — Test: `doc_lint`\n"
            "  - Chạm: `docs/readme.md`\n"
            "```\n  - Chạm: `src/fake.py`\n```\n",
            header="# PLAN — Fenced\n\nNgày: 2026-11-15 · Lane: full",
            ownership=False,
        )
        p_fence = self._write("docs/tdq/plan/2026-11-15-fenced.md", fenced)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(p_fence)), [])

        legacy_bad = _wrap_plan(
            "- [ ] **T1.1** (e5m) Missing logic — Test: `pytest`\n  - Chạm: `src/app.py`\n",
            header="# PLAN — Legacy Bad\n\nNgày: 2026-11-15 · Lane: full",
            ownership=False,
        )
        p_bad = self._write("docs/tdq/plan/2026-11-15-legacy-bad.md", legacy_bad)
        self.assertTrue(any("[R15]" in e for e in doc_lint.r15_loi(doc_lint.Doc(p_bad))))

    def test_r15_full_clean_with_multiline_cham_variants_and_fenced_example(self):
        task = _full_task(
            cham="\n    - `src/app.py`\n    - `tests/test_app.py`",
            req="- Req: `§2 #1`\n  - GIỮ NGUYÊN: CLI interface",
            neo="- Vị trí neo: `src/app.py` (`run()`)",
        ) + "\n    ```\n    TBD inside code fence\n    - Chạm: `ignored.py`\n    assert True\n    1. ...\n    ```"
        plan = _wrap_plan(task)
        p = self._write("docs/tdq/plan/2026-11-20-clean.md", plan)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(p)), [])

    def test_r15_full_missing_required_fields_fails(self):
        cases = {
            "req": {"req": ""},
            "out_of_scope": {"req": "- Req: `§2 #1`"},
            "anchor": {"neo": ""},
            "before_after": {"before_after": ""},
            "ears": {"ears": ""},
            "logic": {"logic": ""},
            "oracle": {"oracle": ""},
        }
        for name, overrides in cases.items():
            with self.subTest(missing=name):
                plan = _wrap_plan(_full_task(**overrides))
                p = self._write(f"docs/tdq/plan/2026-11-20-miss-{name}.md", plan)
                errs = doc_lint.r15_loi(doc_lint.Doc(p))
                self.assertTrue(any("[R15]" in e for e in errs), (name, errs))

    def test_r15_full_ignores_tham_chieu_for_code_classification(self):
        doc_only_with_ref = _wrap_plan(
            "- [ ] **T1.1** (e5m) Update guide — Test: `doc_lint.py docs/a.md`\n"
            "  - Chạm: `docs/a.md`\n"
            "  - Tham chiếu: `src/app.py` (`run`)\n",
            ownership=False,
        )
        p = self._write("docs/tdq/plan/2026-11-20-doc-ref.md", doc_only_with_ref)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(p)), [])

    def test_r15_full_over_35_lines_fails_and_allow_exempts(self):
        extra = "\n".join(f"    {i}. Step detail {i} for flow." for i in range(1, 30))
        long_task = _full_task(logic=f"- Logic cốt lõi:\n{extra}")
        plan = _wrap_plan(long_task)
        p_bad = self._write("docs/tdq/plan/2026-11-20-long.md", plan)
        errs = doc_lint.r15_loi(doc_lint.Doc(p_bad))
        self.assertTrue(any("[R15]" in e for e in errs), errs)

        allowed = plan.replace("- [ ] **T1.1**", "<!-- doc-lint: allow R15 -->\n- [ ] **T1.1**")
        p_ok = self._write("docs/tdq/plan/2026-11-20-long-ok.md", allowed)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(p_ok)), [])

    def test_r15_compact_for_qc_and_quick_plans(self):
        qc_ok = _wrap_plan(_compact_task(code="QC1.1"), ownership=False)
        p_qc_ok = self._write("docs/tdq/plan/2026-11-20-qc-ok.md", qc_ok)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(p_qc_ok)), [])

        qc_bad = _wrap_plan(_compact_task(code="QC1.1", before_after=""), ownership=False)
        p_qc_bad = self._write("docs/tdq/plan/2026-11-20-qc-bad.md", qc_bad)
        self.assertTrue(any("[R15]" in e for e in doc_lint.r15_loi(doc_lint.Doc(p_qc_bad))))

        quick_ok = _wrap_plan(
            _compact_task(code="T1", neo="- Quy luật: add from __future__"),
            header="# QUICK — Patch parser\n\n**Ngày:** 2026-11-20 · Lane: quick",
            ownership=False,
        )
        p_qk_ok = self._write("docs/tdq/plan/2026-11-20-qk-ok.md", quick_ok)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(p_qk_ok)), [])

        quick_bad = _wrap_plan(
            "- [ ] **T1** (e5m) Quick fix — Test: `pytest`\n  - Chạm: `src/app.py`\n",
            header="# QUICK — Patch parser\n\n**Ngày:** 2026-11-20 · Lane: quick",
            ownership=False,
        )
        p_qk_bad = self._write("docs/tdq/plan/2026-11-20-qk-bad.md", quick_bad)
        self.assertTrue(any("[R15]" in e for e in doc_lint.r15_loi(doc_lint.Doc(p_qk_bad))))

    def test_uniform_mechanical_sweep_and_dong_bo_chu_ky_limits(self):
        six_files = ", ".join(f"`src/f{i}.py`" for i in range(1, 7))
        seven_files = ", ".join(f"`src/f{i}.py`" for i in range(1, 8))
        five_files = ", ".join(f"`src/f{i}.py`" for i in range(1, 6))

        sweep_ok = _wrap_plan(_compact_task(code="T1.1", label="(Uniform Mechanical Sweep)", cham=six_files), ownership=False)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(self._write("docs/tdq/plan/2026-11-20-sw6.md", sweep_ok))), [])

        sweep_bad = _wrap_plan(_compact_task(code="T1.1", label="(Uniform Mechanical Sweep)", cham=seven_files), ownership=False)
        errs_sw = doc_lint.r15_loi(doc_lint.Doc(self._write("docs/tdq/plan/2026-11-20-sw7.md", sweep_bad)))
        self.assertTrue(any("[R15]" in e for e in errs_sw), errs_sw)

        sync_ok = _wrap_plan(_compact_task(code="T1.1", label="(dong-bo-chu-ky)", cham=five_files), ownership=False)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(self._write("docs/tdq/plan/2026-11-20-sy5.md", sync_ok))), [])

        sync_bad = _wrap_plan(_compact_task(code="T1.1", label="(dong-bo-chu-ky)", cham=six_files), ownership=False)
        errs_sy = doc_lint.r15_loi(doc_lint.Doc(self._write("docs/tdq/plan/2026-11-20-sy6.md", sync_bad)))
        self.assertTrue(any("[R15]" in e for e in errs_sy), errs_sy)

    def test_config_file_requires_schema_key_and_verification(self):
        bad_cfg = _wrap_plan(
            "- [ ] **T1.1** (e5m) Update config — Test: `py -3 -m unittest tests/test_cfg.py`\n"
            "  - Chạm: `config/settings.json`\n",
            ownership=False,
        )
        errs = doc_lint.r15_loi(doc_lint.Doc(self._write("docs/tdq/plan/2026-11-20-cfg-bad.md", bad_cfg)))
        self.assertTrue(any("[R15]" in e for e in errs), errs)

        ok_cfg = _wrap_plan(
            "- [ ] **T1.1** (e5m) Update config — Test: `py -3 -m unittest tests/test_cfg.py`\n"
            "  - Chạm: `config/settings.yaml`\n"
            "  - Schema/Key: `retry_limit` integer\n"
            "  - Tiêu chí: `assert cfg['retry_limit'] == 3`\n",
            ownership=False,
        )
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(self._write("docs/tdq/plan/2026-11-20-cfg-ok.md", ok_cfg))), [])

    def test_banned_placeholders_caught_and_fenced_ignored(self):
        placeholders = [
            "TBD",
            "`TBD`",
            "TODO",
            "handle edge cases",
            "appropriate validation",
            "xử lý các edge case",  # i18n-allow
            "thêm validation phù hợp",  # i18n-allow
            "cập nhật các file liên quan",  # i18n-allow
            "viết test cho các hàm trên",  # i18n-allow
            "tối ưu nếu cần",  # i18n-allow
        ]
        for idx, ph in enumerate(placeholders):
            with self.subTest(placeholder=ph):
                plan = _wrap_plan(
                    "- [ ] **T1.1** (e3m) Update doc — Test: `doc_lint.py docs/a.md`\n"
                    f"  - Chạm: `docs/a.md`\n  - Ghi chú: {ph}\n",
                    ownership=False,
                )
                p = self._write(f"docs/tdq/plan/2026-11-20-ph-{idx}.md", plan)
                errs = doc_lint.r15_loi(doc_lint.Doc(p))
                self.assertTrue(any("[R15]" in e for e in errs), (ph, errs))

        ellipsis_plan = _wrap_plan(_full_task(logic="- Logic cốt lõi:\n    1. Parse input\n    2. ..."))
        errs_el = doc_lint.r15_loi(doc_lint.Doc(self._write("docs/tdq/plan/2026-11-20-dots.md", ellipsis_plan)))
        self.assertTrue(any("[R15]" in e for e in errs_el), errs_el)

    def test_anti2_caught_on_task_qc_non_code_and_dod(self):
        bad_cases = [
            ("assert_true_oracle", _full_task(oracle="- Tiêu chí: `assert True`"), "- [ ] Q1 Ok — `pytest`"),
            ("assert_true_subbullet", _full_task(oracle="- Ca góc hiểm & Assert:\n    - `assert True`"), "- [ ] Q1 Ok — `pytest`"),
            ("assert_eq_oracle", _full_task(oracle="- Tiêu chí: `assert 1 == 1`"), "- [ ] Q1 Ok — `pytest`"),
            ("assert_len_ge_0", _full_task(oracle="- Assert: `assert len(res) >= 0`"), "- [ ] Q1 Ok — `pytest`"),
            ("bare_test_path_test", _full_task(test_cmd="`Test-Path src/app.py`"), "- [ ] Q1 Ok — `pytest`"),
            ("bare_exists_oracle", _full_task(oracle="- Tiêu chí: `os.path.exists('src/app.py')`"), "- [ ] Q1 Ok — `pytest`"),
            (
                "non_code_task_assert_true",
                "- [ ] **T1.1** (e2m) Edit doc — Test: `doc_lint`\n  - Chạm: `docs/a.md`\n  - Tiêu chí: `assert True`",
                "- [ ] Q1 Ok — `pytest`",
            ),
            ("dod_assert_true", _full_task(), "- [ ] Q1 Check — `python3 -c \"assert True\"`"),
            ("dod_bare_test_path", _full_task(), "- Check file — `Test-Path docs/out.md`"),
        ]
        for name, body, dod in bad_cases:
            with self.subTest(case=name):
                p = self._write(f"docs/tdq/plan/2026-11-20-a2-{name}.md", _wrap_plan(body, dod=dod))
                errs = doc_lint.r15_loi(doc_lint.Doc(p))
                self.assertTrue(any("[R15]" in e and "ANTI-2" in e for e in errs), (name, errs))

        real_exists = _wrap_plan(
            _full_task(oracle="- Tiêu chí: `assert os.path.exists('out.txt') and 'ok' in open('out.txt').read()`"),
            dod="- [ ] Q1 Check — `Test-Path out.txt; (Get-Content out.txt) -match 'ok'`",
        )
        p_ok = self._write("docs/tdq/plan/2026-11-20-a2-real.md", real_exists)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(p_ok)), [])

    def test_ownership_map_required_for_two_contract_code_tasks(self):
        t1 = _full_task(code="T1.1", cham="`src/a.py`", giao_tiep="- Giao tiếp: Consumes: `raw` | Produces: `Model`")
        t2 = _full_task(code="T1.2", cham="`src/b.py`", giao_tiep="- Giao tiếp: Consumes: `Model` | Produces: `out`")
        no_map = _wrap_plan(f"{t1}\n\n{t2}", ownership=False)
        errs = doc_lint.r15_loi(doc_lint.Doc(self._write("docs/tdq/plan/2026-11-20-nomap.md", no_map)))
        self.assertTrue(any("[R15]" in e for e in errs), errs)

        with_map = _wrap_plan(f"{t1}\n\n{t2}", ownership=True)
        self.assertEqual(doc_lint.r15_loi(doc_lint.Doc(self._write("docs/tdq/plan/2026-11-20-map.md", with_map))), [])

    def test_pair_runs_r15_outside_plan_dir_and_real_2026_11_20_plan_passes(self):
        spec_p = self._write("s.md", SPEC_MIN)
        bad_plan = _wrap_plan("- [ ] **T1.1** (e5m) Bad — Test: `pytest`\n  - Chạm: `src/app.py`\n", ownership=False)
        bad_p = self._write("2026-11-20-bad-pair.md", bad_plan)
        proc_bad = subprocess.run([sys.executable, LINT_SCRIPT, "--pair", spec_p, bad_p], capture_output=True, encoding="utf-8", text=True)
        self.assertEqual(proc_bad.returncode, 1, proc_bad.stdout + proc_bad.stderr)
        self.assertIn("[R15]", proc_bad.stdout)

        good_p = self._write("2026-11-20-good-pair.md", _wrap_plan(_full_task()))
        proc_good = subprocess.run([sys.executable, LINT_SCRIPT, "--pair", spec_p, good_p], capture_output=True, encoding="utf-8", text=True)
        self.assertEqual(proc_good.returncode, 0, proc_good.stdout + proc_good.stderr)

        real_spec = os.path.join(ROOT, "docs", "tdq", "spec", "2026-11-20-0015-trien-khai-plan-v2-planner-spec.md")
        real_plan = os.path.join(ROOT, "docs", "tdq", "plan", "2026-11-20-0015-trien-khai-plan-v2-planner-spec.md")
        proc_real = subprocess.run([sys.executable, LINT_SCRIPT, real_plan], capture_output=True, encoding="utf-8", text=True)
        self.assertEqual(proc_real.returncode, 0, proc_real.stdout + proc_real.stderr)
        proc_real_pair = subprocess.run([sys.executable, LINT_SCRIPT, "--pair", real_spec, real_plan], capture_output=True, encoding="utf-8", text=True)
        self.assertEqual(proc_real_pair.returncode, 0, proc_real_pair.stdout + proc_real_pair.stderr)


if __name__ == "__main__":
    unittest.main()
