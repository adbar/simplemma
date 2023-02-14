"""Tests for Simplemma's language detection utilities."""

import logging

from simplemma.language_detector import (
    in_target_language,
    langdetect,
)

from .test_token_sampler import CustomTokenSampler

logging.basicConfig(level=logging.DEBUG)


def test_detection() -> None:
    # sanity checks
    assert langdetect(" aa ", lang=("de", "en"), greedy=True) == [("unk", 1)]
    text = "Test test"

    assert langdetect(text, lang=("de", "en"), greedy=False) == [
        ("de", 1.0),
        ("en", 1.0),
        ("unk", 0.0),
    ]
    assert langdetect(text, lang=("de", "en"), greedy=True) == [
        ("de", 1.0),
        ("en", 1.0),
        ("unk", 0.0),
    ]

    # language detection
    results = langdetect(
        "Dieser Satz ist auf Deutsch.", lang=("de", "en"), greedy=False
    )
    assert results[0][0] == "de"
    results = langdetect("Dieser Satz ist auf Deutsch.", lang=("de", "en"), greedy=True)
    assert results[0][0] == "de"
    results = langdetect(
        "Nztruedg nsüplke deutsches weiter bgfnki gtrpinadsc.",
        lang=("de", "en"),
        greedy=False,
    )
    assert results == [("de", 0.4), ("en", 0.0), ("unk", 0.6)]

    assert langdetect(
        '"Exoplaneta, též extrasolární planeta, je planeta obíhající kolem jiné hvězdy než kolem Slunce."',
        lang=("cs", "sk"),
    ) == [("cs", 0.75), ("sk", 0.125), ("unk", 0.25)]

    assert langdetect(
        '"Moderní studie narazily na několik tajemství." Extracted from Wikipedia.',
        lang=("cs", "en"),
        token_samplers=[CustomTokenSampler(6)],
    ) == [("en", 1.0), ("cs", 0.0), ("unk", 0.0)]


def test_in_target_language() -> None:
    assert in_target_language("", lang="en") == 0
    assert (
        in_target_language(
            "opera post physica posita (τὰ μετὰ τὰ φυσικά)", lang=("la",)
        )
        == 0.5
    )
    assert (
        in_target_language("opera post physica posita (τὰ μετὰ τὰ φυσικά)", lang="la")
        == 0.5
    )

    assert (
        in_target_language(
            '"Moderní studie narazily na několik tajemství." Extracted from Wikipedia.',
            lang="en",
            token_sampler=CustomTokenSampler(6),
        )
        == 1.0
    )
