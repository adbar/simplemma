from .generic import SuffixRules

# no definite-adjective cells on purpose: OOV hits are never definite forms
DEFAULT_RULES = SuffixRules(
    {
        "isks": "iskām iskās iskos iskus iska isku iskā",
        "īgs": "īgos īgus īgās īga īgu īgā",
        "ums": "umam uma umu umā",
        "ība": "ības ību ībā ībām ībās",
        "ija": "ijas ijai",
        "šana": "šanas šanai šanu šani",
    },
    min_len=6,
)

# not for capitalized tokens: feminine surnames end in -a (Straujuma)
_CAPS_UNSAFE_TARGETS = frozenset({"isks", "īgs", "ums"})
_PROPER_NOUN_RULES = SuffixRules(
    {t: s for t, s in DEFAULT_RULES.cells.items() if t not in _CAPS_UNSAFE_TARGETS},
    min_len=6,
)

# pluralia tantum and lexicalized invariants
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
    # jā- marks debitive verb forms
    if token.startswith("jā") or token in _EXCLUDED:
        return None

    rules = _PROPER_NOUN_RULES if token[0].isupper() else DEFAULT_RULES
    return rules.apply(token)
