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
    caps: bool = True,
    hyphen: bool = True,
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
}

# data-only: (code, module, min_len) — caps=True, hyphen=True are defaults
_DATA_LANGS: list[tuple[str, object, int]] = [
    ("cs", cs, 6),
    ("eo", eo, 4),
    ("es", es, 6),
    ("et", et, 8),
    ("fi", fi, 10),
    ("is", is_mod, 6),
    ("la", la, 6),
    ("ms", ms, 7),
    ("nn", nn, 6),
    ("pt", pt, 6),
    ("ro", ro, 6),
    ("sk", sk, 6),
    ("sl", sl, 6),
    ("sv", sv, 6),
    ("uk", uk, 6),
]
for _code, _mod, _min_len in _DATA_LANGS:
    RULE_FUNCTIONS[_code] = _data_fn(
        _mod.DEFAULT_RULES,  # type: ignore[attr-defined]
        min_len=_min_len,
        caps=_code != "ms",
        excluded=getattr(_mod, "_EXCLUDED", frozenset()),
    )
