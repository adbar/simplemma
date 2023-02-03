"""Tests for `simplemma` package."""

import logging
import pytest
from typing import Optional, Tuple, Union

import simplemma
from simplemma import lemmatize, DictionaryFactory

logging.basicConfig(level=logging.DEBUG)


def test_custom_dictionary_factory() -> None:
    class CustomDictionaryFactory:
        def get_dictionaries(
            self, langs: Optional[Union[str, Tuple[str, ...]]]
        ) -> None:
            return {"en": {"testing": "the test works!!"}}  # type: ignore

    assert (
        lemmatize("testing", lang="en", dictionary_factory=CustomDictionaryFactory())
        == "the test works!!"
    )


def test_readme() -> None:
    """Test function to verify readme examples."""
    myword = "masks"
    assert lemmatize(myword, lang="en") == "mask"
    mytokens = ["Hier", "sind", "Vaccines", "."]
    assert [lemmatize(t, lang="de") for t in mytokens] == [
        "hier",
        "sein",
        "Vaccines",
        ".",
    ]
    # greediness
    assert lemmatize("angekündigten", lang="de", greedy=False) == "angekündigt"
    assert lemmatize("angekündigten", lang="de", greedy=True) == "ankündigen"
    # chaining
    assert [lemmatize(t, lang=("de", "en")) for t in mytokens] == [
        "hier",
        "sein",
        "vaccine",
        ".",
    ]
    assert lemmatize("spaghettis", lang="it") == "spaghettis"
    assert lemmatize("spaghettini", lang="it") == "spaghettini"
    assert lemmatize("spaghettis", lang=("it", "fr")) == "spaghetti"
    assert lemmatize("spaghetti", lang=("it", "fr")) == "spaghetto"
    assert lemmatize("spaghettis", lang=("it", "fr"), greedy=True) == "spaghetto"
    assert simplemma.text_lemmatizer(
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
    with pytest.raises(ValueError):
        lemmatize("スパゲッティ", lang="pt", silent=False)


def test_logic() -> None:
    """Test if certain code parts correspond to the intended logic."""
    # missing languages or faulty language codes
    dictionary_factory = DictionaryFactory()
    dictionaries = dictionary_factory.get_dictionaries(("de", "abc", "en"))
    with pytest.raises(TypeError):
        lemmatize("test", lang=["test"])  # type: ignore[arg-type]

    deDict = dictionaries["de"]

    # searches
    with pytest.raises(TypeError):
        assert lemmatize(None, lang="en") is None
    with pytest.raises(ValueError):
        assert lemmatize("", lang="en") is None
    assert simplemma.lemmatizer._suffix_search("ccc", deDict) is None

    assert (
        simplemma.lemmatizer._return_lemma("Gender-Sternchens", deDict)
        == "Gendersternchen"
    )
    assert simplemma.lemmatizer._return_lemma("an-gespieltes", deDict) == "anspielen"

    assert (
        simplemma.lemmatizer._greedy_search("getesteten", deDict, steps=0, distance=20)
        == "getestet"
    )
    assert (
        simplemma.lemmatizer._greedy_search("getesteten", deDict, steps=1, distance=20)
        == "getestet"
    )
    assert (
        simplemma.lemmatizer._greedy_search("getesteten", deDict, steps=2, distance=20)
        == "testen"
    )
    assert (
        simplemma.lemmatizer._greedy_search("getesteten", deDict, steps=2, distance=2)
        == "getestet"
    )

    # prefixes
    dictionaries = dictionary_factory.get_dictionaries(("de", "ru"))
    deDict = dictionaries["de"]
    assert (
        simplemma.lemmatizer._prefix_search("zerlemmatisiertes", "de", deDict)
        == "zerlemmatisiert"
    )
    ruDict = dictionaries["ru"]
    assert (
        simplemma.lemmatizer._prefix_search("зафиксированные", "ru", ruDict)
        == "зафиксированный"
    )


def test_convenience() -> None:
    """Test convenience functions."""
    # logic
    with pytest.raises(TypeError):
        assert simplemma.lemmatizer.is_known(None, lang="en") is None  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        assert simplemma.lemmatizer.is_known("", lang="en") is None
    assert simplemma.is_known("FanCY", lang="en") is True
    # known words
    assert simplemma.is_known("Fancy-String", lang="en") is False
    # text lemmatization
    text = "Nous déciderons une fois arrivées. Voilà."
    assert simplemma.text_lemmatizer(text, lang="fr", greedy=False) == [
        "nous",
        "décider",
        "un",
        "fois",
        "arrivée",
        ".",
        "voilà",
        ".",
    ]
    text = "Nous déciderons une fois arrivées. Voilà."
    assert [
        lemma
        for lemma in simplemma.lemmatizer.lemma_iterator(text, lang="fr", greedy=False)
    ] == simplemma.text_lemmatizer(text, lang="fr", greedy=False)
    text = "Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas."
    assert (simplemma.text_lemmatizer(text, lang="es", greedy=False)) == [
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
    assert simplemma.text_lemmatizer(text, lang="es", greedy=True) == [
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


def test_search() -> None:
    """Test simple and greedy dict search."""
    dictionary_factory = DictionaryFactory()
    dictionaries = dictionary_factory.get_dictionaries(("en",))
    enDict = dictionaries["en"]
    assert simplemma.lemmatizer._simple_search("ignorant", enDict) == "ignorant"
    assert simplemma.lemmatizer._simple_search("Ignorant", enDict) == "ignorant"
    assert (
        simplemma.lemmatizer._dehyphen("magni-ficent", enDict, False) == "magnificent"
    )
    assert simplemma.lemmatizer._dehyphen("magni-ficents", enDict, False) is None
    # assert simplemma.simplemma._greedy_search('Ignorance-Tests', enDict) == 'Ignorance-Test'
    # don't lemmatize numbers
    assert simplemma.lemmatizer._return_lemma("01234", enDict) == "01234"
    # initial or not
    dictionaries = dictionary_factory.get_dictionaries(("de",))
    deDict = dictionaries["de"]
    assert (
        simplemma.lemmatizer._simple_search("Dritte", deDict, initial=True) == "dritt"
    )
    assert (
        simplemma.lemmatizer._simple_search("Dritte", deDict, initial=False)
        == "Dritter"
    )


def test_subwords() -> None:
    """Test recognition and conversion of subword units."""
    assert lemmatize("OBI", lang="de", greedy=True) == "OBI"
    assert lemmatize("mRNA-Impfstoffe", lang="de", greedy=False) == "mRNA-Impfstoff"
    assert lemmatize("mRNA-impfstoffe", lang="de", greedy=True) == "mRNA-Impfstoff"
    # greedy subword
    myword = "Impftermine"
    assert lemmatize(myword, lang="de", greedy=False) == "Impftermine"
    assert lemmatize(myword, lang="de", greedy=True) == "Impftermin"
    myword = "Impfbeginn"
    assert lemmatize(myword, lang="de", greedy=False) == "Impfbeginn"
    assert lemmatize(myword, lang="de", greedy=True) == "Impfbeginn"
    myword = "Hoffnungsmaschinen"
    assert lemmatize(myword, lang="de", greedy=False) == "Hoffnungsmaschinen"
    assert lemmatize(myword, lang="de", greedy=True) == "Hoffnungsmaschine"
    assert lemmatize("börsennotierter", lang="de", greedy=True) == "börsennotiert"
    assert lemmatize("journalistischer", lang="de", greedy=True) == "journalistisch"
    assert (
        lemmatize("Delegiertenstimmen", lang="de", greedy=True) == "Delegiertenstimme"
    )
    assert lemmatize("Koalitionskreisen", lang="de", greedy=True) == "Koalitionskreis"
    assert lemmatize("Infektionsfälle", lang="de", greedy=True) == "Infektionsfall"
    assert (
        lemmatize("Corona-Einsatzstabes", lang="de", greedy=True)
        == "Corona-Einsatzstab"
    )
    assert lemmatize("Clearinghäusern", lang="de", greedy=True) == "Clearinghaus"
    assert (
        lemmatize("Mittelstreckenjets", lang="de", greedy=True) == "Mittelstreckenjet"
    )
    assert lemmatize("Länderministerien", lang="de", greedy=True) == "Länderministerium"
    assert (
        lemmatize("Gesundheitsschutzkontrollen", lang="de", greedy=True)
        == "Gesundheitsschutzkontrolle"
    )
    assert lemmatize("Nachkriegsjuristen", lang="de", greedy=True) == "Nachkriegsjurist"
    assert (
        lemmatize("insulinproduzierende", lang="de", greedy=True)
        == "insulinproduzierend"
    )
    assert lemmatize("Urlaubsreisenden", lang="de", greedy=True) == "Urlaubsreisende"
    assert lemmatize("Grünenvorsitzende", lang="de", greedy=True) == "Grünenvorsitzende"
    assert (
        lemmatize("Qualifikationsrunde", lang="de", greedy=True)
        == "Qualifikationsrunde"
    )
    assert lemmatize("krisensichere", lang="de", greedy=True) == "krisensicher"
    assert lemmatize("ironischerweise", lang="de", greedy=True) == "ironischerweise"
    assert (
        lemmatize("Landespressedienstes", lang="de", greedy=True)
        == "Landespressedienst"
    )
    assert lemmatize("Lehrerverbänden", lang="de", greedy=True) == "Lehrerverband"
    assert (
        lemmatize("Terminvergaberunden", lang="de", greedy=True) == "Terminvergaberunde"
    )
    assert (
        lemmatize("Gen-Sequenzierungen", lang="de", greedy=True) == "Gen-Sequenzierung"
    )
    assert lemmatize("wiederverwendbaren", lang="de", greedy=True) == "wiederverwendbar"
    assert lemmatize("Spitzenposten", lang="de", greedy=True) == "Spitzenposten"
    assert lemmatize("I-Pace", lang="de", greedy=True) == "I-Pace"
    assert (
        lemmatize("PCR-Bestätigungstests", lang="de", greedy=True)
        == "PCR-Bestätigungstest"
    )
    # assert (
    #    lemmatize("standortübergreifend", lang="de", greedy=True)
    #    == "standortübergreifend"
    # )
    assert lemmatize("obamamäßigsten", lang="de", greedy=True) == "obamamäßig"
    assert lemmatize("obamaartigere", lang="de", greedy=True) == "obamaartig"
    assert lemmatize("durchgestyltes", lang="de", greedy=True) == "durchgestylt"
    assert lemmatize("durchgeknallte", lang="de", greedy=True) == "durchgeknallt"
    assert lemmatize("herunterfährt", lang="de", greedy=True) == "herunterfahren"
    assert lemmatize("Atomdeals", lang="de", greedy=True) == "Atomdeal"
    assert (
        lemmatize("Anspruchsberechtigten", lang="de", greedy=True)
        == "Anspruchsberechtigte"
    )
    assert (
        lemmatize("Bürgerschaftsabgeordneter", lang="de", greedy=True)
        == "Bürgerschaftsabgeordnete"
    )
    assert lemmatize("Lichtbild-Ausweis", lang="de", greedy=True) == "Lichtbildausweis"
    assert lemmatize("Kapuzenpullis", lang="de", greedy=True) == "Kapuzenpulli"
    assert lemmatize("Pharmagrößen", lang="de", greedy=True) == "Pharmagröße"

    # assert lemmatize("beständigsten", lang="de", greedy=True) == "beständig"
    # assert lemmatize('zweitstärkster', lang='de', greedy=True) == 'zweitstärkste'
    # assert lemmatize('Abholservices', lang='de', greedy=True) == 'Abholservice'
    # assert lemmatize('Funktionärsebene', lang='de', greedy=True) == 'Funktionärsebene'
    # assert lemmatize('strafbewehrte', lang='de', greedy=True) == 'strafbewehrt'
    # assert lemmatize('fälschungssicheren', lang='de', greedy=True) == 'fälschungssicher'
    # assert lemmatize('Spargelstangen', lang='de', greedy=True) == 'Spargelstange'
    # assert lemmatize("Bandmitgliedern", lang="de", greedy=True) == "Bandmitglied"

    # prefixes
    assert lemmatize("lemmatisiertes", lang="de") == "lemmatisiert"
    assert lemmatize("zerlemmatisiertes", lang="de") == "zerlemmatisiert"
    assert lemmatize("фиксированные", lang="ru") == "фиксированный"
    assert lemmatize("зафиксированные", lang="ru") == "зафиксированный"
