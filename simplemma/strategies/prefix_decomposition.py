"""Prefix decomposition lemmatization strategy.

Each language: a UD-validated prefix list and an optional suffix regex fragment
(stem-floor lookahead, infinitive-collision guard, or none). DROP_PREFIX_LANGS
says whether a matched prefix is a separate particle to discard (ar/he
proclitics + article) or a derivational prefix that stays part of the lemma
(de/ru/uk). Prefixes are sorted by length so list order carries no meaning.
"""

import re

from ..utils import canonicalize_token, longest_first
from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy


def _prefix_regex(prefixes: str, suffix: str = "") -> re.Pattern[str]:
    return re.compile(r"^(" + "|".join(longest_first(prefixes.split())) + r")" + suffix)


DEFAULT_KNOWN_PREFIXES: dict[str, re.Pattern[str]] = {
    # UD-validated (ar_padt train): proclitics و/ب/ل + article ال + fused
    # stacks (وال/بال/فال, assimilated لل, comparative كال). ف/ك/س + the
    # other stacks EXCLUDED: 0-32% fix precision, and adding them reduces
    # net gain (19.9:1 vs 26.0:1 fix:regression) -- same pattern as he's
    # excluded מ. (?=..) stem floor: >=2 chars must remain, mirroring he's
    # guard against a short token stripping to a single-letter abbreviation key.
    "ar": _prefix_regex("و ب ل ال لل وال بال فال كال", r"(?=..)"),
    # UD-validated (de_gsd/de_hdt): dropped 27 entries that were
    # unreachable under first-match alternation ("herab" shadowed by
    # "her") plus "zu" (fabricated zufolge->zufolgen). (?!zu) blocks
    # prefix+zu-infinitive splits (abzuholen must not be read as
    # ab+zuholen) -- unrelated to the "zu" entry removed above.
    "de": _prefix_regex(
        "ab an auf aus be da durch ein ent er gegen heim her hin hinzu innen "
        "los miss mit nach neben nieder ran raus rein rum runter über um unter "
        "ver vor weg weiter wieder zer",
        r"(?!zu)",
    ),
    # UD-validated (he_htb train): single-letter proclitics attach to a
    # host word with no separator. The 7th proclitic מ is excluded -- 57%
    # fix precision vs 71-88% for these six, and a much worse
    # fix:regression ratio (8.5:1 vs 47.8:1) end-to-end. 2-letter stacked
    # combos (וש/ומ/ול/...) also excluded: all under 68% precision.
    # (?=..) stem floor: at least 2 chars must remain after the prefix,
    # else a 2-letter token strips to a single letter and hits a
    # one-letter abbreviation key (בצ -> צ -> צפון).
    "he": _prefix_regex("ו ה ב כ ל ש", r"(?=..)"),
    # UD-validated (ru_gsd/ru_syntagrus): "за"/"при" removed -- net
    # harmful, fabricating lemmas for lexicalized adverbs
    # (затем->затема).
    "ru": _prefix_regex(
        "гидро контр много микро недо пере под пред про радио раз рас само "
        "экстра электро"
    ),
    # UD-validated (uk_iu): clean accept, no harmful entry. See
    # README.md "Slavic prefix wave".
    "uk": _prefix_regex("по за ви на при про роз пере від до під об без"),
}

# Languages where a matched prefix is a separate grammatical particle, not
# part of the stem's lemma (ar/he proclitics + article: "بالبيت"/"בבית" ->
# "بيت"/"בית"); elsewhere the prefix stays attached (the default).
DROP_PREFIX_LANGS = frozenset({"ar", "he"})


class PrefixDecompositionStrategy(LemmatizationStrategy):
    """Strip a known prefix, look up the remainder; for DROP_PREFIX_LANGS the
    prefix is a particle (dropped), otherwise it stays attached."""

    __slots__ = ["_known_prefixes", "_dictionary_lookup"]

    def __init__(
        self,
        known_prefixes: dict[str, re.Pattern[str]] = DEFAULT_KNOWN_PREFIXES,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        self._known_prefixes = known_prefixes
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        if lang not in self._known_prefixes:
            return None

        # Fold BEFORE matching (no-op for unregistered langs): ar tashkeel
        # sits between a fused prefix's letters (بِالْكِتَابِ), so a
        # multi-char prefix can never match the raw token.
        token = canonicalize_token(token, lang)
        prefix_match = self._known_prefixes[lang].match(token)
        if not prefix_match or prefix_match[1] == token:
            return None

        prefix = prefix_match[1]

        subword = self._dictionary_lookup.get_lemma(token[len(prefix) :], lang)
        if not subword:
            return None

        # DROP_PREFIX_LANGS: the prefix is its own particle, so the stem's
        # lemma alone is the answer -- see the module comment above.
        if lang in DROP_PREFIX_LANGS:
            return subword

        return prefix + subword.lower()
