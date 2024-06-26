"""Tests for `simplemma` package."""

from typing import Mapping

import pytest

from simplemma import Lemmatizer, is_known, lemma_iterator, lemmatize, text_lemmatizer
from simplemma.strategies import (
    DefaultStrategy,
    DictionaryFactory,
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
    assert Lemmatizer().lemmatize("スパゲッティ", lang="pt") == lemmatize(
        "スパゲッティ", lang="pt"
    )
    assert lemmatize("スパゲッティ", lang="pt") == "スパゲッティ"

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


def test_is_known() -> None:
    with pytest.raises(TypeError):
        assert is_known(None, lang="en") is None  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        assert is_known("", lang="en") is None

    assert is_known("FanCY", lang="en") == True
    assert is_known("Fancy-String", lang="en") == False

    assert is_known("espejos", lang=("es", "de")) == True
    assert is_known("espejos", lang=("de", "es")) == True


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
