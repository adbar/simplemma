import re

from .generic import apply_rules

# Latvian: indefinite adjectives (-isks/-īgs) and -ums/-ija/-ība/-šana nouns,
# each cell >=99% precise. Deliberately absent: -iju/-ijā (collides with -ijs
# masculines), -i adverbs (open class UD lemmatizes as-is), and the whole
# definite-adjective declension family -- >=99% in-dict but 85-100% wrong on
# UD real text (OOV firings are participles or indefinite adjectives, never
# the definite citation form).
DEFAULT_RULES = {
    re.compile(r"(?:iskām|iskās|iskos|iskus|iska|isku|iskā)$"): "isks",
    re.compile(r"(?:īgos|īgus|īgās|īga|īgu|īgā)$"): "īgs",
    re.compile(r"(?:umam|uma|umu|umā)$"): "ums",
    re.compile(r"(?:ības|ību|ībā|ībām|ībās)$"): "ība",
    re.compile(r"(?:ijas|ijai)$"): "ija",
    re.compile(r"(?:šanas|šanai|šanu|šani)$"): "šana",
}

# capitalized tokens decline like nouns (Latvijas -> Latvija); "ums" excluded
# (feminine surnames end in -a: Straujuma)
_CAPS_UNSAFE_TARGETS = frozenset({"isks", "īgs", "ums"})
_PROPER_NOUN_RULES = {
    pattern: repl
    for pattern, repl in DEFAULT_RULES.items()
    if repl not in _CAPS_UNSAFE_TARGETS
}

# pluralia tantum colliding with the -ība/-šana singular cells, plus two
# lexicalized invariants
_EXCLUDED = frozenset(
    {
        "priekšvēlēšanu",
        "vēlēšanas",
        "vēlēšanu",
        "ganības",
        "ganību",
        "ganībā",
        "ganībām",
        "ganībās",
        "kristības",
        "kristību",
        "kristībā",
        "kristībām",
        "kristībās",
        "tiesības",
        "tiesību",
        "tiesībā",
        "tiesībām",
        "tiesībās",
        "dzemdības",
        "dzemdību",
        "dzemdībās",
        "medības",
        "medību",
        "balsstiesības",
        "drīzumā",
        "pretinflācijas",
    }
)


def apply_lv(token: str) -> str | None:
    "Apply pre-defined rules for Latvian."
    # jā- marks debitive verb forms (infinitive lemma, out of reach here)
    if len(token) < 6 or token.startswith("jā") or token in _EXCLUDED:
        return None

    rules = _PROPER_NOUN_RULES if token[0].isupper() else DEFAULT_RULES
    return apply_rules(token, rules)
