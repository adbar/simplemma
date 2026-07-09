import unicodedata

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
    # mixed punctuation splits; same-char runs stay whole
    text = 'Er sagte: "Gut." Wirklich... ja?!'
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == ["Er", "sagte", ":", '"', "Gut", ".", '"', "Wirklich", "...", "ja", "?", "!"]
    )
    # standalone hyphens are tokens; hyphenated words stay whole
    text = "Berlin - die Hauptstadt -- und mehr"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == ["Berlin", "-", "die", "Hauptstadt", "--", "und", "mehr"]
    )
    # Devanagari: vowel signs stay inside the word, danda is a token
    text = "वह घर जाता है। ठीक॥"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == ["वह", "घर", "जाता", "है", "।", "ठीक", "॥"]
    )
    # NFD input: combining diacritics stay inside the word
    text = unicodedata.normalize("NFD", "H\u00e4user stehen.")
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == [unicodedata.normalize("NFD", "H\u00e4user"), "stehen", "."]
    )
    # Persian: ZWNJ stays inside words, Arabic punctuation marks are tokens
    text = "می‌روم و کتاب‌ها را می‌خوانم؟ بله، خوب؛"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == [
            "می‌روم",
            "و",
            "کتاب‌ها",
            "را",
            "می‌خوانم",
            "؟",
            "بله",
            "،",
            "خوب",
            "؛",
        ]
    )
    # Armenian full stop is a token of its own
    text = "Նա ապրում է Երևանում։"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == ["Նա", "ապրում", "է", "Երևանում", "։"]
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
    # word-internal apostrophes stay; quotes and edge apostrophes split
    text = "L'homme n'est qu'un roseau."
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == ["L'homme", "n'est", "qu'un", "roseau", "."]
    )
    # ca elides articles before numerals: the join must not eat the numeral
    assert "11" in simple_tokenizer("l'11 de setembre")
    # tr suffix on a numeric form: the apostrophe joins (digit BEFORE it)
    assert simple_tokenizer("2020'de") == ["2020'de"]
    text = "he said 'hello' about Türkiye’nin dogs' owners"
    assert (
        list(RegexTokenizer().split_text(text))
        == simple_tokenizer(text)
        == [
            "he",
            "said",
            "'",
            "hello",
            "'",
            "about",
            "Türkiye’nin",
            "dogs",
            "'",
            "owners",
        ]
    )
