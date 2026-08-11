"""Tests for Simplemma's language detection utilities."""

import pytest

from simplemma import LanguageDetector, in_target_language, langdetect
from simplemma.strategies import DefaultStrategy
from simplemma.utils import normalize_token

from .conftest import CustomTokenSampler


def test_langdetect_no_samplers() -> None:
    # no samplers means no results, not an UnboundLocalError
    assert langdetect("Dies ist ein Test.", lang=("de", "en"), token_samplers=[]) == []


_LANGS = ("de", "en", "cs", "sk")
_TEXTS = (
    "The quick brown fox jumps over the lazy dog.",
    "Der schnelle braune Fuchs springt ueber den Hund.",
    "Exoplaneta extrasolarni planeta obihajici kolem hvezdy.",
    "aa bb cc dd ee",
)


def _reference_each(detector: LanguageDetector, text: str) -> dict[str, float]:
    # tokens-outer reference: the pre-refactor algorithm the langs-outer scan replaces
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
            if detector._lemmatization_strategy.get_lemma(token, lang_code) is not None:
                known[lang_code] += 1
                found = True
        if not found:
            unknown += 1
    results = {lang_code: count / total for lang_code, count in known.items()}
    results["unk"] = unknown / total
    return results


def test_langs_outer_matches_tokens_outer() -> None:
    # the languages-outer refactor must be bit-identical to the tokens-outer scan
    detector = LanguageDetector(lang=_LANGS)
    for text in (*_TEXTS, ""):
        assert detector.proportion_in_each_language(text) == _reference_each(
            detector, text
        )


def test_target_agrees_with_each_language() -> None:
    # the two un-shared loops must agree: target == non-unknown share
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
    "lang, text, greedy",
    [
        (("de", "en"), " aa ", True),
        (("de", "en"), "Test test", False),
        (("de", "en"), "Test test", True),
        (("de", "en"), "Nztruedg nsüplke deutsches weiter bgfnki gtrpinadsc.", False),
        (
            ("cs", "sk"),
            '"Exoplaneta, též extrasolární planeta, je planeta obíhající kolem jiné hvězdy než kolem Slunce."',
            None,
        ),
        # en outscores de: pins the descending sort against alphabetical order
        (("de", "en"), "It was a true gift", None),
        # "unk" outscores both languages: pins its unconditional last place
        (("de", "sv"), "Nztruedg nsüplke deutsches weiter bgfnki gtrpinadsc.", None),
    ],
)
def test_langdetect_agrees_with_class(
    lang: tuple[str, ...], text: str, greedy: bool | None
) -> None:
    """langdetect() must return the class' data, descending by score, "unk" last."""
    if greedy is not None:
        detector = LanguageDetector(
            lang=lang, lemmatization_strategy=DefaultStrategy(greedy=greedy)
        )
        result = langdetect(text, lang=lang, greedy=greedy)
    else:
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
    ).proportion_in_each_language(" aa ") == {"unk": 1}

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
        "cs": 1.0,
        "sk": 0.25,
        "unk": 0.0,
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
        == 2 / 3  # la fill raised coverage of this text from 0.5
    )

    assert (
        LanguageDetector(lang=lang).proportion_in_target_languages(text)
        == in_target_language(text, lang=lang)
        == 2 / 3  # la fill raised coverage of this text from 0.5
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


@pytest.mark.parametrize("greedy", [False, True])
def test_main_language(greedy: bool) -> None:
    text = "Dieser Satz ist auf Deutsch."
    lang = ("de", "en")
    assert (
        LanguageDetector(
            lang=lang, lemmatization_strategy=DefaultStrategy(greedy=greedy)
        ).main_language(text)
        == langdetect(text, lang=lang, greedy=greedy)[0][0]
        == "de"
    )


def test_main_language_unknown() -> None:
    """When no language wins across any sampler, "unk" is returned."""
    detector = LanguageDetector(lang=("de", "en"))
    original_sampler = detector._token_sampler
    # no recognizable tokens: proportion_in_each_language yields {"unk": 1}
    # for every sampler, so no language ever wins
    assert detector.main_language("aa bb cc") == "unk"
    # main_language passes samplers as arguments, never mutating the instance
    assert detector._token_sampler is original_sampler


def test_main_language_tie() -> None:
    """A genuine tie between two supported languages also yields "unk"."""
    detector = LanguageDetector(lang=("de", "en"))
    original_sampler = detector._token_sampler
    # "test" is a valid lemma in both German and English, so de and en stay
    # tied at 1.0 across both the default and the relaxed sampler: there is
    # never a single winner, so the fallback returns "unk"
    assert detector.proportion_in_each_language("Test test") == {
        "de": 1.0,
        "en": 1.0,
        "unk": 0.0,
    }
    assert detector.main_language("Test test") == "unk"
    assert detector._token_sampler is original_sampler
