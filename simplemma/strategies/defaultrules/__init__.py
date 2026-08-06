"""Rule-based lemmatization of unknown tokens."""

import re
from collections.abc import Callable, Container
from functools import partial

from .generic import apply_rules

# Custom apply functions (logic beyond a single apply_rules call)
from .de import apply_de
from .en import apply_en
from .ka import apply_ka
from .lv import apply_lv
from .nl import apply_nl
from .ru import apply_ru

# Data-only rule modules
from . import cs, eo, es, et, fi, is_ as is_mod, la, ms, nn, pt, ro, sk, sl, sv, uk


def _data_fn(
    rules: dict[re.Pattern[str], str],
    *,
    min_len: int = 1,
    caps: bool = False,
    hyphen: bool = False,
    excluded: Container[str] = frozenset(),
) -> Callable[[str], str | None]:
    """Build an apply function from a rule table and its guards."""
    return partial(
        apply_rules,
        rules=rules,
        min_len=min_len,
        caps=caps,
        hyphen=hyphen,
        excluded=excluded,
    )


RULE_FUNCTIONS: dict[str, Callable[[str], str | None]] = {
    # custom logic
    "de": apply_de,
    "en": apply_en,
    "ka": apply_ka,
    "lv": apply_lv,
    "nl": apply_nl,
    "ru": apply_ru,
    # data-only (generated from rule tables)
    "cs": _data_fn(cs.DEFAULT_RULES, min_len=6, caps=True, hyphen=True),
    "eo": _data_fn(
        eo.DEFAULT_RULES, min_len=4, caps=True, hyphen=True, excluded=eo._EXCLUDED
    ),
    "es": _data_fn(
        es.DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=es._EXCLUDED
    ),
    "et": _data_fn(et.DEFAULT_RULES, min_len=8, caps=True, hyphen=True),
    "fi": _data_fn(
        fi.DEFAULT_RULES, min_len=10, caps=True, hyphen=True, excluded=fi._EXCLUDED
    ),
    "is": _data_fn(is_mod.DEFAULT_RULES, min_len=6, caps=True, hyphen=True),
    "la": _data_fn(
        la.DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=la._EXCLUDED
    ),
    "ms": _data_fn(ms.DEFAULT_RULES, min_len=7, hyphen=True),
    "nn": _data_fn(
        nn.DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=nn._EXCLUDED
    ),
    "pt": _data_fn(
        pt.DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=pt._EXCLUDED
    ),
    "ro": _data_fn(
        ro.DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=ro._EXCLUDED
    ),
    "sk": _data_fn(
        sk.DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=sk._EXCLUDED
    ),
    "sl": _data_fn(
        sl.DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=sl._EXCLUDED
    ),
    "sv": _data_fn(
        sv.DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=sv._EXCLUDED
    ),
    "uk": _data_fn(
        uk.DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=uk._EXCLUDED
    ),
}
