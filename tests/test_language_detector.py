"""Tests for Simplemma's language detection utilities."""

import logging
from typing import List

from simplemma.tokenizer import Tokenizer

from simplemma.language_detector import (
    in_target_language,
    langdetect,
    TokenSampler,
    RELAXED_SPLIT_INPUT,
)

logging.basicConfig(level=logging.DEBUG)


class CustomTokenSampler(TokenSampler):
    def __init__(self, skip_tokens: int) -> None:
        super().__init__()
        self.skip_tokens: int = skip_tokens

    def sample_tokens(self, text: str) -> List[str]:
        return list(self.tokenizer.split_text(text))[self.skip_tokens :]


def test_token_sampler():
    sampler = TokenSampler()
    assert sampler.sample_tokens("ABCD Efgh ijkl mn") == ["ijkl"]
    assert sampler.sample_tokens("Abcd_E Abcde") == ["Abcd", "Abcde"]

    sampler = TokenSampler(capitalized_threshold=0)
    assert sampler.sample_tokens("ABCD Efgh ijkl mn") == ["ABCD", "Efgh", "ijkl"]

    sampler = TokenSampler(capitalized_threshold=0, max_tokens=1)
    assert sampler.sample_tokens("Efgh Efgh ijkl mn") == ["Efgh"]

    relaxed = TokenSampler(
        tokenizer=Tokenizer(splitting_regex=RELAXED_SPLIT_INPUT),
        max_tokens=1000,
        capitalized_threshold=0,
    )
    assert relaxed.sample_tokens("ABCD Efgh ijkl mn") == ["ABCD", "Efgh", "ijkl"]

    custom = CustomTokenSampler(3)
    assert custom.sample_tokens("ABCD Efgh ijkl mn") == []


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
