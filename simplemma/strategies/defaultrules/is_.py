import re

from .generic import apply_rules

# Icelandic: adjective declension/comparison (-egur/-legur families) and
# definite-article-suffixed noun forms. Lemma-first build: 7 groups, 5.86%
# coverage, 99.70% in-dict. NB: is_modern's dict agreement is only ~59%,
# so only the diff-token audit is a meaningful UD signal here.
DEFAULT_RULES = {
    re.compile(
        r"(?:egastrar|egastur|egastan|egastar|egastir|egastra|egastri"
        r"|egustum|egasta|egasti|egasts|egustu|egrar|egust|egri|egan|egir"
        r"|egra|egt|egu|egs|eg)$"
    ): r"egur",
    re.compile(r"(?:ingunni|inguna|ingin|ingu)$"): r"ing",
    re.compile(r"(?:gurinn)$"): r"gur",
    re.compile(r"(?:rsins)$"): r"r",
    re.compile(r"(?:legi)$"): r"legur",
    re.compile(r"(?:unin)$"): r"un",
    re.compile(r"(?:aðu)$"): r"a",
}


def apply_is(token: str) -> str | None:
    "Apply pre-defined rules for Icelandic."
    return apply_rules(token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True)
