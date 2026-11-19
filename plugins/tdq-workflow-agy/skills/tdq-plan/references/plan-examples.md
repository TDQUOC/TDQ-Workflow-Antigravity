# Plan Contrastive Examples (~70% PASS / ~30% FAIL)

Fictional paths (`src/...`, `cases/...`): Greenfield, Refactor, and Sweep pairs.

## Pair 1 — Greenfield Feature

**PASS (`R15-Full`):**
<!-- i18n-allow -->
```markdown
- [ ] **T1.1** (e10m) Rate limiter `src/lim.py` — Test: `pytest cases/t_lim.py`
  - Req: `§2#1` · Ngoài phạm vi: `GIỮ NGUYÊN` CLI
  - Chạm: `src/lim.py`, `cases/t_lim.py` · Cần: Không
  - Giao tiếp: Consumes: `cfg: dict` | Produces: `allow(k: str, t: float) -> bool`
  - Neo & Công cụ: `write_file` `src/lim.py`, `cases/t_lim.py`
  - Trước → Sau: none → refills up to `cap`, `False` on burst
  - Tiêu chí chấp nhận (EARS): KHI `cap=2` full, HỆ THỐNG PHẢI return `False`
  - Logic cốt lõi: store `{k:(tok,ts)}`, refill to `cap`, dec `1.0`
  - Ca góc hiểm & Assert: empty `k`→`ValueError` · `assert allow("u",0) and not allow("u",0)`
```

**FAIL (`[Why it fails]` — `TBD` + `ANTI-2`):**
<!-- i18n-allow -->
```markdown
- [ ] **T1.1** (e10m) Limiter — Test: `pytest cases/t_lim.py`
  - Chạm: `src/lim.py` · Logic: rate limit TBD · Ca hiểm: `assert True`
```
> **[Why it fails]:** Missing Mini-Spec fields; uses `TBD` and `assert True`.

## Pair 2 — Brownfield Refactor

**PASS (AST anchor, caller ref, invariant):**
<!-- i18n-allow -->
```markdown
- [ ] **T2.1** (e12m) Extract `check_hdr()` in `src/par.py` — Test: `pytest cases/t_par.py`
  - Req: `§2#3` · Ngoài phạm vi: `GIỮ NGUYÊN` `parse(s: str) -> dict`
  - Chạm: `src/par.py`, `cases/t_par.py` · Cần: T1.1
  - Tham chiếu: `src/cli.py` (`run`) · Giao tiếp: Consumes: `s: str` | Produces: `check_hdr(d)`
  - Neo & Công cụ: `edit_file` `src/par.py` at `parse()` (`L42-68`)
  - Trước → Sau: raw `KeyError` → `ValueError("no ver")`
  - Tiêu chí chấp nhận (EARS): KHI no `ver`, HỆ THỐNG PHẢI raise `ValueError`
  - Logic cốt lõi: validate keys + `TDQ_LOG`
  - Ca góc hiểm & Assert: `ver=0` · `assert parse("ver:2")["ver"] == 2`
```

**FAIL (`[Why it fails]` — wildcard + no invariant):**
<!-- i18n-allow -->
```markdown
- [ ] **T2.1** (e10m) Clean parser — Test: `pytest`
  - Chạm: `src/*.py` · Logic: refactor cleanly
```
> **[Why it fails]:** Wildcard `src/*.py`; omits invariant, caller ref, and test path.

## Pair 3 — Uniform Mechanical Sweep (`<= 6` files)

**PASS (`<= 6` files):**
<!-- i18n-allow -->
```markdown
- [ ] **T3.1** (e6m) Uniform Mechanical Sweep: `old_f`→`new_f` — Test: `pytest cases/t_s.py`
  - Ngoài phạm vi: `GIỮ NGUYÊN` returns
  - Chạm: `src/1.py`, `src/2.py`, `src/3.py`, `src/4.py`
  - Neo & Công cụ: `edit_file` `old_f=` → `new_f=` · Tiêu chí: `0` hits `old_f`
```

**FAIL (`[Why it fails]` — `> 6` cap):**
<!-- i18n-allow -->
```markdown
- [ ] **T3.1** (e15m) Uniform Mechanical Sweep: 7 files — Test: `pytest`
  - Chạm: `src/1.py`, `src/2.py`, `src/3.py`, `src/4.py`, `src/5.py`, `src/6.py`, `src/7.py`
```
> **[Why it fails]:** 7 files exceed `<= 6` Sweep cap (`R15`); split batches.
