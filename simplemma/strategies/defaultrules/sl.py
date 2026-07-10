import re

from .generic import apply_rules

# Slovenian adjective declension and a handful of noun/verb suffixes,
# mined lemma-first (99.73% in-dict).
DEFAULT_RULES = {
    re.compile(r"(?:nska)$"): r"nski",
    re.compile(r"(?:jenih)$"): r"jen",
    re.compile(r"(?:skega|skimi|skemu|skima|skem|skim)$"): r"ski",
    re.compile(r"(?:tnega|tnih|tni|tne)$"): r"ten",
    re.compile(r"(?:anega|anih)$"): r"an",
    re.compile(r"(?:enega|enimi)$"): r"en",
    re.compile(r"(?:čnega|čnih)$"): r"čen",
    re.compile(r"(?:nikom|niku)$"): r"nik",
    re.compile(r"(?:ostjo)$"): r"ost",
    re.compile(r"(?:ajte|ajmo|ajta|ajva|amo)$"): r"ati",
    re.compile(r"(?:nice|nici|nic)$"): r"nica",
    re.compile(r"(?:cije|cijo|ciji)$"): r"cija",
    re.compile(r"(?:anju)$"): r"anje",
    re.compile(r"(?:alni|alne|alno)$"): r"alen",
    re.compile(r"(?:jali|jajo)$"): r"jati",
    re.compile(r"(?:kami)$"): r"ka",
    re.compile(r"(?:itve)$"): r"itev",
    re.compile(r"(?:ikih)$"): r"ik",
    re.compile(r"(?:ico)$"): r"ica",
    re.compile(r"(?:tva)$"): r"tvo",
}

# OOV invariants plus one pluralia-tantum conflict
_EXCLUDED = frozenset({"eventualno", "epiduralno", "totalno", "počitnice"})


def apply_sl(token: str) -> str | None:
    "Apply pre-defined rules for Slovenian."
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
