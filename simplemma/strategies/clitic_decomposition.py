"""Enclitic stripping: portar-lo -> portar, don't -> do.

Proclitics are handled by `PrefixDecompositionStrategy`.
"""

from ..utils import CANON_LANGS, canonicalize_token, strip_diacritics
from .defaultrules.generic import SuffixRules
from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

MIN_STEM_LEN = 4

# pt and ca clitics always carry a hyphen or apostrophe, a bare strip mangles words
CLITIC_LANGS: dict[str, SuffixRules] = {
    "es": SuffixRules(
        {"": "nos les las los me te se le la lo os"}, min_stem=MIN_STEM_LEN, caps=True
    ),
    "pt": SuffixRules(
        {
            "": "-lhes -nos -vos -lhe -las -los -me -te -se -la -lo -na -no -as -os -a -o"
        },
        min_stem=MIN_STEM_LEN,
        caps=True,
    ),
    "ca": SuffixRules(
        {
            "": (
                "-nos 'nos -les 'les -los 'los -me 'me -te 'te -se 'se -le 'le -la"
                " 'la -lo 'lo -hi 'hi -ho 'ho -ne 'ne -el 'el -en 'en -li 'li"
            )
        },
        min_stem=MIN_STEM_LEN,
        caps=True,
    ),
    "it": SuffixRules(
        {"": "gli vi ci si mi ti ne lo la le li"}, min_stem=MIN_STEM_LEN, caps=True
    ),
    "gl": SuffixRules(
        {
            "": "-lles lles -lle lle -nos nos -vos vos -me me -te te -se se -as as -os os -a a -o o"
        },
        min_stem=MIN_STEM_LEN,
        caps=True,
    ),
    # stripping n't off can't/won't/shan't leaves a wrong real word
    "en": SuffixRules(
        {"": "n't 're 've 'll 'm 's 'd"},
        min_stem=1,
        excluded=frozenset({"can't", "won't", "shan't"}),
    ),
    # ك and ي left out: they collide with root-final letters and nisba endings
    "ar": SuffixRules({"": "هن هم ها ه كم نا"}, min_stem=MIN_STEM_LEN, caps=True),
    # particles, verb endings and copula forms after a dictionary stem
    "ko": SuffixRules(
        {
            "": (
                "가 같이 거든 거라 게 겠다 겠습니다 겠어요 고 과 구나 구요 군요 기"
                " 길래 까지 께 께서 나 냐 네 느냐 느냐고 느니 는 는가 는다 는데 니 니까"
                " 다 다고 더니 더라도 던 도 도록 들 라 라고 라도 란 랑 려고 로 로부터"
                " 로서 를 마다 마저 만 만큼 며 면 밖에 보다 보다도 부터 서 세요 셔 셔서"
                " 소 슴 습니까 습니다 시고 십니다 십시오 아요 야 야말로 어서 어야 어요"
                " 었기 었음 에 에게로 에는 에다 에다가 에요 엔 여 여서 여야 였기"
                " 였음 오 요 으 으니 으라 으러 으려 으로 으로서 은 을 을지 읍시다 이다"
                " 이라서 인가 인데 자 조차 죠 지 지만 질 한테 한테서 인다 여요"
                " 입니다 였다 였어요 였습니다 입니까 였느냐 일"
            ),
        },
        min_stem=1,
    ),
}

# second strip: hyphen chains (portar-se-la), bare only in es and gl
_HYPHEN_CHAIN = SuffixRules(
    {"": "-nos -vos -me -te -se"}, min_stem=MIN_STEM_LEN, caps=True
)
CLITIC_CHAINS: dict[str, SuffixRules] = {
    "es": CLITIC_LANGS["es"],
    "gl": CLITIC_LANGS["gl"],
    "pt": _HYPHEN_CHAIN,
    "ca": _HYPHEN_CHAIN,
    # the copula before an ending (곳이에요, 학생이지만)
    "ko": SuffixRules({"": "이"}, min_stem=1),
}


class CliticDecompositionStrategy(LemmatizationStrategy):
    """Strip an enclitic and look up the remaining stem."""

    __slots__ = ["_dictionary_lookup"]

    def __init__(
        self,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        rules = CLITIC_LANGS.get(lang)
        if rules is None:
            return None
        stem = rules.apply(canonicalize_token(token, lang))
        if stem is None:
            return None
        lemma = self._stem_lookup(stem, lang)
        chain = CLITIC_CHAINS.get(lang)
        if lemma is None and chain is not None:
            stem = chain.apply(stem)
            if stem is not None:
                lemma = self._stem_lookup(stem, lang)
        return lemma

    def _stem_lookup(self, stem: str, lang: str) -> str | None:
        lemma = self._dictionary_lookup.get_lemma(stem, lang)
        # enclisis can add an accent (calificándole), not folded for CANON_LANGS
        if lemma is not None or lang in CANON_LANGS:
            return lemma
        folded = strip_diacritics(stem)
        if folded == stem:
            return None
        return self._dictionary_lookup.get_lemma(folded, lang)
