"""Simple rules for unknown tokens."""
from typing import Callable, Dict, Optional
from .de import apply_de, fix_known_prefix_de
from .en import apply_en
from .fi import apply_fi
from .nl import apply_nl
from .pl import apply_pl
from .ru import apply_ru, fix_known_prefix_ru

FIND_KNOWN_PREFIXES: Dict[str, Callable[[str], Optional[str]]] = {
    "de": fix_known_prefix_de,
    "ru": fix_known_prefix_ru,
}

APPLY_RULES: Dict[str, Callable[[str, bool], Optional[str]]] = {
    "de": apply_de,
    "en": apply_en,
    "fi": apply_fi,
    "nl": apply_nl,
    "pl": apply_pl,
    "ru": apply_ru,
}
