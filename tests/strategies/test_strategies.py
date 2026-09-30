import pytest

from simplemma.strategies import (
    AffixDecompositionStrategy,
    CliticDecompositionStrategy,
    DefaultStrategy,
    DictionaryLookupStrategy,
    GreedyDictionaryLookupStrategy,
    HyphenRemovalStrategy,
    MorphemeDecompositionStrategy,
    PrefixDecompositionStrategy,
)
from simplemma.strategies.greedy_dictionary_lookup import greedy_min_length
from simplemma.strategies.morpheme_decomposition import _morphemes
from simplemma import lemmatize
from simplemma.utils import normalize_token
from tests.conftest import FixedMapping

_LOOKUP = DictionaryLookupStrategy()
_CLITIC = CliticDecompositionStrategy()
_PREFIX = PrefixDecompositionStrategy()
_MORPHEME = MorphemeDecompositionStrategy()


def test_search() -> None:
    """Test simple and greedy dict search."""
    assert _LOOKUP.get_lemma("ignorant", "en") == "ignorant"
    assert _LOOKUP.get_lemma("Ignorant", "en") == "ignorant"

    assert _LOOKUP.get_lemma("dritte", "de") == "dritt"
    assert _LOOKUP.get_lemma("Dritte", "de") == "Dritter"
    assert _LOOKUP.get_lemma("", "en") is None

    assert HyphenRemovalStrategy().get_lemma("Mail-Clients", "de") == "Mail-Client"
    assert HyphenRemovalStrategy().get_lemma("Mail_Clients", "de") == "Mail_Client"
    assert HyphenRemovalStrategy().get_lemma("-ce", "fr") == "ce"
    assert HyphenRemovalStrategy().get_lemma("magni-ficent", "en") is None
    assert HyphenRemovalStrategy().get_lemma("magni-", "en") is None

    assert DefaultStrategy().get_lemma("01234", "en") == "01234"

    assert DefaultStrategy().get_lemma("Gender-Sternchens", "de") == "Gender-Sternchen"
    assert DefaultStrategy().get_lemma("vor-bereitetes", "de") == "vor-bereitet"

    assert (
        GreedyDictionaryLookupStrategy(steps=0, distance=20).get_lemma(
            "getesteten", "de"
        )
        == "getesteten"
    )
    assert (
        GreedyDictionaryLookupStrategy(steps=1, distance=20).get_lemma(
            "getesteten", "de"
        )
        == "getestet"
    )
    assert (
        GreedyDictionaryLookupStrategy(steps=2, distance=20).get_lemma(
            "getesteten", "de"
        )
        == "testen"
    )
    assert (
        GreedyDictionaryLookupStrategy(steps=2, distance=2).get_lemma(
            "getesteten", "de"
        )
        == "getestet"
    )
    # the greedy strategy must canonicalize when run standalone
    assert GreedyDictionaryLookupStrategy().get_lemma("آذربايجانَ", "ar") == "أذربيجان"

    assert PrefixDecompositionStrategy().get_lemma("за", "uk") is None


@pytest.mark.parametrize(
    ("lang", "greedy", "token", "expected"),
    [
        ("fi", True, "kissammeko", "kissa"),  # "and our cat?" -> cat
        ("hu", True, "könyveiteket", "könyv"),  # "your books" -> book
        ("et", True, "raamatutest", "raamat"),  # "from books" -> book
        ("da", False, "drabsdagen", "drabsdag"),
        ("da", False, "menighedsrådsvalget", "menighedsrådsvalg"),
        ("nn", False, "pastasalaten", "pastasalat"),
        ("nn", False, "underleverandørane", "underleverandør"),
        ("is", False, "guðsríkis", "guðsríki"),
        ("ro", False, "degenerativă", "degenerativ"),
        ("sv", False, "kibbutzbarnen", "kibbutzbarn"),
        # compound splits are greedy-only
        ("lv", False, "spēlēties", None),
        # lt's entry gate is 7, below these 8-char forms
        ("lt", False, "rengiami", "rengti"),
        ("lt", False, "teikiant", "teikti"),
        ("et", True, "aadelkond", None),
        ("sw", True, "-changanya", None),  # GREEDY_EXCLUDE: prefixing/mutating
        ("es", False, "microrregiones", None),  # not in AFFIX_LANGS
        ("pt", True, "supostamente", None),
        ("gl", True, "virtualmente", None),
        ("de", True, "ccc", None),
    ],
)
def test_affix_decomposition(
    lang: str, greedy: bool, token: str, expected: str | None
) -> None:
    assert AffixDecompositionStrategy(greedy=greedy).get_lemma(token, lang) == expected


def test_affix_decomposition_guards() -> None:
    """The entry gate excludes sw, not the sub-strategy. Long tokens are capped.

    The 100k-char token is not parametrized: its node id breaks Windows env vars.
    """
    affix = AffixDecompositionStrategy(greedy=True)
    assert greedy_min_length("lt") == 7
    assert greedy_min_length("bg") == 6
    assert greedy_min_length("xx") == 8
    assert affix._suffix_decomposition("-changanya", "sw") is not None
    assert affix.get_lemma("a" * 101, "fi") is None
    assert affix.get_lemma("a" * 100000, "fi") is None


def test_clitic_decomposition_skips_diacritic_fold_for_canon_languages() -> None:
    """The diacritic fold would decompose Arabic hamza into an unrelated entry."""
    # only the hamza-decomposed form is a (deliberately unrelated) dict entry
    clitic = CliticDecompositionStrategy(
        dictionary_lookup=DictionaryLookupStrategy(
            dictionary_factory=FixedMapping({"مومن": "أيمن"})
        )
    )
    assert clitic.get_lemma("مؤمنه", "ar") is None


_CLITIC_CASES = [
    pytest.param("transmitiéndose", "es", "transmitir", id="enclitic-es-transmitir"),
    pytest.param("encontrarlo", "es", "encontrar", id="enclitic-es-encontrar"),
    pytest.param("aprova-se", "pt", "aprovar", id="enclitic-pt-aprovar"),
    pytest.param("mobilitzar-se", "ca", "mobilitzar", id="enclitic-ca-mobilitzar"),
    pytest.param("mettersi", "it", "mettere", id="enclitic-it-mettere"),
    pytest.param("sitúanse", "gl", "situar", id="enclitic-gl-situar"),
    pytest.param("transmitiéndose", "de", None, id="enclitic-unsupported-lang"),
    pytest.param("Paulo", "pt", None, id="guard-capitalized-paulo"),
    pytest.param("tê-lo", "pt", None, id="guard-short-stem-telo"),
    pytest.param("fer-ho", "ca", None, id="guard-short-stem-ferho"),
    pytest.param("zzzzzzselo", "es", None, id="guard-no-dict-hit"),
    # pt/ca strip only a hyphenated clitic: a bare strip would mangle these
    pytest.param("paulo", "pt", None, id="guard-bare-strip-paulo"),
    pytest.param("carona", "pt", None, id="guard-bare-strip-carona"),
    pytest.param("alumne", "ca", None, id="guard-bare-strip-alumne"),
    # hyphen-chained clitics get one more strip, a dead chain stays None
    pytest.param("portar-se-la", "ca", "portar", id="chain-ca-portar-se-la"),
    pytest.param("vendê-se-lo", "pt", "vender", id="chain-pt-vende-se-lo"),
    pytest.param("zzzzzz-se-lo", "pt", None, id="chain-pt-dead-stem"),
    pytest.param("don't", "en", "do", id="en-dont"),
    pytest.param("Don't", "en", "do", id="en-sentence-initial-Dont"),
    pytest.param("I'm", "en", "I", id="en-Im"),
    pytest.param("you're", "en", "you", id="en-youre"),
    pytest.param("isn't", "en", "be", id="en-isnt"),
    # "'s" and "'d" are ambiguous, so only the stem is lemmatized
    pytest.param("it's", "en", "it", id="en-its"),
    pytest.param("company's", "en", "company", id="en-companys"),
    pytest.param("he'd", "en", "he", id="en-hed"),
    # stripping "n't" from "can't" leaves "ca", a real but wrong entry
    pytest.param("can't", "en", None, id="en-cant-excluded"),
    pytest.param("won't", "en", None, id="en-wont-excluded"),
    pytest.param("كتابه", "ar", "كتاب", id="ar-enclitic-hu"),
    pytest.param("كتابها", "ar", "كتاب", id="ar-enclitic-ha"),
    pytest.param("كتابهم", "ar", "كتاب", id="ar-enclitic-hum"),
    # ك excluded: it collides with root-final letters
    pytest.param("كتابك", "ar", None, id="ar-enclitic-kaf-excluded"),
    # MIN_STEM_LEN=4 rejects the 3-letter stem
    pytest.param("بيته", "ar", None, id="ar-enclitic-short-stem"),
    pytest.param("كِتَابُهُ", "ar", "كتاب", id="ar-enclitic-vocalized"),
]


@pytest.mark.parametrize("token, lang, expected", _CLITIC_CASES)
def test_clitic_decomposition(token: str, lang: str, expected: str | None) -> None:
    assert _CLITIC.get_lemma(token, lang) == expected


_PREFIX_CASES = [
    pytest.param("Відкликала", "uk", None, id="attached-prefix-case-sensitive"),
    pytest.param("l'arbre", "fr", "arbre", id="proclitic-fr-arbre"),
    pytest.param("qu'avait", "fr", "avoir", id="proclitic-fr-avoir"),
    pytest.param("jusqu'alors", "fr", "alors", id="proclitic-fr-alors"),
    pytest.param("quest'anno", "it", "anno", id="proclitic-it-anno"),
    pytest.param("nell'aula", "it", "aula", id="proclitic-it-aula"),
    pytest.param("l'home", "ca", "home", id="proclitic-ca-home"),
    pytest.param("l'arbre", "de", None, id="proclitic-unsupported-lang"),
    pytest.param("c'est", "fr", "être", id="proclitic-fr-cest"),
    pytest.param("j'ai", "fr", "avoir", id="proclitic-fr-jai"),
    pytest.param("qu'il", "fr", "il", id="proclitic-fr-quil"),
    pytest.param("L'arbre", "fr", "arbre", id="proclitic-guard-lowercase-stem"),
    pytest.param("D'Annunzio", "it", None, id="proclitic-guard-capitalized-stem"),
    pytest.param("aujourd'hui", "fr", None, id="proclitic-guard-no-prefix-match"),
]


@pytest.mark.parametrize("token, lang, expected", _PREFIX_CASES)
def test_prefix_decomposition_drop_langs(
    token: str, lang: str, expected: str | None
) -> None:
    assert _PREFIX.get_lemma(token, lang) == expected


def test_apostrophe_boundary() -> None:
    """A Turkish apostrophe splits a proper noun from its suffixes."""
    strat = DefaultStrategy()
    assert strat.get_lemma("İstanbul'da", "tr") == "İstanbul"
    assert strat.get_lemma("Erdoğan'ın", "tr") == "Erdoğan"
    assert strat.get_lemma("1991'de", "tr") == "1991"
    assert strat.get_lemma("Erdoğan’ın", "tr") == "Erdoğan"
    # a whole-token dict entry beats boundary splitting (head would be "i")
    assert _LOOKUP.is_dictionary_member("isen'e", "tr")
    assert strat._apostrophe_lemma("isen'e", "tr") is None
    assert strat.get_lemma("isen'e", "tr") == "isen"
    assert strat._apostrophe_lemma("l'arbre", "fr") is None


def test_dictionary_lookup_apostrophe_variant() -> None:
    """Straight, curly and modifier apostrophes all reach a straight-keyed entry."""
    for glyph in ("’", "ʼ", "'"):
        assert lemmatize(f"виб{glyph}єш", lang="uk") == "вибити"
        assert lemmatize(f"don{glyph}t", lang="en") == "do"
        assert lemmatize(f"l{glyph}arbre", lang="fr") == "arbre"
    assert lemmatize("un’", lang="it") == "uno"
    assert _LOOKUP.get_lemma("Vaa'assa", "fi") == "vaaka"


def test_dictionary_lookup_grc_accent_canon() -> None:
    """grc grave queries hit acute keys. Other languages are not folded."""
    mapping = {"δέ": "δέ", "garā": "gara"}
    lookup = DictionaryLookupStrategy(dictionary_factory=FixedMapping(mapping))
    assert lookup.get_lemma("δὲ", "grc") == "δέ"
    assert lookup.get_lemma("garā", "lv") == "gara"
    assert lookup.is_dictionary_member("δὲ", "grc")


def test_dictionary_lookup_he_niqqud_canon() -> None:
    """he pointed queries hit unpointed keys. Other languages are not folded."""
    mapping = {"בית": "בית"}
    lookup = DictionaryLookupStrategy(dictionary_factory=FixedMapping(mapping))
    assert lookup.get_lemma("בַּיִת", "he") == "בית"
    assert lookup.get_lemma("בַּיִת", "ar") is None


def test_prefix_decomposition_drops_particle_for_drop_prefix_langs() -> None:
    """he prefixes are particles, so only the stem's lemma is returned."""
    import re

    strategy = PrefixDecompositionStrategy(
        known_prefixes={"he": re.compile("^(ב)")},
        dictionary_lookup=DictionaryLookupStrategy(
            dictionary_factory=FixedMapping({"בית": "בית"})
        ),
    )
    assert strategy.get_lemma("בבית", "he") == "בית"


def test_morphemes_sorts_affixes_longest_first_regardless_of_input_order() -> None:
    """A shorter affix listed first must not shadow a longer one."""
    m = _morphemes("a aba", "n wan")
    assert m.prefixes == ("aba", "a")
    assert m.suffixes == ("wan", "n")


def test_morpheme_decomposition_tagalog_prefixes_and_ability_forms() -> None:
    """Actor and ability focus prefixes are discarded entirely."""
    assert _MORPHEME.get_lemma("nagbasa", "tl") == "basa"  # mag-/nag- actor focus
    assert _MORPHEME.get_lemma("magkakatrabaho", "tl") == "trabaho"  # distributive
    assert _MORPHEME.get_lemma("maulit", "tl") == "ulit"  # ma- stative


def test_morpheme_decomposition_tagalog_infix() -> None:
    """-um-/-in- infixes attach after the root's onset consonant."""
    assert _MORPHEME.get_lemma("tumakbo", "tl") == "takbo"
    assert _MORPHEME.get_lemma("binasa", "tl") == "basa"
    # vowel-initial root: -um- acts as a plain prefix
    assert _MORPHEME.get_lemma("umalis", "tl") == "alis"


def test_morpheme_decomposition_tagalog_reduplication() -> None:
    """Aspect reduplication. Deepest decomposition wins over the wrong entry "iiwas"."""
    assert _MORPHEME.get_lemma("maiiwasan", "tl") == "iwas"  # ma-i-REDUP(i)-was-an


def test_morpheme_decomposition_capitalized_token() -> None:
    """Affixes match on the lowercased form, so capitalized verbs still resolve."""
    assert _MORPHEME.get_lemma("Nagbasa", "tl") == "basa"
    assert _MORPHEME.get_lemma("Tumakbo", "tl") == "takbo"


def test_morpheme_decomposition_guards() -> None:
    """Unconfigured languages and unresolvable residues return None."""
    assert _MORPHEME.get_lemma("maiiwasan", "en") is None
    assert _MORPHEME.get_lemma("zzzznagzzzzz", "tl") is None


def test_morpheme_decomposition_infix_and_reduplication_respect_min_stem_len() -> None:
    """No strip may leave a residue under MIN_STEM_LEN, even a real entry."""
    morpheme = MorphemeDecompositionStrategy(
        dictionary_lookup=DictionaryLookupStrategy(
            dictionary_factory=FixedMapping({"to": "to", "ab": "ab"})
        )
    )
    # stripping -um- leaves "to", under the floor
    assert morpheme.get_lemma("tumo", "tl") is None
    # the reduplication fold leaves "ab", under the floor
    assert morpheme.get_lemma("aab", "tl") is None


def test_morpheme_decomposition_indonesian_prefix_and_suffix() -> None:
    """Indonesian verbs combine a prefix and a suffix."""
    assert _MORPHEME.get_lemma("ditingkatkan", "id") == "tingkat"  # di- + -kan
    assert _MORPHEME.get_lemma("berdasarkan", "id") == "dasar"  # ber- + -kan
    assert _MORPHEME.get_lemma("menceritakan", "id") == "cerita"  # men- + -kan


def test_morpheme_decomposition_indonesian_conservative_config() -> None:
    """Bare me, ke, se and pe prefixes overfire and are excluded."""
    # me- + "lihat" (a real root) would resolve only with bare "me" configured
    assert _MORPHEME.get_lemma("melihat", "id") is None


def test_dictionary_lookup_apostrophe_variant_recased() -> None:
    """A curly lowercase query finds a straight capitalized key."""
    mapping = {"L'eau": "eau"}
    lookup = DictionaryLookupStrategy(dictionary_factory=FixedMapping(mapping))
    assert lookup.get_lemma(normalize_token("l’eau"), "xx") == "eau"
