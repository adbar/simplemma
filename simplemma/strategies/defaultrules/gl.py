import re

from .generic import apply_rules

# Galician verb conjugation and noun/adjective plural endings, mined
# lemma-first (99.67% in-dict).
DEFAULT_RULES = {
    re.compile(r"(?:laras|lara|lase|lade|lei)$"): r"lar",
    re.compile(r"(?:tei)$"): r"tar",
    re.compile(r"(?:zaras|zases|zade|zara|zase|cei)$"): r"zar",
    re.compile(r"(?:raras|rara)$"): r"rar",
    re.compile(
        r"(?:ariades|ariamos|ándodes|aremos|arades|abades|abamos|aramos"
        r"|ásedes|ásemos|aredes|arías|astes|aches|ardes|arían|armos|ares"
        r"|abas|aría|arei|ando|aren|aran|asen|arás|aban|arán|aron|aba|ará"
        r"|ou)$"
    ): r"ar",
    re.compile(r"(?:cases|camos|case)$"): r"car",
    re.compile(r"(?:dores)$"): r"dor",
    re.compile(r"(?:bles)$"): r"ble",
    re.compile(r"(?:beis)$"): r"bel",
    re.compile(r"(?:smos)$"): r"smo",
    re.compile(r"(?:ntos)$"): r"nto",
    re.compile(r"(?:cos)$"): r"co",
    re.compile(r"(?:ros)$"): r"ro",
    re.compile(r"(?:ios)$"): r"io",
    re.compile(r"(?:ais)$"): r"al",
    re.compile(r"(?:los)$"): r"lo",
    re.compile(r"(?:nos)$"): r"no",
    re.compile(r"(?:sos)$"): r"so",
    re.compile(r"(?:vos)$"): r"vo",
    re.compile(r"(?:ns)$"): r"n",
}

# invariant words colliding with the -ais/-ando/-nos cells and a few forms
# the short -ar alternatives over-strip
_EXCLUDED = frozenset(
    {
        "ademais",
        "demais",
        "quizais",
        "jamais",
        "xamais",
        "varios",
        "alomenos",
        "quando",
        "cuando",
        "recabará",
        "conlevaría",
        "sobrepasarán",
        "mensaxaría",
        "acabamos",
        "paredes",
        "varían",
    }
)


def apply_gl(token: str) -> str | None:
    "Apply pre-defined rules for Galician."
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
