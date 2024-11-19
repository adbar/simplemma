"""Tests for Simplemma's language detection utilities."""

from simplemma import LanguageDetector, in_target_language, langdetect
from simplemma.strategies import DefaultStrategy

from .test_token_sampler import CustomTokenSampler


def test_proportion_in_each_language() -> None:
    # sanity checks
    assert LanguageDetector(
        lang=("de", "en"), lemmatization_strategy=DefaultStrategy(greedy=True)
    ).proportion_in_each_language(" aa ") == {"unk": 1}
    assert langdetect(" aa ", lang=("de", "en"), greedy=True) == [("unk", 1)]

    text = "Test test"
    assert LanguageDetector(
        lang=("de", "en"), lemmatization_strategy=DefaultStrategy(greedy=False)
    ).proportion_in_each_language(text) == {"de": 1.0, "en": 1.0, "unk": 0.0}
    assert langdetect(text, lang=("de", "en"), greedy=False) == [
        ("de", 1.0),
        ("en", 1.0),
        ("unk", 0.0),
    ]
    assert LanguageDetector(
        lang=("de", "en"), lemmatization_strategy=DefaultStrategy(greedy=True)
    ).proportion_in_each_language(text) == {"de": 1.0, "en": 1.0, "unk": 0.0}
    assert langdetect(text, lang=("de", "en"), greedy=True) == [
        ("de", 1.0),
        ("en", 1.0),
        ("unk", 0.0),
    ]

    lang = ("de", "en")
    text = "Nztruedg nsüplke deutsches weiter bgfnki gtrpinadsc."
    assert LanguageDetector(
        lang=lang, lemmatization_strategy=DefaultStrategy(greedy=False)
    ).proportion_in_each_language(text) == {
        "de": 0.4,
        "en": 0.0,
        "unk": 0.6,
    }
    assert langdetect(
        text,
        lang=lang,
        greedy=False,
    ) == [("de", 0.4), ("en", 0.0), ("unk", 0.6)]

    lang = ("cs", "sk")
    text = '"Exoplaneta, též extrasolární planeta, je planeta obíhající kolem jiné hvězdy než kolem Slunce."'
    assert LanguageDetector(lang=lang).proportion_in_each_language(text) == {
        "cs": 0.75,
        "sk": 0.125,
        "unk": 0.25,
    }
    assert langdetect(text, lang=lang) == [("cs", 0.75), ("sk", 0.125), ("unk", 0.25)]

    lang = ("cs", "en")
    text = '"Moderní studie narazily na několik tajemství." Extracted from Wikipedia.'
    assert LanguageDetector(
        lang=lang, token_sampler=CustomTokenSampler(6)
    ).proportion_in_each_language(text) == {
        "en": 1.0,
        "cs": 0.0,
        "unk": 0.0,
    }
    assert langdetect(
        text,
        lang=lang,
        token_samplers=[CustomTokenSampler(6)],
    ) == [("en", 1.0), ("cs", 0.0), ("unk", 0.0)]


def test_in_target_language() -> None:
    lang = "en"
    text = ""

    assert (
        LanguageDetector(lang=(lang,)).proportion_in_target_languages(text)
        == in_target_language(text, lang=lang)
        == 0
    )

    lang = "la"
    text = "opera post physica posita (τὰ μετὰ τὰ φυσικά)"
    assert (
        LanguageDetector(lang=(lang,)).proportion_in_target_languages(text)
        == in_target_language(text, lang=(lang,))
        == 0.5
    )

    assert (
        LanguageDetector(lang=lang).proportion_in_target_languages(text)
        == in_target_language(text, lang=lang)
        == 0.5
    )

    lang = "en"
    text = '"Moderní studie narazily na několik tajemství." Extracted from Wikipedia.'
    assert (
        LanguageDetector(
            lang=lang, token_sampler=CustomTokenSampler(6)
        ).proportion_in_target_languages(text)
        == in_target_language(
            text,
            lang=lang,
            token_sampler=CustomTokenSampler(6),
        )
        == 1.0
    )

    langs = ("en", "de")
    text = "It was a true gift"
    assert (
        LanguageDetector(lang=langs).proportion_in_target_languages(text)
        == in_target_language(text, lang=langs)
        == 1.0
    )


def test_main_language():
    text = "Dieser Satz ist auf Deutsch."
    lang = ("de", "en")

    assert (
        LanguageDetector(
            lang=lang, lemmatization_strategy=DefaultStrategy(greedy=False)
        ).main_language(text)
        == langdetect(text, lang=lang, greedy=False)[0][0]
        == "de"
    )

    assert (
        LanguageDetector(
            lang=lang, lemmatization_strategy=DefaultStrategy(greedy=True)
        ).main_language(text)
        == langdetect(text, lang=lang, greedy=False)[0][0]
        == "de"
    )

    # text = "Dieser Satz ist auf Deutsch. Y esta está en Español."
    # lang = ("de", "es")
    # assert (
    #     LanguageDetector(lang=lang, greedy=False).main_language(text)
    #     == langdetect(text, lang=lang, greedy=False)[0][0]
    #     == "unk"
    # )
