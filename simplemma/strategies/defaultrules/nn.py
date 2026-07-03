import re

from .generic import apply_rules

# Norwegian Nynorsk: -ing nominalizations, -ar agent nouns, -isk adjectives,
# and a few borrowed suffix families (-jon, -nar), definite/plural declension.
DEFAULT_RULES = {
    re.compile(r"(?:ingane|ingar|ingen|inga)$"): "ing",
    re.compile(r"(?:arane|arar|aren)$"): "ar",
    re.compile(r"(?:jonane|jonar|jonen)$"): "jon",
    re.compile(r"(?:iske)$"): "isk",
    re.compile(r"(?:narane|narar|naren)$"): "nar",
    re.compile(r"(?:aene|aen|aer)$"): "a",
    re.compile(r"(?:gaste|gare)$"): "g",
    re.compile(r"(?:ikken)$"): "ikk",
}


def apply_nn(token: str) -> str | None:
    "Apply pre-defined rules for Norwegian Nynorsk."
    if len(token) < 6 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
