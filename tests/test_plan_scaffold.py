#!/usr/bin/env python3
"""Tests for T1.2: scripts/tdq_plan_scaffold.py (AST/spec scaffolder, card emitter, verifier, wave checker)."""
from __future__ import annotations

import ast
import os
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
for _p in (TESTS_DIR, SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tdq_plan_scaffold as scaffold  # noqa: E402
import tdq_ten_lenh  # noqa: E402


def _write(root: str, rel_path: str, content: str) -> str:
    full = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full


def _run_scaffold(cwd: str, *args: str, env: dict | None = None):
    full_env = dict(os.environ)
    full_env["TDQ_PROJECT_DIR"] = cwd
    if env is not None:
        full_env.update(env)
    proc = tdq_ten_lenh.chay_subprocess(
        [sys.executable, os.path.join(SCRIPTS_DIR, "tdq_plan_scaffold.py"), *args],
        cwd=cwd,
        env=full_env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestExtractSymbols(unittest.TestCase):
    """AST extraction for Python (HIGH) and regex fallback for .rs/.ts/.tsx/.js/.jsx (LOW)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_python_ast_extracts_functions_classes_decorators_with_high_confidence(self):
        py_file = _write(
            self.cwd,
            "src/sample.py",
            "\n".join([
                "CONST_VER = 1",
                "",
                "def _helper(x: int) -> int:",
                "    return x + 1",
                "",
                "class Processor:",
                "    @staticmethod",
                "    async def run_async(item: dict) -> bool:",
                "        return bool(item)",
                "",
            ]),
        )
        syms = scaffold.extract_symbols(py_file)
        by_qual = {s["qual"]: s for s in syms}
        self.assertIn("_helper", by_qual)
        self.assertIn("Processor", by_qual)
        self.assertIn("Processor.run_async", by_qual)
        helper = by_qual["_helper"]
        self.assertEqual(helper["name"], "_helper")
        self.assertEqual(helper["start"], 3)
        self.assertEqual(helper["end"], 4)
        self.assertIn("def _helper(x: int) -> int:", helper["sig"])
        self.assertEqual(helper["anchor_confidence"], "HIGH")
        run_async = by_qual["Processor.run_async"]
        self.assertEqual(run_async["start"], 7)  # includes decorator line
        self.assertEqual(run_async["end"], 9)
        self.assertEqual(run_async["anchor_confidence"], "HIGH")

    def test_python_syntax_error_and_missing_file_return_empty(self):
        broken = _write(self.cwd, "src/broken.py", "def bad(:\n    pass\n")
        self.assertEqual(scaffold.extract_symbols(broken), [])
        self.assertEqual(scaffold.extract_symbols(os.path.join(self.cwd, "nope.py")), [])

    def test_rust_and_ts_js_fallback_regex_assigns_low_confidence(self):
        rs_file = _write(
            self.cwd,
            "src/engine.rs",
            "\n".join([
                "pub struct Engine {",
                "    pub active: bool,",
                "}",
                "",
                "pub async fn start_engine(port: u16) -> Result<(), String> {",
                "    Ok(())",
                "}",
                "",
            ]),
        )
        ts_file = _write(
            self.cwd,
            "src/client.ts",
            "\n".join([
                "export interface ClientConfig {",
                "  endpoint: string;",
                "}",
                "",
                "export async function fetchStatus(id: string): Promise<boolean> {",
                "  return id.length > 0;",
                "}",
                "",
                "export const formatLabel = (raw: string): string => {",
                "  return raw.trim();",
                "};",
                "",
            ]),
        )
        jsx_file = _write(
            self.cwd,
            "src/widget.jsx",
            "export function StatusBadge({ ok }) {\n  return ok;\n}\n",
        )
        rs_syms = scaffold.extract_symbols(rs_file)
        ts_syms = scaffold.extract_symbols(ts_file)
        jsx_syms = scaffold.extract_symbols(jsx_file)

        self.assertEqual({s["name"] for s in rs_syms} >= {"Engine", "start_engine"}, True)
        self.assertTrue(all(s["anchor_confidence"] == "LOW" for s in rs_syms))
        start_fn = next(s for s in rs_syms if s["name"] == "start_engine")
        self.assertEqual(start_fn["start"], 5)
        self.assertEqual(start_fn["end"], 7)

        self.assertEqual({s["name"] for s in ts_syms} >= {"ClientConfig", "fetchStatus", "formatLabel"}, True)
        self.assertTrue(all(s["anchor_confidence"] == "LOW" for s in ts_syms))
        self.assertEqual([s["name"] for s in jsx_syms], ["StatusBadge"])
        self.assertEqual(jsx_syms[0]["anchor_confidence"], "LOW")


class TestParseSpecContracts(unittest.TestCase):
    """Parsing §3c interface/signature contracts for Greenfield files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_parses_3c_bullets_tables_and_code_fences(self):
        spec = _write(
            self.cwd,
            "docs/tdq/spec/2026-11-20-green.md",
            "\n".join([
                "# SPEC — Greenfield",
                "## 2. Đầu ra",  # i18n-allow
                "- `src/outside.py`: `ignored_outside_3c()`",
                "## 3c. Giải thuật & Xử lý cốt lõi",  # i18n-allow
                "- `src/orders.py`:",
                "  - `create_order(user_id: str, total: float) -> dict`",
                "  - `OrderValidator`: validates payload",
                "",
                "| File | Signature | Purpose |",
                "|---|---|---|",
                "| `src/billing.py` | `charge_card(order_id: str, cents: int) -> bool` | Charge card |",
                "",
                "### `src/hooks_helper.py`",
                "```python",
                "def normalize_key(raw: str) -> str:",
                "    ...",
                "```",
                "## 3d. Mental Model",
                "- Glossary item",
                "",
            ]),
        )
        contracts = scaffold.parse_spec_contracts(spec)
        pairs = {(c["file"], c["symbol"]) for c in contracts}
        self.assertIn(("src/orders.py", "create_order"), pairs)
        self.assertIn(("src/orders.py", "OrderValidator"), pairs)
        self.assertIn(("src/billing.py", "charge_card"), pairs)
        self.assertIn(("src/hooks_helper.py", "normalize_key"), pairs)
        self.assertNotIn(("src/outside.py", "ignored_outside_3c"), pairs)

    def test_returns_empty_when_3c_has_only_generic_prose(self):
        spec = _write(
            self.cwd,
            "docs/tdq/spec/2026-11-20-empty3c.md",
            "\n".join([
                "# SPEC — Empty 3c",
                "## 3c. Giải thuật & Xử lý cốt lõi",  # i18n-allow
                "1. Step one: initialize structures.",
                "2. Step two: process items in loop.",
                "- Time Complexity: $O(N)$",
                "## 4. Yêu cầu bắt buộc",  # i18n-allow
                "",
            ]),
        )
        self.assertEqual(scaffold.parse_spec_contracts(spec), [])


class TestEmitCardsAndCLI(unittest.TestCase):
    """CLI --files, --refs, --from-spec, --emit-cards, and Greenfield fail-closed behavior."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_cli_files_and_refs_prints_high_and_low_confidence(self):
        _write(self.cwd, "src/core.py", "def compute(a: int) -> int:\n    return a * 2\n")
        _write(self.cwd, "src/native.rs", "pub fn fast_hash(v: &str) -> u64 {\n    42\n}\n")
        _write(self.cwd, "src/utils.py", "def slugify(text: str) -> str:\n    return text.lower()\n")
        rc, out, err = _run_scaffold(
            self.cwd, "--files", "src/core.py", "src/native.rs", "--refs", "src/utils.py"
        )
        self.assertEqual(rc, 0, out + err)
        self.assertIn("ANCHOR_CONFIDENCE: HIGH", out)
        self.assertIn("ANCHOR_CONFIDENCE: LOW", out)
        self.assertIn("def compute(a: int) -> int:", out)
        self.assertIn("pub fn fast_hash", out)
        self.assertIn("def slugify(text: str) -> str:", out)

    def test_emit_cards_preserves_pass1_fields_and_emits_mini_spec_skeleton(self):
        _write(
            self.cwd,
            "src/calc.py",
            "def add_tax(amount: float, rate: float = 0.1) -> float:\n    return amount * (1.0 + rate)\n",
        )
        _write(
            self.cwd,
            "src/fmt.py",
            "def fmt_money(val: float) -> str:\n    return f'{val:.2f}'\n",
        )
        plan_path = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-pass1.md",
            "\n".join([
                "# PLAN — pass1",
                "## P1 — core",
                "- [ ] **T1.1** (e10m) Update tax rounding — Test: `py -3 -m unittest tests/test_calc.py -v`",
                "  - Chạm: `src/calc.py`",  # i18n-allow
                "  - Cần: T0.1",  # i18n-allow
                "",
            ]),
        )
        rc, out, err = _run_scaffold(
            self.cwd, "--emit-cards", plan_path, "--refs", "src/fmt.py"
        )
        self.assertEqual(rc, 0, out + err)
        self.assertIn("- [ ] **T1.1** (e10m) Update tax rounding — Test: `py -3 -m unittest tests/test_calc.py -v`", out)
        self.assertIn("ANCHOR_CONFIDENCE: HIGH", out)
        self.assertIn("add_tax", out)
        self.assertIn("fmt_money", out)
        for label in (
            "Req:",
            "Ngoài phạm vi:",  # i18n-allow
            "Chạm:",  # i18n-allow
            "Cần:",  # i18n-allow
            "Giao tiếp:",  # i18n-allow
            "Neo & Công cụ:",  # i18n-allow
            "Trước → Sau:",  # i18n-allow
            "Tiêu chí chấp nhận (EARS):",  # i18n-allow
            "Logic cốt lõi:",  # i18n-allow
            "Ca góc hiểm & Assert:",  # i18n-allow
        ):
            self.assertIn(label, out)
        self.assertLessEqual(len(out.strip().splitlines()), 25)

    def test_greenfield_from_spec_pass_and_fail_closed_exit_1(self):
        spec_ok = _write(
            self.cwd,
            "docs/tdq/spec/2026-11-20-gf.md",
            "\n".join([
                "# SPEC — GF",
                "## 3c. Giải thuật & Xử lý cốt lõi",  # i18n-allow
                "- `src/new_service.py`:",
                "  - `build_service(cfg: dict) -> str`",
                "## 4. Yêu cầu",  # i18n-allow
                "",
            ]),
        )
        spec_empty = _write(
            self.cwd,
            "docs/tdq/spec/2026-11-20-gf-empty.md",
            "# SPEC — Empty\n## 3c. Giải thuật\n1. Do work.\n## 4. Req\n",  # i18n-allow
        )
        plan_gf = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-gf.md",
            "\n".join([
                "# PLAN — GF",
                "## P1 — greenfield",
                "- [ ] **T1.1** (e10m) Create service — Test: `py -3 -m unittest tests/test_gf.py`",
                "  - Chạm: `src/new_service.py`",  # i18n-allow
                "  - Cần: Không",  # i18n-allow
                "",
            ]),
        )
        rc_ok, out_ok, err_ok = _run_scaffold(
            self.cwd, "--emit-cards", plan_gf, "--from-spec", spec_ok
        )
        self.assertEqual(rc_ok, 0, out_ok + err_ok)
        self.assertIn("build_service(cfg: dict) -> str", out_ok)

        # Empty §3c with --from-spec must fail closed with exit 1 mentioning §3c
        rc_empty, _out_empty, err_empty = _run_scaffold(
            self.cwd, "--emit-cards", plan_gf, "--from-spec", spec_empty
        )
        self.assertEqual(rc_empty, 1)
        self.assertIn("§3c", err_empty)

        # Missing Greenfield file without --from-spec must fail closed with exit 1
        rc_nospec, _out_nospec, err_nospec = _run_scaffold(
            self.cwd, "--emit-cards", plan_gf
        )
        self.assertEqual(rc_nospec, 1)
        self.assertIn("src/new_service.py", err_nospec)


class TestVerifyPlan(unittest.TestCase):
    """--verify-plan symbol existence, Write exemption, Python assert AST, and ANTI-2 blocking."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        _write(
            self.cwd,
            "src/real_mod.py",
            "\n".join([
                "MAX_ITEMS = 50",
                "",
                "def real_func(val: int) -> int:",
                "    return val + 1",
                "",
            ]),
        )
        _write(
            self.cwd,
            "src/ref_mod.py",
            "def real_helper(name: str) -> str:\n    return name.strip()\n",
        )

    def test_verify_plan_passes_with_real_symbols_write_file_and_real_assert(self):
        plan = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-good.md",
            "\n".join([
                "# PLAN — good",
                "## P1 — core",
                "- [ ] **T1.1** (e10m) Update `real_func` — Test: `py -3 -m unittest tests/test_real.py`",
                "  - Chạm: `src/real_mod.py`, `tests/test_real.py`",  # i18n-allow
                "  - Tham chiếu: `src/ref_mod.py` (`real_helper`)",  # i18n-allow
                "  - Neo & Công cụ: `Edit` on `src/real_mod.py` at `real_func()` (`L3-4`), `MAX_ITEMS`; `Write` for `tests/test_real.py`",  # i18n-allow
                "  - Ca góc hiểm & Assert:",  # i18n-allow
                "    - Tiêu chí: `assert real_func(2) == 3 and len(items) > 0`",  # i18n-allow
                "  ```markdown",
                "  - Tiêu chí: `assert True`",  # inside fence -> must NOT trigger  # i18n-allow
                "  ```",
                "",
            ]),
        )
        rc, errs = scaffold.verify_plan(plan, self.cwd)
        self.assertEqual(rc, 0, errs)
        self.assertEqual(errs, [])

    def test_verify_plan_blocks_fake_symbol_in_anchor_and_reference(self):
        plan = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-bad-sym.md",
            "\n".join([
                "# PLAN — bad symbol",
                "## P1 — core",
                "- [ ] **T1.1** (e10m) Update fake — Test: `py -3 -m unittest tests/test_real.py`",
                "  - Chạm: `src/real_mod.py`",  # i18n-allow
                "  - Tham chiếu: `src/ref_mod.py` (`ghost_helper`)",  # i18n-allow
                "  - Neo & Công cụ: `Edit` on `src/real_mod.py` at `missing_func()` (`L1-4`)",  # i18n-allow
                "  - Ca góc hiểm & Assert:",  # i18n-allow
                "    - Tiêu chí: `assert real_func(1) == 2`",  # i18n-allow
                "",
            ]),
        )
        rc, out, err = _run_scaffold(self.cwd, "--verify-plan", plan)
        self.assertEqual(rc, 1)
        combined = out + err
        self.assertIn("symbol", combined.lower())
        self.assertIn("missing_func", combined)
        self.assertIn("ghost_helper", combined)

    def test_verify_plan_blocks_anti2_tautologies_and_broken_assert_syntax(self):
        for bad_assert in (
            "`assert True`",
            "`assert 1 == 1`",
            "`assert len(result) >= 0`",
            "`assert x == x`",
            "`assert ok or True`",
            "`assert broken_syntax( == 1`",
        ):
            plan = _write(
                self.cwd,
                "docs/tdq/plan/2026-11-20-bad-assert.md",
                "\n".join([
                    "# PLAN — bad assert",
                    "## P1 — core",
                    "- [ ] **T1.1** (e5m) Check — Test: `py -3 -m unittest tests/test_real.py`",
                    "  - Chạm: `src/real_mod.py`",  # i18n-allow
                    "  - Neo & Công cụ: `Edit` on `src/real_mod.py` at `real_func()`",  # i18n-allow
                    "  - Ca góc hiểm & Assert:",  # i18n-allow
                    f"    - Tiêu chí: {bad_assert}",  # i18n-allow
                    "",
                ]),
            )
            rc, errs = scaffold.verify_plan(plan, self.cwd)
            self.assertEqual(rc, 1, f"Expected failure for {bad_assert}, got {errs}")

    def test_verify_plan_accepts_greenfield_write_symbols_from_spec(self):
        spec = _write(
            self.cwd,
            "docs/tdq/spec/2026-11-20-gf.md",
            "## 3c. Contracts\n- `src/gf.py`:\n  - `init_gf(flag: bool) -> dict`\n## 4. Req\n",
        )
        plan = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-gf.md",
            "\n".join([
                "# PLAN — gf",
                "## P1 — gf",
                "- [ ] **T1.1** (e5m) Add gf — Test: `py -3 -m unittest tests/test_gf.py`",
                "  - Chạm: `src/gf.py`",  # i18n-allow
                "  - Neo & Công cụ: `Write` new `src/gf.py` (`init_gf`)",  # i18n-allow
                "  - Ca góc hiểm & Assert:",  # i18n-allow
                "    - Tiêu chí: `assert init_gf(True)['ok'] is True`",  # i18n-allow
                "",
            ]),
        )
        rc, out, err = _run_scaffold(self.cwd, "--verify-plan", plan, "--from-spec", spec)
        self.assertEqual(rc, 0, out + err)

    def test_verify_plan_ignores_assert_true_in_ears_prose_and_allows_upstream_write(self):
        plan = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-upstream.md",
            "\n".join([
                "# PLAN — upstream write and EARS prose",
                "## P1 — core",
                "- [ ] **T1.1** (e5m) Create generated module — Test: `py -3 -m unittest tests/test_gen.py`",
                "  - Chạm: `src/generated.py`",  # i18n-allow
                "  - Cần: Không",  # i18n-allow
                "  - Neo & Công cụ: `Write` tạo mới `src/generated.py`",  # i18n-allow
                "  - Tiêu chí chấp nhận (EARS): WHEN input has `assert True`, SYSTEM MUST block it.",  # i18n-allow
                "  - Ca góc hiểm & Assert:",  # i18n-allow
                "    - Ca hiểm: negative case rejects `assert True` input",  # i18n-allow
                "    - Tiêu chí: `assert real_func(1) == 2`",  # i18n-allow
                "- [ ] **T1.2** (e5m) Consume generated module — Test: `py -3 -m unittest tests/test_gen.py`",
                "  - Chạm: `src/real_mod.py`, `src/generated.py`",  # i18n-allow
                "  - Cần: T1.1",  # i18n-allow
                "  - Neo & Công cụ: `Edit` on `src/real_mod.py` at `real_func()`",  # i18n-allow
                "  - Ca góc hiểm & Assert:",  # i18n-allow
                "    - Tiêu chí: `assert real_func(3) == 4`",  # i18n-allow
                "",
            ]),
        )
        rc, errs = scaffold.verify_plan(plan, self.cwd)
        self.assertEqual(rc, 0, errs)


class TestCheckWave(unittest.TestCase):
    """--check-wave validates CONTRACT-DELTA and producer/consumer consistency across waves."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_check_wave_passes_consistent_waves(self):
        plan = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-wave-ok.md",
            "\n".join([
                "# PLAN — wave ok",
                "## P1 — core",
                "- [ ] **T1.1** (e10m) Build index — Test: `pytest`",
                "  - Chạm: `src/idx.py`",  # i18n-allow
                "  - Cần: Không",  # i18n-allow
                "  - Giao tiếp: Consumes: `dict` | Produces: `build_index(items: list) -> dict`",  # i18n-allow
                "  - CONTRACT-DELTA: adds `build_index(items: list) -> dict` in `src/idx.py`",
                "- [ ] **T1.2** (e10m) Use index — Test: `pytest`",
                "  - Chạm: `src/cli.py`",  # i18n-allow
                "  - Cần: T1.1",  # i18n-allow
                "  - Tham chiếu: `src/idx.py` (`build_index`)",  # i18n-allow
                "  - Giao tiếp: Consumes: `build_index(items: list) -> dict` | Produces: `run_cli()`",  # i18n-allow
                "  - CONTRACT-DELTA: none",
                "",
            ]),
        )
        rc, out, err = _run_scaffold(self.cwd, "--check-wave", plan)
        self.assertEqual(rc, 0, out + err)

    def test_check_wave_catches_parallel_conflict_missing_dep_and_signature_mismatch(self):
        plan_parallel = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-wave-conflict.md",
            "\n".join([
                "# PLAN — parallel conflict",
                "## P1 — core",
                "- [ ] **T1.1** (e10m) Producer A — Test: `pytest`",
                "  - Chạm: `src/a.py`",  # i18n-allow
                "  - Cần: Không",  # i18n-allow
                "  - CONTRACT-DELTA: adds `parse_cfg(path: str) -> dict`",
                "- [ ] **T1.2** (e10m) Producer B — Test: `pytest`",
                "  - Chạm: `src/b.py`",  # i18n-allow
                "  - Cần: Không",  # i18n-allow
                "  - CONTRACT-DELTA: adds `parse_cfg(path: str, strict: bool) -> dict`",
                "",
            ]),
        )
        rc_par, out_par, err_par = _run_scaffold(self.cwd, "--check-wave", plan_parallel)
        self.assertEqual(rc_par, 1, out_par + err_par)

        plan_sig = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-wave-sig.md",
            "\n".join([
                "# PLAN — sig mismatch",
                "## P1 — core",
                "- [ ] **T1.1** (e10m) Producer — Test: `pytest`",
                "  - Chạm: `src/a.py`",  # i18n-allow
                "  - Cần: Không",  # i18n-allow
                "  - CONTRACT-DELTA: adds `parse_cfg(path: str, strict: bool) -> dict`",
                "- [ ] **T1.2** (e10m) Consumer — Test: `pytest`",
                "  - Chạm: `src/b.py`",  # i18n-allow
                "  - Cần: T1.1",  # i18n-allow
                "  - Giao tiếp: Consumes: `parse_cfg(path: str)` | Produces: `run()`",  # i18n-allow
                "",
            ]),
        )
        rc_sig, errs_sig = scaffold.check_wave(plan_sig, self.cwd)
        self.assertEqual(rc_sig, 1, errs_sig)

        plan_removed = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-wave-removed.md",
            "\n".join([
                "# PLAN — removed symbol",
                "## P1 — core",
                "- [ ] **T1.1** (e5m) Drop legacy — Test: `pytest`",
                "  - Chạm: `src/a.py`",  # i18n-allow
                "  - Cần: Không",  # i18n-allow
                "  - CONTRACT-DELTA: removes `legacy_fn`",
                "- [ ] **T1.2** (e5m) Use legacy — Test: `pytest`",
                "  - Chạm: `src/b.py`",  # i18n-allow
                "  - Cần: T1.1",  # i18n-allow
                "  - Tham chiếu: `src/a.py` (`legacy_fn`)",  # i18n-allow
                "",
            ]),
        )
        rc_rem, errs_rem = scaffold.check_wave(plan_removed, self.cwd)
        self.assertEqual(rc_rem, 1, errs_rem)

        plan_missing_dep = _write(
            self.cwd,
            "docs/tdq/plan/2026-11-20-wave-nodep.md",
            "\n".join([
                "# PLAN — missing dep",
                "## P1 — core",
                "- [ ] **T1.1** (e5m) Add api — Test: `pytest`",
                "  - Chạm: `src/a.py`",  # i18n-allow
                "  - Giao tiếp: Consumes: `None` | Produces: `make_token(id: str) -> str`",  # i18n-allow
                "- [ ] **T1.2** (e5m) Call api — Test: `pytest`",
                "  - Chạm: `src/b.py`",  # i18n-allow
                "  - Tham chiếu: `src/a.py` (`make_token`)",  # i18n-allow
                "",
            ]),
        )
        rc_dep, errs_dep = scaffold.check_wave(plan_missing_dep, self.cwd)
        self.assertEqual(rc_dep, 1, errs_dep)


class TestLoggingAndCompliance(unittest.TestCase):
    """TDQ_LOG default-on / TDQ_LOG=0 muted, stdlib-only, no hooks import."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_tdq_log_on_by_default_and_silent_when_0(self):
        _write(self.cwd, "src/mod.py", "def ping() -> str:\n    return 'pong'\n")
        rc_on, _out_on, err_on = _run_scaffold(
            self.cwd, "--files", "src/mod.py", env={"TDQ_LOG": "1"}
        )
        self.assertEqual(rc_on, 0, err_on)
        self.assertRegex(err_on, r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\]")

        rc_off, _out_off, err_off = _run_scaffold(
            self.cwd, "--files", "src/mod.py", env={"TDQ_LOG": "0"}
        )
        self.assertEqual(rc_off, 0, err_off)
        self.assertEqual(err_off.strip(), "")

    def test_no_hooks_import_and_stdlib_only(self):
        src_path = os.path.join(SCRIPTS_DIR, "tdq_plan_scaffold.py")
        with open(src_path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=src_path)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module.split(".")[0])
        self.assertNotIn("hooks", imported)
        allowed_local = {"utf8_io", "tdq_team", "tdq_ten_lenh"}
        stdlib = getattr(sys, "stdlib_module_names", set())
        for mod in imported:
            if mod in allowed_local:
                continue
            self.assertIn(mod, stdlib, f"Non-stdlib import not allowed: {mod}")


if __name__ == "__main__":
    unittest.main()
