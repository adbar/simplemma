"""Rule-based lemmatization of unknown tokens."""

from typing import Callable, Dict, Optional

from .de import apply_de, fix_known_prefix_de
from .en import apply_en
from .fi import apply_fi
from .nl import apply_nl
from .pl import apply_pl
from .ru import apply_ru, fix_known_prefix_ru


APPLY_RULES: Dict[str, Callable[[str, bool], Optional[str]]] = {
    "de": apply_de,
    "en": apply_en,
    "fi": apply_fi,
    "nl": apply_nl,
    "pl": apply_pl,
    "ru": apply_ru,
}


FIND_KNOWN_PREFIXES: Dict[str, Callable[[str], Optional[str]]] = {
    "de": fix_known_prefix_de,
    "ru": fix_known_prefix_ru,
}


def apply_rules(token: str, lang: Optional[str]) -> Optional[str]:
    "Apply simple rules to out-of-vocabulary words."
    if lang in APPLY_RULES:
        return APPLY_RULES[lang](token)
    return None


def _find_prefix(token: str, lang: Optional[str]) -> Optional[str]:
    "Subword decomposition: pre-defined prefixes (often absent from vocabulary if they are not words)."
    if lang not in FIND_KNOWN_PREFIXES:
        return None

    prefix = FIND_KNOWN_PREFIXES[lang](token)
    if prefix is None or len(prefix) >= len(token):
        return None

    return prefix
