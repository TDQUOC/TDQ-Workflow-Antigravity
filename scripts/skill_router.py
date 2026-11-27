#!/usr/bin/env python3
"""skill_router.py — a PROTOTYPE skill lookup store: find the few right skills instead of
loading all 284.
**This is a prototype built to MEASURE, wired into no flow yet.** No hook calls this file;
QC item Q18 checks exactly that. Its only purpose in this request is to answer one question
in numbers: if skill descriptions are hidden away and looked up on demand, does the lookup
HIT. Answer that wrong and the token saving breaks the work — a skill that should have been
used goes missing and nobody notices.

Why BM25 and not a vector DB: the whole store is 284 descriptions, ~38,700 characters —
smaller than a mid-sized source file. BM25 runs instantly, needs no embedding model and no
API key (the constraint the user settled at question 7b of the brief). Move up to vectors
only when the numbers show keywords missing, never on a feeling.

Two commands:
    python3 scripts/skill_router.py --dung-kho          # rebuild docs/tdq/audit/skill-index.json
    python3 scripts/skill_router.py --tra "<sentence>"  # look up the top-k fitting skills

Log service: ISO timestamps on stderr, on by default, muted with `TDQ_LOG=0`.
Exit: 0 finished · 2 bad syntax · 4 store not built yet.
"""
import argparse
import json
import math
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import skill_inventory
import skill_tokens
import tdq_config
import tdq_domains
import tdq_state
import utf8_io

KHO = os.path.join(ROOT, "docs", "tdq", "audit", "skill-index.json")
TRUONG = ("ten", "mo_ta", "nguon", "duong_dan")
EXIT_THIEU_KHO = 4
TOP_K = 5
DOMAIN_BOOST = 1.25
PREFERRED_FLOOR_SCORE = 0.05

# Standard BM25 parameters. k1 tunes the reward when a word repeats, b tunes the penalty on
# long documents. Keep the standard values so the numbers compare with outside literature.
BM25_K1 = 1.5
BM25_B = 0.75


def _log(msg):
    if tdq_state.log_enabled():
        print(f"[{tdq_state.now_iso()}] {msg}", file=sys.stderr)


def bo_dau(chu):
    """Strip Vietnamese diacritics so an accented word and its bare form hit the same entry."""
    tach = unicodedata.normalize("NFD", unicodedata.normalize("NFC", chu))
    return "".join(c for c in tach if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "d")  # i18n-allow


TU_RE = re.compile(r"[a-z0-9]+")

# Function words — dropped before scoring. This is NOT tuning for prettier numbers: the
# skill store is nearly all English, only 6 `tdq-*` descriptions are Vietnamese. So every
# Vietnamese function word appears in exactly those 6 documents → very high IDF → every
# Vietnamese question returns tdq-*. Measured for real: a Vietnamese sentence asking to run
# a sonarqube scan put tdq-plan at rank 1 and sonar-integrate at rank 3, purely on function
# words. Dropping function words in both languages is standard IR, not a sample-set trick.
DUNG_TU = frozenset([
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "how",
    "i", "in", "is", "it", "its", "of", "on", "or", "that", "the", "to", "was", "what",
    "when", "where", "which", "who", "will", "with", "you", "your", "this", "these",
    "those", "do", "does", "can", "could", "should", "would", "if", "then", "than",
    "there", "here", "s", "bi", "boi", "ca", "cac", "cai", "cho", "chua", "chuc", "co",
    "con", "cua", "cung", "da", "dang", "de", "den", "di", "do", "doi", "duoc", "dung",
    "gi", "gia", "giup", "hay", "hoac", "khi", "khong", "la", "lai", "lam", "len", "luc",
    "mA", "ma", "moi", "mot", "muon", "nao", "nay", "nen", "ngay", "nhu", "nhung", "no",
    "o", "phai", "qua", "ra", "rang", "rat", "roi", "sau", "se", "so", "ta", "thi",
    "tren", "tu", "tuy", "va", "vao", "ve", "vi", "voi", "vua", "xong", "y", "toi",
    "ban", "minh", "chung", "ho", "nhieu", "it", "hon", "nua", "lan", "cach", "kieu",
    "duoi",
])


def tach_tu(chu, bo_hu_tu=True):
    """str → list of normalised words with camel/snake/acronym tokenization and NFC/casefold."""
    chu_nfc = unicodedata.normalize("NFC", chu)
    # Split camelCase, PascalCase, and acronyms:
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", chu_nfc)
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s1)
    s_khong_dau = bo_dau(s2.casefold())
    tu = TU_RE.findall(s_khong_dau)
    return [t for t in tu if t not in DUNG_TU] if bo_hu_tu else tu


def dung_kho(project=ROOT):
    """Build the store from ENABLED skills. Every record carries all 4 fields of `TRUONG`."""
    hang = skill_inventory.inventory(project)
    ban_do = skill_tokens.ban_do_skill_md()
    ban_ghi = []
    for ten, mo_ta_ngan, nguon in hang:
        duong_dan = ""
        ds = ban_do.get(skill_tokens.khoa_tra(ten), [])
        if ds:
            duong_dan = os.path.relpath(ds[0], ROOT) if ds[0].startswith(ROOT) else ds[0]
        ban_ghi.append({
            "ten": ten,
            "mo_ta": skill_tokens._mo_ta_day_du(ten, mo_ta_ngan, ban_do),
            "nguon": nguon,
            "duong_dan": duong_dan,
        })
    thieu = [b["ten"] for b in ban_ghi if not b["duong_dan"]]
    _log(f"store built: {len(ban_ghi)} record(s) from {len(hang)} enabled skill(s)")
    if thieu:
        # Not silent: these are the skills the router could find yet still not point at a
        # file to read — meaning the "off + read SKILL.md directly" layer cannot serve them.
        _log(f"warning: {len(thieu)} skill(s) with no SKILL.md found (declared name differs "
             f"from the directory name), e.g. {thieu[:3]}")
    return ban_ghi


def ghi_kho(ban_ghi, path=KHO):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ban_ghi, f, ensure_ascii=False, indent=2)
        f.write("\n")
    _log(f"ghi kho → {os.path.relpath(path, ROOT)}")


def doc_kho(path=KHO):
    """Read the store. Not built yet → exit 4 with the exact command to run, no blind lookup."""
    try:
        with open(path, encoding="utf-8") as f:
            ban_ghi = json.load(f)
    except OSError:
        print(f"skill_router.py: no store at {os.path.relpath(path, ROOT)}.\n"
              "Build it with: python3 scripts/skill_router.py --dung-kho", file=sys.stderr)
        sys.exit(EXIT_THIEU_KHO)
    thieu = [b.get("ten", "?") for b in ban_ghi
             if any(t not in b for t in TRUONG)]
    if thieu:
        print(f"skill_router.py: {len(thieu)} record(s) missing a required field "
              f"(e.g. {thieu[0]}). Rebuild with: "
              "python3 scripts/skill_router.py --dung-kho", file=sys.stderr)
        sys.exit(EXIT_THIEU_KHO)
    return ban_ghi


class KhoBM25:
    """A BM25 index over the skill store. Built once, queried many times."""

    def __init__(self, ban_ghi):
        self.ban_ghi = ban_ghi
        self.tai_lieu = [tach_tu(f"{b['ten']} {b['ten']} {b['mo_ta']}") for b in ban_ghi]
        # The skill name counts twice: whoever types the prompt tends to name the tool exactly,
        # and the name is a stronger signal than any single word of a long description.
        self.do_dai = [len(d) for d in self.tai_lieu]
        self.dai_tb = sum(self.do_dai) / len(self.do_dai) if self.do_dai else 0
        self.df = {}
        for doc in self.tai_lieu:
            for tu in set(doc):
                self.df[tu] = self.df.get(tu, 0) + 1
        self.tf = [{} for _ in self.tai_lieu]
        for i, doc in enumerate(self.tai_lieu):
            for tu in doc:
                self.tf[i][tu] = self.tf[i].get(tu, 0) + 1

    def _idf(self, tu):
        n = len(self.tai_lieu)
        df = self.df.get(tu, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def diem(self, cau_hoi, i):
        tong = 0.0
        for tu in tach_tu(cau_hoi):
            f = self.tf[i].get(tu, 0)
            if not f:
                continue
            chuan = 1 - BM25_B + BM25_B * (self.do_dai[i] / self.dai_tb or 1)
            tong += self._idf(tu) * f * (BM25_K1 + 1) / (f + BM25_K1 * chuan)
        return tong

    def tra(self, cau_hoi, k=TOP_K, preferred_skills=None):
        """The top-k fitting records as (score, record), optionally boosting preferred skills."""
        pref = (
            {str(name).strip() for name in preferred_skills if name}
            if preferred_skills is not None
            else set()
        )
        scored = []
        for i, record in enumerate(self.ban_ghi):
            score = self.diem(cau_hoi, i)
            if score > 0:
                if pref and record["ten"] in pref:
                    score *= DOMAIN_BOOST
                scored.append((score, record))
        if not scored and pref:
            scored = [
                (PREFERRED_FLOOR_SCORE, record)
                for record in self.ban_ghi
                if record["ten"] in pref
            ]
        scored.sort(key=lambda item: (-item[0], item[1]["ten"]))
        return scored[:k]


def _default_project(project=None):
    if project is not None:
        return project
    env_dir = os.environ.get("TDQ_PROJECT_DIR", "").strip()
    return env_dir or ROOT


def _domain_router_enabled(cwd):
    cfg = tdq_config.load_config(cwd=cwd)
    p1_cfg = cfg.get("p1")
    if isinstance(p1_cfg, dict) and "domain_router_enabled" in p1_cfg:
        return bool(p1_cfg["domain_router_enabled"])
    if "domain_router_enabled" in cfg:
        return bool(cfg["domain_router_enabled"])
    return True


def _preferred_skills_for_domain(domain_id, cwd):
    if not isinstance(domain_id, str) or not domain_id.strip():
        return None
    did = domain_id.strip()
    if not _domain_router_enabled(cwd):
        _log(f"domain boost disabled by config; ignoring domain={did}")
        return None
    packs = tdq_domains.load_domain_packs(cwd)
    pack = packs.get(did)
    if not isinstance(pack, dict):
        _log(f"unknown domain {did!r}; falling back to standard BM25")
        return None
    skills = pack.get("preferred_skills")
    if not isinstance(skills, list) or not skills:
        return None
    cleaned = [str(name).strip() for name in skills if isinstance(name, str) and name.strip()]
    return cleaned or None


def _resolve_tra_cuu_args(ban_ghi, top_k, cwd, k, project):
    """Normalize both Spec (ban_ghi, top_k, cwd) and helper (k, project) call shapes."""
    is_int_k = isinstance(ban_ghi, int) and not isinstance(ban_ghi, bool)
    records = doc_kho() if (ban_ghi is None or is_int_k) else ban_ghi
    eff_k = ban_ghi if is_int_k else top_k
    eff_cwd = top_k if (is_int_k and isinstance(top_k, (str, os.PathLike))) else cwd
    if k is not None:
        eff_k = k
    if project is not None:
        eff_cwd = project
    return records, eff_k, _default_project(eff_cwd)


def tra_cuu(
    cau,
    ban_ghi=None,
    domain_id=None,
    top_k=TOP_K,
    cwd=None,
    *,
    k=None,
    project=None,
):
    """Look up top-k skills for a prompt, optionally boosting a domain pack's preferred skills."""
    records, eff_k, eff_cwd = _resolve_tra_cuu_args(ban_ghi, top_k, cwd, k, project)
    preferred = _preferred_skills_for_domain(domain_id, eff_cwd)
    results = KhoBM25(records).tra(cau, eff_k, preferred_skills=preferred)
    return [dict(record, score=score) for score, record in results]


def lenh_dung_kho(args):
    project = getattr(args, "project", None) or ROOT
    ghi_kho(dung_kho(project))
    print(f"Store built: {os.path.relpath(KHO, ROOT)}")
    return 0


def lenh_tra(args):
    project = _default_project(getattr(args, "project", None))
    preferred = _preferred_skills_for_domain(getattr(args, "domain", None), project)
    kho = KhoBM25(doc_kho())
    ket_qua = kho.tra(args.tra, args.k, preferred_skills=preferred)
    if not ket_qua:
        print(f"No skill matches {args.tra!r}.")
        return 0
    print("| # | skill | score | source |")
    print("|---|---|---|---|")
    for thu_tu, (diem, b) in enumerate(ket_qua, 1):
        print(f"| {thu_tu} | {b['ten']} | {diem:.2f} | {b['nguon']} |")
    return 0


def main(argv=None):
    utf8_io.force_utf8()
    parser = argparse.ArgumentParser(
        prog="skill_router.py",
        description="Offline BM25 skill lookup store with optional domain pack boosting.",
    )
    parser.add_argument(
        "--dung-kho",
        action="store_true",
        dest="dung_kho",
        help="rebuild docs/tdq/audit/skill-index.json",
    )
    parser.add_argument(
        "--tra",
        metavar="SENTENCE",
        help="look up the top-k skills fitting this sentence",
    )
    parser.add_argument(
        "-k",
        type=int,
        default=TOP_K,
        help=f"how many results (default {TOP_K})",
    )
    parser.add_argument(
        "--domain",
        default=None,
        help="optional domain_id whose preferred_skills receive a boost",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="project directory to inventory skills or read domain packs in",
    )
    args = parser.parse_args(argv)

    if bool(args.dung_kho) == bool(args.tra):
        parser.error('pick exactly one: --dung-kho or --tra "<sentence>"')
    domain_note = f" domain={args.domain}" if args.domain else ""
    _log(f"skill_router · {'--dung-kho' if args.dung_kho else '--tra'}{domain_note}")
    return lenh_dung_kho(args) if args.dung_kho else lenh_tra(args)


if __name__ == "__main__":
    sys.exit(main())
