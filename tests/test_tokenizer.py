import unicodedata

import pytest

from simplemma import RegexTokenizer, simple_tokenizer

_TOKENIZATION_CASES = [
    # tokenization and chaining
    (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        [
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
        ],
    ),
    ("Sent1. Sent2\r\nSent3", ["Sent1", ".", "Sent2", "Sent3"]),
    (
        "200er-Inzidenz 1.000er-Inzidenz 5%-Hürde 5-%-Hürde FFP2-Masken St.-Martini-Gemeinde, Lebens-, Liebes- und Arbeitsbedingungen",
        [
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
        ],
    ),
    (
        "360-Grad-Panorama @sebastiankurz 2,5-Zimmer-Wohnung 1,2-butylketoaldehyde",
        [
            "360-Grad-Panorama",
            "@sebastiankurz",
            "2,5-Zimmer-Wohnung",
            "1,2-butylketoaldehyde",
        ],
    ),
    (
        "Covid-19, Covid19, Covid-19-Pandemie https://example.org/covid-test",
        [
            "Covid-19",
            ",",
            "Covid19",
            ",",
            "Covid-19-Pandemie",
            "https://example.org/covid-test",
        ],
    ),
    (
        "Test 4:1-Auswärtssieg 2,5€ €3.5 $3.5 §52, for $5, 3/5 -1.4",
        [
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
        ],
    ),
    # mixed punctuation splits; same-char runs stay whole
    (
        'Er sagte: "Gut." Wirklich... ja?!',
        ["Er", "sagte", ":", '"', "Gut", ".", '"', "Wirklich", "...", "ja", "?", "!"],
    ),
    # standalone hyphens are tokens; hyphenated words stay whole
    (
        "Berlin - die Hauptstadt -- und mehr",
        ["Berlin", "-", "die", "Hauptstadt", "--", "und", "mehr"],
    ),
    # Devanagari: vowel signs stay inside the word, danda is a token
    ("वह घर जाता है। ठीक॥", ["वह", "घर", "जाता", "है", "।", "ठीक", "॥"]),
    # NFD input: combining diacritics stay inside the word
    (
        unicodedata.normalize("NFD", "Häuser stehen."),
        [unicodedata.normalize("NFD", "Häuser"), "stehen", "."],
    ),
    # Persian: ZWNJ stays inside words, Arabic punctuation marks are tokens
    (
        "می‌روم و کتاب‌ها را می‌خوانم؟ بله، خوب؛",
        ["می‌روم", "و", "کتاب‌ها", "را", "می‌خوانم", "؟", "بله", "،", "خوب", "؛"],
    ),
    # Armenian full stop is a token of its own
    ("Նա ապրում է Երևանում։", ["Նա", "ապրում", "է", "Երևանում", "։"]),
    # problem here: WDR5-„Morgenecho“
    ("WDR5-„Morgenecho“", ["WDR5-", "„", "Morgenecho", "“"]),
    # word-internal apostrophes stay; quotes and edge apostrophes split
    ("L'homme n'est qu'un roseau.", ["L'homme", "n'est", "qu'un", "roseau", "."]),
    # ca elides articles before numerals: the join must not eat the numeral
    ("l'11 de setembre", ["l", "'", "11", "de", "setembre"]),
    # tr suffix on a numeric form: the apostrophe joins (digit BEFORE it)
    ("2020'de", ["2020'de"]),
    (
        "he said 'hello' about Türkiye’nin dogs' owners",
        [
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
        ],
    ),
]


@pytest.mark.parametrize("text, expected", _TOKENIZATION_CASES)
def test_tokenizer(text: str, expected: list[str]) -> None:
    assert simple_tokenizer(text) == expected


def test_simple_tokenizer_wraps_regex_tokenizer() -> None:
    """`simple_tokenizer` is the default RegexTokenizer; the equivalence only
    needs proving once, the table above runs through the wrapper."""
    text = "Sent1. Sent2\r\nSent3"
    assert list(RegexTokenizer().split_text(text)) == simple_tokenizer(text)
