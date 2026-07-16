import re

from .generic import apply_rules

# Macedonian verbal/nominal declension, re-mined lemma-first from the v2
# dictionary (99.79% in-dict; the earlier rule set predated that data and
# mis-stripped -иве/-ине/-ите definite forms on -н nouns).
DEFAULT_RULES = {
    re.compile(
        r"(?<=..)(?:увавме|увавте|увало|увале|увала|увај|уваа|увал|увам|ував)$"
    ): r"ува",
    re.compile(r"(?<=..)(?:вајте|ваат|ваш)$"): r"ва",
    re.compile(r"(?<=..)(?:рајте|раш)$"): r"ра",
    re.compile(r"(?<=..)(?:ирала|ирало|ираат|ирал|ираа)$"): r"ира",
    re.compile(r"(?<=..)(?:ајќи|аше|ате|аме)$"): r"а",
    re.compile(r"(?<=..)(?:њето|њево|њено)$"): r"ње",
    re.compile(r"(?<=..)(?:оста)$"): r"ост",
    re.compile(r"(?<=..)(?:име|иш)$"): r"и",
    re.compile(r"(?<=..)(?:ијо)$"): r"ија",
    re.compile(r"(?<=..)(?:рот)$"): r"р",
    re.compile(r"(?<=..)(?:кот)$"): r"к",
    re.compile(r"(?<=..)(?:тот)$"): r"т",
    re.compile(r"(?<=..)(?:ке)$"): r"ка",
    re.compile(r"(?<=..)(?:еш)$"): r"е",
}


def apply_mk(token: str) -> str | None:
    "Apply pre-defined rules for Macedonian."
    return apply_rules(token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True)
