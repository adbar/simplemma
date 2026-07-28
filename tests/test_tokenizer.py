import pickle
import re
import tracemalloc
import unicodedata

import pytest

from simplemma import RegexTokenizer, simple_tokenizer
from simplemma.tokenizer import _BLOCK, _PUNCT, _TRAILING_PUNCT, TOKREGEX, _fast_split

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
    # a URL ends at any whitespace, not just a space
    ("siehe https://x.org/a?b=1\nDanach", ["siehe", "https://x.org/a?b=1", "Danach"]),
    (
        "Test 4:1-Auswärtssieg 2,5€ €3.5 $3.5 §52, for $5, 3/5 -1.4",
        [
            "Test",
            "4:1-Auswärtssieg",
            # a currency sign next to a number is its own token, either side
            # (UD gold splits it even where the text glues it)
            "2,5",
            "€",
            "€",
            "3.5",
            "$",
            "3.5",
            "§52",
            ",",
            "for",
            "$",
            "5",
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
    # Hebrew: niqqud/cantillation marks stay inside the word (pointed text
    # must not shatter into single letters)
    ("וְהַבַּיִת הַגָּדוֹל", ["וְהַבַּיִת", "הַגָּדוֹל"]),
    # Hebrew: maqaf joins a compound like an ASCII hyphen (stays one token);
    # standalone/leading maqaf still becomes its own punctuation token
    ("הוא לומד בבית־ספר גדול.", ["הוא", "לומד", "בבית־ספר", "גדול", "."]),
    ("א ־ ב", ["א", "־", "ב"]),
    # Malayalam: vowel signs/virama stay inside the word (alphasyllabic text
    # must not shatter at every vowel sign)
    ("മലയാളം കേരളത്തിലെ ഭാഷ.", ["മലയാളം", "കേരളത്തിലെ", "ഭാഷ", "."]),
    # problem here: WDR5-„Morgenecho“
    ("WDR5-„Morgenecho“", ["WDR5-", "„", "Morgenecho", "“"]),
    # word-internal apostrophes stay; quotes and edge apostrophes split
    ("L'homme n'est qu'un roseau.", ["L'homme", "n'est", "qu'un", "roseau", "."]),
    # ca elides articles before numerals: the join must not eat the numeral
    ("l'11 de setembre", ["l", "'", "11", "de", "setembre"]),
    # tr suffix on a numeric form: the apostrophe joins (digit BEFORE it)
    ("2020'de", ["2020'de"]),
    # ca interpunct is word-internal (ela geminada); edge interpunct splits
    ("els col·legis nous", ["els", "col·legis", "nous"]),
    ("mig · mig", ["mig", "·", "mig"]),
    # he geresh/gershayim join inside acronyms/loanwords; quote-like edges split
    ("ש״ח", ["ש״ח"]),
    # ASCII-quote spelling of the same acronyms (what real text types)
    ('שילם ש"ח היום', ["שילם", 'ש"ח', "היום"]),
    ('he said "yes"', ["he", "said", '"', "yes", '"']),
    ("צ׳יפס", ["צ׳יפס"]),
    # at a token edge they are punctuation, like the ASCII quote
    ("״שלום״", ["״", "שלום", "״"]),
    # hy intonation marks are word-internal (՞ on the stressed vowel);
    # a word-final or bare mark is punctuation
    ("Մի՞թե այդպիսի", ["Մի՞թե", "այդպիսի"]),
    ("ասա՛ նրան", ["ասա", "՛", "նրան"]),
    # a sign priced against a number is a token of its own on either side,
    # even where the text glues it; only a sign on a word stays glued (pt R$)
    ("Es kostet 5 €.", ["Es", "kostet", "5", "€", "."]),
    ("R$ 659 e US$ 200", ["R$", "659", "e", "US$", "200"]),
    ("€3,50 und 50€", ["€", "3,50", "und", "50", "€"]),
    ("comprou $PETR4 a R$ 30", ["comprou", "$PETR4", "a", "R$", "30"]),
    # every symbol behaves alike, and both yen widths are punctuation only
    ("50€ 50$ 50£", ["50", "€", "50", "$", "50", "£"]),
    ("￥100 ¥100", ["￥", "100", "¥", "100"]),
    # punctuation-only currency: emitted, never glued (these were dropped)
    ("Ціна 100 ₴ сьогодні", ["Ціна", "100", "₴", "сьогодні"]),
    ("שילם 50 ₪", ["שילם", "50", "₪"]),
    ("стоит 500₽", ["стоит", "500", "₽"]),
    # symbols outside the word/punctuation sets are not emitted
    ("👍 super", ["super"]),
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


def _raw(text: str) -> list[str]:
    """What TOKREGEX itself yields: the ground truth every fast path must match."""
    return [m[0] for m in TOKREGEX.finditer(text)]


def test_simple_tokenizer_wraps_regex_tokenizer() -> None:
    text = "Sent1. Sent2\r\nSent3"
    assert list(RegexTokenizer().split_text(text)) == simple_tokenizer(text)


def test_fast_path_matches_raw_regex() -> None:
    text = (
        'Dr. Meier zahlt 3,50 € für "das" Buch – l\'homme, ש"ח und\n'
        "https://x.org/a?b=1  fertig.\tEnde"  # \n \t and a double space
    )
    assert simple_tokenizer(text) == _raw(text)


def test_fast_flag_only_for_the_default_pattern() -> None:
    custom = RegexTokenizer(re.compile(r"[a-z]+"))
    assert list(custom.split_text("ab cd.ef")) == ["ab", "cd", "ef"]
    assert not custom._fast
    # by pattern, not identity: unpickling would otherwise lose the fast path
    assert pickle.loads(pickle.dumps(RegexTokenizer()))._fast
    # same pattern, different flags: a different tokenizer
    assert not RegexTokenizer(re.compile(TOKREGEX.pattern, re.IGNORECASE))._fast


def test_trailing_punct_set_is_exactly_the_separable_punctuation() -> None:
    prefixes = (
        "wort",
        "Wort",
        "St",
        "Dr",
        "a",
        "l",
        "L",
        "col",
        "Türkiye",
        "שלום",
        "בית",
        "Մի",
        "ասա",
        "کتاب",
        "الكتاب",
        "λόγος",
        "русский",
        "वह",
        "乔治",
        "ქართული",
        "한국어",
    )
    for char in _PUNCT:
        splits_cleanly = all(
            _raw(prefix + char) == [prefix, char] for prefix in prefixes
        )
        assert splits_cleanly == (char in _TRAILING_PUNCT), char


def test_fast_path_streams_without_materializing_the_text() -> None:
    text = ("Ein Satz mit Wörtern, Zahlen 3,50 € und Dr. Meier. " * 40_000)[:2_000_000]

    # text without a single space must be blocked just the same
    newlines = ("Wort\n" * 400_000)[: len(text)]

    for source in (text, newlines):
        tracemalloc.start()
        try:
            tokens = _fast_split(source)
            next(tokens)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert peak < len(source)


def test_block_boundaries_match_raw_regex() -> None:
    text = ("Ein Satz mit Wörtern, Zahlen 3,50 € und Dr. Meier. " * 40_000)[:2_000_000]
    for length in (_BLOCK - 2, _BLOCK - 1, _BLOCK, _BLOCK + 1, _BLOCK + 2):
        chunk = text[:length]
        assert simple_tokenizer(chunk) == _raw(chunk)
    # a token straddling the boundary stays whole
    straddle = "a" * (_BLOCK - 3) + " übergreifendes Wort"
    assert simple_tokenizer(straddle) == _raw(straddle)
