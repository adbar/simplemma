import re
from collections.abc import Container


def apply_rules(
    token: str,
    rules: dict[re.Pattern[str], str],
    *,
    min_len: int = 1,
    caps: bool = False,
    hyphen: bool = False,
    excluded: Container[str] = frozenset(),
) -> str | None:
    """Use pre-defined rules to look for a lemma.

    The keyword-only guard parameters cover the shape shared by every
    data-driven language module (a length floor, a capitalized-token skip, a
    hyphenated-compound skip, and an explicit stoplist); their defaults are
    neutral (no guard applied) so a caller that only wants first-match
    dispatch -- e.g. lv, which picks between two rule tables by hand -- is
    unaffected."""
    if (
        len(token) < min_len
        or (caps and token[0].isupper())
        or (hyphen and "-" in token)
        or token in excluded
    ):
        return None
    for rule, substitution in rules.items():
        candidate = rule.sub(substitution, token)
        if candidate != token:
            return candidate
    return None
