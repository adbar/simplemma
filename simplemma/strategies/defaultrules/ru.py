from .generic import SuffixRules

DEFAULT_RULES = SuffixRules(
    {
        "ость": "ости остью остей остям остями остях",
        "ство": "ства ств ству ствам ством ствами стве ствах",
    },
    min_len=9,
    caps=True,
    hyphen=True,
)


def apply_ru(token: str) -> str | None:
    "Apply pre-defined rules for Russian."
    if token.endswith("ё"):
        return token.replace("ё", "е")

    return DEFAULT_RULES.apply(token)
