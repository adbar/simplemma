import re

from .generic import apply_rules

# Luxembourgish adjective declension, mined lemma-first (99.75% in-dict).
DEFAULT_RULES = {
    re.compile(r"(?:ertstem|ertsten|ertster|ertste|erten|ertem|erter|ertst)$"): r"ert",
    re.compile(r"(?:schstem|schsten|schster|schste|scher|schem|schst)$"): r"sch",
    re.compile(r"(?:echstem|echster|echer|echem)$"): r"ech",
    re.compile(r"(?:egstem|egsten|egster|egste|eger|egem)$"): r"eg",
    re.compile(r"(?:elten|elter|elte)$"): r"elt",
    re.compile(r"(?:chtem)$"): r"cht",
    re.compile(r"(?:ltem)$"): r"lt",
    re.compile(r"(?:ener|enem)$"): r"en",
    re.compile(r"(?:ntem)$"): r"nt",
    re.compile(r"(?:alem)$"): r"al",
    re.compile(r"(?:els)$"): r"elen",
}


def apply_lb(token: str) -> str | None:
    "Apply pre-defined rules for Luxembourgish."
    return apply_rules(token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True)
