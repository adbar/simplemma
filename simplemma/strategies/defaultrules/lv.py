from .generic import SuffixRules

# Latvian: indefinite adjectives (-isks/-īgs) and -ums/-ija/-ība/-šana nouns,
# each cell >=99% precise. Deliberately absent: -iju/-ijā (collides with -ijs
# masculines), -i adverbs (open class UD lemmatizes as-is), and the whole
# definite-adjective declension family -- >=99% in-dict but 85-100% wrong on
# UD real text (OOV firings are participles or indefinite adjectives, never
# the definite citation form).
DEFAULT_RULES = SuffixRules(
    {
        "isks": "iskām iskās iskos iskus iska isku iskā",
        "īgs": "īgos īgus īgās īga īgu īgā",
        "ums": "umam uma umu umā",
        "ība": "ības ību ībā ībām ībās",
        "ija": "ijas ijai",
        "šana": "šanas šanai šanu šani",
    }
)

# capitalized tokens decline like nouns (Latvijas -> Latvija); "ums" excluded
# (feminine surnames end in -a: Straujuma)
_CAPS_UNSAFE_TARGETS = frozenset({"isks", "īgs", "ums"})
_PROPER_NOUN_RULES = SuffixRules(
    {t: s for t, s in DEFAULT_RULES.cells.items() if t not in _CAPS_UNSAFE_TARGETS}
)

# pluralia tantum colliding with the -ība/-šana singular cells, plus two
# lexicalized invariants
_EXCLUDED = frozenset(
    (
        "priekšvēlēšanu vēlēšanas vēlēšanu ganības ganību ganībā ganībām ganībās "
        "kristības kristību kristībā kristībām kristībās tiesības tiesību tiesībā "
        "tiesībām tiesībās dzemdības dzemdību dzemdībās medības medību "
        "balsstiesības drīzumā pretinflācijas".split()
    )
)


def apply_lv(token: str) -> str | None:
    "Apply pre-defined rules for Latvian."
    # jā- marks debitive verb forms (infinitive lemma, out of reach here)
    if len(token) < 6 or token.startswith("jā") or token in _EXCLUDED:
        return None

    rules = _PROPER_NOUN_RULES if token[0].isupper() else DEFAULT_RULES
    return rules.apply(token)
