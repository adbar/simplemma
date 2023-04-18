"""Prefix-based lemmatization of unknown tokens."""

from typing import Dict, Pattern

from .de import DE_PREFIX_REGEX
from .ru import RU_PREFIX_REGEX

DEFAULT_KNOWN_PREFIXES: Dict[str, Pattern[str]] = {
    "de": DE_PREFIX_REGEX,
    "ru": RU_PREFIX_REGEX,
}
