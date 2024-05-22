"""
This module provides support for deprecated language detection functions.
It will be removed in further versions.
"""


def in_target_language(*args, **kwargs):
    raise ValueError(
        "Deprecated module: Use from language_detector import in_target_language instead."
    )


def lang_detector(*args, **kwargs):
    raise ValueError(
        "Deprecated module: Usse from language_detector import lang_detector instead."
    )
