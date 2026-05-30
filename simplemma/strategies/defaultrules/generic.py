import re


def apply_rules(token: str, rules: dict[re.Pattern[str], str]) -> str | None:
    "Use pre-defined rules to look for a lemma."
    for rule, substitution in rules.items():
        candidate = rule.sub(substitution, token)
        if candidate != token:
            return candidate
    return None
