"""Tests for `simplemma` package."""

import unicodedata
from collections.abc import Iterator, Mapping

import pytest

from simplemma import Lemmatizer, is_known, lemma_iterator, lemmatize, text_lemmatizer
from simplemma.strategies import (
    DefaultStrategy,
    DictionaryFactory,
    LemmatizationStrategy,
    RaiseErrorFallbackStrategy,
)


def test_custom_dictionary_factory() -> None:
    class CustomDictionaryFactory(DictionaryFactory):
        def get_dictionary(
            self,
            lang: str,
        ) -> Mapping[str, str]:
            return {"testing": "the test works!!"}

    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(
                dictionary_factory=CustomDictionaryFactory()
            )
        ).lemmatize("testing", lang="en")
        == "the test works!!"
    )


def test_readme() -> None:
    """Test function to verify readme examples."""
    myword = "masks"
    assert (
        Lemmatizer().lemmatize(myword, lang="en")
        == lemmatize(myword, lang="en")
        == "mask"
    )
    mytokens = ["Hier", "sind", "Vaccines", "."]
    assert [lemmatize(t, lang="de") for t in mytokens] == [
        "hier",
        "sein",
        "Vaccines",
        ".",
    ]
    # greediness
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False)).lemmatize(
            "angekündigten", lang="de"
        )
        == lemmatize("angekündigten", lang="de", greedy=False)
        == "angekündigt"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "angekündigten", lang="de"
        )
        == lemmatize("angekündigten", lang="de", greedy=True)
        == "ankündigen"
    )
    # chaining
    assert [lemmatize(t, lang=("de", "en")) for t in mytokens] == [
        "hier",
        "sein",
        "vaccine",
        ".",
    ]
    assert (
        Lemmatizer().lemmatize("spaghettis", lang="it")
        == lemmatize("spaghettis", lang="it")
        == "spaghettis"
    )
    assert (
        Lemmatizer().lemmatize("spaghettini", lang="it")
        == lemmatize("spaghettini", lang="it")
        == "spaghettini"
    )
    assert (
        Lemmatizer().lemmatize("spaghettis", lang=("it", "fr"))
        == lemmatize("spaghettis", lang=("it", "fr"))
        == "spaghetti"
    )
    assert (
        Lemmatizer().lemmatize("spaghetti", lang=("it", "fr"))
        == lemmatize("spaghetti", lang=("it", "fr"))
        == "spaghetto"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "spaghettis", lang=("it", "fr")
        )
        == lemmatize("spaghettis", lang=("it", "fr"), greedy=True)
        == "spaghetti"
    )
    assert text_lemmatizer(
        "Sou o intervalo entre o que desejo ser e os outros me fizeram.", lang="pt"
    ) == [
        "ser",
        "o",
        "intervalo",
        "entre",
        "o",
        "que",
        "desejo",
        "ser",
        "e",
        "o",
        "outro",
        "me",
        "fazer",
        ".",
    ]
    # error
    assert Lemmatizer().lemmatize("スパゲッティ", lang="pt") == lemmatize(
        "スパゲッティ", lang="pt"
    )
    assert lemmatize("スパゲッティ", lang="pt") == "スパゲッティ"

    with pytest.raises(ValueError):
        Lemmatizer(
            fallback_lemmatization_strategy=RaiseErrorFallbackStrategy()
        ).lemmatize("スパゲッティ", lang="pt")


def test_apostrophe_variants() -> None:
    """All three apostrophe glyphs fold to the same lemma, including the
    modifier-letter U+02BC common in Ukrainian text (dict keys use U+0027)."""
    assert lemmatize("здоров'я", lang="uk") == "здоров'я"  # straight
    assert lemmatize("здоров’я", lang="uk") == "здоров'я"  # curly U+2019
    assert lemmatize("здоровʼя", lang="uk") == "здоров'я"  # modifier U+02BC


def test_exceptions() -> None:
    """Test if certain code parts correspond to the intended logic."""
    # missing languages or faulty language codes
    with pytest.raises(TypeError):
        Lemmatizer().lemmatize("test", lang=["test"])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        lemmatize("test", lang=["test"])  # type: ignore[arg-type]

    # searches
    with pytest.raises(TypeError):
        assert Lemmatizer().lemmatize(None, lang="en") is None  # type: ignore
    with pytest.raises(TypeError):
        assert lemmatize(None, lang="en") is None  # type: ignore
    with pytest.raises(ValueError):
        assert lemmatize("", lang="en") is None
    with pytest.raises(ValueError):
        assert Lemmatizer().lemmatize("", lang="en") is None


def test_subwords() -> None:
    """Test recognition and conversion of subword units."""
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "OBI", lang="de"
        )
        == lemmatize("OBI", lang="de", greedy=True)
        == "OBI"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False)).lemmatize(
            "mRNA-Impfstoffe", lang="de"
        )
        == lemmatize("mRNA-Impfstoffe", lang="de", greedy=False)
        == "mRNA-Impfstoff"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "mRNA-impfstoffe", lang="de"
        )
        == lemmatize("mRNA-impfstoffe", lang="de", greedy=True)
        == "mRNA-Impfstoff"
    )
    # greedy subword
    myword = "Impftermine"
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False)).lemmatize(
            myword, lang="de"
        )
        == lemmatize(myword, lang="de", greedy=False)
        == "Impftermine"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            myword, lang="de"
        )
        == lemmatize(myword, lang="de", greedy=True)
        == "Impftermin"
    )
    myword = "Impfbeginn"
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False)).lemmatize(
            myword, lang="de"
        )
        == lemmatize(myword, lang="de", greedy=False)
        == "Impfbeginn"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            myword, lang="de"
        )
        == lemmatize(myword, lang="de", greedy=True)
        == "Impfbeginn"
    )
    myword = "Hoffnungsmaschinen"
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False)).lemmatize(
            myword, lang="de"
        )
        == lemmatize(myword, lang="de", greedy=False)
        == "Hoffnungsmaschinen"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            myword, lang="de"
        )
        == lemmatize(myword, lang="de", greedy=True)
        == "Hoffnungsmaschine"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "börsennotierter", lang="de"
        )
        == lemmatize("börsennotierter", lang="de", greedy=True)
        == "börsennotiert"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "journalistischer", lang="de"
        )
        == lemmatize("journalistischer", lang="de", greedy=True)
        == "journalistisch"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Delegiertenstimmen", lang="de"
        )
        == lemmatize("Delegiertenstimmen", lang="de", greedy=True)
        == "Delegiertenstimme"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Koalitionskreisen", lang="de"
        )
        == lemmatize("Koalitionskreisen", lang="de", greedy=True)
        == "Koalitionskreis"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Infektionsfälle", lang="de"
        )
        == lemmatize("Infektionsfälle", lang="de", greedy=True)
        == "Infektionsfall"
    )
    assert (
        lemmatize("Corona-Einsatzstabes", lang="de", greedy=True)
        == "Corona-Einsatzstab"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Clearinghäusern", lang="de"
        )
        == lemmatize("Clearinghäusern", lang="de", greedy=True)
        == "Clearinghaus"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Mittelstreckenjets", lang="de"
        )
        == lemmatize("Mittelstreckenjets", lang="de", greedy=True)
        == "Mittelstreckenjet"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Länderministerien", lang="de"
        )
        == lemmatize("Länderministerien", lang="de", greedy=True)
        == "Länderministerium"
    )
    assert (
        lemmatize("Gesundheitsschutzkontrollen", lang="de", greedy=True)
        == "Gesundheitsschutzkontrolle"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Nachkriegsjuristen", lang="de"
        )
        == lemmatize("Nachkriegsjuristen", lang="de", greedy=True)
        == "Nachkriegsjurist"
    )
    assert (
        lemmatize("insulinproduzierende", lang="de", greedy=True)
        == "insulinproduzierend"
    )
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize("Urlaubsreisenden", lang="de") == lemmatize("Urlaubsreisenden", lang="de", greedy=True) == "Urlaubsreisende"
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Grünenvorsitzende", lang="de"
        )
        == lemmatize("Grünenvorsitzende", lang="de", greedy=True)
        == "Grünenvorsitzende"
    )
    assert (
        lemmatize("Qualifikationsrunde", lang="de", greedy=True)
        == "Qualifikationsrunde"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "krisensichere", lang="de"
        )
        == lemmatize("krisensichere", lang="de", greedy=True)
        == "krisensicher"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "ironischerweise", lang="de"
        )
        == lemmatize("ironischerweise", lang="de", greedy=True)
        == "ironischerweise"
    )
    assert (
        lemmatize("Landespressedienstes", lang="de", greedy=True)
        == "Landespressedienst"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Lehrerverbänden", lang="de"
        )
        == lemmatize("Lehrerverbänden", lang="de", greedy=True)
        == "Lehrerverband"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Terminvergaberunden", lang="de"
        )
        == lemmatize("Terminvergaberunden", lang="de", greedy=True)
        == "Terminvergaberunde"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Gen-Sequenzierungen", lang="de"
        )
        == lemmatize("Gen-Sequenzierungen", lang="de", greedy=True)
        == "Gen-Sequenzierung"
    )
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize("wiederverwendbaren", lang="de") == lemmatize("wiederverwendbaren", lang="de", greedy=True) == "wiederverwendbar"
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Spitzenposten", lang="de"
        )
        == lemmatize("Spitzenposten", lang="de", greedy=True)
        == "Spitzenposten"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "I-Pace", lang="de"
        )
        == lemmatize("I-Pace", lang="de", greedy=True)
        == "I-Pace"
    )
    assert (
        lemmatize("PCR-Bestätigungstests", lang="de", greedy=True)
        == "PCR-Bestätigungstest"
    )
    # assert (
    #    lemmatize("standortübergreifend", lang="de", greedy=True)
    #    == "standortübergreifend"
    # )
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize("obamamäßigsten", lang="de") == lemmatize("obamamäßigsten", lang="de", greedy=True) == "obamamäßig"
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize("obamaartigere", lang="de") == lemmatize("obamaartigere", lang="de", greedy=True) == "obamaartig"
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "durchgestyltes", lang="de"
        )
        == lemmatize("durchgestyltes", lang="de", greedy=True)
        == "durchgestylt"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "durchgeknallte", lang="de"
        )
        == lemmatize("durchgeknallte", lang="de", greedy=True)
        == "durchgeknallt"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "herunterfährt", lang="de"
        )
        == lemmatize("herunterfährt", lang="de", greedy=True)
        == "herunterfahren"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Atomdeals", lang="de"
        )
        == lemmatize("Atomdeals", lang="de", greedy=True)
        == "Atomdeal"
    )
    assert (
        lemmatize("Anspruchsberechtigten", lang="de", greedy=True)
        == "Anspruchsberechtigte"
    )
    # assert (
    #    lemmatize("Bürgerschaftsabgeordneter", lang="de", greedy=True)
    #    == "Bürgerschaftsabgeordnete"
    # )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Lichtbild-Ausweis", lang="de"
        )
        == lemmatize("Lichtbild-Ausweis", lang="de", greedy=True)
        == "Lichtbildausweis"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Kapuzenpullis", lang="de"
        )
        == lemmatize("Kapuzenpullis", lang="de", greedy=True)
        == "Kapuzenpulli"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "Pharmagrößen", lang="de"
        )
        == lemmatize("Pharmagrößen", lang="de", greedy=True)
        == "Pharmagröße"
    )

    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize("beständigsten", lang="de") == lemmatize("beständigsten", lang="de", greedy=True) == "beständig"
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize('zweitstärkster', lang='de') == lemmatize('zweitstärkster', lang='de', greedy=True) == 'zweitstärkste'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize('Abholservices', lang='de') == lemmatize('Abholservices', lang='de', greedy=True) == 'Abholservice'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize('Funktionärsebene', lang='de') == lemmatize('Funktionärsebene', lang='de', greedy=True) == 'Funktionärsebene'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize('strafbewehrte', lang='de') == lemmatize('strafbewehrte', lang='de', greedy=True) == 'strafbewehrt'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize('fälschungssicheren', lang='de') == lemmatize('fälschungssicheren', lang='de', greedy=True) == 'fälschungssicher'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize('Spargelstangen', lang='de') == lemmatize('Spargelstangen', lang='de', greedy=True) == 'Spargelstange'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize("Bandmitgliedern", lang="de") == lemmatize("Bandmitgliedern", lang="de", greedy=True) == "Bandmitglied"

    # prefixes
    assert (
        Lemmatizer().lemmatize("lemmatisiertes", lang="de")
        == lemmatize("lemmatisiertes", lang="de")
        == "lemmatisiert"
    )
    assert (
        Lemmatizer().lemmatize("zerlemmatisiertes", lang="de")
        == lemmatize("zerlemmatisiertes", lang="de")
        == "zerlemmatisiert"
    )
    assert (
        Lemmatizer().lemmatize("фиксированные", lang="ru")
        == lemmatize("фиксированные", lang="ru")
        == "фиксированный"
    )
    assert (
        Lemmatizer().lemmatize("зафиксированные", lang="ru")
        == lemmatize("зафиксированные", lang="ru")
        == "зафиксированный"
    )


def test_numeric_tokens() -> None:
    """Numeric tokens are returned unchanged regardless of language."""
    assert (
        Lemmatizer().lemmatize("2024", lang="en")
        == lemmatize("2024", lang="en")
        == "2024"
    )
    assert lemmatize("123", lang=("de", "en")) == "123"
    # unicode numerals also count as numeric: the short-circuit returns the
    # token verbatim instead of lowercasing it (which would yield "ⅻ")
    assert "Ⅻ".isnumeric()
    assert lemmatize("Ⅻ", lang="en") == "Ⅻ"
    # near-misses are NOT numeric: the strategy falls through to a normal
    # lookup (returning None here) rather than short-circuiting on the token
    assert DefaultStrategy().get_lemma("2024", "en") == "2024"
    assert DefaultStrategy().get_lemma("12.5", "en") is None


def test_is_known() -> None:
    with pytest.raises(TypeError):
        assert is_known(None, lang="en") is None  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        assert is_known("", lang="en") is None

    assert is_known("FanCY", lang="en")
    assert not is_known("Fancy-String", lang="en")

    assert is_known("espejos", lang=("es", "de"))
    assert is_known("espejos", lang=("de", "es"))


def test_get_lemmas_in_text() -> None:
    # text lemmatization
    text = "Nous déciderons une fois arrivées. Voilà."
    assert (
        list(
            Lemmatizer(
                lemmatization_strategy=DefaultStrategy(greedy=False)
            ).get_lemmas_in_text(text, lang="fr")
        )
        == text_lemmatizer(text, lang="fr", greedy=False)
        == [
            "nous",
            "décider",
            "un",
            "fois",
            "arrivée",
            ".",
            "voilà",
            ".",
        ]
    )
    text = "Nous déciderons une fois arrivées. Voilà."
    assert (
        list(
            Lemmatizer(
                lemmatization_strategy=DefaultStrategy(greedy=False)
            ).get_lemmas_in_text(text, lang="fr")
        )
        == list(lemma_iterator(text, lang="fr", greedy=False))
        == text_lemmatizer(text, lang="fr", greedy=False)
    )
    text = "Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas."
    assert (
        list(
            Lemmatizer(
                lemmatization_strategy=DefaultStrategy(greedy=False)
            ).get_lemmas_in_text(text, lang="es")
        )
        == text_lemmatizer(text, lang="es", greedy=False)
        == [
            "pepa",
            "e",
            "iván",
            "son",
            "uno",
            "pareja",
            "sentimental",
            ",",
            "ambos",
            "dedicar",
            "al",
            "doblaje",
            "de",
            "película",
            ".",
        ]
    )
    assert (
        list(
            Lemmatizer(
                lemmatization_strategy=DefaultStrategy(greedy=True)
            ).get_lemmas_in_text(text, lang="es")
        )
        == text_lemmatizer(text, lang="es", greedy=True)
        == [
            "pepa",
            "e",
            "iván",
            "son",
            "uno",
            "pareja",
            "sentimental",
            ",",
            "ambos",
            "dedicar",
            "al",
            "doblaje",
            "de",
            "película",
            ".",
        ]
    )
    # apostrophe-joined tokens reach the clitic/boundary strategies
    assert text_lemmatizer("L'homme n'est qu'un roseau.", lang="fr") == [
        "homme",
        "être",
        "un",
        "roseau",
        ".",
    ]
    assert text_lemmatizer("Ankara Türkiye’nin başkentidir.", lang="tr") == [
        "ankara",
        "Türkiye",
        "başkent",
        ".",
    ]
    assert "здоров'я" in text_lemmatizer("Це для здоров’я людини.", lang="uk")
    assert "do" in text_lemmatizer("They don't sing.", lang="en")
    # test for Esperanto
    text = "Mi vidas la pomon."
    assert (
        list(
            Lemmatizer(
                lemmatization_strategy=DefaultStrategy(greedy=False)
            ).get_lemmas_in_text(text, lang="eo")
        )
        == text_lemmatizer(text, lang="eo", greedy=False)
        == [
            "mi",
            "vidi",
            "la",
            "pomo",
            ".",
        ]
    )


# (lang, text, expected first lemma): sentence-initial casing policy per
# language. Gated languages (da/de/en) keep probable proper nouns; all-caps
# initials are lowered (and may be recovered by lookup); non-gated languages
# lower unconditionally as before.
_INITIAL_CASING_CASES = [
    ("en", "Iran is large.", "Iran"),  # proper noun kept
    ("en", "The cat sleeps.", "the"),  # common word lowered
    ("de", "BERLIN meldet Erfolg.", "Berlin"),  # all-caps recovered
    ("de", "Schöne Tage kommen.", "schön"),  # adjective lowered
    ("de", "Häuser stehen dort.", "Haus"),  # noun kept
    ("da", "MED venlig hilsen.", "med"),  # da: all-caps still lowered
    ("es", "Pepa baila.", "pepa"),  # non-gated lang: unchanged
    ("de", "DENIC verwaltet die Domains.", "DENIC"),  # initial acronym kept
    ("de", "MIT dem Auto fahren.", "mit"),  # dateline homograph defers to D' gate
]


@pytest.mark.parametrize("lang, text, first", _INITIAL_CASING_CASES)
def test_sentence_initial_casing(lang: str, text: str, first: str) -> None:
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False))
    assert next(lem.get_lemmas_in_text(text, lang)) == first


# (lang, text, kept, dropped): tokens that must / must not survive verbatim.
_ACRONYM_CASES = [
    ("de", "Die Firma heißt MIT und ist bekannt.", ["MIT"], []),  # kept mid-sentence
    ("uk", "Колишній Радянський Союз, або СССР, розпався.", ["СССР"], []),
    ("lv", "Viņš dzīvo ASV jau daudzus gadus.", ["ASV"], []),
    ("lt", "Šiaurės Amerikoje esanti JAV yra didelė valstybė.", ["JAV"], []),
    # es/pt/ca: acronym kept instead of collapsing to a verb homograph
    ("es", "El PSOE negocia el IVA con la UE.", ["IVA"], []),
    ("pt", "O IBGE informou que os EUA assinaram.", ["IBGE"], []),
    ("ca", "La FEDER i la USA financen el projecte.", ["USA"], []),
    ("de", "Das steht in Kapitel XII.", ["XII"], []),  # Roman numeral, not an acronym
    # 2-char Roman-numeral lookalikes stay keepable as acronyms
    ("es", "El disco CD es popular hoy.", ["CD"], []),
    ("de", "MM und DC sind hier bekannt.", ["MM", "DC"], []),
    ("uk", "Це СБУ.", ["СБУ"], []),  # lone acronym isn't "shouting" (leave-one-out)
    # an opening quote shifts neither the initial slot nor the flush
    ("de", "„MIT dem Auto fahren.“", ["mit"], ["MIT"]),
    # hy: the Armenian full stop isolates the shouted heading from sentence 2
    (
        "hy",
        "ՎՏԱՆԳ ԱՅՍՏԵՂ։ Կառավարությունը հրապարակեց, որ ՀՀ ստորագրեց փաստաթուղթը։",
        ["ՀՀ"],
        ["ԱՅՍՏԵՂ"],
    ),
    # punctuation runs ('!!!', '...') end the sentence: the shouted headline
    # stays isolated from the next sentence
    (
        "uk",
        "УВАГА НЕБЕЗПЕКА!!! Це звичайне речення про природу.",
        ["небезпека"],
        ["НЕБЕЗПЕКА"],
    ),
    (
        "uk",
        "УВАГА НЕБЕЗПЕКА... Це речення про природу.",
        ["небезпека"],
        ["НЕБЕЗПЕКА"],
    ),
    # non-allowlisted language: acronym still lowered as before
    ("fr", "Ils ont vu un OVNI hier soir.", ["ovni"], ["OVNI"]),
]


@pytest.mark.parametrize("lang, text, kept, dropped", _ACRONYM_CASES)
def test_allcaps_acronym_keeping(
    lang: str, text: str, kept: list[str], dropped: list[str]
) -> None:
    """ALL-CAPS tokens are kept verbatim as likely acronyms in the allowlisted
    languages, unless the sentence is shouted or the token is a Roman numeral."""
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False))
    out = list(lem.get_lemmas_in_text(text, lang))
    for token in kept:
        assert token in out, (token, out)
    for token in dropped:
        assert token not in out, (token, out)


def test_shouted_sentence_defers_to_gate() -> None:
    """A fully shouted sentence turns acronym-keep off; the initial D' gate
    still lowers the first word."""
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False))
    out = list(lem.get_lemmas_in_text("WARNUNG VOR DEM HUNDE", "de"))
    assert out == ["Warnung", "vor", "der", "HUNDE"]


def test_casing_heuristics_off_without_membership() -> None:
    """Both casing heuristics need a dictionary-membership check; a strategy
    without one falls back to unconditional initial-lowering."""

    class _LowerStrategy(LemmatizationStrategy):
        def get_lemma(self, token: str, lang: str) -> str | None:
            return token.lower()

    custom = Lemmatizer(lemmatization_strategy=_LowerStrategy())
    # en gate off: initial proper noun lowered
    assert next(custom.get_lemmas_in_text("Iran is large.", "en")) == "iran"
    # de acronym-keep off: all-caps token lowered as before
    out = list(custom.get_lemmas_in_text("Die Firma heißt MIT und.", "de"))
    assert "mit" in out and "MIT" not in out


def test_lang_tuple_casing_follows_first_language() -> None:
    """Documented semantics: the first language owns the casing policy."""
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy())
    text = "Ils ont vu un OVNI hier soir."
    assert "OVNI" in list(lem.get_lemmas_in_text(text, ("de", "fr")))
    assert "ovni" in list(lem.get_lemmas_in_text(text, ("fr", "de")))


def test_gate_probes_nfc_normalized() -> None:
    """The casing gate must find NFD tokenizer output in the NFC dictionaries
    (unit-level coverage lives in test_casing.py)."""

    class _NFDTokenizer:
        def split_text(self, text: str) -> Iterator[str]:
            return (unicodedata.normalize("NFD", t) for t in text.split(" "))

    lem = Lemmatizer(
        tokenizer=_NFDTokenizer(), lemmatization_strategy=DefaultStrategy()
    )
    # the NFD initial token is still found in the dict and lowered
    assert list(lem.get_lemmas_in_text("Schöne Tage kommen .", "de"))[0] == "schön"


def test_nfc_normalization() -> None:
    """Decomposed (NFD) input must lemmatize like its composed (NFC) form."""
    nfd = unicodedata.normalize("NFD", "Häuser")
    assert lemmatize(nfd, lang="de") == lemmatize("Häuser", lang="de") == "Haus"
    assert is_known(nfd, lang="de") == is_known("Häuser", lang="de") is True
    # output is always NFC, even when the input was decomposed
    out = lemmatize(unicodedata.normalize("NFD", "café"), lang="fr")
    assert out == unicodedata.normalize("NFC", out)


def test_long_token_does_not_hang() -> None:
    """A pathologically long token must return quickly, not trigger O(n²) decomposition."""
    assert lemmatize("a" * 50000, lang="fi") == "a" * 50000  # was minutes, now instant
    assert lemmatize("a" * 101, lang="fi") == "a" * 101
    assert lemmatize("masks", lang="en") == "mask"
