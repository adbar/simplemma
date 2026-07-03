"""Rule-based lemmatization of unknown tokens."""

from collections.abc import Callable

from .cs import apply_cs
from .de import apply_de
from .en import apply_en
from .eo import apply_eo
from .et import apply_et
from .fi import apply_fi
from .ka import apply_ka
from .la import apply_la
from .lb import apply_lb
from .lv import apply_lv
from .mk import apply_mk
from .ms import apply_ms
from .nl import apply_nl
from .nn import apply_nn
from .pl import apply_pl
from .ru import apply_ru
from .se import apply_se
from .sv import apply_sv
from .uk import apply_uk

DEFAULT_RULES: dict[str, Callable[[str], str | None]] = {
    "cs": apply_cs,
    "de": apply_de,
    "en": apply_en,
    "eo": apply_eo,
    "et": apply_et,
    "fi": apply_fi,
    "ka": apply_ka,
    "la": apply_la,
    "lb": apply_lb,
    "lv": apply_lv,
    "mk": apply_mk,
    "ms": apply_ms,
    "nl": apply_nl,
    "nn": apply_nn,
    "pl": apply_pl,
    "ru": apply_ru,
    "se": apply_se,
    "sv": apply_sv,
    "uk": apply_uk,
}
