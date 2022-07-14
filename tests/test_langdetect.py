"""Tests for Simplemma's language detection utilities."""

import logging

from simplemma.langdetect import in_target_language, lang_detector

logging.basicConfig(level=logging.DEBUG)


def test_detection():
    # sanity checks
    assert lang_detector(" aa ", lang=("de", "en"), extensive=True) == [("unk", 1)]
    text = "Test test"
    assert lang_detector(text, lang=("de", "en"), extensive=False) == [("unk", 1)]
    assert lang_detector(text, lang=("de", "en"), extensive=True) == [("unk", 1)]
    # language detection
    results = lang_detector(
        "Dieser Satz ist auf Deutsch.", lang=("de", "en"), extensive=False
    )
    assert results[0][0] == "de"
    results = lang_detector(
        "Dieser Satz ist auf Deutsch.", lang=("de", "en"), extensive=True
    )
    assert results[0][0] == "de"
    assert in_target_language("Diese Wörter", lang=("de", "en")) == 1
