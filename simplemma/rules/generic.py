from typing import Dict, Optional, Pattern


def apply_rules(token: str, rules: Dict[Pattern[str], str]) -> Optional[str]:
    for rule, substitution in rules.items():
        candidate = rule.sub(substitution, token)
        if candidate != token:
            return candidate
    return None
