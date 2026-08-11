import pytest

from simplemma.strategies import (
    AffixDecompositionStrategy,
    ApostropheBoundaryStrategy,
    CliticDecompositionStrategy,
    DefaultStrategy,
    DictionaryLookupStrategy,
    GreedyDictionaryLookupStrategy,
    HyphenRemovalStrategy,
    MorphemeDecompositionStrategy,
    PrefixDecompositionStrategy,
)
from simplemma.strategies.greedy_dictionary_lookup import greedy_min_length
from simplemma.strategies.morpheme_decomposition import _Morphemes
from tests.conftest import FixedMapping

_LOOKUP = DictionaryLookupStrategy()
_CLITIC = CliticDecompositionStrategy()
_MORPHEME = MorphemeDecompositionStrategy()


def test_search() -> None:
    """Test simple and greedy dict search."""
    assert _LOOKUP.get_lemma("ignorant", "en") == "ignorant"
    assert _LOOKUP.get_lemma("Ignorant", "en") == "ignorant"

    assert _LOOKUP.get_lemma("dritte", "de") == "dritt"
    assert _LOOKUP.get_lemma("Dritte", "de") == "Dritter"
    # empty token must not crash the case-flip retry
    assert _LOOKUP.get_lemma("", "en") is None

    assert HyphenRemovalStrategy().get_lemma("magni-ficent", "en") == "magnificent"
    assert HyphenRemovalStrategy().get_lemma("magni-ficents", "en") is None
    assert HyphenRemovalStrategy().get_lemma("magni-", "en") is None

    # don't lemmatize numbers
    assert DefaultStrategy().get_lemma("01234", "en") == "01234"

    assert DefaultStrategy().get_lemma("Gender-Sternchens", "de") == "Gender-Sternchen"
    assert DefaultStrategy().get_lemma("vor-bereitetes", "de") == "vorbereitet"

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
    # canonicalize_token must apply here too, not just in DictionaryLookupStrategy,
    # so a vocalized token resolves even when this strategy runs standalone.
    assert GreedyDictionaryLookupStrategy().get_lemma("آذربايجانَ", "ar") == "أذربيجان"

    assert PrefixDecompositionStrategy().get_lemma("auf", "de") is None


@pytest.mark.parametrize(
    ("lang", "greedy", "token", "expected"),
    [
        # greedy mode: multi-character affixes
        ("fi", True, "kissammeko", "kissa"),  # "and our cat?" -> cat
        ("hu", True, "könyveiteket", "könyv"),  # "your books" -> book
        ("et", True, "raamatutest", "raamat"),  # "from books" -> book
        # UD-validated AFFIX_LANGS members, non-greedy mode
        ("da", False, "drabsdagen", "drabsdag"),
        ("da", False, "menighedsrådsvalget", "menighedsrådsvalg"),
        ("nn", False, "pastasalaten", "pastasalat"),
        # WD fill added standalone "ane" (a real nn verb), which wins this
        # word's affix-only split; the full pipeline still resolves it
        # correctly via dictionary_lookup (locked by
        # test_lemmatizer.py::test_nn_fill_full_pipeline).
        ("nn", False, "underleverandørane", "underleverandørane"),
        # es re-admitted on UD v2.18 (old es_gsd PROPN-convention artifact fixed)
        ("es", False, "microrregiones", "microrregión"),
        ("es", False, "estanquillas", "estanquilla"),
        # lt's entry gate is lowered to 7, admitting these 8-char forms
        ("lt", False, "rengiami", "rengti"),
        ("lt", False, "teikiant", "teikti"),
        # None: gated-out languages and unresolvable forms
        # laudkonna's stem is now a fill entry; aadelkond is the stable canary instead
        ("et", True, "aadelkond", None),
        ("sw", True, "-changanya", None),  # GREEDY_EXCLUDE: prefixing/mutating
        ("pt", True, "supostamente", None),
        ("gl", True, "virtualmente", None),
        ("de", True, "ccc", None),  # nothing decomposes
    ],
)
def test_affix_decomposition(
    lang: str, greedy: bool, token: str, expected: str | None
) -> None:
    """get_lemma resolves inflected forms to their lemma, or returns None for
    gated-out languages and unresolvable forms."""
    assert AffixDecompositionStrategy(greedy=greedy).get_lemma(token, lang) == expected


def test_affix_decomposition_guards() -> None:
    """Entry gate (shared with GreedyDictionaryLookupStrategy), not the
    sub-strategy, excludes a language (`_suffix_decomposition` still fires for
    sw); plus the MAXLEN cap. The 100k-char token stays out of parametrize --
    its node id would overflow Windows' 32767-char env-var limit."""
    affix = AffixDecompositionStrategy(greedy=True)
    assert greedy_min_length("lt") == 7  # lowered from the default
    assert greedy_min_length("bg") == 6
    assert greedy_min_length("xx") == 8
    assert affix._suffix_decomposition("-changanya", "sw", 4) is not None
    assert affix.get_lemma("a" * 101, "fi") is None
    assert affix.get_lemma("a" * 100000, "fi") is None


def test_clitic_decomposition_skips_diacritic_fold_for_canon_languages() -> None:
    """strip_diacritics is a blind NFD combining-mark strip built for Romance
    stress accents; for ar (a _CANON_TABLES language) it also decomposes
    hamza letters, which can land on a real but UNRELATED dictionary entry.
    A _CANON_TABLES language must skip that retry, not fire it."""

    # Only the hamza-decomposed form is a (deliberately unrelated) dict
    # entry; the correctly-spelled stem itself is absent.
    clitic = CliticDecompositionStrategy(
        dictionary_lookup=DictionaryLookupStrategy(
            dictionary_factory=FixedMapping({"مومن": "أيمن"})
        )
    )
    # "مؤمنه" ("مؤمن" + the "ه" enclitic) must NOT resolve to "أيمن" via the
    # fold -- it must fail cleanly (None) since the correctly-spelled stem
    # isn't a real dictionary entry here.
    assert clitic.get_lemma("مؤمنه", "ar") is None


# (token, lang, expected): clitic decomposition through the shared architecture.
# Enclitics strip to the bare verb/noun lemma (no reattachment); proclitics
# strip from the front (elision before vowel-initial words).
_CLITIC_CASES = [
    # --- enclitics: pronoun chains strip to the bare verb lemma ---
    pytest.param("transmitiéndose", "es", "transmitir", id="enclitic-es-transmitir"),
    pytest.param("encontrarlo", "es", "encontrar", id="enclitic-es-encontrar"),
    pytest.param("aprova-se", "pt", "aprovar", id="enclitic-pt-aprovar"),
    pytest.param("mobilitzar-se", "ca", "mobilitzar", id="enclitic-ca-mobilitzar"),
    pytest.param("mettersi", "it", "mettere", id="enclitic-it-mettere"),
    pytest.param("sitúanse", "gl", "situar", id="enclitic-gl-situar"),
    pytest.param("transmitiéndose", "de", None, id="enclitic-unsupported-lang"),
    # --- enclitic guards: capitalized/short-stem/unresolvable → None ---
    pytest.param("Paulo", "pt", None, id="guard-capitalized-paulo"),
    pytest.param("tê-lo", "pt", None, id="guard-short-stem-telo"),
    pytest.param("fer-ho", "ca", None, id="guard-short-stem-ferho"),
    pytest.param("zzzzzzselo", "es", None, id="guard-no-dict-hit"),
    # pt/ca strip only a hyphenated clitic: a bare strip would mangle these
    pytest.param("paulo", "pt", None, id="guard-bare-strip-paulo"),
    pytest.param("carona", "pt", None, id="guard-bare-strip-carona"),
    pytest.param("alumne", "ca", None, id="guard-bare-strip-alumne"),
    # --- English contractions: same enclitic architecture ---
    pytest.param("don't", "en", "do", id="en-dont"),
    pytest.param("don’t", "en", "do", id="en-curly-dont"),
    pytest.param("Don't", "en", "do", id="en-sentence-initial-Dont"),
    pytest.param("I'm", "en", "I", id="en-Im"),
    pytest.param("you're", "en", "you", id="en-youre"),
    pytest.param("isn't", "en", "be", id="en-isnt"),
    # "'s"/"'d" are multi-valued clitics; the stem lemma isn't
    pytest.param("it's", "en", "it", id="en-its"),
    pytest.param("company's", "en", "company", id="en-companys"),
    pytest.param("he'd", "en", "he", id="en-hed"),
    # can't/won't: "can" is the only English modal ending in "n", so
    # stripping "n't" would leave "ca" (a real, wrong entry) — excluded
    pytest.param("can't", "en", None, id="en-cant-excluded"),
    pytest.param("won't", "en", None, id="en-wont-excluded"),
    # --- proclitics: elision before a vowel-initial word ---
    pytest.param("l'arbre", "fr", "arbre", id="proclitic-fr-arbre"),
    pytest.param("qu'avait", "fr", "avoir", id="proclitic-fr-avoir"),
    pytest.param("jusqu'alors", "fr", "alors", id="proclitic-fr-alors"),
    pytest.param("l’arbre", "fr", "arbre", id="proclitic-fr-curly"),
    pytest.param("quest'anno", "it", "anno", id="proclitic-it-anno"),
    pytest.param("nell'aula", "it", "aula", id="proclitic-it-aula"),
    pytest.param("l'home", "ca", "home", id="proclitic-ca-home"),
    pytest.param("l'arbre", "de", None, id="proclitic-unsupported-lang"),
    # PROCLITIC_MIN_STEM_LEN=1: short remainders are structurally always
    # elision in these orthographies
    pytest.param("c'est", "fr", "être", id="proclitic-fr-cest"),
    pytest.param("j'ai", "fr", "avoir", id="proclitic-fr-jai"),
    pytest.param("qu'il", "fr", "il", id="proclitic-fr-quil"),
    # --- proclitic guards: capitalized stem = surname, no strip ---
    pytest.param("L'arbre", "fr", "arbre", id="proclitic-guard-lowercase-stem"),
    pytest.param("D'Annunzio", "it", None, id="proclitic-guard-capitalized-stem"),
    pytest.param("aujourd'hui", "fr", None, id="proclitic-guard-no-prefix-match"),
    # --- Arabic enclitic pronouns: same drop-not-reattach shape ---
    pytest.param("كتابه", "ar", "كتاب", id="ar-enclitic-hu"),
    pytest.param("كتابها", "ar", "كتاب", id="ar-enclitic-ha"),
    pytest.param("كتابهم", "ar", "كتاب", id="ar-enclitic-hum"),
    # ك excluded (measured net-negative: collides with root-final letters)
    pytest.param("كتابك", "ar", None, id="ar-enclitic-kaf-excluded"),
    # MIN_STEM_LEN=4: a 3-letter stem is rejected
    pytest.param("بيته", "ar", None, id="ar-enclitic-short-stem"),
    pytest.param("كِتَابُهُ", "ar", "كتاب", id="ar-enclitic-vocalized"),
]


@pytest.mark.parametrize("token, lang, expected", _CLITIC_CASES)
def test_clitic_decomposition(token: str, lang: str, expected: str | None) -> None:
    assert _CLITIC.get_lemma(token, lang) == expected


def test_apostrophe_boundary() -> None:
    """Turkish marks a fixed proper-noun/suffix boundary with an
    apostrophe; the head is lemmatized via the full pipeline."""
    strat = DefaultStrategy()
    assert strat.get_lemma("İstanbul'da", "tr") == "İstanbul"
    assert strat.get_lemma("Erdoğan'ın", "tr") == "Erdoğan"
    # curly apostrophes (smart quotes) mark the same boundary
    assert strat.get_lemma("Erdoğan’ın", "tr") == "Erdoğan"
    # a curated whole-token dict entry is authoritative: boundary splitting
    # defers so dictionary lookup wins ("isen'e" -> "isen", not head "i").
    assert _LOOKUP.exact_lemma("isen'e", "tr") == "isen"
    assert (
        ApostropheBoundaryStrategy(strat.get_lemma, _LOOKUP).get_lemma("isen'e", "tr")
        is None
    )
    assert strat.get_lemma("isen'e", "tr") == "isen"
    # unsupported language: no-op
    assert (
        ApostropheBoundaryStrategy(strat.get_lemma, _LOOKUP).get_lemma("l'arbre", "fr")
        is None
    )


def test_dictionary_lookup_apostrophe_variant() -> None:
    """A key stored under another apostrophe variant (straight ', curly U+2019,
    modifier-letter U+02BC -- NFC does not unify them) is still found."""
    assert _LOOKUP.get_lemma("виб’єш", "uk") == "вибити"  # curly
    assert _LOOKUP.get_lemma("вибʼєш", "uk") == "вибити"  # U+02BC (Ukrainian)
    assert _LOOKUP.get_lemma("виб'єш", "uk") == "вибити"  # straight
    assert _LOOKUP.get_lemma("un’", "it") == "uno"
    # Probe order preserved across variants: this glyph-mixed fi entry keeps
    # its straight-variant answer.
    assert _LOOKUP.get_lemma("Vaa'assa", "fi") == "vaaka"


def test_dictionary_lookup_grc_accent_canon() -> None:
    """grc: a positional-grave query resolves against an acute-keyed dict
    (the form dictionary_builder ships); other languages are untouched."""

    # grc acute key; lv macron key
    mapping = {"δέ": "δέ", "garā": "gara"}
    lookup = DictionaryLookupStrategy(dictionary_factory=FixedMapping(mapping))
    assert lookup.get_lemma("δὲ", "grc") == "δέ"  # grave query -> acute key
    assert lookup.get_lemma("garā", "lv") == "gara"  # unrelated: no fold applied
    assert lookup.is_dictionary_member("δὲ", "grc")
    assert lookup.exact_lemma("δὲ", "grc") == "δέ"


def test_dictionary_lookup_he_niqqud_canon() -> None:
    """he: a pointed query resolves against an unpointed-keyed dict (the form
    dictionary_builder ships); other languages are untouched."""

    mapping = {"בית": "בית"}  # unpointed key
    lookup = DictionaryLookupStrategy(dictionary_factory=FixedMapping(mapping))
    assert lookup.get_lemma("בַּיִת", "he") == "בית"  # pointed query -> unpointed key
    assert lookup.get_lemma("בַּיִת", "ar") is None  # unrelated: no fold applied


def test_prefix_decomposition_drops_particle_for_drop_prefix_langs() -> None:
    """he (DROP_PREFIX_LANGS): the matched prefix is its own grammatical
    particle, not part of the stem's lemma, so only the stem's lemma is
    returned -- unlike de/ru/uk, where the prefix stays attached (see
    test_prefixes_basic.py)."""
    import re

    strategy = PrefixDecompositionStrategy(
        known_prefixes={"he": re.compile("^(ב)")},
        dictionary_lookup=DictionaryLookupStrategy(
            dictionary_factory=FixedMapping({"בית": "בית"})
        ),
    )
    assert strategy.get_lemma("בבית", "he") == "בית"  # prefix dropped, not "בבית"


def test_morphemes_sorts_affixes_longest_first_regardless_of_input_order() -> None:
    """_Morphemes.__post_init__ sorts every field so a config literal never
    has to be pre-sorted -- a shorter prefix listed BEFORE a longer one it's
    a prefix of must not shadow the longer, correct match."""
    m = _Morphemes(prefixes=("a", "aba"), suffixes=("n", "wan"))
    assert m.prefixes == ("aba", "a")
    assert m.suffixes == ("wan", "n")


def test_morpheme_decomposition_tagalog_prefixes_and_ability_forms() -> None:
    """Actor/ability-focus prefixes are discarded entirely (unlike
    PrefixDecompositionStrategy, which keeps a derivational prefix)."""
    assert _MORPHEME.get_lemma("nagbasa", "tl") == "basa"  # mag-/nag- actor focus
    assert _MORPHEME.get_lemma("magkakatrabaho", "tl") == "trabaho"  # distributive
    assert _MORPHEME.get_lemma("maulit", "tl") == "ulit"  # ma- stative


def test_morpheme_decomposition_tagalog_infix() -> None:
    """-um-/-in- infixes attach after the root's onset consonant."""
    assert _MORPHEME.get_lemma("tumakbo", "tl") == "takbo"  # -um- infix
    assert _MORPHEME.get_lemma("binasa", "tl") == "basa"  # -in- infix
    assert _MORPHEME.get_lemma("umalis", "tl") == "alis"  # -um- as a plain
    # prefix when the root is vowel-initial (no onset consonant to infix after)


def test_morpheme_decomposition_tagalog_reduplication() -> None:
    """Aspect reduplication of the root's first syllable. Also locks the
    deepest-decomposition order: "maiiwasan" hit "iiwas" (a real but wrong
    entry) before reaching "iwas" when candidates were tried shallowest-first.
    (A further vowel-alternation stage -- gusto+han -> gustuhan, folding u->o
    back -- was measured at <=0.3pp on one treebank with no verdict change and
    removed: not worth a config dimension.)"""
    assert _MORPHEME.get_lemma("maiiwasan", "tl") == "iwas"  # ma-i-REDUP(i)-was-an


def test_morpheme_decomposition_capitalized_token() -> None:
    """A sentence-initial capitalized verb still resolves -- affix matching
    works on the lowercased form, and the dictionary lemma is lowercase."""
    assert _MORPHEME.get_lemma("Nagbasa", "tl") == "basa"
    assert _MORPHEME.get_lemma("Tumakbo", "tl") == "takbo"


def test_morpheme_decomposition_guards() -> None:
    """Unconfigured languages and unresolvable residues return None."""
    assert _MORPHEME.get_lemma("maiiwasan", "en") is None  # not a configured lang
    assert _MORPHEME.get_lemma("zzzznagzzzzz", "tl") is None  # no dict hit at all


def test_morpheme_decomposition_infix_and_reduplication_respect_min_stem_len() -> None:
    """An infix/reduplication strip that would leave a residue under
    MIN_STEM_LEN must not fire, even if that short residue is coincidentally
    a real dictionary entry -- same floor the prefix/suffix strippers apply."""

    morpheme = MorphemeDecompositionStrategy(
        dictionary_lookup=DictionaryLookupStrategy(
            dictionary_factory=FixedMapping({"to": "to", "ab": "ab"})
        )
    )
    # "tumo" -um-> stripped would leave "to" (2 chars, under the floor)
    assert morpheme.get_lemma("tumo", "tl") is None
    # "aab" reduplication-folded would leave "ab" (2 chars, under the floor)
    assert morpheme.get_lemma("aab", "tl") is None


def test_morpheme_decomposition_indonesian_prefix_and_suffix() -> None:
    """Indonesian verbal affixes are compositional (prefix + suffix together);
    a single-strip mechanism (PrefixDecompositionStrategy) can't reach these."""
    assert _MORPHEME.get_lemma("ditingkatkan", "id") == "tingkat"  # di- + -kan
    assert _MORPHEME.get_lemma("berdasarkan", "id") == "dasar"  # ber- + -kan
    assert _MORPHEME.get_lemma("menceritakan", "id") == "cerita"  # men- + -kan


def test_morpheme_decomposition_indonesian_conservative_config() -> None:
    """Short/ambiguous prefixes (bare me/ke/se/pe, without their
    consonant-initial variants) were measured to overfire and are
    deliberately excluded -- only the longer, unambiguous forms ship."""
    # "melihat" = me- (no epenthetic consonant) + "lihat" (a real dict root) --
    # would resolve if bare "me" were configured, but it isn't.
    assert _MORPHEME.get_lemma("melihat", "id") is None


def test_dictionary_lookup_apostrophe_variant_recased() -> None:
    """A key stored capitalized under a different apostrophe glyph is found via
    the variant + reverse-case fallback (curly, lowercased input -> straight,
    capitalized key)."""

    mapping = {"L'eau": "eau"}  # straight apostrophe, capitalized
    lookup = DictionaryLookupStrategy(dictionary_factory=FixedMapping(mapping))
    assert lookup.get_lemma("l’eau", "xx") == "eau"  # curly, lowercase
