from simplemma import RegexTokenizer, simple_tokenizer


def test_tokenizer() -> None:
    # tokenization and chaining
    text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == [
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
    )
    text = "Sent1. Sent2\r\nSent3"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == ["Sent1", ".", "Sent2", "Sent3"]
    )
    text = "200er-Inzidenz 1.000er-Inzidenz 5%-Hürde 5-%-Hürde FFP2-Masken St.-Martini-Gemeinde, Lebens-, Liebes- und Arbeitsbedingungen"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == [
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
    )
    text = "360-Grad-Panorama @sebastiankurz 2,5-Zimmer-Wohnung 1,2-butylketoaldehyde"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == [
            "360-Grad-Panorama",
            "@sebastiankurz",
            "2,5-Zimmer-Wohnung",
            "1,2-butylketoaldehyde",
        ]
    )
    text = "Covid-19, Covid19, Covid-19-Pandemie https://example.org/covid-test"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == [
            "Covid-19",
            ",",
            "Covid19",
            ",",
            "Covid-19-Pandemie",
            "https://example.org/covid-test",
        ]
    )
    text = "Test 4:1-Auswärtssieg 2,5€ €3.5 $3.5 §52, for $5, 3/5 -1.4"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == [
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
    )
    # problem here: WDR5-„Morgenecho“
    text = "WDR5-„Morgenecho“"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == [
            "WDR5-",
            "„",
            "Morgenecho",
            "“",
        ]
    )
