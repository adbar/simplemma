"""Rule-based lemmatization of unknown tokens."""

from typing import Callable, Dict, Optional

from .de import apply_de
from .en import apply_en
from .et import apply_et
from .fi import apply_fi
from .lv import apply_lv
from .nl import apply_nl
from .pl import apply_pl
from .ru import apply_ru

DEFAULT_RULES: Dict[str, Callable[[str], Optional[str]]] = {
    "de": apply_de,
    "en": apply_en,
    "et": apply_et,
    "fi": apply_fi,
    "lv": apply_lv,
    "nl": apply_nl,
    "pl": apply_pl,
    "ru": apply_ru,
}
