"""Prefix-based lemmatization of unknown tokens.

Each language: a UD-validated prefix list, an optional suffix regex fragment
(stem-floor lookahead, infinitive-collision guard, or none), and `drop` --
whether a matched prefix is a separate particle to discard (ar/he proclitics
+ article) or a derivational prefix that stays part of the lemma (de/ru/uk).
Regex sorts prefixes by length so alternation order carries no meaning.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class _Prefixes:
    prefixes: list[str]
    suffix: str  # regex fragment appended after the prefix group
    drop: bool  # matched prefix is a separate particle, not part of the lemma


_PREFIX_CONFIG: dict[str, _Prefixes] = {
    "ar": _Prefixes(
        # UD-validated (ar_padt train): proclitics و/ب/ل + article ال + fused
        # stacks (وال/بال/فال, assimilated لل, comparative كال). ف/ك/س + the
        # other stacks EXCLUDED: 0-32% fix precision, and adding them reduces
        # net gain (19.9:1 vs 26.0:1 fix:regression) -- same pattern as he's
        # excluded מ.
        ["و", "ب", "ل", "ال", "لل", "وال", "بال", "فال", "كال"],
        # (?=..) stem floor: >=2 chars must remain, mirroring he's guard
        # against a short token stripping to a single-letter abbreviation key.
        r"(?=..)",
        drop=True,
    ),
    "de": _Prefixes(
        # UD-validated (de_gsd/de_hdt): dropped 27 entries that were
        # unreachable under first-match alternation ("herab" shadowed by
        # "her") plus "zu" (fabricated zufolge->zufolgen).
        [
            "ab",
            "an",
            "auf",
            "aus",
            "be",
            "da",
            "durch",
            "ein",
            "ent",
            "er",
            "gegen",
            "heim",
            "her",
            "hin",
            "hinzu",
            "innen",
            "los",
            "miss",
            "mit",
            "nach",
            "neben",
            "nieder",
            "ran",
            "raus",
            "rein",
            "rum",
            "runter",
            "über",
            "um",
            "unter",
            "ver",
            "vor",
            "weg",
            "weiter",
            "wieder",
            "zer",
        ],
        # (?!zu) blocks prefix+zu-infinitive splits (abzuholen must not be
        # read as ab+zuholen) -- unrelated to the "zu" entry removed above.
        r"(?!zu)",
        drop=False,
    ),
    "he": _Prefixes(
        # UD-validated (he_htb train): single-letter proclitics attach to a
        # host word with no separator. The 7th proclitic מ is excluded -- 57%
        # fix precision vs 71-88% for these six, and a much worse
        # fix:regression ratio (8.5:1 vs 47.8:1) end-to-end. 2-letter stacked
        # combos (וש/ומ/ול/...) also excluded: all under 68% precision.
        ["ו", "ה", "ב", "כ", "ל", "ש"],
        # (?=..) stem floor: at least 2 chars must remain after the prefix,
        # else a 2-letter token strips to a single letter and hits a
        # one-letter abbreviation key (בצ -> צ -> צפון).
        r"(?=..)",
        drop=True,
    ),
    "ru": _Prefixes(
        # UD-validated (ru_gsd/ru_syntagrus): "за"/"при" removed -- net
        # harmful, fabricating lemmas for lexicalized adverbs
        # (затем->затема).
        [
            "гидро",
            "контр",
            "много",
            "микро",
            "недо",
            "пере",
            "под",
            "пред",
            "про",
            "радио",
            "раз",
            "рас",
            "само",
            "экстра",
            "электро",
        ],
        "",
        drop=False,
    ),
    "uk": _Prefixes(
        # UD-validated (uk_iu): clean accept, no harmful entry. See
        # README.md "Slavic prefix wave".
        [
            "по",
            "за",
            "ви",
            "на",
            "при",
            "про",
            "роз",
            "пере",
            "від",
            "до",
            "під",
            "об",
            "без",
        ],
        "",
        drop=False,
    ),
}


def _build_regex(config: _Prefixes) -> re.Pattern[str]:
    ordered = sorted(config.prefixes, key=len, reverse=True)
    return re.compile(r"^(" + "|".join(ordered) + r")" + config.suffix)


DEFAULT_KNOWN_PREFIXES: dict[str, re.Pattern[str]] = {
    lang: _build_regex(config) for lang, config in _PREFIX_CONFIG.items()
}

# Languages where a matched prefix is a separate grammatical particle, not
# part of the stem's lemma (ar/he proclitics + article: "بالبيت"/"בבית" ->
# "بيت"/"בית"); elsewhere the prefix stays attached (the default).
DROP_PREFIX_LANGS = frozenset(
    lang for lang, config in _PREFIX_CONFIG.items() if config.drop
)
