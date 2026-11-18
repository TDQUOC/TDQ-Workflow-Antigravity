"""Tests for persistent repo_root cache and PowerShell search parsing."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = str(ROOT / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import search_rules as sr  # noqa: E402
import tdq_state  # noqa: E402


def _setup_fake_temp_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    temp_dir = tmp_path / "temp_cache"
    temp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(temp_dir))
    monkeypatch.setattr(tdq_state, "_ROOT_CACHE", {})
    return temp_dir


def test_find_git_head_directory_and_nested_subdir(tmp_path: Path) -> None:
    """Locate .git/HEAD from the repo root or a nested subdirectory."""
    repo = tmp_path / "repo"
    head = repo / ".git" / "HEAD"
    head.parent.mkdir(parents=True)
    head.write_text("ref: refs/heads/main\n", encoding="utf-8")
    nested = repo / "src" / "pkg" / "sub"
    nested.mkdir(parents=True)

    assert tdq_state._find_git_head(str(repo)) == str(head)
    assert tdq_state._find_git_head(str(nested)) == str(head)


def test_find_git_head_respects_max_depth(tmp_path: Path) -> None:
    """Stop searching parent directories once max_depth is reached."""
    repo = tmp_path / "repo"
    head = repo / ".git" / "HEAD"
    head.parent.mkdir(parents=True)
    head.write_text("ref: refs/heads/main\n", encoding="utf-8")
    deep = repo / "d1" / "d2" / "d3" / "d4"
    deep.mkdir(parents=True)

    assert tdq_state._find_git_head(str(deep), max_depth=3) is None
    assert tdq_state._find_git_head(str(deep), max_depth=4) == str(head)


def test_find_git_head_worktree_gitdir_file(tmp_path: Path) -> None:
    """Resolve HEAD when .git is a gitdir pointer file (absolute or relative)."""
    real_gitdir = tmp_path / "main_repo" / ".git" / "worktrees" / "t1"
    real_gitdir.mkdir(parents=True)
    head = real_gitdir / "HEAD"
    head.write_text("ref: refs/heads/feat\n", encoding="utf-8")

    wt_abs = tmp_path / "wt_abs"
    wt_abs.mkdir()
    (wt_abs / ".git").write_text(f"gitdir: {real_gitdir}\n", encoding="utf-8")

    wt_rel = tmp_path / "main_repo" / "wt_rel"
    wt_rel_sub = wt_rel / "sub"
    wt_rel_sub.mkdir(parents=True)
    (wt_rel / ".git").write_text("gitdir: ../.git/worktrees/t1\n", encoding="utf-8")

    assert tdq_state._find_git_head(str(wt_abs)) == str(head)
    assert tdq_state._find_git_head(str(wt_rel_sub)) == str(head)


def test_repo_root_disk_cache_avoids_subprocess_across_spawns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clearing _ROOT_CACHE still hits JSON cache with 0 _git calls."""
    temp_dir = _setup_fake_temp_root(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    head = repo / ".git" / "HEAD"
    head.parent.mkdir(parents=True)
    head.write_text("ref: refs/heads/main\n", encoding="utf-8")
    sub = repo / "scripts"
    sub.mkdir()

    calls = []

    def fake_git(cwd, *args):
        calls.append((cwd, args))
        return (str(repo) + "\n").encode("utf-8")

    monkeypatch.setattr(tdq_state, "_git", fake_git)

    assert tdq_state.repo_root(str(sub)) == str(repo)
    assert len(calls) == 1
    cache_file = temp_dir / "tdq-repo-roots.json"
    assert cache_file.is_file()

    # Simulate fresh hook subprocess: clear in-memory cache
    tdq_state._ROOT_CACHE.clear()
    assert tdq_state.repo_root(str(sub)) == str(repo)
    assert len(calls) == 1


def test_repo_root_invalidates_when_head_mtime_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing .git/HEAD mtime_ns invalidates disk cache and refreshes via _git."""
    _setup_fake_temp_root(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    head = repo / ".git" / "HEAD"
    head.parent.mkdir(parents=True)
    head.write_text("ref: refs/heads/main\n", encoding="utf-8")

    calls = []

    def fake_git(cwd, *args):
        calls.append(cwd)
        return str(repo).encode("utf-8")

    monkeypatch.setattr(tdq_state, "_git", fake_git)

    assert tdq_state.repo_root(str(repo)) == str(repo)
    assert len(calls) == 1

    old_stat = os.stat(head)
    os.utime(head, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 5_000_000))
    tdq_state._ROOT_CACHE.clear()

    assert tdq_state.repo_root(str(repo)) == str(repo)
    assert len(calls) == 2

    tdq_state._ROOT_CACHE.clear()
    assert tdq_state.repo_root(str(repo)) == str(repo)
    assert len(calls) == 2


def test_repo_root_handles_corrupt_json_and_missing_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Corrupt cache JSON or deleted cached root falls back to _git and heals cache."""
    temp_dir = _setup_fake_temp_root(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    head = repo / ".git" / "HEAD"
    head.parent.mkdir(parents=True)
    head.write_text("ref: refs/heads/main\n", encoding="utf-8")

    cache_file = temp_dir / "tdq-repo-roots.json"
    cache_file.write_text("{broken json", encoding="utf-8")

    calls = []

    def fake_git(cwd, *args):
        calls.append(cwd)
        return str(repo).encode("utf-8")

    monkeypatch.setattr(tdq_state, "_git", fake_git)

    assert tdq_state.repo_root(str(repo)) == str(repo)
    assert len(calls) == 1
    healed = json.loads(cache_file.read_text(encoding="utf-8"))
    assert healed[os.path.abspath(str(repo))]["root"] == str(repo)

    # Point cached root to a non-existent directory with matching mtime_ns
    tdq_state._ROOT_CACHE.clear()
    mtime_ns = os.stat(head).st_mtime_ns
    stale_payload = {
        os.path.abspath(str(repo)): {
            "root": str(tmp_path / "removed_dir"),
            "head_mtime_ns": mtime_ns,
        }
    }
    cache_file.write_text(json.dumps(stale_payload), encoding="utf-8")

    assert tdq_state.repo_root(str(repo)) == str(repo)
    assert len(calls) == 2


def test_repo_root_non_git_dir_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-git directory returns None without caching fake roots."""
    temp_dir = _setup_fake_temp_root(tmp_path, monkeypatch)
    plain = tmp_path / "plain"
    plain.mkdir()

    calls = []
    monkeypatch.setattr(tdq_state, "_git", lambda cwd, *args: calls.append(cwd) or None)

    assert tdq_state.repo_root(str(plain)) is None
    assert len(calls) == 1
    assert not (temp_dir / "tdq-repo-roots.json").exists()


def test_repo_root_caps_cache_at_64_and_fails_open_on_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cache trims old entries beyond 64 and fails open if disk write raises OSError."""
    temp_dir = _setup_fake_temp_root(tmp_path, monkeypatch)
    cache_file = temp_dir / "tdq-repo-roots.json"
    seed = {
        str(tmp_path / f"old_{idx}"): {
            "root": str(tmp_path / f"old_{idx}"),
            "head_mtime_ns": idx,
        }
        for idx in range(70)
    }
    cache_file.write_text(json.dumps(seed), encoding="utf-8")

    repo = tmp_path / "fresh_repo"
    head = repo / ".git" / "HEAD"
    head.parent.mkdir(parents=True)
    head.write_text("ref: refs/heads/main\n", encoding="utf-8")

    monkeypatch.setattr(tdq_state, "_git", lambda cwd, *args: str(repo).encode("utf-8"))
    assert tdq_state.repo_root(str(repo)) == str(repo)

    saved = json.loads(cache_file.read_text(encoding="utf-8"))
    assert len(saved) <= 64
    assert os.path.abspath(str(repo)) in saved

    # Verify fail-open when atomic write raises PermissionError
    tdq_state._ROOT_CACHE.clear()
    cache_file.unlink()

    def broken_write(path, text):
        raise PermissionError("read-only temp")

    monkeypatch.setattr(tdq_state, "_atomic_write", broken_write)
    monkeypatch.setenv("TDQ_LOG", "0")
    assert tdq_state.repo_root(str(repo)) == str(repo)


def test_strip_ps_herestrings_preserves_lines_lf_and_crlf() -> None:
    """Blank out PowerShell @'...'@ and @"..."@ bodies while preserving line counts."""
    lf_script = "$a = @'\nrg foo\n  '@\ngrep bar\n'@\necho done"
    stripped_lf = sr._strip_ps_herestrings(lf_script)
    assert stripped_lf.count("\n") == lf_script.count("\n")
    assert "rg foo" not in stripped_lf
    assert "grep bar" not in stripped_lf
    assert "echo done" in stripped_lf

    crlf_script = '$b = @"\r\nSelect-String foo\r\n"@\r\nWrite-Host ok'
    stripped_crlf = sr._strip_ps_herestrings(crlf_script)
    assert stripped_crlf.count("\n") == crlf_script.count("\n")
    assert "Select-String" not in stripped_crlf
    assert "Write-Host ok" in stripped_crlf

    empty_hs = "@'\n'@"
    assert sr._strip_ps_herestrings(empty_hs) == empty_hs


def test_ps_herestring_ignores_inner_search_and_detects_outer_search() -> None:
    """Ignore search cmds inside PS here-strings; match real searches outside."""
    safe_single = "$code = @'\nrg fake_match\ngrep -rn bar src/\n'@\npy -3 -c $code"
    pl_single = sr.phan_loai("Bash", safe_single)
    assert pl_single["status"] != "unknown"
    assert pl_single["reason"] != "malformed"
    assert pl_single["loai"] == sr.KHONG

    safe_double = (
        '$txt = @"\r\n"unbalanced quote\r\n`backtick\r\n'
        '<<EOF\r\ngrep foo\r\n"@\nWrite-Host ok'
    )
    pl_double = sr.phan_loai("PowerShell", safe_double)
    assert pl_double["status"] != "unknown"
    assert pl_double["reason"] != "malformed"
    assert pl_double["loai"] == sr.KHONG

    mixed = "$note = @'\nrg ignored_inside\n'@\nrg realSymbol src/"
    pl_mixed = sr.phan_loai("Bash", mixed)
    assert pl_mixed["status"] == "recognized"
    assert pl_mixed["loai"] == sr.TIM_CODE
    assert pl_mixed["tu_khoa"] == ["realSymbol"]


@pytest.mark.parametrize(
    "cmd",
    [
        r'py -3 -c "print(\"hello \`world\")"',
        'py -3 -c "print(\'see `foo` and `bar\')"',
        'py -3 -c "print(\'unpaired `backtick\')"',
        'Write-Host "line1`nline2`r`n`t`$var``end"',
        'Write-Host "trailing newline`n"',
        'Write-Host "say `"hello`" world"',
        'Write-Host "single `" quote"',
        'git commit -m "fix `parser`"',
        "Get-ChildItem `\n  -Path scripts",
        "Get-ChildItem `\n  -Path scripts `\n  -Filter *.py",
        "Get-ChildItem `\r\n  -Path scripts `\r\n  -Filter *.py",
        "Write-Host `$env:PATH",
        "echo `n",
    ],
)
def test_powershell_and_py_c_commands_not_malformed(cmd: str) -> None:
    """PowerShell escapes, backticks, and py -c commands never trigger malformed."""
    for tool in ("Bash", "PowerShell"):
        pl = sr.phan_loai(tool, cmd)
        assert pl["status"] != "unknown", f"{tool} failed on {cmd!r}: {pl}"
        assert pl["reason"] != "malformed", f"{tool} marked malformed on {cmd!r}: {pl}"
        assert pl["loai"] == sr.KHONG, f"{tool} misclassified {cmd!r}: {pl}"


def test_ps_line_continuation_preserves_search_arguments() -> None:
    """PowerShell line continuations keep Select-String options in the same command."""
    cmd = "Select-String `\n  -Pattern foo `\n  -Path src/*.py"
    pl = sr.phan_loai("PowerShell", cmd)
    assert pl["status"] == "recognized"
    assert pl["loai"] == sr.TIM_CODE
    assert pl["tu_khoa"] == ["foo"]


def test_real_bash_subshells_and_unbalanced_quotes_preserved() -> None:
    """Valid bash subshells detect searches; unterminated quotes stay malformed."""
    pl_bt = sr.phan_loai("Bash", "echo `grep -c foo a.ts`")
    assert pl_bt["loai"] == sr.TIM_CODE

    sub_cmd = (
        'for d in packages/*; do echo "$d: $(git ls-files $d '
        '| grep -E \'\\.(ts|tsx)$\' | wc -l)"; done'
    )
    pl_sub = sr.phan_loai("Bash", sub_cmd)
    assert pl_sub["loai"] == sr.LOC_FILE

    pl_bad_bash = sr.phan_loai("Bash", 'bash -c "rg \'unterminated')
    assert pl_bad_bash["status"] == "unknown"
    assert pl_bad_bash["reason"] == "malformed"

    pl_bad_quote = sr.phan_loai("PowerShell", 'Write-Host "unterminated')
    assert pl_bad_quote["status"] == "unknown"
    assert pl_bad_quote["reason"] == "malformed"


def test_repo_root_save_re_reads_under_lock_without_dropping_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_save_repo_root_cache merges fresh disk entries so concurrent repos never clobber keys."""
    temp_dir = _setup_fake_temp_root(tmp_path, monkeypatch)
    cache_path = temp_dir / "tdq-repo-roots.json"
    other_repo = str(tmp_path / "other_repo")
    Path(other_repo).mkdir()
    cache_path.write_text(
        json.dumps({other_repo: {"root": other_repo, "head_mtime_ns": 123}}),
        encoding="utf-8",
    )
    repo_b = str(tmp_path / "repo_b")
    Path(repo_b).mkdir()
    # Even if caller passes an empty stale dict, merging from disk preserves other_repo.
    tdq_state._save_repo_root_cache(str(cache_path), {}, repo_b, repo_b, 456)
    saved = json.loads(cache_path.read_text(encoding="utf-8"))
    assert other_repo in saved
    assert repo_b in saved


def test_repo_status_digest_skips_git_diff_when_clean_or_untracked_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clean or untracked-only git status must not spawn a redundant git diff HEAD call."""
    (tmp_path / "new.txt").write_text("hello", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_git(cwd: str, *args: str):
        calls.append(args)
        if args[0] == "status":
            return b"?? new.txt\n"
        raise AssertionError(f"Unexpected extra git call: {args}")

    monkeypatch.setattr(tdq_state, "_git", fake_git)
    monkeypatch.setattr(tdq_state, "repo_root", lambda _cwd: str(tmp_path))
    digest_untracked = tdq_state.repo_status_digest(str(tmp_path))
    assert isinstance(digest_untracked, str) and len(digest_untracked) == 64
    assert len(calls) == 1 and calls[0][0] == "status"

    calls.clear()
    digest_clean = tdq_state.repo_status_digest(str(tmp_path), status=b"")
    assert isinstance(digest_clean, str) and len(digest_clean) == 64
    assert calls == []
