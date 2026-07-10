import re

from .generic import apply_rules

# Swedish noun declension, adjective comparison, and verb conjugation,
# mined lemma-first (99.76% in-dict).
DEFAULT_RULES = {
    re.compile(
        r"(?:barastes|barares|baraste|barasts|barare|barast|bares|baras"
        r"|barts|bare|bara|bart)$"
    ): r"bar",
    re.compile(r"(?:ingarnas|ingarna|ingens|ingars|ingen|ings)$"): r"ing",
    re.compile(r"(?:heternas|hetens|heten|heter|hets)$"): r"het",
    re.compile(r"(?:iskares|iskare)$"): r"isk",
    re.compile(r"(?:ionernas|ionerna|ionens|ioners|ionen|ioner)$"): r"ion",
    re.compile(
        r"(?:igastes|igares|igaste|igasts|igare|igast|iges|igts|igs|ige|igt)$"
    ): r"ig",
    re.compile(r"(?:skasts|skast|skts|sks|skt)$"): r"sk",
    re.compile(r"(?:ndenas|ndena)$"): r"nde",
    re.compile(r"(?:kastes|kaste)$"): r"k",
    re.compile(r"(?:erande|eras)$"): r"era",
    re.compile(r"(?:els)$"): r"el",
}

# OOV invariants
_EXCLUDED = frozenset({"enligt", "antingen", "enbart"})


def apply_sv(token: str) -> str | None:
    "Apply pre-defined rules for Swedish."
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
