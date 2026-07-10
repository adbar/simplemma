import re

from .generic import apply_rules

# Portuguese verb conjugation and noun/adjective endings, mined lemma-first
# (99.72% in-dict).
DEFAULT_RULES = {
    re.compile(r"(?:tara|tá)$"): r"tar",
    re.compile(r"(?:raras|rara)$"): r"rar",
    re.compile(r"(?:eamos|earas|eemos|eara|eeis|eamo|eemo|eei)$"): r"ear",
    re.compile(r"(?:haras|hara)$"): r"har",
    re.compile(r"(?:quemos|camos|cam)$"): r"car",
    re.compile(
        r"(?:aríamos|ássemos|aremos|aríeis|ávamos|ásseis|áramos|areis|ariam"
        r"|ardes|asses|astes|assem|armos|áreis|ávamo|áramo|ares|arei|avas"
        r"|ando|arem|aram|avam|arão|arás|asse|aste|ámos|armo|arde|ávei|árei"
        r"|ará|ava|ámo|are|ou|ai)$"
    ): r"ar",
    re.compile(r"(?:zarias|zaras|zaria|zara|zá)$"): r"zar",
    re.compile(r"(?:izamos|izais|izamo|izam)$"): r"izar",
    re.compile(r"(?:dores|dora)$"): r"dor",
    re.compile(r"(?:naras|nemos|nara|nemo|nei)$"): r"nar",
    re.compile(r"(?:êreis|erás)$"): r"er",
    re.compile(r"(?:irdes|irmos)$"): r"ir",
    re.compile(r"(?:icos)$"): r"ico",
    re.compile(r"(?:ções)$"): r"ção",
    re.compile(r"(?:ntos)$"): r"nto",
    re.compile(r"(?:smos)$"): r"smo",
    re.compile(r"(?:ivos)$"): r"ivo",
    re.compile(r"(?:anos)$"): r"ano",
    re.compile(r"(?:ros)$"): r"ro",
    re.compile(r"(?:ios)$"): r"io",
    re.compile(r"(?:sos)$"): r"so",
    re.compile(r"(?:los)$"): r"lo",
    re.compile(r"(?:eos)$"): r"eo",
    re.compile(r"(?:gos)$"): r"go",
}

# invariant words, feminine agent nouns kept as their own lemma,
# stem-extending verb forms, and lowercased proper nouns
_EXCLUDED = frozenset(
    {
        "quando",
        "vários",
        "classe",
        "comando",
        "rarará",
        "contraste",
        "software",
        "arredores",
        "hectare",
        "hectares",
        "óculos",
        "contrabando",
        "alvará",
        "trezentos",
        "pizzaria",
        "expiatórios",
        "moradora",
        "revendedora",
        "montadora",
        "investigadora",
        "passes",
        "passem",
        "variam",
        "preparam",
        "disparam",
        "fernando",
        "carlos",
        "orlando",
        "soares",
        "girolando",
    }
)


def apply_pt(token: str) -> str | None:
    "Apply pre-defined rules for Portuguese."
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
