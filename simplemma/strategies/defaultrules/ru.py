import re

from .generic import apply_rules

DEFAULT_RULES = {
    re.compile(r"(?:ости|остью|остей|остям|остями|остях)$"): "ость",
    re.compile(r"(?:ства|ств|ству|ствам|ством|ствами|стве|ствах)$"): "ство",
}


def apply_ru(token: str) -> str | None:
    "Apply pre-defined rules for Russian."
    if token.endswith("ё"):
        return token.replace("ё", "е")

    if len(token) < 10 or token[0].isupper() or "-" in token:
        return None

    # token = token.replace("а́", "a")
    # token = token.replace("о́", "o")
    # token = token.replace("и́", "и")
    # if RUSSIAN_ENDINGS_OCTB.search(token):
    #     return RUSSIAN_ENDINGS_OCTB.sub("ость", token)
    # if RUSSIAN_ENDINGS_CTBO.search(token):
    #     return RUSSIAN_ENDINGS_CTBO.sub("ство", token)

    return apply_rules(token, DEFAULT_RULES)
