from .generic import SuffixRules

_EXCLUDED = frozenset({"enligt", "antingen", "enbart"})

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
    excluded=_EXCLUDED,
)


apply_sv = DEFAULT_RULES.apply
