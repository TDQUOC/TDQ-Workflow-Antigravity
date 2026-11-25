"""Unit tests for 3-tier priority queue, aging, blocked_by, and TCAS wave dispatch."""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

tdq_team = importlib.import_module("tdq_team")

ISO_TS_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def test_constants_preserved():
    """Queue and concurrency constants keep their canonical defaults."""
    assert tdq_team.TRAN_SONG_SONG == 4
    assert tdq_team.OLDEST_DISPATCH_SHARE == 4


def test_prioritize_three_tiers_and_aging_prevents_starvation():
    """After OLDEST_DISPATCH_SHARE high-tier items, 1 globally oldest task promotes."""
    tasks = [
        {"id": "low_old", "priority": "low", "enqueued_at": 10},
        {"id": "low_new", "priority": "low", "enqueued_at": 900},
        {"id": "n1", "priority": "normal", "enqueued_at": 300},
        {"id": "h1", "priority": "high", "enqueued_at": 200},
        {"id": "h2", "priority": "high", "enqueued_at": 201},
        {"id": "h3", "priority": "high", "enqueued_at": 202},
        {"id": "h4", "priority": "high", "enqueued_at": 203},
        {"id": "h5", "priority": "high", "enqueued_at": 204},
        {"id": "h6", "priority": "high", "enqueued_at": 205},
    ]

    out = tdq_team.prioritize_tasks(tasks)
    ids = [t["id"] for t in out]

    assert ids[:5] == ["h1", "h2", "h3", "h4", "low_old"]
    assert ids[5:] == ["h5", "h6", "n1", "low_new"]


def test_prioritize_aging_with_iso_timestamps_and_numeric_age():
    """Aging supports ISO-8601 enqueued_at strings and numeric age fallbacks."""
    iso_tasks = [
        {"id": "low_old", "priority": "low", "enqueued_at": "2026-11-25T08:00:00Z"},
        {"id": "h1", "priority": "high", "enqueued_at": "2026-11-25T10:00:00Z"},
        {"id": "h2", "priority": "high", "enqueued_at": "2026-11-25T10:01:00Z"},
        {"id": "h3", "priority": "high", "enqueued_at": "2026-11-25T10:02:00Z"},
        {"id": "h4", "priority": "high", "enqueued_at": "2026-11-25T10:03:00Z"},
        {"id": "h5", "priority": "high", "enqueued_at": "2026-11-25T10:04:00Z"},
    ]
    assert [t["id"] for t in tdq_team.prioritize_tasks(iso_tasks)][:5] == [
        "h1",
        "h2",
        "h3",
        "h4",
        "low_old",
    ]

    age_tasks = [
        {"id": "low_old", "priority": "low", "age": 500},
        {"id": "h1", "priority": "high", "age": 5},
        {"id": "h2", "priority": "high", "age": 4},
        {"id": "h3", "priority": "high", "age": 3},
        {"id": "h4", "priority": "high", "age": 2},
        {"id": "h5", "priority": "high", "age": 1},
    ]
    assert [t["id"] for t in tdq_team.prioritize_tasks(age_tasks)][:5] == [
        "h1",
        "h2",
        "h3",
        "h4",
        "low_old",
    ]


def test_prioritize_tier_order_default_normal_and_share_overrides():
    """High > normal (default) > low FIFO order, custom share, and zero share."""
    tasks = [
        {"id": "l1", "priority": "low", "enqueued_at": 1},
        {"id": "n1"},
        {"id": "n2", "priority": "normal", "enqueued_at": 30},
        {"id": "h1", "priority": "high", "enqueued_at": 20},
        {"id": "h2", "priority": "high", "enqueued_at": 21},
    ]
    out_default = tdq_team.prioritize_tasks(tasks, oldest_share=2)
    assert [t["id"] for t in out_default] == ["h1", "h2", "l1", "n1", "n2"]

    out_zero = tdq_team.prioritize_tasks(
        [
            {"id": "h1", "priority": "high", "enqueued_at": 50},
            {"id": "l1", "priority": "low", "enqueued_at": 10},
            {"id": "n1", "priority": "normal", "enqueued_at": 20},
        ],
        oldest_share=0,
    )
    assert [t["id"] for t in out_zero] == ["l1", "n1", "h1"]

    with pytest.raises(ValueError):
        tdq_team.prioritize_tasks(tasks, oldest_share=-1)


def test_idempotency_key_deduplication_preserves_first_and_keeps_empty():
    """Non-empty idempotency_key keeps first item; None/empty keys are untouched."""
    tasks = [
        {"id": "a1", "priority": "normal", "idempotency_key": "k-1"},
        {"id": "a2", "priority": "high", "idempotency_key": "k-1"},
        {"id": "none_1", "idempotency_key": None},
        {"id": "none_2", "idempotency_key": None},
        {"id": "empty_1", "idempotency_key": ""},
        {"id": "empty_2", "idempotency_key": "   "},
        {"id": "missing"},
        {"id": "b1", "idempotency_key": "k-2"},
    ]

    out = tdq_team.prioritize_tasks(tasks)
    ids = [t["id"] for t in out]

    assert "a1" in ids
    assert "a2" not in ids
    for kept in ("none_1", "none_2", "empty_1", "empty_2", "missing", "b1"):
        assert kept in ids
    assert len(ids) == 7


def test_dispatch_ready_waves_blocked_by_and_circular_deadlock():
    """Filters unsatisfied blocked_by and exits cleanly on circular deadlocks."""
    tasks = [
        {"id": "done_already", "blocked_by": None},
        {"id": "r1", "blocked_by": None, "files": ["a.py"]},
        {"id": "r2", "blocked_by": [], "files": ["b.py"]},
        {"id": "r3", "blocked_by": {"done_already"}, "files": ["c.py"]},
        {"id": "waiting", "blocked_by": ["done_already", "missing"], "files": ["d.py"]},
        {"id": "dup_1", "idempotency_key": "same", "files": ["e.py"]},
        {"id": "dup_2", "idempotency_key": "same", "files": ["f.py"]},
    ]
    waves = tdq_team.dispatch_ready_waves(tasks, done_ids=["done_already"])
    dispatched_ids = [t["id"] for wave in waves for t in wave]
    assert dispatched_ids == ["r1", "r2", "r3", "dup_1"]
    assert len(waves) == 1

    cycle = [
        {"id": "c1", "blocked_by": ["c2"], "files": ["x.py"]},
        {"id": "c2", "blocked_by": ["c1"], "files": ["y.py"]},
    ]
    assert tdq_team.dispatch_ready_waves(cycle) == []
    assert tdq_team.dispatch_ready_waves([]) == []

    partial = [{"id": "ready_one", "files": ["z.py"]}, *cycle]
    assert [[t["id"] for t in w] for w in tdq_team.dispatch_ready_waves(partial)] == [
        ["ready_one"]
    ]


def test_prioritize_handles_epoch_zero_and_mixed_timestamps():
    """Falsy epoch 0 and mixed naive/UTC/missing enqueued_at never raise TypeError."""
    tasks = [
        {"id": "low_zero", "priority": "low", "enqueued_at": 0},
        {"id": "h1", "priority": "high", "enqueued_at": 10},
        {"id": "h2", "priority": "high", "enqueued_at": "2026-11-25T10:00:00Z"},
        {"id": "h3", "priority": "high", "enqueued_at": "2026-11-25T09:00:00"},
        {"id": "h4", "priority": "high", "enqueued_at": None},
        {"id": "h5", "priority": "high"},
    ]
    out = tdq_team.prioritize_tasks(tasks)
    assert [t["id"] for t in out][:5] == ["h1", "h2", "h3", "h4", "low_zero"]


def test_existing_cli_subcommands_preserved():
    """Existing CLI subcommand table remains unchanged."""
    for name in (
        "assign",
        "audit",
        "wave",
        "open",
        "check",
        "merge",
        "sweep",
        "clean",
    ):
        assert name in tdq_team.LENH


def test_dispatch_ready_waves_respects_cap_and_tcas_collisions(tmp_path: Path):
    """Splits direct/AST TCAS collisions into separate waves and caps at 4."""
    (tmp_path / "producer.py").write_text(
        "def value():\n    return 1\n", encoding="utf-8"
    )
    (tmp_path / "consumer.py").write_text(
        "import producer\n\ndef read():\n    return producer.value()\n",
        encoding="utf-8",
    )
    (tmp_path / "other.py").write_text("X = 2\n", encoding="utf-8")

    # 1. Direct file + AST import collision splitting
    colliding_tasks = [
        {"id": "t_prod", "priority": "high", "files": ["producer.py"]},
        {"id": "t_direct", "priority": "high", "vung_file": ["producer.py"]},
        {"id": "t_ast", "priority": "high", "files": ["consumer.py"]},
        {"id": "t_indep", "priority": "normal", "files": ["other.py"]},
    ]
    waves = tdq_team.dispatch_ready_waves(colliding_tasks, project_root=str(tmp_path))
    wave_ids = [[t["id"] for t in wave] for wave in waves]
    assert wave_ids[0] == ["t_prod", "t_indep"]
    assert len(waves) == 3
    for wave in waves:
        assert len(wave) <= tdq_team.TRAN_SONG_SONG

    # 2. TRAN_SONG_SONG = 4 concurrency cap + aging preserved across waves
    many = [
        {"id": "low_old", "priority": "low", "enqueued_at": 1, "files": ["f0.py"]},
        {"id": "h1", "priority": "high", "enqueued_at": 10, "files": ["f1.py"]},
        {"id": "h2", "priority": "high", "enqueued_at": 11, "files": ["f2.py"]},
        {"id": "h3", "priority": "high", "enqueued_at": 12, "files": ["f3.py"]},
        {"id": "h4", "priority": "high", "enqueued_at": 13, "files": ["f4.py"]},
        {"id": "h5", "priority": "high", "enqueued_at": 14, "files": ["f5.py"]},
    ]
    capped_waves = tdq_team.dispatch_ready_waves(many, project_root=str(tmp_path))
    assert [[t["id"] for t in w] for w in capped_waves] == [
        ["h1", "h2", "h3", "h4"],
        ["low_old", "h5"],
    ]


def test_dispatch_ready_waves_logging_respects_tdq_log(monkeypatch, capsys):
    """Logs ISO-timestamped summary on stderr by default and mutes when TDQ_LOG=0."""
    tasks = [{"id": "t1", "files": ["a.py"]}]

    monkeypatch.setenv("TDQ_LOG", "1")
    tdq_team.dispatch_ready_waves(tasks)
    err_on = capsys.readouterr().err
    assert "dispatch-queue" in err_on
    assert ISO_TS_RE.match(err_on.strip())

    monkeypatch.setenv("TDQ_LOG", "0")
    tdq_team.dispatch_ready_waves(tasks)
    err_off = capsys.readouterr().err
    assert err_off == ""


def test_chia_dot_backward_compatibility_preserved(tmp_path: Path, monkeypatch):
    """Existing chia_dot() dependency and collision wave ordering stays intact."""
    t1 = tdq_team.Task("T1.1", " ", "P1")
    t1.vung_file = ["a.py"]
    t2 = tdq_team.Task("T1.2", " ", "P1")
    t2.vung_file = ["a.py"]
    t3 = tdq_team.Task("T1.3", " ", "P1")
    t3.vung_file = ["b.py"]
    t3.text = ["Do work", f"{tdq_team.NHAN_CAN} T1.1"]

    quyet = {"T1.1": ("giao", ""), "T1.2": ("giao", ""), "T1.3": ("giao", "")}
    monkeypatch.setenv("TDQ_LOG", "0")
    waves = tdq_team.chia_dot([t1, t2, t3], quyet, project_root=str(tmp_path))

    assert waves["T1.1"] == 1
    assert waves["T1.2"] == 2
    assert waves["T1.3"] == 2
