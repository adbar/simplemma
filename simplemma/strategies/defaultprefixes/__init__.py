"""Prefix-based lemmatization of unknown tokens."""

import re

from .de import DE_PREFIX_REGEX
from .ru import RU_PREFIX_REGEX

DEFAULT_KNOWN_PREFIXES: dict[str, re.Pattern[str]] = {
    "de": DE_PREFIX_REGEX,
    "ru": RU_PREFIX_REGEX,
}
