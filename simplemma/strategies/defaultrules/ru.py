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

    return apply_rules(token, DEFAULT_RULES, min_len=9, caps=True, hyphen=True)
