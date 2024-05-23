"""
This module provides support for deprecated language detection functions.
It will be removed in further versions.
"""

from typing import Any


def in_target_language(*args: Any, **kwargs: Any) -> None:
    raise ValueError(
        "Deprecated module: Use from language_detector import in_target_language instead."
    )


def lang_detector(*args: Any, **kwargs: Any) -> None:
    raise ValueError(
        "Deprecated module: Use from language_detector import lang_detector instead."
    )
