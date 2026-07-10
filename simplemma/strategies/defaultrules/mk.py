import re

from .generic import apply_rules

# Macedonian definite-article and plural declension, mined lemma-first
# (99.28% in-dict).
DEFAULT_RULES = {
    re.compile(r"(?:ствава|ствана|ствата|ства)$"): r"ство",
    re.compile(r"(?:ации)$"): r"ација",
    re.compile(r"(?:ркана|рката)$"): r"рка",
    re.compile(r"(?:ирање)$"): r"ира",
    re.compile(r"(?:ииве|иине|иите|ијо)$"): r"ија",
    re.compile(r"(?:нине|ниве|ните)$"): r"на",
    re.compile(r"(?:уван)$"): r"ува",
    re.compile(r"(?:чево)$"): r"че",
    re.compile(r"(?:ке)$"): r"ка",
}


def apply_mk(token: str) -> str | None:
    "Apply pre-defined rules for Macedonian."
    return apply_rules(token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True)
