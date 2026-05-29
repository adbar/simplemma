"""Prefix-based lemmatization of unknown tokens."""

import re
from typing import Dict

from .de import DE_PREFIX_REGEX
from .ru import RU_PREFIX_REGEX

DEFAULT_KNOWN_PREFIXES: Dict[str, re.Pattern[str]] = {
    "de": DE_PREFIX_REGEX,
    "ru": RU_PREFIX_REGEX,
}
