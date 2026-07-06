import re

from .generic import apply_rules

# Latvian: definite-adjective declension (-ais family), indefinite
# adjectives (-isks/-īgs), and the -ums/-ija/-ība/-šana noun suffixes.
# Lemma-first build plus a measured hand-recovery pass (the noun cells fell
# to the trim cut-off or lie beyond mine()'s extension range; each recovered
# cell re-measured >=99% strict in this combined set, ~1,200 UD tokens).
# Deliberately absent: the bare "-ajiem" family (residue ~98%, low real-text
# value), "-iju/-ijā" (collides with -ijs masculines), "-isko" (dict uses
# definite "-iskais"), and every "-i"-shaped alternative -- Latvian's
# productive adverb-from-adjective suffix, an open class UD keeps as its
# own lemma (atbilstoši, pilnīgi, faktiski).
DEFAULT_RULES = {
    re.compile(r"(?:ākiem|ākam|ākas|āko)$"): "ākais",
    re.compile(r"(?:ušajiem|ušajai|ušajam|ušajos|ušie|usī|ušo)$"): "ušais",
    re.compile(r"(?:ošajiem|ošajam|ošajos|ošajai|ošie|ošo)$"): "ošais",
    re.compile(r"(?:kajiem|kajai|kajam|kajos|kie)$"): "kais",
    re.compile(r"(?:tajiem|tajam|tajos|tajai)$"): "tais",
    re.compile(r"(?:majiem|majai|majam|majos|mie)$"): "mais",
    re.compile(r"(?:ošiem|ošus|ošai|ošam|ošas|ošām|ošās|oša|ošā)$"): "ošs",
    re.compile(r"(?:ajām|ajās|ajā)$"): "ais",
    re.compile(r"(?:iskām|iskās|iskos|iskus|iska|isku|iskā)$"): "isks",
    re.compile(r"(?:īgos|īgus|īgās|īga|īgu|īgā)$"): "īgs",
    re.compile(r"(?:umam|uma|umu|umā)$"): "ums",
    re.compile(r"(?:ības|ību|ībā|ībām|ībās)$"): "ība",
    re.compile(r"(?:ijas|ijai)$"): "ija",
    re.compile(r"(?:šanas|šanai|šanu|šani)$"): "šana",
    re.compile(r"(?:amas|ama)$"): "ams",
}

# Capitalized tokens decline like nouns, so most noun cells apply cleanly
# (Latvijas -> Latvija); the adjective cells would mangle names, and "ums"
# is excluded too (feminine surnames end in -a: Straujuma).
_CAPS_UNSAFE_TARGETS = frozenset(
    {
        "ākais",
        "ušais",
        "ošais",
        "kais",
        "tais",
        "mais",
        "ošs",
        "ais",
        "ams",
        "isks",
        "īgs",
        "ums",
    }
)
_PROPER_NOUN_RULES = {
    pattern: repl
    for pattern, repl in DEFAULT_RULES.items()
    if repl not in _CAPS_UNSAFE_TARGETS
}

# Pluralia tantum whose citation form IS the plural, colliding with the
# "-ība"/"-šana" singular cells (in-dict members are resolved by lookup
# before rules; the OOV ones do reach the rules), plus two lexicalized
# invariants (drīzumā, pretinflācijas).
_EXCLUDED = frozenset(
    {
        "priekšvēlēšanu",
        "vēlēšanas",
        "vēlēšanu",
        "vēlēšanām",
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
    # jā- marks debitive verb forms (infinitive lemma, out of reach here);
    # min_len 6 matches the mining/validation floor.
    if len(token) < 6 or token.startswith("jā") or token in _EXCLUDED:
        return None

    rules = _PROPER_NOUN_RULES if token[0].isupper() else DEFAULT_RULES
    return apply_rules(token, rules)
