"""Tests for `split_sentences`, one case per decision rule."""

import time
import unicodedata

import pytest

from simplemma import split_sentences


def test_basic_and_tail() -> None:
    assert split_sentences("Erster Satz. Zweiter Satz!", "de") == [
        "Erster Satz.",
        "Zweiter Satz!",
    ]
    # a final sentence without terminator is still returned
    assert split_sentences("Ende gut. alles gut", "de") == ["Ende gut. alles gut"]
    assert split_sentences("", "de") == []
    assert split_sentences("   \n ", "de") == []


def test_initials_are_no_boundary() -> None:
    assert split_sentences("Der Preis, den J. Schmidt gewann.", "de") == [
        "Der Preis, den J. Schmidt gewann."
    ]
    assert split_sentences("Voici M. Dupont annonçant sa victoire.", "fr") == [
        "Voici M. Dupont annonçant sa victoire."
    ]


def test_ordinals_and_units() -> None:
    assert split_sentences("Das Tor fiel in der 95. Minute des Spiels.", "de") == [
        "Das Tor fiel in der 95. Minute des Spiels."
    ]
    # a lowercase single letter after a digit is a unit that ends the sentence
    assert split_sentences("Словарь издан в 1957 г. Алгоритм известен.", "ru") == [
        "Словарь издан в 1957 г.",
        "Алгоритм известен.",
    ]


def test_sentence_initial_abbreviation() -> None:
    assert split_sentences("Er kam an. Dr. Meier sprach lange.", "de") == [
        "Er kam an.",
        "Dr. Meier sprach lange.",
    ]


def test_block_initial_terminator() -> None:
    assert split_sentences(". Ende", "de") == [". Ende"]
    assert split_sentences(".", "de") == ["."]
    assert split_sentences("\n\n. Ende", "de") == [". Ende"]
    assert split_sentences("Ende. . Weiter", "de") == ["Ende.", ". Weiter"]


def test_abbreviations_and_starter_arbitration() -> None:
    assert split_sentences("Wir liefern in ca. 7 Tagen aus.", "de") == [
        "Wir liefern in ca. 7 Tagen aus."
    ]
    # an abbreviation CAN end a sentence before a known sentence starter
    assert split_sentences("Er kauft die Firma u. a. Die Preise steigen.", "de") == [
        "Er kauft die Firma u. a.",
        "Die Preise steigen.",
    ]


def test_no_arbitration_after_initials() -> None:
    assert split_sentences("Voici M. Le Pen qui a gagné hier.", "fr") == [
        "Voici M. Le Pen qui a gagné hier."
    ]
    assert split_sentences("Hij sprak met J. De Wit gisteren.", "nl") == [
        "Hij sprak met J. De Wit gisteren."
    ]


def test_ellipsis_and_closers() -> None:
    assert split_sentences("Er zögerte . . . Dann kam er doch.", "de") == [
        "Er zögerte . . . Dann kam er doch."
    ]
    # a spaced "..." ends a sentence, like "…" and like the unspaced form
    assert split_sentences("Er zögerte ... Dann kam er doch.", "de") == [
        "Er zögerte ...",
        "Dann kam er doch.",
    ]
    assert split_sentences("Er zögerte … Dann kam er doch.", "de") == [
        "Er zögerte …",
        "Dann kam er doch.",
    ]
    # ... but a lowercase continuation still suppresses it
    assert split_sentences("Er zögerte ... dann kam er doch.", "de") == [
        "Er zögerte ... dann kam er doch."
    ]
    # a bracketed run is an elision marker inside the sentence, not an end
    assert split_sentences("Er sagte (...) Dann ging er.", "de") == [
        "Er sagte (...) Dann ging er."
    ]
    assert split_sentences('Sie rief: "Komm!") Danach Stille.', "de") == [
        'Sie rief: "Komm!")',
        "Danach Stille.",
    ]


def test_lowercase_next() -> None:
    # '.' before a lowercase word is no boundary...
    assert split_sentences("The end. or was it?", "en") == ["The end. or was it?"]
    # ...but a bare '?'/'!' is (informal text, measured safe)
    assert split_sentences("where did you grow up? india?", "en") == [
        "where did you grow up?",
        "india?",
    ]
    # a closed '?' is not bare: lowercase continuation stays glued
    assert split_sentences('"Was?" fragte sie leise.', "de") == [
        '"Was?" fragte sie leise.'
    ]


def test_word_window_stops_at_any_whitespace() -> None:
    assert split_sentences("Er kam\nDr. Meier sprach.\tEnde gut. Aus.", "de") == [
        "Er kam\nDr. Meier sprach.",
        "Ende gut.",
        "Aus.",
    ]
    assert split_sentences("Wir liefern in\xa0ca. 7 Tagen aus.", "de") == [
        "Wir liefern in\xa0ca. 7 Tagen aus."
    ]


def test_spaced_punctuation_register() -> None:
    assert split_sentences("Le prix est bas . Les clients sont contents .", "fr") == [
        "Le prix est bas .",
        "Les clients sont contents .",
    ]


def test_space_free_text_stays_linear() -> None:
    text = "wort.\n" * 40_000
    tick = time.perf_counter()
    assert split_sentences(text, "de") == [text.strip()]
    assert time.perf_counter() - tick < 2.0


def test_quote_final_word_is_not_read_as_an_ordinal() -> None:
    assert split_sentences(
        "a high of 943 in September of '67. By March the Dow fell.", "en"
    ) == ["a high of 943 in September of '67.", "By March the Dow fell."]
    assert split_sentences(
        'expositions like "Revolution number 9". At the same time it grew.', "en"
    ) == ['expositions like "Revolution number 9".', "At the same time it grew."]
    # the price: a quoted abbreviation now ends a sentence (26 UD cases)
    assert split_sentences('"Dr." Meier kam an.', "de") == ['"Dr."', "Meier kam an."]


def test_nfd_input_matches_nfc_input() -> None:
    for text, lang in (
        ("Ver a pág. 12 do livro. Fim.", "pt"),
        ("Zobacz św. Jana dzisiaj. Koniec.", "pl"),
        ("Wir liefern in ca. Während dessen kam er.", "de"),
        ("Mluvil s dr. Když přišel domů.", "cs"),
    ):
        assert split_sentences(unicodedata.normalize("NFD", text), lang) == [
            unicodedata.normalize("NFD", s) for s in split_sentences(text, lang)
        ], lang


def test_spaced_closer_stays_with_the_following_sentence() -> None:
    """The closer stays with the sentence it starts, not the one it ends."""
    assert split_sentences("Il a dit : « Bonjour. » Puis il est parti.", "fr") == [
        "Il a dit : « Bonjour.",
        "» Puis il est parti.",
    ]
    # unspaced closers do attach, which is what _CLOSERS is for
    assert split_sentences('Sie rief "Komm!" Danach war es still.', "de") == [
        'Sie rief "Komm!"',
        "Danach war es still.",
    ]


def test_greek_question_mark() -> None:
    assert split_sentences("Ήρθες; Ναι, ήρθα.", "el") == ["Ήρθες;", "Ναι, ήρθα."]
    # a bare ';' gets the same informal-lowercase exception as '?'
    assert split_sentences("ήρθες; ναι ήρθα;", "el") == ["ήρθες;", "ναι ήρθα;"]
    # U+037E, the legacy spelling of the same mark (NFC folds it to ';'), in
    # both paths: as a terminator and under the bare-question exception
    assert split_sentences("Ήρθες\u037e Ναι.", "el") == ["Ήρθες\u037e", "Ναι."]
    assert split_sentences("ήρθες\u037e ναι ήρθα\u037e", "el") == [
        "ήρθες\u037e",
        "ναι ήρθα\u037e",
    ]


def test_starter_arbitration_crosses_hard_wrap() -> None:
    assert split_sentences("Er kauft die Firma u. a. Die\nPreise steigen.", "de") == [
        "Er kauft die Firma u. a.",
        "Die\nPreise steigen.",
    ]


def test_paragraph_break_is_always_a_boundary() -> None:
    assert split_sentences("Überschrift ohne Punkt\n\nDer Text beginnt.", "de") == [
        "Überschrift ohne Punkt",
        "Der Text beginnt.",
    ]


def test_generic_profile_for_unknown_languages() -> None:
    assert split_sentences("Una frase. Otra frase.", None) == [
        "Una frase.",
        "Otra frase.",
    ]
    assert split_sentences("Una frase. Otra frase.", "xx") == [
        "Una frase.",
        "Otra frase.",
    ]


def test_language_tuple_selects_the_profile() -> None:
    text = "Er kauft die Firma u. a. Die Preise steigen."
    two = ["Er kauft die Firma u. a.", "Die Preise steigen."]
    assert split_sentences(text, ("de",)) == split_sentences(text, "de") == two
    # first code wins: text has one segmentation
    assert split_sentences(text, ("de", "en")) == two
    assert split_sentences(text, None) == [text]  # the profile does the work
    with pytest.raises(TypeError):
        split_sentences(text, ["de"])  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        split_sentences(text, ())


def test_new_language_profiles() -> None:
    # cs/nl/pt lists gated 2026-07-25 (cs formal registers +0.05 F1)
    for text, lang, expected in (
        (
            "Zkouška je např. velmi dobrá. Nový odstavec začíná.",
            "cs",
            ["Zkouška je např. velmi dobrá.", "Nový odstavec začíná."],
        ),
        (
            "De heer dr. Jansen kwam aan. Daarna begon het.",
            "nl",
            ["De heer dr. Jansen kwam aan.", "Daarna begon het."],
        ),
        (
            "Chegou o Sr. Silva de manhã. Depois saiu.",
            "pt",
            ["Chegou o Sr. Silva de manhã.", "Depois saiu."],
        ),
    ):
        assert split_sentences(text, lang) == expected, lang
