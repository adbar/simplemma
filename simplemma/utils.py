"""Shared utility functions for language processing."""

import unicodedata
from collections.abc import Iterable, Mapping


# curly U+2019 and modifier-letter U+02BC fold to U+0027 (NFC does not unify them)
_APOSTROPHE_GLYPHS = "’ʼ"
_APOSTROPHES = str.maketrans(_APOSTROPHE_GLYPHS, "''")


def fold_apostrophes(token: str) -> str:
    # guard: translate costs 10x NFC, and almost no token carries either glyph
    return token.translate(_APOSTROPHES) if "’" in token or "ʼ" in token else token


def normalize_token(token: str) -> str:
    """Normalize a token to NFC with straight apostrophes, matching the shipped
    dictionaries (keys and values go through the same call at build time)."""
    return fold_apostrophes(unicodedata.normalize("NFC", token))


def strip_diacritics(word: str) -> str:
    """Remove combining diacritics, re-normalizing to NFC (dictionaries are
    NFC-keyed)."""
    decomposed = unicodedata.normalize("NFD", word)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    )


def longest_first(words: Iterable[str]) -> tuple[str, ...]:
    """Longest first, so a shorter affix never shadows a longer one it prefixes."""
    return tuple(sorted(words, key=len, reverse=True))


# hy intonation marks (Մի՞թե); NOT a canon table -- some dict keys carry the
# mark contrastively (ազատի՛ -> ազատել vs ազատի -> ազատ)
_ARMENIAN_MARKS = "՛՜՞"


# Per-language dictionary-matching canonicalization, applied to BOTH
# dictionary keys (dictionary_builder, at build time) and lookup tokens
# (DictionaryLookupStrategy, at runtime) -- the single hook that keeps the two
# sides symmetric. Adding a language means adding one str.translate table
# below; no strategy/builder code changes needed.
#
# grc: positional grave accent -> citation acute. Greek running text marks a
# non-final grave; Wiktionary/dictionary headwords key on the acute (citation)
# form.
_GRAVE_TO_ACUTE = str.maketrans(
    "ἂἃἊἋἒἓἚἛἢἣἪἫἲἳἺἻὂὃὊὋὒὓὛὢὣὪὫὰὲὴὶὸὺὼᾂᾃᾊᾋᾒᾓᾚᾛᾢᾣᾪᾫᾲᾺῂῈῊῒῚῢῪῲῸῺ",
    "ἄἅἌἍἔἕἜἝἤἥἬἭἴἵἼἽὄὅὌὍὔὕὝὤὥὬὭάέήίόύώᾄᾅᾌᾍᾔᾕᾜᾝᾤᾥᾬᾭᾴΆῄΈΉΐΊΰΎῴΌΏ",
)

# he: strip niqqud/cantillation points. Wiktionary headwords/forms are
# pointed for pedagogical clarity; running text (and UD gold) is unpointed.
_HEBREW_POINTS = str.maketrans("", "", "ְֱֲֳִֵֶַָׇֹֺֻּֽֿׁׂ֑֖֛֢֣֤֥֦֧֪ׅ֚֭֮֒֓֔֕֗֘֙֜֝֞֟֠֡֨֩֫֬֯ׄ")

# ar: strip tashkeel/dagger-alef (U+064B-065F, U+0670; same pedagogical-
# vocalization mismatch as he) + tatweel U+0640 (a pure elongation stroke).
# Deliberately NOT hamza-seat folds (أإآ->ا, ى->ي): those change spelling
# on the VALUE side too, and gold text spells hamza correctly.
_ARABIC_MARKS = str.maketrans("", "", "ـًٌٍَُِّْٰٕٖٜٟٓٔٗ٘ٙٚٛٝٞ")

# NOT a general fold: each table encodes one language's convention;
# applying it elsewhere would collide distinct words (e.g. Latvian's
# macron is orthographic, not positional).
# Canon langs must stay out of AFFIX_LANGS/RULE_FUNCTIONS (those match the
# raw token): test_canon_langs_disjoint_from_raw_token_strategies.
_CANON_TABLES: dict[str, Mapping[int, int | None]] = {
    "grc": _GRAVE_TO_ACUTE,
    "he": _HEBREW_POINTS,
    "ar": _ARABIC_MARKS,
}

# Public membership view of _CANON_TABLES, for callers that only need to ask
# "is this language canonicalized?" without importing the private tables dict.
CANON_LANGS: frozenset[str] = frozenset(_CANON_TABLES)


def canonicalize_token(token: str, lang: str) -> str:
    """Fold `token` to its dictionary-matching canonical form for `lang`:
    straight apostrophes, plus `_CANON_TABLES` for the languages it lists."""
    table = _CANON_TABLES.get(lang)
    return fold_apostrophes(token.translate(table) if table is not None else token)


def validate_lang_input(lang: str | tuple[str, ...]) -> tuple[str, ...]:
    """Normalize `lang` to a tuple, raising on invalid input."""
    # convert string
    if isinstance(lang, str):
        lang = (lang,)
    if not isinstance(lang, tuple):
        raise TypeError("lang argument must be a two-letter language code")
    if not lang:
        raise ValueError("lang argument is empty: provide at least one language code")
    return lang


def levenshtein_dist(str1: str, str2: str) -> int:
    """Minimum edit distance between two strings."""
    # inspired by this noticeably faster code:
    # https://gist.github.com/p-hash/9e0f9904ce7947c133308fbe48fe032b
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
