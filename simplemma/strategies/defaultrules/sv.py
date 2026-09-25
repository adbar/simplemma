from .generic import SuffixRules

# OOV invariants
_EXCLUDED = frozenset({"enligt", "antingen", "enbart"})

# Swedish noun declension, adjective comparison, and verb conjugation,
# mined lemma-first (99.76% in-dict).
DEFAULT_RULES = SuffixRules(
    {
        "bar": (
            "barastes barares baraste barasts barare barast bares baras barts bare"
            " bara bart"
        ),
        "ing": "ingarnas ingarna ingens ingars ingen ings",
        "het": "heternas hetens heten heter hets",
        "isk": "iskares iskare",
        "ion": "ionernas ionerna ionens ioners ionen ioner",
        "ig": "igastes igares igaste igasts igare igast iges igts igs ige igt",
        "sk": "skasts skast skts sks skt",
        "nde": "ndenas ndena",
        "k": "kastes kaste",
        "era": "erande eras",
        "el": "els",
    },
    min_len=6,
    caps=True,
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_sv = DEFAULT_RULES.apply
