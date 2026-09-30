"""Shared utility functions for language processing."""

import unicodedata
from collections.abc import Iterable, Mapping


# NFC does not unify these with U+0027
_APOSTROPHE_GLYPHS = "’ʼ"
_APOSTROPHES = str.maketrans(_APOSTROPHE_GLYPHS, "''")


def fold_apostrophes(token: str) -> str:
    # guard: translate is slow and almost no token carries either glyph
    return token.translate(_APOSTROPHES) if "’" in token or "ʼ" in token else token


def normalize_token(token: str) -> str:
    """Normalize a token to NFC with straight apostrophes, as in the dictionaries."""
    return fold_apostrophes(unicodedata.normalize("NFC", token))


def strip_diacritics(word: str) -> str:
    """Remove combining diacritics and return NFC."""
    decomposed = unicodedata.normalize("NFD", word)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    )


def longest_first(words: Iterable[str]) -> tuple[str, ...]:
    """Longest first, so a shorter affix never shadows a longer one it prefixes."""
    return tuple(sorted(words, key=len, reverse=True))


# hy intonation marks, not canonicalized: some dict keys carry them contrastively
_ARMENIAN_MARKS = "՛՜՞"


# canonicalization tables apply to dictionary keys at build time and tokens at runtime
# grc: running text writes a non-final grave, headwords use the acute
_GRAVE_TO_ACUTE = str.maketrans(
    "ἂἃἊἋἒἓἚἛἢἣἪἫἲἳἺἻὂὃὊὋὒὓὛὢὣὪὫὰὲὴὶὸὺὼᾂᾃᾊᾋᾒᾓᾚᾛᾢᾣᾪᾫᾲᾺῂῈῊῒῚῢῪῲῸῺ",
    "ἄἅἌἍἔἕἜἝἤἥἬἭἴἵἼἽὄὅὌὍὔὕὝὤὥὬὭάέήίόύώᾄᾅᾌᾍᾔᾕᾜᾝᾤᾥᾬᾭᾴΆῄΈΉΐΊΰΎῴΌΏ",
)

# he: dictionary forms are pointed, running text is not
_HEBREW_POINTS = str.maketrans("", "", "ְֱֲֳִֵֶַָׇֹֺֻּֽֿׁׂ֑֖֛֢֣֤֥֦֧֪ׅ֚֭֮֒֓֔֕֗֘֙֜֝֞֟֠֡֨֩֫֬֯ׄ")

# ar: strip tashkeel and tatweel, but not hamza seats (they change the lemma too)
_ARABIC_MARKS = str.maketrans("", "", "ـًٌٍَُِّْٰٕٖٜٟٓٔٗ٘ٙٚٛٝٞ")

# canon langs must stay out of AFFIX_LANGS and RULE_FUNCTIONS (raw token matchers)
_CANON_TABLES: dict[str, Mapping[int, int | None]] = {
    "grc": _GRAVE_TO_ACUTE,
    "he": _HEBREW_POINTS,
    "ar": _ARABIC_MARKS,
}

CANON_LANGS: frozenset[str] = frozenset(_CANON_TABLES)


def canonicalize_token(token: str, lang: str) -> str:
    """Fold `token` to its dictionary-matching form for `lang`."""
    table = _CANON_TABLES.get(lang)
    return fold_apostrophes(token.translate(table) if table is not None else token)


def validate_lang_input(lang: str | tuple[str, ...]) -> tuple[str, ...]:
    """Normalize `lang` to a tuple, raising on invalid input."""
    if isinstance(lang, str):
        lang = (lang,)
    if not isinstance(lang, tuple):
        raise TypeError("lang argument must be a language code or a tuple of codes")
    if not lang:
        raise ValueError("lang argument is empty: provide at least one language code")
    return lang


def levenshtein_dist(str1: str, str2: str) -> int:
    """Minimum edit distance between two strings."""
    # adapted from https://gist.github.com/p-hash/9e0f9904ce7947c133308fbe48fe032b
    if str1 == str2:
        return 0
    if len(str1) > len(str2):
        str1, str2 = str2, str1
    r1 = list(range(len(str2) + 1))
    r2 = [0] * len(r1)
    for i, c1 in enumerate(str1):
        r2[0] = i + 1
        for j, c2 in enumerate(str2):
            if c1 == c2:
                r2[j + 1] = r1[j]
            else:
                a1, a2, a3 = r2[j], r1[j], r1[j + 1]
                if a1 > a2:
                    if a2 > a3:
                        r2[j + 1] = 1 + a3
                    else:
                        r2[j + 1] = 1 + a2
                else:
                    if a1 > a3:
                        r2[j + 1] = 1 + a3
                    else:
                        r2[j + 1] = 1 + a1
        aux = r1
        r1, r2 = r2, aux
    return r1[-1]
