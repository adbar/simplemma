import warnings

import pytest

from simplemma import LanguageDetector, in_target_language, langdetect
from simplemma.strategies import DefaultStrategy, DictionaryLookupStrategy
from simplemma.utils import normalize_token

from .conftest import CustomTokenSampler


def test_langdetect_no_samplers() -> None:
    assert langdetect("Dies ist ein Test.", lang=("de", "en"), token_samplers=[]) == []


_LANGS = ("de", "en", "cs", "sk")
_TEXTS = (
    "The quick brown fox jumps over the lazy dog.",
    "Der schnelle braune Fuchs springt ueber den Hund.",
    "Exoplaneta extrasolarni planeta obihajici kolem hvezdy.",
    "aa bb cc dd ee",
)


def _reference_each(detector: LanguageDetector, text: str) -> dict[str, float]:
    tokens = [
        normalize_token(token) for token in detector._token_sampler.sample_text(text)
    ]
    total = len(tokens)
    if total == 0:
        return {"unk": 1}
    known = dict.fromkeys(detector._lang, 0)
    unknown = 0
    for token in tokens:
        found = False
        for lang_code in detector._lang:
            if detector._strategies[0].get_lemma(token, lang_code) is not None:
                known[lang_code] += 1
                found = True
        if not found:
            unknown += 1
    results = {lang_code: count / total for lang_code, count in known.items()}
    results["unk"] = unknown / total
    return results


def test_langs_outer_matches_tokens_outer() -> None:
    detector = LanguageDetector(lang=_LANGS)
    for text in (*_TEXTS, ""):
        assert detector.proportion_in_each_language(text) == _reference_each(
            detector, text
        )


def test_target_agrees_with_each_language() -> None:
    detector = LanguageDetector(lang=_LANGS)
    for text in (
        *_TEXTS,
        "the quick zzzzzq",
    ):  # 2/3 recognized: catches exact-float divergence
        each = detector.proportion_in_each_language(text)
        assert detector.proportion_in_target_languages(text) == pytest.approx(
            1 - each["unk"]
        )


@pytest.mark.parametrize(
    "lang, text",
    [
        (("de", "en"), "Test test"),
        (("de", "en"), "Nztruedg nsüplke deutsches weiter bgfnki gtrpinadsc."),
        (
            ("cs", "sk"),
            '"Exoplaneta, též extrasolární planeta, je planeta obíhající kolem jiné hvězdy než kolem Slunce."',
        ),
        # en outscores de: pins the descending sort against alphabetical order
        (("de", "en"), "It was a true gift"),
        # "unk" outscores both languages: pins its unconditional last place
        (("de", "sv"), "Nztruedg nsüplke deutsches weiter bgfnki gtrpinadsc."),
    ],
)
def test_langdetect_agrees_with_class(lang: tuple[str, ...], text: str) -> None:
    """langdetect() must return the class' data, descending by score, "unk" last."""
    detector = LanguageDetector(lang=lang)
    result = langdetect(text, lang=lang)
    assert dict(result) == detector.proportion_in_each_language(text)
    scores = [score for code, score in result if code != "unk"]
    assert scores == sorted(scores, reverse=True)
    if len(result) > 1:
        assert result[-1][0] == "unk"


def test_proportion_in_each_language() -> None:
    assert LanguageDetector(
        lang=("de", "en"), lemmatization_strategy=DefaultStrategy(greedy=True)
    ).proportion_in_each_language(" a ") == {"unk": 1}

    text = "Test test"
    assert LanguageDetector(
        lang=("de", "en"), lemmatization_strategy=DefaultStrategy(greedy=False)
    ).proportion_in_each_language(text) == {"de": 1.0, "en": 1.0, "unk": 0.0}
    assert LanguageDetector(
        lang=("de", "en"), lemmatization_strategy=DefaultStrategy(greedy=True)
    ).proportion_in_each_language(text) == {"de": 1.0, "en": 1.0, "unk": 0.0}

    lang = ("de", "en")
    text = "Nztruedg nsüplke deutsches weiter bgfnki gtrpinadsc."
    assert LanguageDetector(
        lang=lang, lemmatization_strategy=DefaultStrategy(greedy=False)
    ).proportion_in_each_language(text) == {
        "de": 0.4,
        "en": 0.0,
        "unk": 0.6,
    }

    lang = ("cs", "sk")
    text = '"Exoplaneta, též extrasolární planeta, je planeta obíhající kolem jiné hvězdy než kolem Slunce."'
    assert LanguageDetector(lang=lang).proportion_in_each_language(text) == {
        "cs": 8 / 9,
        "sk": 3 / 9,
        "unk": 1 / 9,
    }

    lang = ("cs", "en")
    text = '"Moderní studie narazily na několik tajemství." Extracted from Wikipedia.'
    assert LanguageDetector(
        lang=lang, token_sampler=CustomTokenSampler(6)
    ).proportion_in_each_language(text) == {
        "en": 1.0,
        "cs": 0.0,
        "unk": 0.0,
    }


@pytest.mark.parametrize(
    "lang, text, by_class, by_function",
    [
        ("en", "", 0, 0),
        (("la",), "opera post physica posita (τὰ μετὰ τὰ φυσικά)", 4 / 7, 4 / 7),
        ("la", "opera post physica posita (τὰ μετὰ τὰ φυσικά)", 4 / 7, 4 / 7),
        (("en", "de"), "It was a true gift", 1.0, 1.0),
        # the class looks words up, the function lemmatizes (affix-only word)
        (
            "cs",
            '"Exoplaneta, též extrasolární planeta, je planeta obíhající kolem jiné hvězdy než kolem Slunce."',
            8 / 9,
            1.0,
        ),
    ],
)
def test_in_target_language(
    lang: str | tuple[str, ...], text: str, by_class: float, by_function: float
) -> None:
    assert LanguageDetector(lang=lang).proportion_in_target_languages(text) == by_class
    assert in_target_language(text, lang=lang) == by_function


def test_in_target_language_custom_sampler() -> None:
    text = '"Moderní studie narazily na několik tajemství." Extracted from Wikipedia.'
    sampler = CustomTokenSampler(6)
    detector = LanguageDetector(lang="en", token_sampler=sampler)
    assert detector.proportion_in_target_languages(text) == 1.0
    assert in_target_language(text, lang="en", token_sampler=sampler) == 1.0


def test_main_language() -> None:
    text = "Dieser Satz ist auf Deutsch."
    lang = ("de", "en")
    assert (
        LanguageDetector(lang=lang).main_language(text)
        == langdetect(text, lang=lang)[0][0]
        == "de"
    )


def test_full_strategy_fallback() -> None:
    """No dictionary key matches (ko particles), the full strategy decides."""
    text = "대륙과의 왕래가 불가능하게 된 것이다."
    lang = ("ko", "en")
    lookup_only = LanguageDetector(
        lang, lemmatization_strategy=DictionaryLookupStrategy()
    )
    assert lookup_only.main_language(text) == "unk"
    assert LanguageDetector(lang).main_language(text) == "ko"
    assert langdetect(text, lang=lang)[0] == ("ko", 1.0)
    assert langdetect(text, lang=lang, low_memory=True)[0] == ("ko", 1.0)


def test_langdetect_greedy_deprecated() -> None:
    text = "Dieser Satz ist auf Deutsch."
    with pytest.warns(DeprecationWarning, match="greedy"):
        result = langdetect(text, lang=("de", "en"), greedy=True)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert result == langdetect(text, lang=("de", "en"))


def test_main_language_unknown() -> None:
    """When no language wins across any sampler, "unk" is returned."""
    detector = LanguageDetector(lang=("de", "en"))
    original_sampler = detector._token_sampler
    assert detector.main_language("aa bb cc") == "unk"
    # main_language passes samplers as arguments, never mutating the instance
    assert detector._token_sampler is original_sampler


def test_main_language_tie() -> None:
    """A genuine tie between two supported languages also yields "unk"."""
    detector = LanguageDetector(lang=("de", "en"))
    original_sampler = detector._token_sampler
    # "test" is a lemma in both languages under every sampler
    assert detector.proportion_in_each_language("Test test") == {
        "de": 1.0,
        "en": 1.0,
        "unk": 0.0,
    }
    assert detector.main_language("Test test") == "unk"
    assert detector._token_sampler is original_sampler
