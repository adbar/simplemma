"""Tests for `Lemmatizer` module."""

import logging
import pytest

from simplemma import DictionaryFactory, Lemmatizer


logging.basicConfig(level=logging.DEBUG)


def test_readme():
    """Test function to verify readme examples."""
    lemmatizer = Lemmatizer()
    myword = "masks"
    assert lemmatizer.lemmatize_token(myword, lang="en") == "mask"
    mytokens = ["Hier", "sind", "Vaccines", "."]
    assert [lemmatizer.lemmatize_token(t, lang="de") for t in mytokens] == [
        "hier",
        "sein",
        "Vaccines",
        ".",
    ]
    # greediness
    assert (
        lemmatizer.lemmatize_token("angekündigten", lang="de", greedy=False)
        == "angekündigt"
    )
    assert (
        lemmatizer.lemmatize_token("angekündigten", lang="de", greedy=True)
        == "ankündigen"
    )
    # chaining
    assert [lemmatizer.lemmatize_token(t, lang=("de", "en")) for t in mytokens] == [
        "hier",
        "sein",
        "vaccine",
        ".",
    ]
    assert lemmatizer.lemmatize_token("spaghettis", lang="it") == "spaghettis"
    assert lemmatizer.lemmatize_token("spaghettini", lang="it") == "spaghettini"
    assert lemmatizer.lemmatize_token("spaghettis", lang=("it", "fr")) == "spaghetti"
    assert lemmatizer.lemmatize_token("spaghetti", lang=("it", "fr")) == "spaghetto"
    assert (
        lemmatizer.lemmatize_token("spaghettis", lang=("it", "fr"), greedy=True)
        == "spaghetto"
    )
    # tokenization and chaining
    assert lemmatizer.lemmatize_text(
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
        lemmatizer.lemmatize_token("スパゲッティ", lang="pt", silent=False)


def test_logic():
    """Test if certain code parts correspond to the intended logic."""
    # missing languages or faulty language codes
    dictionaryFactory = DictionaryFactory()
    dictionaries = dictionaryFactory.get_dictionaries(("de", "abc", "en"))
    deDict = dictionaries["de"]
    lemmatizer = Lemmatizer(dictionaryFactory)
    with pytest.raises(TypeError):
        lemmatizer.lemmatize_token("test", lang=["test"])
    with pytest.raises(TypeError):
        dictionaryFactory.get_dictionaries(["id", "lv"])

    # searches
    with pytest.raises(TypeError):
        assert lemmatizer.lemmatize_token(None, lang="en") is None
    with pytest.raises(ValueError):
        assert lemmatizer.lemmatize_token("", lang="en") is None
    assert lemmatizer._suffix_search("ccc", deDict) is None

    assert lemmatizer._return_lemma("Gender-Sternchens", deDict) == "Gendersternchen"
    assert lemmatizer._return_lemma("an-gespieltes", deDict) == "anspielen"

    assert (
        lemmatizer._greedy_search("getesteten", deDict, steps=0, distance=20)
        == "getestet"
    )
    assert (
        lemmatizer._greedy_search("getesteten", deDict, steps=1, distance=20)
        == "getestet"
    )
    assert (
        lemmatizer._greedy_search("getesteten", deDict, steps=2, distance=20)
        == "testen"
    )
    assert (
        lemmatizer._greedy_search("getesteten", deDict, steps=2, distance=2)
        == "getestet"
    )

    # prefixes
    dictionaries = dictionaryFactory.get_dictionaries(("de", "ru"))
    deDict = dictionaries["de"]
    ruDict = dictionaries["ru"]
    assert (
        lemmatizer._prefix_search("zerlemmatisiertes", "de", deDict)
        == "zerlemmatisiert"
    )
    assert (
        lemmatizer._prefix_search("зафиксированные", "ru", ruDict) == "зафиксированный"
    )


def test_convenience():
    """Test convenience functions."""
    # logic
    lemmatizer = Lemmatizer()
    with pytest.raises(TypeError):
        assert lemmatizer.is_token_known(None, lang="en") is None
    with pytest.raises(ValueError):
        assert lemmatizer.is_token_known("", lang="en") is None
    assert lemmatizer.is_token_known("FanCY", lang="en") is True
    # known words
    assert lemmatizer.is_token_known("Fancy-String", lang="en") is False
    # text lemmatization
    text = "Nous déciderons une fois arrivées. Voilà."
    assert lemmatizer.lemmatize_text(text, lang="fr", greedy=False) == [
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
        l for l in lemmatizer.lemmatize_text_iterator(text, lang="fr", greedy=False)
    ] == lemmatizer.lemmatize_text(text, lang="fr", greedy=False)
    text = "Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas."
    assert (lemmatizer.lemmatize_text(text, lang="es", greedy=False)) == [
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
    assert lemmatizer.lemmatize_text(text, lang="es", greedy=True) == [
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


def test_search():
    """Test simple and greedy dict search."""
    dictionaryFactory = DictionaryFactory()
    dictionaries = dictionaryFactory.get_dictionaries(("en",))
    enDict = dictionaries["en"]
    lemmatizer = Lemmatizer(dictionaryFactory)
    assert lemmatizer._simple_search("ignorant", enDict) == "ignorant"
    assert lemmatizer._simple_search("Ignorant", enDict) == "ignorant"
    assert lemmatizer._dehyphen("magni-ficent", enDict, False) == "magnificent"
    assert lemmatizer._dehyphen("magni-ficents", enDict, False) is None
    # assert lemmatizer._greedy_search('Ignorance-Tests', enDict) == 'Ignorance-Test'
    # don't lemmatize numbers
    assert lemmatizer._return_lemma("01234", enDict) == "01234"
    # initial or not
    dictionaries = dictionaryFactory.get_dictionaries(("de",))
    deDict = dictionaries["de"]
    assert lemmatizer._simple_search("Dritte", deDict, initial=True) == "dritt"
    assert lemmatizer._simple_search("Dritte", deDict, initial=False) == "Dritter"


def test_subwords():
    lemmatizer = Lemmatizer()
    """Test recognition and conversion of subword units."""
    assert lemmatizer.lemmatize_token("OBI", lang="de", greedy=True) == "OBI"
    assert (
        lemmatizer.lemmatize_token("mRNA-Impfstoffe", lang="de", greedy=False)
        == "mRNA-Impfstoff"
    )
    assert (
        lemmatizer.lemmatize_token("mRNA-impfstoffe", lang="de", greedy=True)
        == "mRNA-Impfstoff"
    )
    # greedy subword
    myword = "Impftermine"
    assert lemmatizer.lemmatize_token(myword, lang="de", greedy=False) == "Impftermine"
    assert lemmatizer.lemmatize_token(myword, lang="de", greedy=True) == "Impftermin"
    myword = "Impfbeginn"
    assert lemmatizer.lemmatize_token(myword, lang="de", greedy=False) == "Impfbeginn"
    assert lemmatizer.lemmatize_token(myword, lang="de", greedy=True) == "Impfbeginn"
    myword = "Hoffnungsmaschinen"
    assert (
        lemmatizer.lemmatize_token(myword, lang="de", greedy=False)
        == "Hoffnungsmaschinen"
    )
    assert (
        lemmatizer.lemmatize_token(myword, lang="de", greedy=True)
        == "Hoffnungsmaschine"
    )
    assert (
        lemmatizer.lemmatize_token("börsennotierter", lang="de", greedy=True)
        == "börsennotiert"
    )
    assert (
        lemmatizer.lemmatize_token("journalistischer", lang="de", greedy=True)
        == "journalistisch"
    )
    assert (
        lemmatizer.lemmatize_token("Delegiertenstimmen", lang="de", greedy=True)
        == "Delegiertenstimme"
    )
    assert (
        lemmatizer.lemmatize_token("Koalitionskreisen", lang="de", greedy=True)
        == "Koalitionskreis"
    )
    assert (
        lemmatizer.lemmatize_token("Infektionsfälle", lang="de", greedy=True)
        == "Infektionsfall"
    )
    assert (
        lemmatizer.lemmatize_token("Corona-Einsatzstabes", lang="de", greedy=True)
        == "Corona-Einsatzstab"
    )
    assert (
        lemmatizer.lemmatize_token("Clearinghäusern", lang="de", greedy=True)
        == "Clearinghaus"
    )
    assert (
        lemmatizer.lemmatize_token("Mittelstreckenjets", lang="de", greedy=True)
        == "Mittelstreckenjet"
    )
    assert (
        lemmatizer.lemmatize_token("Länderministerien", lang="de", greedy=True)
        == "Länderministerium"
    )
    assert (
        lemmatizer.lemmatize_token(
            "Gesundheitsschutzkontrollen", lang="de", greedy=True
        )
        == "Gesundheitsschutzkontrolle"
    )
    assert (
        lemmatizer.lemmatize_token("Nachkriegsjuristen", lang="de", greedy=True)
        == "Nachkriegsjurist"
    )
    assert (
        lemmatizer.lemmatize_token("insulinproduzierende", lang="de", greedy=True)
        == "insulinproduzierend"
    )
    assert (
        lemmatizer.lemmatize_token("Urlaubsreisenden", lang="de", greedy=True)
        == "Urlaubsreisende"
    )
    assert (
        lemmatizer.lemmatize_token("Grünenvorsitzende", lang="de", greedy=True)
        == "Grünenvorsitzende"
    )
    assert (
        lemmatizer.lemmatize_token("Qualifikationsrunde", lang="de", greedy=True)
        == "Qualifikationsrunde"
    )
    assert (
        lemmatizer.lemmatize_token("krisensichere", lang="de", greedy=True)
        == "krisensicher"
    )
    assert (
        lemmatizer.lemmatize_token("ironischerweise", lang="de", greedy=True)
        == "ironischerweise"
    )
    assert (
        lemmatizer.lemmatize_token("Landespressedienstes", lang="de", greedy=True)
        == "Landespressedienst"
    )
    assert (
        lemmatizer.lemmatize_token("Lehrerverbänden", lang="de", greedy=True)
        == "Lehrerverband"
    )
    assert (
        lemmatizer.lemmatize_token("Terminvergaberunden", lang="de", greedy=True)
        == "Terminvergaberunde"
    )
    assert (
        lemmatizer.lemmatize_token("Gen-Sequenzierungen", lang="de", greedy=True)
        == "Gen-Sequenzierung"
    )
    assert (
        lemmatizer.lemmatize_token("wiederverwendbaren", lang="de", greedy=True)
        == "wiederverwendbar"
    )
    assert (
        lemmatizer.lemmatize_token("Spitzenposten", lang="de", greedy=True)
        == "Spitzenposten"
    )
    assert lemmatizer.lemmatize_token("I-Pace", lang="de", greedy=True) == "I-Pace"
    assert (
        lemmatizer.lemmatize_token("PCR-Bestätigungstests", lang="de", greedy=True)
        == "PCR-Bestätigungstest"
    )
    # assert (
    #    lemmatizer.lemmatize_token("standortübergreifend", lang="de", greedy=True)
    #    == "standortübergreifend"
    # )
    assert (
        lemmatizer.lemmatize_token("obamamäßigsten", lang="de", greedy=True)
        == "obamamäßig"
    )
    assert (
        lemmatizer.lemmatize_token("obamaartigere", lang="de", greedy=True)
        == "obamaartig"
    )
    assert (
        lemmatizer.lemmatize_token("durchgestyltes", lang="de", greedy=True)
        == "durchgestylt"
    )
    assert (
        lemmatizer.lemmatize_token("durchgeknallte", lang="de", greedy=True)
        == "durchgeknallt"
    )
    assert (
        lemmatizer.lemmatize_token("herunterfährt", lang="de", greedy=True)
        == "herunterfahren"
    )
    assert lemmatizer.lemmatize_token("Atomdeals", lang="de", greedy=True) == "Atomdeal"
    assert (
        lemmatizer.lemmatize_token("Anspruchsberechtigten", lang="de", greedy=True)
        == "Anspruchsberechtigte"
    )
    assert (
        lemmatizer.lemmatize_token("Bürgerschaftsabgeordneter", lang="de", greedy=True)
        == "Bürgerschaftsabgeordnete"
    )
    assert (
        lemmatizer.lemmatize_token("Lichtbild-Ausweis", lang="de", greedy=True)
        == "Lichtbildausweis"
    )
    assert (
        lemmatizer.lemmatize_token("Kapuzenpullis", lang="de", greedy=True)
        == "Kapuzenpulli"
    )
    assert (
        lemmatizer.lemmatize_token("Pharmagrößen", lang="de", greedy=True)
        == "Pharmagröße"
    )

    # assert lemmatizer.lemmatize_token("beständigsten", lang="de", greedy=True) == "beständig"
    # assert lemmatizer.lemmatize_token('zweitstärkster', lang='de', greedy=True) == 'zweitstärkste'
    # assert lemmatizer.lemmatize_token('Abholservices', lang='de', greedy=True) == 'Abholservice'
    # assert lemmatizer.lemmatize_token('Funktionärsebene', lang='de', greedy=True) == 'Funktionärsebene'
    # assert lemmatizer.lemmatize_token('strafbewehrte', lang='de', greedy=True) == 'strafbewehrt'
    # assert lemmatizer.lemmatize_token('fälschungssicheren', lang='de', greedy=True) == 'fälschungssicher'
    # assert lemmatizer.lemmatize_token('Spargelstangen', lang='de', greedy=True) == 'Spargelstange'
    # assert lemmatizer.lemmatize_token("Bandmitgliedern", lang="de", greedy=True) == "Bandmitglied"

    # prefixes
    assert lemmatizer.lemmatize_token("lemmatisiertes", lang="de") == "lemmatisiert"
    assert (
        lemmatizer.lemmatize_token("zerlemmatisiertes", lang="de") == "zerlemmatisiert"
    )
    assert lemmatizer.lemmatize_token("фиксированные", lang="ru") == "фиксированный"
    assert lemmatizer.lemmatize_token("зафиксированные", lang="ru") == "зафиксированный"
