"""Tests for `simplemma` package."""

import logging
import pytest
from typing import Dict

from simplemma import lemmatize, is_known, text_lemmatizer, lemma_iterator, Lemmatizer
from simplemma.strategies import (
    DictionaryFactory,
    DefaultStrategy,
    DictionaryLookupStrategy,
    GreedyDictionaryLookupStrategy,
    RaiseErrorFallbackStrategy,
)

logging.basicConfig(level=logging.DEBUG)


def test_custom_dictionary_factory() -> None:
    class CustomDictionaryFactory(DictionaryFactory):
        def get_dictionary(
            self,
            lang: str,
        ) -> Dict[str, str]:
            return {"testing": "the test works!!"}

    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(
                DictionaryLookupStrategy(CustomDictionaryFactory())
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
        Lemmatizer(lemmatization_strategy=DefaultStrategy()).lemmatize(
            "angekündigten", lang="de"
        )
        == lemmatize("angekündigten", lang="de", greedy=False)
        == "angekündigt"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("angekündigten", lang="de")
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
        == "spaghetto"
    )
    assert (
        Lemmatizer().lemmatize("spaghettini", lang="it")
        == lemmatize("spaghettini", lang="it")
        == "spaghetto"
    )
    assert (
        Lemmatizer().lemmatize("spaghettis", lang=("it", "fr"))
        == lemmatize("spaghettis", lang=("it", "fr"))
        == "spaghetto"
    )
    assert (
        Lemmatizer().lemmatize("spaghetti", lang=("it", "fr"))
        == lemmatize("spaghetti", lang=("it", "fr"))
        == "spaghetto"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("spaghettis", lang=("it", "fr"))
        == lemmatize("spaghettis", lang=("it", "fr"), greedy=True)
        == "spaghetto"
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
    Lemmatizer().lemmatize("スパゲッティ", lang="pt") == lemmatize(
        "スパゲッティ", lang="pt"
    ) == None

    with pytest.raises(ValueError):
        Lemmatizer(
            fallback_lemmatization_strategy=RaiseErrorFallbackStrategy()
        ).lemmatize("スパゲッティ", lang="pt")


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
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("OBI", lang="de")
        == lemmatize("OBI", lang="de", greedy=True)
        == "OBI"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy()).lemmatize(
            "mRNA-Impfstoffe", lang="de"
        )
        == lemmatize("mRNA-Impfstoffe", lang="de", greedy=False)
        == "mRNA-Impfstoff"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("mRNA-impfstoffe", lang="de")
        == lemmatize("mRNA-impfstoffe", lang="de", greedy=True)
        == "mRNA-Impfstoff"
    )
    # greedy subword
    myword = "Impftermine"
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy()).lemmatize(
            myword, lang="de"
        )
        == lemmatize(myword, lang="de", greedy=False)
        == "Impftermin"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize(myword, lang="de")
        == lemmatize(myword, lang="de", greedy=True)
        == "Impftermin"
    )
    myword = "Impfbeginn"
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy()).lemmatize(
            myword, lang="de"
        )
        == lemmatize(myword, lang="de", greedy=False)
        == "Impfbeginn"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize(myword, lang="de")
        == lemmatize(myword, lang="de", greedy=True)
        == "Impfbeginn"
    )
    myword = "Hoffnungsmaschinen"
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy()).lemmatize(
            myword, lang="de"
        )
        == lemmatize(myword, lang="de", greedy=False)
        == "Hoffnungsmaschine"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize(myword, lang="de")
        == lemmatize(myword, lang="de", greedy=True)
        == "Hoffnungsmaschine"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("börsennotierter", lang="de")
        == lemmatize("börsennotierter", lang="de", greedy=True)
        == "börsennotiert"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("journalistischer", lang="de")
        == lemmatize("journalistischer", lang="de", greedy=True)
        == "journalistisch"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Delegiertenstimmen", lang="de")
        == lemmatize("Delegiertenstimmen", lang="de", greedy=True)
        == "Delegiertenstimme"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Koalitionskreisen", lang="de")
        == lemmatize("Koalitionskreisen", lang="de", greedy=True)
        == "Koalitionskreis"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Infektionsfälle", lang="de")
        == lemmatize("Infektionsfälle", lang="de", greedy=True)
        == "Infektionsfall"
    )
    assert (
        lemmatize("Corona-Einsatzstabes", lang="de", greedy=True)
        == "Corona-Einsatzstab"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Clearinghäusern", lang="de")
        == lemmatize("Clearinghäusern", lang="de", greedy=True)
        == "Clearinghaus"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Mittelstreckenjets", lang="de")
        == lemmatize("Mittelstreckenjets", lang="de", greedy=True)
        == "Mittelstreckenjet"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Länderministerien", lang="de")
        == lemmatize("Länderministerien", lang="de", greedy=True)
        == "Länderministerium"
    )
    assert (
        lemmatize("Gesundheitsschutzkontrollen", lang="de", greedy=True)
        == "Gesundheitsschutzkontrolle"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Nachkriegsjuristen", lang="de")
        == lemmatize("Nachkriegsjuristen", lang="de", greedy=True)
        == "Nachkriegsjurist"
    )
    assert (
        lemmatize("insulinproduzierende", lang="de", greedy=True)
        == "insulinproduzieren"
    )
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize("Urlaubsreisenden", lang="de") == lemmatize("Urlaubsreisenden", lang="de", greedy=True) == "Urlaubsreisende"
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Grünenvorsitzende", lang="de")
        == lemmatize("Grünenvorsitzende", lang="de", greedy=True)
        == "Grünenvorsitzende"
    )
    assert (
        lemmatize("Qualifikationsrunde", lang="de", greedy=True)
        == "Qualifikationsrunde"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("krisensichere", lang="de")
        == lemmatize("krisensichere", lang="de", greedy=True)
        == "krisensicher"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("ironischerweise", lang="de")
        == lemmatize("ironischerweise", lang="de", greedy=True)
        == "ironischerweise"
    )
    assert (
        lemmatize("Landespressedienstes", lang="de", greedy=True)
        == "Landespressedienst"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Lehrerverbänden", lang="de")
        == lemmatize("Lehrerverbänden", lang="de", greedy=True)
        == "Lehrerverband"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Terminvergaberunden", lang="de")
        == lemmatize("Terminvergaberunden", lang="de", greedy=True)
        == "Terminvergaberunde"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Gen-Sequenzierungen", lang="de")
        == lemmatize("Gen-Sequenzierungen", lang="de", greedy=True)
        == "Gen-Sequenzierung"
    )
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize("wiederverwendbaren", lang="de") == lemmatize("wiederverwendbaren", lang="de", greedy=True) == "wiederverwendbar"
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Spitzenposten", lang="de")
        == lemmatize("Spitzenposten", lang="de", greedy=True)
        == "Spitzenposten"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("I-Pace", lang="de")
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
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize("obamamäßigsten", lang="de") == lemmatize("obamamäßigsten", lang="de", greedy=True) == "obamamäßig"
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize("obamaartigere", lang="de") == lemmatize("obamaartigere", lang="de", greedy=True) == "obamaartig"
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("durchgestyltes", lang="de")
        == lemmatize("durchgestyltes", lang="de", greedy=True)
        == "durchgestylt"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("durchgeknallte", lang="de")
        == lemmatize("durchgeknallte", lang="de", greedy=True)
        == "durchgeknallt"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("herunterfährt", lang="de")
        == lemmatize("herunterfährt", lang="de", greedy=True)
        == "herunterfahren"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Atomdeals", lang="de")
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
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Lichtbild-Ausweis", lang="de")
        == lemmatize("Lichtbild-Ausweis", lang="de", greedy=True)
        == "Lichtbildausweis"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Kapuzenpullis", lang="de")
        == lemmatize("Kapuzenpullis", lang="de", greedy=True)
        == "Kapuzenpulli"
    )
    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
        ).lemmatize("Pharmagrößen", lang="de")
        == lemmatize("Pharmagrößen", lang="de", greedy=True)
        == "Pharmagröße"
    )

    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize("beständigsten", lang="de") == lemmatize("beständigsten", lang="de", greedy=True) == "beständig"
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize('zweitstärkster', lang='de') == lemmatize('zweitstärkster', lang='de', greedy=True) == 'zweitstärkste'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize('Abholservices', lang='de') == lemmatize('Abholservices', lang='de', greedy=True) == 'Abholservice'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize('Funktionärsebene', lang='de') == lemmatize('Funktionärsebene', lang='de', greedy=True) == 'Funktionärsebene'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize('strafbewehrte', lang='de') == lemmatize('strafbewehrte', lang='de', greedy=True) == 'strafbewehrt'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize('fälschungssicheren', lang='de') == lemmatize('fälschungssicheren', lang='de', greedy=True) == 'fälschungssicher'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize('Spargelstangen', lang='de') == lemmatize('Spargelstangen', lang='de', greedy=True) == 'Spargelstange'
    # assert Lemmatizer(lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())).lemmatize("Bandmitgliedern", lang="de") == lemmatize("Bandmitgliedern", lang="de", greedy=True) == "Bandmitglied"

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


def test_is_known() -> None:
    # logic
    with pytest.raises(TypeError):
        assert Lemmatizer().is_known(None, lang="en") is None  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        assert is_known(None, lang="en") is None  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        assert Lemmatizer().is_known("", lang="en") is None
    with pytest.raises(ValueError):
        assert is_known("", lang="en") is None

    assert (
        Lemmatizer().is_known("FanCY", lang="en")
        == is_known("FanCY", lang="en")
        == True
    )
    # known words
    assert (
        Lemmatizer().is_known("Fancy-String", lang="en")
        == is_known("Fancy-String", lang="en")
        == False
    )


def test_get_lemmas_in_text() -> None:
    # text lemmatization
    text = "Nous déciderons une fois arrivées. Voilà."
    assert (
        list(
            Lemmatizer(lemmatization_strategy=DefaultStrategy()).get_lemmas_in_text(
                text, lang="fr"
            )
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
            Lemmatizer(lemmatization_strategy=DefaultStrategy()).get_lemmas_in_text(
                text, lang="fr"
            )
        )
        == list(lemma_iterator(text, lang="fr", greedy=False))
        == text_lemmatizer(text, lang="fr", greedy=False)
    )
    text = "Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas."
    assert (
        list(
            Lemmatizer(lemmatization_strategy=DefaultStrategy()).get_lemmas_in_text(
                text, lang="es"
            )
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
                lemmatization_strategy=DefaultStrategy(GreedyDictionaryLookupStrategy())
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
