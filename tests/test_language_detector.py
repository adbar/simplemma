"""Tests for Simplemma's language detection utilities."""

import logging

from simplemma import LaguageDetector

logging.basicConfig(level=logging.DEBUG)


def test_detection():
    lang_detector = LaguageDetector()
    # sanity checks
    assert lang_detector.detect_languages(
        " aa ", lang=("de", "en"), extensive=True
    ) == [("unk", 1)]
    text = "Test test"
    assert lang_detector.detect_languages(text, lang=("de", "en"), extensive=False) == [
        ("unk", 1)
    ]
    assert lang_detector.detect_languages(text, lang=("de", "en"), extensive=True) == [
        ("unk", 1)
    ]
    # language detection
    results = lang_detector.detect_languages(
        "Dieser Satz ist auf Deutsch.", lang=("de", "en"), extensive=False
    )
    assert results[0][0] == "de"
    results = lang_detector.detect_languages(
        "Dieser Satz ist auf Deutsch.", lang=("de", "en"), extensive=True
    )
    assert results[0][0] == "de"
    assert lang_detector.detect_languages(
        '"Moderní studie narazily na několik tajemství." Extracted from Wikipedia.',
        lang=("cs", "sk"),
    ) == [("cs", 0.625), ("unk", 0.375), ("sk", 0.125)]
    # target language
    assert lang_detector.detect_coverage_of_languages("", lang="en") == 0
    assert (
        lang_detector.detect_coverage_of_languages(
            "opera post physica posita (τὰ μετὰ τὰ φυσικά)", lang=("la",)
        )
        == 0.5
    )
    assert (
        lang_detector.detect_coverage_of_languages(
            "opera post physica posita (τὰ μετὰ τὰ φυσικά)", lang="la"
        )
        == 0.5
    )
