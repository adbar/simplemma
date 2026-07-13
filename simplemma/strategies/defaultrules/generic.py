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
    """Use pre-defined rules to look for a lemma. The keyword-only guards
    (length floor, capitalized/hyphenated skip, stoplist) default to no-ops."""
    if (
        len(token) < min_len
        or (caps and token[:1].isupper())
        or (hyphen and "-" in token)
        or token in excluded
    ):
        return None
    for rule, substitution in rules.items():
        candidate = rule.sub(substitution, token)
        if candidate != token:
            return candidate
    return None
