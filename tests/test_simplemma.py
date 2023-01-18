"""Tests for `simplemma` package."""

import logging
import os
import pytest
import tempfile


import simplemma
from simplemma import DictionaryCache, Lemmatizer


TEST_DIR = os.path.abspath(os.path.dirname(__file__))

logging.basicConfig(level=logging.DEBUG)


def test_readme():
    """Test function to verify readme examples."""
    lemmatizer = Lemmatizer()
    myword = "masks"
    assert lemmatizer.lemmatize(myword, lang="en") == "mask"
    mytokens = ["Hier", "sind", "Vaccines", "."]
    assert [lemmatizer.lemmatize(t, lang="de") for t in mytokens] == [
        "hier",
        "sein",
        "Vaccines",
        ".",
    ]
    # greediness
    assert lemmatizer.lemmatize("angekündigten", lang="de", greedy=False) == "angekündigt"
    assert lemmatizer.lemmatize("angekündigten", lang="de", greedy=True) == "ankündigen"
    # chaining
    assert [lemmatizer.lemmatize(t, lang=("de", "en")) for t in mytokens] == [
        "hier",
        "sein",
        "vaccine",
        ".",
    ]
    assert lemmatizer.lemmatize("spaghettis", lang="it") == "spaghettis"
    assert lemmatizer.lemmatize("spaghettini", lang="it") == "spaghettini"
    assert lemmatizer.lemmatize("spaghettis", lang=("it", "fr")) == "spaghetti"
    assert lemmatizer.lemmatize("spaghetti", lang=("it", "fr")) == "spaghetto"
    assert lemmatizer.lemmatize("spaghettis", lang=("it", "fr"), greedy=True) == "spaghetto"
    # tokenization and chaining
    assert simplemma.simple_tokenizer(
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
    ) == [
        "Lorem",
        "ipsum",
        "dolor",
        "sit",
        "amet",
        ",",
        "consectetur",
        "adipiscing",
        "elit",
        ",",
        "sed",
        "do",
        "eiusmod",
        "tempor",
        "incididunt",
        "ut",
        "labore",
        "et",
        "dolore",
        "magna",
        "aliqua",
        ".",
    ]
    assert lemmatizer.text_lemmatizer(
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
        lemmatizer.lemmatize("スパゲッティ", lang="pt", silent=False)


def test_logic():
    """Test if certain code parts correspond to the intended logic."""
    # dict generation
    testfile = os.path.join(TEST_DIR, "data/zz.txt")
    # simple generation, silent mode
    mydict = simplemma.dictionary_pickler._read_dict(testfile, "zz", silent=True)
    assert len(mydict) == 3
    mydict = simplemma.dictionary_pickler._load_dict(
        "zz", listpath=os.path.join(TEST_DIR, "data"), silent=True
    )
    assert len(mydict) == 3
    # log warning
    mydict = simplemma.dictionary_pickler._read_dict(testfile, "zz", silent=False)
    assert len(mydict) == 3
    # different length
    mydict = simplemma.dictionary_pickler._read_dict(testfile, "en", silent=True)
    assert len(mydict) == 5
    # different order
    mydict = simplemma.dictionary_pickler._read_dict(testfile, "es", silent=True)
    assert len(mydict) == 5
    assert mydict["closeones"] == "closeone"
    item = sorted(mydict.keys(), reverse=True)[0]
    assert item == "valid-word"

    # file I/O
    assert simplemma.dictionary_pickler._determine_path("lists", "de").endswith("de.txt")

    # dict pickling
    listpath = os.path.join(TEST_DIR, "data")
    os_handle, temp_outputfile = tempfile.mkstemp(suffix=".pkl", text=True)
    simplemma.dictionary_pickler._pickle_dict("zz", listpath, temp_outputfile)

    # missing languages or faulty language codes
    dictionaryCache = DictionaryCache()
    dictionaryCache.update_lang_data(("de", "abc", "en"))
    deDict = dictionaryCache.data[0].dict
    lemmatizer = Lemmatizer(dictionaryCache)
    with pytest.raises(TypeError):
        lemmatizer.lemmatize("test", lang=["test"])
    with pytest.raises(TypeError):
        dictionaryCache.update_lang_data(["id", "lv"])

    # searches
    with pytest.raises(TypeError):
        assert lemmatizer.lemmatize(None, lang="en") is None
    with pytest.raises(ValueError):
        assert lemmatizer.lemmatize("", lang="en") is None
    assert simplemma.simplemma._suffix_search("ccc",deDict) is None

    assert (
        simplemma.simplemma._return_lemma("Gender-Sternchens",deDict)
        == "Gendersternchen"
    )
    assert (
        simplemma.simplemma._return_lemma("an-gespieltes",deDict)
        == "anspielen"
    )

    assert (
        simplemma.simplemma._greedy_search(
            "getesteten",deDict, steps=0, distance=20
        )
        == "getestet"
    )
    assert (
        simplemma.simplemma._greedy_search(
            "getesteten",deDict, steps=1, distance=20
        )
        == "getestet"
    )
    assert (
        simplemma.simplemma._greedy_search(
            "getesteten",deDict, steps=2, distance=20
        )
        == "testen"
    )
    assert (
        simplemma.simplemma._greedy_search(
            "getesteten",deDict, steps=2, distance=2
        )
        == "getestet"
    )

    # prefixes
    mydata = simplemma.dictionaries._load_data(("de", "ru"))
    assert (
        simplemma.simplemma._prefix_search("zerlemmatisiertes", "de", mydata[0].dict)
        == "zerlemmatisiert"
    )
    assert (
        simplemma.simplemma._prefix_search("зафиксированные", "ru", mydata[1].dict)
        == "зафиксированный"
    )


def test_convenience():
    """Test convenience functions."""
    # logic
    lemmatizer = Lemmatizer()
    with pytest.raises(TypeError):
        assert lemmatizer.is_known(None, lang="en") is None
    with pytest.raises(ValueError):
        assert lemmatizer.is_known("", lang="en") is None
    assert lemmatizer.is_known("FanCY", lang="en") is True
    # known words
    assert lemmatizer.is_known("Fancy-String", lang="en") is False
    # text lemmatization
    text = "Nous déciderons une fois arrivées. Voilà."
    assert lemmatizer.text_lemmatizer(text, lang="fr", greedy=False) == [
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
        l for l in lemmatizer.lemma_iterator(text, lang="fr", greedy=False)
    ] == lemmatizer.text_lemmatizer(text, lang="fr", greedy=False)
    text = "Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas."
    assert (lemmatizer.text_lemmatizer(text, lang="es", greedy=False)) == [
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
    assert lemmatizer.text_lemmatizer(text, lang="es", greedy=True) == [
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
    dictionaryCache = DictionaryCache()
    dictionaryCache.update_lang_data(("en",))
    enDict = dictionaryCache.data[0].dict
    lemmatizer = Lemmatizer(dictionaryCache)
    assert simplemma.simplemma._simple_search("ignorant", enDict) == "ignorant"
    assert simplemma.simplemma._simple_search("Ignorant", enDict) == "ignorant"
    assert (
        simplemma.simplemma._dehyphen("magni-ficent", enDict, False) == "magnificent"
    )
    assert simplemma.simplemma._dehyphen("magni-ficents", enDict, False) is None
    # assert simplemma.simplemma._greedy_search('Ignorance-Tests', enDict) == 'Ignorance-Test'
    # don't lemmatize numbers
    assert simplemma.simplemma._return_lemma("01234", enDict) == "01234"
    # initial or not
    dictionaryCache.update_lang_data(("de",))
    deDict = dictionaryCache.data[0].dict
    assert (
        simplemma.simplemma._simple_search("Dritte", deDict, initial=True) == "dritt"
    )
    assert (
        simplemma.simplemma._simple_search("Dritte", deDict, initial=False)
        == "Dritter"
    )


def test_subwords():
    lemmatizer = Lemmatizer()
    """Test recognition and conversion of subword units."""
    assert lemmatizer.lemmatize("OBI", lang="de", greedy=True) == "OBI"
    assert lemmatizer.lemmatize("mRNA-Impfstoffe", lang="de", greedy=False) == "mRNA-Impfstoff"
    assert lemmatizer.lemmatize("mRNA-impfstoffe", lang="de", greedy=True) == "mRNA-Impfstoff"
    # greedy subword
    myword = "Impftermine"
    assert lemmatizer.lemmatize(myword, lang="de", greedy=False) == "Impftermine"
    assert lemmatizer.lemmatize(myword, lang="de", greedy=True) == "Impftermin"
    myword = "Impfbeginn"
    assert lemmatizer.lemmatize(myword, lang="de", greedy=False) == "Impfbeginn"
    assert lemmatizer.lemmatize(myword, lang="de", greedy=True) == "Impfbeginn"
    myword = "Hoffnungsmaschinen"
    assert lemmatizer.lemmatize(myword, lang="de", greedy=False) == "Hoffnungsmaschinen"
    assert lemmatizer.lemmatize(myword, lang="de", greedy=True) == "Hoffnungsmaschine"
    assert lemmatizer.lemmatize("börsennotierter", lang="de", greedy=True) == "börsennotiert"
    assert lemmatizer.lemmatize("journalistischer", lang="de", greedy=True) == "journalistisch"
    assert (
        lemmatizer.lemmatize("Delegiertenstimmen", lang="de", greedy=True) == "Delegiertenstimme"
    )
    assert lemmatizer.lemmatize("Koalitionskreisen", lang="de", greedy=True) == "Koalitionskreis"
    assert lemmatizer.lemmatize("Infektionsfälle", lang="de", greedy=True) == "Infektionsfall"
    assert (
        lemmatizer.lemmatize("Corona-Einsatzstabes", lang="de", greedy=True)
        == "Corona-Einsatzstab"
    )
    assert lemmatizer.lemmatize("Clearinghäusern", lang="de", greedy=True) == "Clearinghaus"
    assert (
        lemmatizer.lemmatize("Mittelstreckenjets", lang="de", greedy=True) == "Mittelstreckenjet"
    )
    assert lemmatizer.lemmatize("Länderministerien", lang="de", greedy=True) == "Länderministerium"
    assert (
        lemmatizer.lemmatize("Gesundheitsschutzkontrollen", lang="de", greedy=True)
        == "Gesundheitsschutzkontrolle"
    )
    assert lemmatizer.lemmatize("Nachkriegsjuristen", lang="de", greedy=True) == "Nachkriegsjurist"
    assert (
        lemmatizer.lemmatize("insulinproduzierende", lang="de", greedy=True)
        == "insulinproduzierend"
    )
    assert lemmatizer.lemmatize("Urlaubsreisenden", lang="de", greedy=True) == "Urlaubsreisende"
    assert lemmatizer.lemmatize("Grünenvorsitzende", lang="de", greedy=True) == "Grünenvorsitzende"
    assert (
        lemmatizer.lemmatize("Qualifikationsrunde", lang="de", greedy=True)
        == "Qualifikationsrunde"
    )
    assert lemmatizer.lemmatize("krisensichere", lang="de", greedy=True) == "krisensicher"
    assert lemmatizer.lemmatize("ironischerweise", lang="de", greedy=True) == "ironischerweise"
    assert (
        lemmatizer.lemmatize("Landespressedienstes", lang="de", greedy=True)
        == "Landespressedienst"
    )
    assert lemmatizer.lemmatize("Lehrerverbänden", lang="de", greedy=True) == "Lehrerverband"
    assert (
        lemmatizer.lemmatize("Terminvergaberunden", lang="de", greedy=True) == "Terminvergaberunde"
    )
    assert (
        lemmatizer.lemmatize("Gen-Sequenzierungen", lang="de", greedy=True) == "Gen-Sequenzierung"
    )
    assert lemmatizer.lemmatize("wiederverwendbaren", lang="de", greedy=True) == "wiederverwendbar"
    assert lemmatizer.lemmatize("Spitzenposten", lang="de", greedy=True) == "Spitzenposten"
    assert lemmatizer.lemmatize("I-Pace", lang="de", greedy=True) == "I-Pace"
    assert (
        lemmatizer.lemmatize("PCR-Bestätigungstests", lang="de", greedy=True)
        == "PCR-Bestätigungstest"
    )
    # assert (
    #    lemmatize("standortübergreifend", lang="de", greedy=True)
    #    == "standortübergreifend"
    # )
    assert lemmatizer.lemmatize("obamamäßigsten", lang="de", greedy=True) == "obamamäßig"
    assert lemmatizer.lemmatize("obamaartigere", lang="de", greedy=True) == "obamaartig"
    assert lemmatizer.lemmatize("durchgestyltes", lang="de", greedy=True) == "durchgestylt"
    assert lemmatizer.lemmatize("durchgeknallte", lang="de", greedy=True) == "durchgeknallt"
    assert lemmatizer.lemmatize("herunterfährt", lang="de", greedy=True) == "herunterfahren"
    assert lemmatizer.lemmatize("Atomdeals", lang="de", greedy=True) == "Atomdeal"
    assert (
        lemmatizer.lemmatize("Anspruchsberechtigten", lang="de", greedy=True)
        == "Anspruchsberechtigte"
    )
    assert (
        lemmatizer.lemmatize("Bürgerschaftsabgeordneter", lang="de", greedy=True)
        == "Bürgerschaftsabgeordnete"
    )
    assert lemmatizer.lemmatize("Lichtbild-Ausweis", lang="de", greedy=True) == "Lichtbildausweis"
    assert lemmatizer.lemmatize("Kapuzenpullis", lang="de", greedy=True) == "Kapuzenpulli"
    assert lemmatizer.lemmatize("Pharmagrößen", lang="de", greedy=True) == "Pharmagröße"

    # assert lemmatizer.lemmatize("beständigsten", lang="de", greedy=True) == "beständig"
    # assert lemmatizer.lemmatize('zweitstärkster', lang='de', greedy=True) == 'zweitstärkste'
    # assert lemmatizer.lemmatize('Abholservices', lang='de', greedy=True) == 'Abholservice'
    # assert lemmatizer.lemmatize('Funktionärsebene', lang='de', greedy=True) == 'Funktionärsebene'
    # assert lemmatizer.lemmatize('strafbewehrte', lang='de', greedy=True) == 'strafbewehrt'
    # assert lemmatizer.lemmatize('fälschungssicheren', lang='de', greedy=True) == 'fälschungssicher'
    # assert lemmatizer.lemmatize('Spargelstangen', lang='de', greedy=True) == 'Spargelstange'
    # assert lemmatizer.lemmatize("Bandmitgliedern", lang="de", greedy=True) == "Bandmitglied"

    # prefixes
    assert lemmatize("lemmatisiertes", lang="de") == "lemmatisiert"
    assert lemmatize("zerlemmatisiertes", lang="de") == "zerlemmatisiert"
    assert lemmatize("фиксированные", lang="ru") == "фиксированный"
    assert lemmatize("зафиксированные", lang="ru") == "зафиксированный"


def test_tokenizer():
    # tokenization and chaining
    text = "Sent1. Sent2\r\nSent3"
    assert simplemma.simple_tokenizer(text) == ["Sent1", ".", "Sent2", "Sent3"]
    assert simplemma.simple_tokenizer(text) == [
        m[0] for m in simplemma.simple_tokenizer(text, iterate=True)
    ]
    assert simplemma.simple_tokenizer(
        "200er-Inzidenz 1.000er-Inzidenz 5%-Hürde 5-%-Hürde FFP2-Masken St.-Martini-Gemeinde, Lebens-, Liebes- und Arbeitsbedingungen"
    ) == [
        "200er-Inzidenz",
        "1.000er-Inzidenz",
        "5%-Hürde",
        "5-%-Hürde",
        "FFP2-Masken",
        "St.-Martini-Gemeinde",
        ",",
        "Lebens-",
        ",",
        "Liebes-",
        "und",
        "Arbeitsbedingungen",
    ]
    assert simplemma.simple_tokenizer(
        "360-Grad-Panorama @sebastiankurz 2,5-Zimmer-Wohnung 1,2-butylketoaldehyde"
    ) == [
        "360-Grad-Panorama",
        "@sebastiankurz",
        "2,5-Zimmer-Wohnung",
        "1,2-butylketoaldehyde",
    ]
    assert simplemma.simple_tokenizer(
        "Covid-19, Covid19, Covid-19-Pandemie https://example.org/covid-test"
    ) == [
        "Covid-19",
        ",",
        "Covid19",
        ",",
        "Covid-19-Pandemie",
        "https://example.org/covid-test",
    ]
    assert simplemma.simple_tokenizer(
        "Test 4:1-Auswärtssieg 2,5€ €3.5 $3.5 §52, for $5, 3/5 -1.4"
    ) == [
        "Test",
        "4:1-Auswärtssieg",
        "2,5€",
        "€3.5",
        "$3.5",
        "§52",
        ",",
        "for",
        "$5",
        ",",
        "3/5",
        "-1.4",
    ]
    # problem here: WDR5-„Morgenecho“
    assert simplemma.simple_tokenizer("WDR5-„Morgenecho“") == [
        "WDR5-",
        "„",
        "Morgenecho",
        "“",
    ]
