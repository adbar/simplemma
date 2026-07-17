"""Rule-based lemmatization of unknown tokens."""

from collections.abc import Callable

from .cs import apply_cs
from .de import apply_de
from .en import apply_en
from .eo import apply_eo
from .es import apply_es
from .et import apply_et
from .fi import apply_fi
from .is_ import apply_is
from .ka import apply_ka
from .la import apply_la
from .lv import apply_lv
from .ms import apply_ms
from .nl import apply_nl
from .nn import apply_nn
from .pt import apply_pt
from .ro import apply_ro
from .ru import apply_ru
from .sk import apply_sk
from .sl import apply_sl
from .sv import apply_sv
from .uk import apply_uk

RULE_FUNCTIONS: dict[str, Callable[[str], str | None]] = {
    "cs": apply_cs,
    "de": apply_de,
    "en": apply_en,
    "eo": apply_eo,
    "es": apply_es,
    "et": apply_et,
    "fi": apply_fi,
    "is": apply_is,
    "ka": apply_ka,
    "la": apply_la,
    "lv": apply_lv,
    "ms": apply_ms,
    "nl": apply_nl,
    "nn": apply_nn,
    "pt": apply_pt,
    "ro": apply_ro,
    "ru": apply_ru,
    "sk": apply_sk,
    "sl": apply_sl,
    "sv": apply_sv,
    "uk": apply_uk,
}
