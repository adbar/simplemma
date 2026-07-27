"""
Utils module.
Contains utility functions for language processing.

- [levenshtein_dist][simplemma.utils.levenshtein_dist]: Calculates the Levenshtein distance between two strings.
- [validate_lang_input][simplemma.utils.validate_lang_input]: Validates the language input and ensures it is a valid tuple.
- [normalize_token][simplemma.utils.normalize_token]: Normalizes a token to Unicode NFC form.
- [strip_diacritics][simplemma.utils.strip_diacritics]: Removes combining diacritics from a token.
- [canonicalize_token][simplemma.utils.canonicalize_token]: Per-language dictionary-matching canonicalization (grc grave->acute, he/ar vocalization-stripping).
- `CANON_LANGS`: Languages canonicalize_token folds (public membership view of _CANON_TABLES).
"""

import unicodedata
from collections.abc import Mapping


def normalize_token(token: str) -> str:
    """
    Normalize a token to Unicode NFC, matching the shipped dictionaries.

    Args:
        token (str): The input token.

    Returns:
        str: The token in NFC form.
    """
    return unicodedata.normalize("NFC", token)


def strip_diacritics(word: str) -> str:
    """Remove combining diacritics, re-normalizing to NFC (dictionaries are
    NFC-keyed)."""
    decomposed = unicodedata.normalize("NFD", word)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    )


# Apostrophe glyphs folded to straight U+0027 (the form dictionaries key on);
# NFC does not unify them. Single source of truth for the helpers below.
_STRAIGHT_APOSTROPHE = "'"
_FOLDED_APOSTROPHES = ("’", "ʼ")  # curly U+2019, modifier letter U+02BC


def normalize_apostrophes(text: str) -> str:
    """Fold curly and modifier-letter apostrophes to straight (U+0027)."""
    for glyph in _FOLDED_APOSTROPHES:
        text = text.replace(glyph, _STRAIGHT_APOSTROPHE)
    return text


def has_apostrophe(text: str) -> bool:
    """True if the text carries any apostrophe glyph normalize_apostrophes folds.
    Inline (hot path: gates every OOV lookup); mirror the glyph constants above."""
    return "'" in text or "’" in text or "ʼ" in text


def apostrophe_variants(token: str) -> tuple[str, ...]:
    """Every apostrophe-glyph form of the token to try in dictionary lookups."""
    straight = normalize_apostrophes(token)
    if _STRAIGHT_APOSTROPHE not in straight:
        return (token,)
    folded = (straight.replace(_STRAIGHT_APOSTROPHE, g) for g in _FOLDED_APOSTROPHES)
    return tuple(dict.fromkeys((token, straight, *folded)))


# hy intonation marks (Մի՞թե); NOT a canon table -- some dict keys carry the
# mark contrastively (ազատի՛ -> ազատել vs ազատի -> ազատ)
_ARMENIAN_MARKS = "՛՜՞"
_ARMENIAN_MARKS_TABLE = str.maketrans("", "", _ARMENIAN_MARKS)


def has_armenian_marks(text: str) -> bool:
    """True if the text carries any hy intonation mark (՛ ՜ ՞)."""
    return "՛" in text or "՜" in text or "՞" in text


def strip_armenian_marks(text: str) -> str:
    """Remove the hy intonation marks (՛ ՜ ՞)."""
    return text.translate(_ARMENIAN_MARKS_TABLE)


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
    """Fold `token` to its dictionary-matching canonical form for `lang`
    (see `_CANON_TABLES`); returns it unchanged for any other language."""
    table = _CANON_TABLES.get(lang)
    return token.translate(table) if table is not None else token


def validate_lang_input(lang: str | tuple[str, ...]) -> tuple[str, ...]:
    """
    Make sure the lang variable is a valid tuple.

    Args:
        lang (Any): The language input.

    Returns:
        tuple[str, ...]: A tuple containing the language code(s).

    Raises:
        TypeError: If the lang argument is not a tuple or a string.
        ValueError: If the lang argument is empty.

    """
    # convert string
    if isinstance(lang, str):
        lang = (lang,)
    if not isinstance(lang, tuple):
        raise TypeError("lang argument must be a two-letter language code")
    if not lang:
        raise ValueError("lang argument is empty: provide at least one language code")
    return lang


def levenshtein_dist(str1: str, str2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.

    The Levenshtein distance is a metric for measuring the difference between two strings,
    defined as the minimum number of single-character edits (insertions, deletions, or substitutions)
    required to change one string into the other.

    Args:
        str1 (str): The first string.
        str2 (str): The second string.

    Returns:
        int: The Levenshtein distance between the two strings.

    """
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
