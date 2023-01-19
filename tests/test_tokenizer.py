from simplemma import Tokenizer


def test_tokenizer():
    # tokenization and chaining
    text = "Sent1. Sent2\r\nSent3"
    tokenizer = Tokenizer()
    assert tokenizer.simple_tokenizer(text) == ["Sent1", ".", "Sent2", "Sent3"]
    assert tokenizer.simple_tokenizer(text) == [
        m[0] for m in tokenizer.simple_tokenizer(text, iterate=True)
    ]

    assert tokenizer.simple_tokenizer(
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

    assert tokenizer.simple_tokenizer(
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
    assert tokenizer.simple_tokenizer(
        "360-Grad-Panorama @sebastiankurz 2,5-Zimmer-Wohnung 1,2-butylketoaldehyde"
    ) == [
        "360-Grad-Panorama",
        "@sebastiankurz",
        "2,5-Zimmer-Wohnung",
        "1,2-butylketoaldehyde",
    ]

    assert tokenizer.simple_tokenizer(
        "Covid-19, Covid19, Covid-19-Pandemie https://example.org/covid-test"
    ) == [
        "Covid-19",
        ",",
        "Covid19",
        ",",
        "Covid-19-Pandemie",
        "https://example.org/covid-test",
    ]

    assert tokenizer.simple_tokenizer(
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
    assert tokenizer.simple_tokenizer("WDR5-„Morgenecho“") == [
        "WDR5-",
        "„",
        "Morgenecho",
        "“",
    ]
