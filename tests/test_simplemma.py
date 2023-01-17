"""Tests for `simplemma` package."""

import logging
import os
import pytest
import tempfile


import simplemma
from simplemma import lemmatize, lemma_iterator, simple_tokenizer, text_lemmatizer


TEST_DIR = os.path.abspath(os.path.dirname(__file__))

logging.basicConfig(level=logging.DEBUG)


def test_readme():
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


def test_logic():
    """Test if certain code parts correspond to the intended logic."""
    # dict generation
    testfile = os.path.join(TEST_DIR, "data/zz.txt")
    # simple generation, silent mode
    mydict = simplemma.simplemma._read_dict(testfile, "zz", silent=True)
    assert len(mydict) == 3
    mydict = simplemma.simplemma._load_dict(
        "zz", listpath=os.path.join(TEST_DIR, "data"), silent=True
    )
    assert len(mydict) == 3
    # log warning
    mydict = simplemma.simplemma._read_dict(testfile, "zz", silent=False)
    assert len(mydict) == 3
    # different length
    mydict = simplemma.simplemma._read_dict(testfile, "en", silent=True)
    assert len(mydict) == 5
    # different order
    mydict = simplemma.simplemma._read_dict(testfile, "es", silent=True)
    assert len(mydict) == 5
    assert mydict["closeones"] == "closeone"
    item = sorted(mydict.keys(), reverse=True)[0]
    assert item == "valid-word"

    # file I/O
    assert simplemma.simplemma._determine_path("lists", "de").endswith("de.txt")

    # dict pickling
    listpath = os.path.join(TEST_DIR, "data")
    os_handle, temp_outputfile = tempfile.mkstemp(suffix=".pkl", text=True)
    simplemma.simplemma._pickle_dict("zz", listpath, temp_outputfile)

    # missing languages or faulty language codes
    mydata = simplemma.simplemma._load_data(("de", "abc", "en"))
    with pytest.raises(TypeError):
        lemmatize("test", lang=["test"])
    with pytest.raises(TypeError):
        simplemma.simplemma._update_lang_data(["id", "lv"])

    # searches
    with pytest.raises(TypeError):
        assert lemmatize(None, lang="en") is None
    with pytest.raises(ValueError):
        assert lemmatize("", lang="en") is None
    assert simplemma.simplemma._suffix_search("ccc", mydata[0].dict) is None

    assert (
        simplemma.simplemma._return_lemma("Gender-Sternchens", mydata[0].dict)
        == "Gendersternchen"
    )
    assert (
        simplemma.simplemma._return_lemma("an-gespieltes", mydata[0].dict)
        == "anspielen"
    )

    assert (
        simplemma.simplemma._greedy_search(
            "getesteten", mydata[0].dict, steps=0, distance=20
        )
        == "getestet"
    )
    assert (
        simplemma.simplemma._greedy_search(
            "getesteten", mydata[0].dict, steps=1, distance=20
        )
        == "getestet"
    )
    assert (
        simplemma.simplemma._greedy_search(
            "getesteten", mydata[0].dict, steps=2, distance=20
        )
        == "testen"
    )
    assert (
        simplemma.simplemma._greedy_search(
            "getesteten", mydata[0].dict, steps=2, distance=2
        )
        == "getestet"
    )

    # prefixes
    mydata = simplemma.simplemma._load_data(("de", "ru"))
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
    with pytest.raises(TypeError):
        assert simplemma.simplemma.is_known(None, lang="en") is None
    with pytest.raises(ValueError):
        assert simplemma.simplemma.is_known("", lang="en") is None
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
        l for l in simplemma.simplemma.lemma_iterator(text, lang="fr", greedy=False)
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


def test_search():
    """Test simple and greedy dict search."""
    data = simplemma.simplemma._load_data(("en",))[0]
    assert simplemma.simplemma._simple_search("ignorant", data.dict) == "ignorant"
    assert simplemma.simplemma._simple_search("Ignorant", data.dict) == "ignorant"
    assert (
        simplemma.simplemma._dehyphen("magni-ficent", data.dict, False) == "magnificent"
    )
    assert simplemma.simplemma._dehyphen("magni-ficents", data.dict, False) is None
    # assert simplemma.simplemma._greedy_search('Ignorance-Tests', datadict) == 'Ignorance-Test'
    # don't lemmatize numbers
    assert simplemma.simplemma._return_lemma("01234", data.dict) == "01234"
    # initial or not
    data = simplemma.simplemma._load_data(("de",))[0]
    assert (
        simplemma.simplemma._simple_search("Dritte", data.dict, initial=True) == "dritt"
    )
    assert (
        simplemma.simplemma._simple_search("Dritte", data.dict, initial=False)
        == "Dritter"
    )


def test_subwords():
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
