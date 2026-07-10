import re

from .generic import apply_rules

# Latvian: indefinite adjectives (-isks/-īgs) and the -ums/-ija/-ība/-šana
# noun suffixes. Lemma-first build plus a measured hand-recovery pass (the
# noun cells fell to the trim cut-off or lie beyond mine()'s extension
# range; each recovered cell re-measured >=99% strict in this combined set,
# ~1,200 UD tokens). Deliberately absent: "-iju/-ijā" (collides with -ijs
# masculines), "-isko" (dict uses definite "-iskais"), and every
# "-i"-shaped alternative -- Latvian's productive adverb-from-adjective
# suffix, an open class UD keeps as its own lemma (atbilstoši, pilnīgi,
# faktiski).
#
# The definite-adjective declension family (-ais/-ošais/-ušais/-kais/
# -tais/-mais/-ākais targets, plus the -oša/-ošā-etc -> ošs and -ama/-amas
# -> ams cells) was dropped 2026-07: >=99% in-dict, but 85-100% wrong on UD
# real text (n=1734 combined lv_lvtb+lv_cairo) -- an extreme case of the
# in-dict blind spot. The OOV forms these cells fire on are overwhelmingly
# either verb participles (notiekošo -> gold notikt, not notiekošais) or
# plain indefinite adjectives (tehniskajiem -> gold tehnisks, not
# tehniskais), never the definite citation form the cells targeted. See
# training/review_ladder.py rung 2.
DEFAULT_RULES = {
    re.compile(r"(?:iskām|iskās|iskos|iskus|iska|isku|iskā)$"): "isks",
    re.compile(r"(?:īgos|īgus|īgās|īga|īgu|īgā)$"): "īgs",
    re.compile(r"(?:umam|uma|umu|umā)$"): "ums",
    re.compile(r"(?:ības|ību|ībā|ībām|ībās)$"): "ība",
    re.compile(r"(?:ijas|ijai)$"): "ija",
    re.compile(r"(?:šanas|šanai|šanu|šani)$"): "šana",
}

# Capitalized tokens decline like nouns, so most noun cells apply cleanly
# (Latvijas -> Latvija); "ums" is excluded (feminine surnames end in -a:
# Straujuma).
_CAPS_UNSAFE_TARGETS = frozenset({"isks", "īgs", "ums"})
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
