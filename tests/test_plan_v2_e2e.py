#!/usr/bin/env python3
"""E2E suite for Plan V2+ Two-Pass scaffolding, gates, packet assembly, and R15 enforcement."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
for _path in (TESTS_DIR, SCRIPTS_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import tdq_team
import tdq_ten_lenh

TRUONG_PROMPT = ("TASK:", "CỤM:", "BASE:", "WORKTREE:", "VÙNG FILE:", "TEST:", "TRẢ VỀ:")  # i18n-allow
ISO_LOG_PREFIX_RE = r"\[\d{4}-\d{2}-\d{2}"


def _write(root: str, rel_path: str, content: str) -> str:
    full_path = os.path.join(root, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full_path


def _make_env(
    cwd: str, env_overrides: dict[str, str] | None = None, unset_log: bool = False
) -> dict[str, str]:
    full_env = dict(os.environ)
    full_env["TDQ_PROJECT_DIR"] = cwd
    full_env["TDQ_KHOI_TAO_NEN"] = "0"
    full_env["TDQ_KHONG_CHAM_MAY"] = "1"
    if unset_log:
        full_env.pop("TDQ_LOG", None)
    if env_overrides:
        full_env.update(env_overrides)
    return full_env


def _run_cli(
    cwd: str,
    script_name: str,
    *args: str,
    env_overrides: dict[str, str] | None = None,
    unset_log: bool = False,
) -> tuple[int, str, str]:
    proc = tdq_ten_lenh.chay_subprocess(
        [sys.executable, os.path.join(SCRIPTS_DIR, script_name), *args],
        cwd=cwd,
        env=_make_env(cwd, env_overrides=env_overrides, unset_log=unset_log),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _run_ok(
    case: unittest.TestCase, cwd: str, script_name: str, *args: str
) -> tuple[str, str]:
    rc, out, err = _run_cli(cwd, script_name, *args)
    case.assertEqual(rc, 0, f"{script_name} {' '.join(args)} failed:\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    return out, err


def _seed_architecture_doc(cwd: str) -> None:
    _write(
        cwd,
        "docs/kien-truc.md",
        (
            "# Architecture\n\n"
            "## Luật gọi\n\n"  # i18n-allow
            "- Rule 1: `src/` modules must validate external boundary inputs.\n"
            "- Rule 2: `scripts/` must NOT import `hooks/`.\n"
            "- Rule 3: `tests/` may call any layer.\n"
            "- Rule 4: Keep machine-facing stdout English.\n"
        ),
    )


def _seed_greenfield_sources(cwd: str) -> None:
    _write(
        cwd,
        "src/existing_adapter.py",
        (
            "def load_profile(user_id: str) -> dict:\n"
            '    """Load profile record."""\n'
            '    return {"user_id": user_id, "tier": "free"}\n\n\n'
            "def format_reply(payload: dict) -> str:\n"
            "    return f\"{payload.get('user_id', '')}:{payload.get('ok', False)}\"\n"
        ),
    )
    _write(
        cwd,
        "src/native_hash.rs",
        (
            "pub struct HashConfig {\n"
            "    pub seed: u64,\n"
            "}\n\n"
            "pub fn compute_hash(seed: u64) -> u64 {\n"
            "    let internal_salt = 0x517cc1b727220a95;\n"
            "    seed.wrapping_mul(31) ^ internal_salt\n"
            "}\n"
        ),
    )
    _write(
        cwd,
        "src/green_consumer.py",
        (
            "def handle_green_request(user_id: str) -> dict:\n"
            '    return {"user_id": user_id, "handled": False}\n'
        ),
    )


def _greenfield_spec_md() -> str:
    return (
        "# SPEC — Greenfield Session\n\n"
        "Ngày: 2026-11-20 · Bản: 1.0 · Lane: full\n\n"  # i18n-allow
        "## 2b. Ranh giới module\n\n"  # i18n-allow
        "| Module | Vùng file | Phụ thuộc module | Đầu ra §2 nào |\n"  # i18n-allow
        "|---|---|---|---|\n"
        "| session | `src/green_svc.py`, `src/existing_adapter.py` | không | 1 |\n"  # i18n-allow
        "| consumer | `src/green_consumer.py` | session | 2 |\n\n"
        "## 3b. Năng lực & công cụ\n\n"  # i18n-allow
        "| Công cụ | Mục đích | Phán quyết | Lý do |\n"  # i18n-allow
        "|---|---|---|---|\n"
        "| `tdq-build` | Execute implementation | DÙNG | Implement tasks |\n"  # i18n-allow
        "| `tdq-lean` | Scope guard | NỀN | Built-in workflow check |\n\n"  # i18n-allow
        "## 3c. Contracts\n\n"
        "| File | Signature | Purpose |\n"
        "|---|---|---|\n"
        "| `src/green_svc.py` | `create_session(user_id: str, limit: int = 10) -> dict` | Build session payload |\n\n"
        "## 6. QC & Definition of Done\n\n"
        "| # | Hạng mục kiểm | Điều kiện PASS | Đo trước | Dự phòng nếu trượt |\n"  # i18n-allow
        "|---|---|---|---|---|\n"
        "| Q1 | Session latency | Latency < 50 ms on empty store | Baseline 10 ms measured | Fallback to cache |\n"  # i18n-allow
    )


def _greenfield_pass1_plan_md() -> str:
    return (
        "# PLAN — 2026-11-20-0100-green (Pass 1)\n\n"
        "Ngày: 2026-11-20 · Lane: full\n\n"  # i18n-allow
        "## P1 — Core\n"
        "- [ ] **T1.1** (e10m) Create green session — Test: `py -3 -m unittest tests/test_green.py -v`\n"
        "  - Chạm: `src/green_svc.py`\n"  # i18n-allow
        "  - Cần: Không\n"  # i18n-allow
    )


def _greenfield_tasks_lines() -> list[str]:
    return [
        "## P1 — Core",
        "- [ ] **T1.1** (e10m) Create green session service — Test: `py -3 -m unittest tests/test_green.py -v`",
        "  - Req: `§2 #1` · Ngoài phạm vi: `GIỮ NGUYÊN` `format_reply()` signature",  # i18n-allow
        "  - Chạm: `src/green_svc.py`, `src/existing_adapter.py`",  # i18n-allow
        "  - Tham chiếu: `src/native_hash.rs` (`compute_hash`)",  # i18n-allow
        "  - Sinh ra: `docs/green-api.md`",
        "  - Cần: Không",  # i18n-allow
        "  - Giao tiếp: Consumes: `compute_hash(seed: u64) -> u64` | Produces: `create_session(user_id: str, limit: int = 10) -> dict`",  # i18n-allow
        "  - CONTRACT-DELTA: adds `create_session(user_id: str, limit: int = 10) -> dict` in `src/green_svc.py`",
        "  - Neo & Công cụ: `Write` new `src/green_svc.py` (`create_session`); `Edit` on `src/existing_adapter.py` at `load_profile()` (`L1-3`)",  # i18n-allow
        "  - Trước → Sau: missing creator -> `create_session` builds session payload",  # i18n-allow
        "  - Tiêu chí chấp nhận (EARS): WHEN `create_session('u1')` runs, SYSTEM MUST return dict with `ok=True`",  # i18n-allow
        "  - Logic cốt lõi:",  # i18n-allow
        "    1. Validate non-empty `user_id` and positive `limit`.",
        "    2. Return normalized session dictionary.",
        "  - Ca góc hiểm & Assert:",  # i18n-allow
        "    - Ca hiểm: empty user_id raises ValueError",  # i18n-allow
        "    - Tiêu chí: `assert create_session('u1', 5)['limit'] == 5`",  # i18n-allow
        "- [ ] **T1.2** (e10m) Wire green consumer — Test: `py -3 -m unittest tests/test_green.py -v`",
        "  - Req: `§2 #2` · Ngoài phạm vi: `GIỮ NGUYÊN` HTTP envelope keys",  # i18n-allow
        "  - Chạm: `src/green_consumer.py`",  # i18n-allow
        "  - Tham chiếu: `src/green_svc.py` (`create_session`)",  # i18n-allow
        "  - Cần: T1.1",  # i18n-allow
        "  - Giao tiếp: Consumes: `create_session(user_id: str, limit: int = 10) -> dict` | Produces: `handle_green_request(user_id: str) -> dict`",  # i18n-allow
        "  - CONTRACT-DELTA: none",
        "  - Neo & Công cụ: `Edit` on `src/green_consumer.py` at `handle_green_request()` (`L1-2`)",  # i18n-allow
        "  - Trước → Sau: static stub -> calls `create_session` and returns `handled=True`",  # i18n-allow
        "  - Tiêu chí chấp nhận (EARS): WHEN `handle_green_request('u1')` runs, SYSTEM MUST call `create_session`",  # i18n-allow
        "  - Logic cốt lõi:",  # i18n-allow
        "    1. Delegate to `create_session(user_id)`.",
        "    2. Return combined response dict.",
        "  - Ca góc hiểm & Assert:",  # i18n-allow
        "    - Ca hiểm: blank user_id propagates ValueError",  # i18n-allow
        "    - Tiêu chí: `assert handle_green_request('u1')['handled'] is True`",  # i18n-allow
    ]


def _greenfield_full_plan_md() -> str:
    header = [
        "# PLAN — 2026-11-20-0100-green",
        "",
        "Ngày: 2026-11-20 · Lane: full · Spec: ../spec/2026-11-20-0100-green.md",  # i18n-allow
        "",
        "## Ownership Map",
        "",
        "| Contract | Owner | Users |",
        "|---|---|---|",
        "| `create_session(user_id: str, limit: int = 10) -> dict` | `src/green_svc.py` (`T1.1`) | `T1.2` |",
        "",
        "## Tool Contracts",
        "",
        "- Dùng: `tdq-build`",  # i18n-allow
        "  - Để: execute wave tasks cleanly",  # i18n-allow
        "  - Ra: verified module edits",
        "  - Kiểm: unit tests pass",  # i18n-allow
        "  - Không dùng cho: spec modification",  # i18n-allow
        "",
        "## Cụm song song",  # i18n-allow
        "",
        "Wave 1: T1.1 -> Wave 2: T1.2.",
        "",
    ]
    footer = [
        "",
        "## Definition of Done",
        "",
        "- [ ] Q1 Session passes — `assert create_session('u1')['ok'] is True`",
        "",
    ]
    return "\n".join(header + _greenfield_tasks_lines() + footer)


def _seed_refactor_repo(cwd: str) -> None:
    _seed_architecture_doc(cwd)
    _write(
        cwd,
        "src/service.py",
        (
            "# service module\n"
            "def unrelated_fn(code: str) -> str:\n"
            "    return code.upper()\n\n"
            "# span-before-1\n"
            "def compute_discount(amount: float, rate: float) -> float:\n"
            '    """Compute bounded discount."""\n'
            "    clamped = max(0.0, min(rate, 0.5))\n"
            "    return round(amount * clamped, 2)\n"
            "# span-after-1\n"
        ),
    )
    _write(
        cwd,
        "src/caller.py",
        (
            "def invoke_discount(order_id: str, rate: float) -> dict:\n"
            '    """Caller wrapper."""\n'
            "    INTERNAL_CALLER_SECRET_BODY = 999\n"
            '    return {"order_id": order_id, "rate": rate, "tag": INTERNAL_CALLER_SECRET_BODY}\n'
        ),
    )


def _refactor_tasks_lines() -> list[str]:
    return [
        "## P1 — Refactor",
        "- [ ] **T1.1** (e10m) Refactor `compute_discount` — Test: `py -3 -m unittest tests/test_svc.py`",
        "  - Req: `§2 #1` · Ngoài phạm vi: `GIỮ NGUYÊN` `unrelated_fn()` API",  # i18n-allow
        "  - Chạm: `src/service.py`",  # i18n-allow
        "  - Tham chiếu: `src/caller.py` (`invoke_discount`)",  # i18n-allow
        "  - Cần: Không",  # i18n-allow
        "  - Giao tiếp: Consumes: `float` | Produces: `compute_discount(amount: float, rate: float) -> float`",  # i18n-allow
        "  - Vị trí neo: `src/service.py:6-9`",  # i18n-allow
        "  - Neo & Công cụ: `Edit` on `src/service.py` at `compute_discount()` (`L6-9`)",  # i18n-allow
        "  - Trước → Sau: unchecked rate -> clamped rate in `[0.0, 0.5]`",  # i18n-allow
        "  - Tiêu chí chấp nhận (EARS): WHEN `rate > 0.5`, SYSTEM MUST clamp discount rate to `0.5`",  # i18n-allow
        "  - Logic cốt lõi:",  # i18n-allow
        "    1. Clamp rate to `[0.0, 0.5]`.",
        "    2. Return rounded discount amount.",
        "  - Ca góc hiểm & Assert:",  # i18n-allow
        "    - Ca hiểm: negative rate clamps to 0.0",  # i18n-allow
        "    - Tiêu chí: `assert compute_discount(100.0, 0.9) == 50.0`",  # i18n-allow
        "- [ ] **T1.2** (e10m) Update caller integration — Test: `py -3 -m unittest tests/test_caller.py`",
        "  - Req: `§2 #2` · Ngoài phạm vi: `GIỮ NGUYÊN` return dict keys",  # i18n-allow
        "  - Chạm: `src/caller.py`",  # i18n-allow
        "  - Tham chiếu: `src/service.py` (`compute_discount`)",  # i18n-allow
        "  - Cần: T1.1",  # i18n-allow
        "  - Giao tiếp: Consumes: `compute_discount(amount: float, rate: float) -> float` | Produces: `invoke_discount(order_id: str, rate: float) -> dict`",  # i18n-allow
        "  - Neo & Công cụ: `Edit` on `src/caller.py` at `invoke_discount()` (`L1-4`)",  # i18n-allow
        "  - Trước → Sau: static tag -> includes computed discount",  # i18n-allow
        "  - Tiêu chí chấp nhận (EARS): WHEN `invoke_discount` runs, SYSTEM MUST return bounded discount",  # i18n-allow
        "  - Logic cốt lõi:",  # i18n-allow
        "    1. Invoke `compute_discount(100.0, rate)`.",
        "    2. Return summary dictionary.",
        "  - Ca góc hiểm & Assert:",  # i18n-allow
        "    - Ca hiểm: zero rate returns 0.0 discount",  # i18n-allow
        "    - Tiêu chí: `assert invoke_discount('o1', 0.0)['rate'] == 0.0`",  # i18n-allow
    ]


def _refactor_plan_md() -> str:
    header = [
        "# PLAN — 2026-11-20-0200-refactor",
        "",
        "Ngày: 2026-11-20 · Lane: full",  # i18n-allow
        "",
        "## Ownership Map",
        "",
        "Prose note: preserve caller boundary.",
        "",
        "| Contract | Owner | Users |",
        "|---|---|---|",
        "| `compute_discount(amount: float, rate: float) -> float` | `src/service.py` (`T1.1`) | `T1.2` |",
        "",
        "## Cụm song song",  # i18n-allow
        "",
        "Wave 1: T1.1 -> Wave 2: T1.2.",
        "",
    ]
    footer = [
        "",
        "## Definition of Done",
        "",
        "- [ ] Q1 Refactor passes — `assert compute_discount(10.0, 0.2) == 2.0`",
        "",
    ]
    return "\n".join(header + _refactor_tasks_lines() + footer)


def _quick_sweep_plan_md() -> str:
    return (
        "# QUICK — Uniform Mechanical Sweep\n\n"
        "Ngày: 2026-11-20 · Lane: quick\n\n"  # i18n-allow
        "## Cụm song song\n\n"  # i18n-allow
        "Single cluster (quick sweep).\n\n"
        "## P1 — Sweep\n"
        "- [ ] **T1.1** (e5m) Uniform Mechanical Sweep across 5 helpers — Test: `py -3 -m unittest tests/test_sweep.py`\n"
        "  - Loại: Uniform Mechanical Sweep\n"  # i18n-allow
        "  - Chạm:\n"  # i18n-allow
        "    - `src/m1.py`\n"
        "    - `src/m2.py`\n"
        "    - `src/m3.py`\n"
        "    - `src/m4.py`\n"
        "    - `src/m5.py`\n"
        "  - Vị trí neo: `src/m1.py`..`src/m5.py` (`VERSION = 2`)\n"  # i18n-allow
        "  - Trước → Sau: `VERSION = 1` -> `VERSION = 2`\n"  # i18n-allow
        "  - Logic: Update constant `VERSION` from `1` to `2` in each listed module.\n"
        "  - Tiêu chí: `assert m1.VERSION == 2 and m5.VERSION == 2`\n\n"  # i18n-allow
        "## Definition of Done\n\n"
        "- [ ] Q1 Sweep — `assert m1.VERSION == 2`\n"
    )


def _valid_gate_plan_md() -> str:
    return (
        "# PLAN — Gate Baseline\n\n"
        "Ngày: 2026-11-20 · Lane: full\n\n"  # i18n-allow
        "## Ownership Map\n\n"
        "| Contract | Owner | Users |\n"
        "|---|---|---|\n"
        "| `run` | `src/app.py` | `T1.1` |\n\n"
        "## Cụm song song\n\n"  # i18n-allow
        "Single cluster.\n\n"
        "## P1 — Core\n"
        "- [ ] **T1.1** (e5m) Implement runner — Test: `py -3 -m unittest tests/test_app.py`\n"
        "  - Req: `§2 #1` · Ngoài phạm vi: `GIỮ NGUYÊN` CLI flags\n"  # i18n-allow
        "  - Chạm: `src/app.py`\n"  # i18n-allow
        "  - Neo & Công cụ: `Edit` on `src/app.py` (`run()`)\n"  # i18n-allow
        "  - Trước → Sau: `run()` returns None -> returns status dict\n"  # i18n-allow
        "  - Tiêu chí chấp nhận (EARS): WHEN `run()` is called, SYSTEM MUST return status dict\n"  # i18n-allow
        "  - Logic cốt lõi:\n"  # i18n-allow
        "    1. Build status payload.\n"
        "    2. Return payload dict.\n"
        "  - Ca góc hiểm & Assert:\n"  # i18n-allow
        "    - Ca hiểm: empty payload\n"  # i18n-allow
        "    - Tiêu chí: `assert run({})['ok'] is True`\n"  # i18n-allow
    )


def _bad_plan_variants() -> dict[str, str]:
    valid = _valid_gate_plan_md()
    return {
        "missing_mini_spec": (
            "# PLAN — Missing Mini-Spec\n\n"
            "Ngày: 2026-11-20 · Lane: full\n\n"  # i18n-allow
            "- [ ] **T1.1** (e5m) Incomplete task — Test: `py -3 -m unittest tests/test_app.py`\n"
            "  - Chạm: `src/app.py`\n"  # i18n-allow
            "  - Logic: Return dict.\n"
        ),
        "banned_tbd": valid.replace("Build status payload.", "TBD"),
        "anti2_assert_true": valid.replace("assert run({})['ok'] is True", "assert True"),
    }


def _legacy_plan_md() -> str:
    return (
        "# PLAN — Legacy Pre-Cutoff\n\n"
        "Ngày: 2026-11-19 · Lane: full\n\n"  # i18n-allow
        "- [ ] **T1.1** (e5m) Legacy update — Test: `py -3 -m unittest tests/test_app.py`\n"
        "  - Chạm: `src/app.py`\n"  # i18n-allow
        "  - Logic: Keep legacy entry point returning status dict.\n"
    )


class TestPlanV2GreenfieldE2E(unittest.TestCase):
    """Scenario 1: Greenfield Two-Pass + --emit-cards + verify/wave/lint + state gates + packet."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def _run_greenfield_state_gates(self, spec_rel: str, plan_rel: str) -> None:
        _run_ok(self, self.cwd, "tdq_state.py", "init", "2026-11-20-0100-green", "full", "--bo-qua-lsp", "e2e")
        _run_ok(self, self.cwd, "tdq_state.py", "set", "lane=full")
        _run_ok(self, self.cwd, "tdq_state.py", "set", "phase=spec", f"spec_file={spec_rel}")
        _run_ok(
            self,
            self.cwd,
            "tdq_state.py",
            "approve",
            "spec",
            "--by",
            "approve spec",
            "--bo-qua-archify",
            "e2e",
        )
        _run_ok(self, self.cwd, "tdq_state.py", "set", "phase=plan", f"plan_file={plan_rel}")
        _run_ok(self, self.cwd, "tdq_state.py", "approve", "plan", "--mode", "subagent", "--by", "approve plan")

    def _assert_greenfield_packet(self, packet_out: str) -> None:
        for field in TRUONG_PROMPT:
            self.assertIn(field, packet_out)
        self.assertIn("## Symbol-Spans", packet_out)
        self.assertIn("[NEW FILE] `src/green_svc.py`", packet_out)
        self.assertIn("## Reference Signatures", packet_out)
        self.assertIn("## Architecture Invariants", packet_out)
        self.assertIn("pub fn compute_hash(seed: u64) -> u64", packet_out)
        self.assertNotIn("internal_salt", packet_out)

    def test_greenfield_full_flow_end_to_end(self):
        _seed_architecture_doc(self.cwd)
        _seed_greenfield_sources(self.cwd)
        spec_rel = "docs/tdq/spec/2026-11-20-0100-green.md"
        plan_rel = "docs/tdq/plan/2026-11-20-0100-green.md"
        _write(self.cwd, spec_rel, _greenfield_spec_md())
        _write(self.cwd, plan_rel, _greenfield_pass1_plan_md())

        out_cards, _ = _run_ok(
            self, self.cwd, "tdq_plan_scaffold.py", "--root", self.cwd,
            "--from-spec", spec_rel, "--plan", plan_rel,
            "--files", "src/existing_adapter.py", "--refs", "src/native_hash.rs", "--emit-cards",
        )
        self.assertIn("Req:", out_cards)
        self.assertIn("§3c", out_cards)
        self.assertIn("ANCHOR_CONFIDENCE: LOW", out_cards)
        self.assertRegex(out_cards, r"`load_profile`\s*\(L\d+-\d+\)")
        self.assertIn("def load_profile(user_id: str) -> dict:", out_cards)

        _write(self.cwd, plan_rel, _greenfield_full_plan_md())
        _run_ok(
            self, self.cwd, "tdq_plan_scaffold.py", "--root", self.cwd,
            "--verify-plan", plan_rel, "--from-spec", spec_rel,
        )
        _run_ok(self, self.cwd, "tdq_plan_scaffold.py", "--root", self.cwd, "--check-wave", plan_rel)
        _run_ok(self, self.cwd, "doc_lint.py", "--pair", spec_rel, plan_rel)

        self._run_greenfield_state_gates(spec_rel, plan_rel)
        _run_ok(self, self.cwd, "tdq_team.py", "assign")
        _run_ok(self, self.cwd, "tdq_team.py", "audit")
        packet_out, _ = _run_ok(self, self.cwd, "tdq_team.py", "packet", "T1.1")
        self._assert_greenfield_packet(packet_out)


class TestPlanV2RefactorAndStaleE2E(unittest.TestCase):
    """Scenario 2: Multi-file refactor + Ownership Map + GIỮ NGUYÊN + SHA stability + packet spans."""  # i18n-allow

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_refactor_ownership_giu_nguyen_stale_guard_and_packet_spans(self):
        _seed_refactor_repo(self.cwd)
        slug = "2026-11-20-0200-refactor"
        plan_rel = f"docs/tdq/plan/{slug}.md"
        base_plan = _refactor_plan_md()
        plan_abs = _write(self.cwd, plan_rel, base_plan)

        _run_ok(self, self.cwd, "doc_lint.py", plan_rel)
        _run_ok(self, self.cwd, "tdq_plan_scaffold.py", "--root", self.cwd, "--verify-plan", plan_rel)
        _run_ok(self, self.cwd, "tdq_state.py", "init", slug, "full", "--bo-qua-lsp", "e2e")
        _run_ok(self, self.cwd, "tdq_state.py", "set", f"plan_file={plan_rel}")
        _run_ok(self, self.cwd, "tdq_team.py", "assign")

        sha_before, mode_before = tdq_team.tinh_sha_projection(tdq_team.doc_plan(plan_abs))
        self.assertEqual(mode_before, "explicit")

        edited_anchor = (
            base_plan
            .replace("`src/service.py:6-9`", "`src/service.py:16-24`")
            .replace("`L6-9`", "`L16-24`")
            .replace("Prose note: preserve caller boundary.", "Prose note: keep unrelated_fn untouched.")
        )
        _write(self.cwd, plan_rel, edited_anchor)
        sha_after, mode_after = tdq_team.tinh_sha_projection(tdq_team.doc_plan(plan_abs))
        self.assertEqual(mode_after, "explicit")
        self.assertEqual(sha_before, sha_after)
        _run_ok(self, self.cwd, "tdq_team.py", "audit")

        changed_cham = edited_anchor.replace("- Chạm: `src/service.py`", "- Chạm: `src/service.py`, `src/extra.py`")  # i18n-allow
        _write(self.cwd, plan_rel, changed_cham)
        sha_cham, _ = tdq_team.tinh_sha_projection(tdq_team.doc_plan(plan_abs))
        self.assertNotEqual(sha_before, sha_cham)

        _write(self.cwd, plan_rel, base_plan)
        packet_out, _ = _run_ok(self, self.cwd, "tdq_team.py", "packet", "T1.1", "--plan", plan_rel)
        self.assertIn("## Symbol-Spans", packet_out)
        self.assertIn("def compute_discount(amount: float, rate: float) -> float:", packet_out)
        self.assertIn("## Reference Signatures", packet_out)
        ref_section = packet_out.split("## Reference Signatures", 1)[1].split("## ", 1)[0]
        sig_lines = [ln for ln in ref_section.splitlines() if ln.strip().startswith("- ")]
        self.assertEqual(sig_lines, ["- `src/caller.py`: `def invoke_discount(order_id: str, rate: float) -> dict:`"])
        self.assertNotIn("INTERNAL_CALLER_SECRET_BODY", packet_out)


class TestPlanV2QuickNegativeAndLoggingE2E(unittest.TestCase):
    """Scenario 3: Quick R15-Compact sweep + negative R15 gates + pre-cutoff legacy + TDQ_LOG."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def _setup_full_ready_for_plan(self, work_dir: str, slug: str) -> str:
        spec_rel = f"docs/tdq/spec/{slug}.md"
        _write(work_dir, spec_rel, "# Spec\n\n## 1. Goal\n\nVerify R15 gate.\n")
        _run_ok(self, work_dir, "tdq_state.py", "init", slug, "full", "--bo-qua-lsp", "e2e")
        _run_ok(self, work_dir, "tdq_state.py", "set", "phase=spec", f"spec_file={spec_rel}")
        _run_ok(
            self,
            work_dir,
            "tdq_state.py",
            "approve",
            "spec",
            "--by",
            "approve spec",
            "--bo-qua-do",
            "e2e",
            "--bo-qua-archify",
            "e2e",
        )
        return f"docs/tdq/plan/{slug}.md"

    def test_quick_compact_sweep_5_files_and_fail_open_without_plan(self):
        slug = "2026-11-20-0300-sweep"
        plan_rel = f"docs/tdq/plan/{slug}.md"
        plan_abs = _write(self.cwd, plan_rel, _quick_sweep_plan_md())
        self.assertEqual(len(tdq_team.doc_plan(plan_abs)[0].vung_file), 5)

        _run_ok(self, self.cwd, "doc_lint.py", plan_rel)
        _run_ok(self, self.cwd, "tdq_state.py", "init", slug, "quick", "--bo-qua-lsp", "e2e")
        _run_ok(self, self.cwd, "tdq_state.py", "set", "lane=quick")
        _run_ok(self, self.cwd, "tdq_state.py", "set", f"plan_file={plan_rel}")
        _run_ok(
            self,
            self.cwd,
            "tdq_state.py",
            "approve",
            "quick",
            "--by",
            "duyet nhanh",  # i18n-allow
            "--bo-qua-archify",
            "e2e",
        )
        approved_out, _ = _run_ok(self, self.cwd, "tdq_state.py", "get", "quick_approved")
        self.assertEqual(approved_out.strip(), "true")

        no_plan_dir = os.path.join(self.cwd, "no_plan")
        os.makedirs(no_plan_dir, exist_ok=True)
        _run_ok(self, no_plan_dir, "tdq_state.py", "init", "2026-11-20-0301-noplan", "quick", "--bo-qua-lsp", "e2e")
        _run_ok(
            self,
            no_plan_dir,
            "tdq_state.py",
            "approve",
            "quick",
            "--by",
            "duyet nhanh",  # i18n-allow
            "--bo-qua-archify",
            "e2e",
        )
        no_plan_out, _ = _run_ok(self, no_plan_dir, "tdq_state.py", "get", "quick_approved")
        self.assertEqual(no_plan_out.strip(), "true")

    def test_negative_r15_gates_and_pre_moc_legacy_pass(self):
        for idx, (name, bad_md) in enumerate(_bad_plan_variants().items(), start=1):
            with self.subTest(case=name):
                sub_dir = os.path.join(self.cwd, name)
                os.makedirs(sub_dir, exist_ok=True)
                slug = f"2026-11-20-040{idx}-bad"
                plan_rel = self._setup_full_ready_for_plan(sub_dir, slug)
                plan_abs = _write(sub_dir, plan_rel, bad_md)

                rc_lint, out_lint, _ = _run_cli(sub_dir, "doc_lint.py", plan_rel)
                self.assertEqual(rc_lint, 1, out_lint)
                self.assertIn("R15", out_lint)

                rc_set, _, err_set = _run_cli(sub_dir, "tdq_state.py", "set", f"plan_file={plan_rel}")
                self.assertEqual(rc_set, 1, err_set)
                self.assertIn("R15", err_set)

                _write(sub_dir, plan_rel, _valid_gate_plan_md())
                _run_ok(self, sub_dir, "tdq_state.py", "set", "phase=plan", f"plan_file={plan_rel}")
                with open(plan_abs, "w", encoding="utf-8") as fh:
                    fh.write(bad_md)
                rc_app, _, err_app = _run_cli(
                    sub_dir, "tdq_state.py", "approve", "plan", "--mode", "subagent", "--by", "approve plan"
                )
                self.assertEqual(rc_app, 1, err_app)
                self.assertIn("R15", err_app)
                app_state, _ = _run_ok(self, sub_dir, "tdq_state.py", "get", "plan_approved")
                self.assertEqual(app_state.strip(), "false")

        legacy_dir = os.path.join(self.cwd, "legacy")
        os.makedirs(legacy_dir, exist_ok=True)
        legacy_slug = "2026-11-19-0900-legacy"
        legacy_plan = self._setup_full_ready_for_plan(legacy_dir, legacy_slug)
        _write(legacy_dir, legacy_plan, _legacy_plan_md())
        _run_ok(self, legacy_dir, "doc_lint.py", legacy_plan)
        _run_ok(self, legacy_dir, "tdq_state.py", "set", "phase=plan", f"plan_file={legacy_plan}")
        _run_ok(self, legacy_dir, "tdq_state.py", "approve", "plan", "--mode", "subagent", "--by", "approve plan")
        leg_state, _ = _run_ok(self, legacy_dir, "tdq_state.py", "get", "plan_approved")
        self.assertEqual(leg_state.strip(), "true")

    def test_tdq_log_default_on_and_muted_with_0_for_scaffold_and_packet(self):
        _write(self.cwd, "src/mod.py", "def ping() -> str:\n    return 'pong'\n")
        plan_rel = "docs/tdq/plan/2026-11-20-0500-log.md"
        _write(
            self.cwd,
            plan_rel,
            (
                "# PLAN — Log Check\n\n"
                "## P1 — core\n"
                "- [ ] **T1.1** (e5m) Check `ping` — Test: `py -3 -m unittest`\n"
                "  - Chạm: `src/mod.py`\n"  # i18n-allow
            ),
        )

        calls: list[tuple[str, tuple[str, ...]]] = [
            ("tdq_plan_scaffold.py", ("--root", self.cwd, "--files", "src/mod.py")),
            ("tdq_team.py", ("packet", "T1.1", "--plan", plan_rel)),
        ]
        for script_name, args in calls:
            with self.subTest(script=script_name):
                rc_on, _, err_on = _run_cli(self.cwd, script_name, *args, unset_log=True)
                self.assertEqual(rc_on, 0, err_on)
                self.assertRegex(err_on, ISO_LOG_PREFIX_RE)

                rc_off, _, err_off = _run_cli(
                    self.cwd, script_name, *args, env_overrides={"TDQ_LOG": "0"}
                )
                self.assertEqual(rc_off, 0, err_off)
                self.assertEqual(err_off.strip(), "")


if __name__ == "__main__":
    unittest.main()
