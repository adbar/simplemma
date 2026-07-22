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


def test_search() -> None:
    """Test simple and greedy dict search."""
    assert DictionaryLookupStrategy().get_lemma("ignorant", "en") == "ignorant"
    assert DictionaryLookupStrategy().get_lemma("Ignorant", "en") == "ignorant"

    assert DictionaryLookupStrategy().get_lemma("dritte", "de") == "dritt"
    assert DictionaryLookupStrategy().get_lemma("Dritte", "de") == "Dritter"
    # empty token must not crash the case-flip retry
    assert DictionaryLookupStrategy().get_lemma("", "en") is None

    assert HyphenRemovalStrategy().get_lemma("magni-ficent", "en") == "magnificent"
    assert HyphenRemovalStrategy().get_lemma("magni-ficents", "en") is None
    assert HyphenRemovalStrategy().get_lemma("magni-", "en") is None

    # assert simplemma.simplemma._greedy_dictionary_lookup('Ignorance-Tests') == 'Ignorance-Test'
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


def test_clitic_decomposition() -> None:
    """Enclitic pronoun chains strip to the bare verb lemma, no reattachment."""
    clitic = CliticDecompositionStrategy()
    assert clitic.get_lemma("transmitiéndose", "es") == "transmitir"
    assert clitic.get_lemma("encontrarlo", "es") == "encontrar"
    assert clitic.get_lemma("aprova-se", "pt") == "aprovar"
    assert clitic.get_lemma("mobilitzar-se", "ca") == "mobilitzar"
    assert clitic.get_lemma("mettersi", "it") == "mettere"
    assert clitic.get_lemma("sitúanse", "gl") == "situar"
    # unsupported language
    assert clitic.get_lemma("transmitiéndose", "de") is None


def test_clitic_decomposition_guards() -> None:
    """Capitalized-initial tokens (proper nouns) and stems under the
    length floor are rejected, not decomposed."""
    clitic = CliticDecompositionStrategy()
    assert clitic.get_lemma("Paulo", "pt") is None  # would otherwise fabricate "paul"
    assert clitic.get_lemma("tê-lo", "pt") is None  # "ter" is under the stem floor
    assert clitic.get_lemma("fer-ho", "ca") is None  # "fer" is under the stem floor
    # MAX_CLITICS strips succeed but no stem ever verifies in the dictionary
    assert clitic.get_lemma("zzzzzzselo", "es") is None
    # pt/ca strip only a hyphenated clitic: a bare strip would mangle these
    assert clitic.get_lemma("paulo", "pt") is None  # not "paul"
    assert clitic.get_lemma("carona", "pt") is None  # not "caro"
    assert clitic.get_lemma("alumne", "ca") is None  # not "alumar"


def test_clitic_decomposition_english_contractions() -> None:
    """English auxiliary contractions use the same enclitic architecture
    (a per-language stem floor and case guard, not new code)."""
    clitic = CliticDecompositionStrategy()
    assert clitic.get_lemma("don't", "en") == "do"
    assert clitic.get_lemma("don’t", "en") == "do"  # curly apostrophe (smart quotes)
    assert (
        clitic.get_lemma("Don't", "en") == "do"
    )  # sentence-initial, not a proper noun
    assert clitic.get_lemma("I'm", "en") == "I"
    assert clitic.get_lemma("you're", "en") == "you"
    assert clitic.get_lemma("isn't", "en") == "be"
    # "'s"/"'d" are multi-valued clitics; the stem lemma isn't
    assert clitic.get_lemma("it's", "en") == "it"
    assert clitic.get_lemma("company's", "en") == "company"
    assert clitic.get_lemma("he'd", "en") == "he"
    # can't/won't/shan't are irregular exceptions: "can" is the only
    # English modal ending in "n", so stripping "n't" would leave "ca"
    # (itself a real, wrong dictionary entry) -- excluded, not mapped wrong.
    assert clitic.get_lemma("can't", "en") is None
    assert clitic.get_lemma("won't", "en") is None


def test_clitic_decomposition_proclitics() -> None:
    """Romance proclitics (elision before a vowel-initial word) strip from
    the front; only the following content word's lemma is ever returned,
    never the elided article/pronoun/conjunction's own (sidesteps their
    genuine article-vs-pronoun / soi-vs-si ambiguity entirely)."""
    clitic = CliticDecompositionStrategy()
    assert clitic.get_lemma("l'arbre", "fr") == "arbre"
    assert clitic.get_lemma("qu'avait", "fr") == "avoir"
    assert clitic.get_lemma("jusqu'alors", "fr") == "alors"
    assert clitic.get_lemma("l’arbre", "fr") == "arbre"  # curly apostrophe
    assert clitic.get_lemma("quest'anno", "it") == "anno"
    assert (
        clitic.get_lemma("nell'aula", "it") == "aula"
    )  # contracted preposition+article
    assert clitic.get_lemma("l'home", "ca") == "home"
    # unsupported language for the proclitic table
    assert clitic.get_lemma("l'arbre", "de") is None
    # PROCLITIC_MIN_STEM_LEN=1: a 1-3 letter remainder after an
    # apostrophe is structurally almost never anything but elision in
    # these orthographies (unlike a bare short stem), so the floor is
    # much lower than the enclitic side's -- these are some of the
    # highest-frequency apostrophe tokens in French and were previously
    # unreachable at floor=4.
    assert clitic.get_lemma("c'est", "fr") == "être"
    assert clitic.get_lemma("j'ai", "fr") == "avoir"
    assert clitic.get_lemma("qu'il", "fr") == "il"


def test_clitic_decomposition_proclitic_guards() -> None:
    """A sentence-initial capital on the proclitic still strips when the
    stem stays lowercase ("L'arbre" -> "arbre"), but a capitalized stem
    signals a surname where stripping is wrong -- "D'Annunzio" (a real
    Italian surname) must not strip to the unrelated verb "annunziare"."""
    clitic = CliticDecompositionStrategy()
    assert clitic.get_lemma("L'arbre", "fr") == "arbre"
    assert clitic.get_lemma("D'Annunzio", "it") is None
    # apostrophe present but no proclitic matches the prefix: no strip
    assert clitic.get_lemma("aujourd'hui", "fr") is None


def test_clitic_decomposition_ar_enclitic_pronouns() -> None:
    """Arabic possessive/object pronoun suffixes strip to the bare noun/verb
    lemma, same drop-not-reattach shape as Romance enclitics. ك/ي are
    deliberately NOT in CLITIC_LANGS["ar"] -- measured net-negative (collide
    with native root-final letters/nisba endings), so "كتابك" must not strip."""
    clitic = CliticDecompositionStrategy()
    assert clitic.get_lemma("كتابه", "ar") == "كتاب"
    assert clitic.get_lemma("كتابها", "ar") == "كتاب"
    assert clitic.get_lemma("كتابهم", "ar") == "كتاب"
    assert clitic.get_lemma("كتابك", "ar") is None  # ك excluded: no strip attempted
    # MIN_STEM_LEN=4 (the shared default, no ar override needed): a 3-letter
    # stem is rejected, matching every other enclitic language's floor.
    assert clitic.get_lemma("بيته", "ar") is None  # "بيت" is under the stem floor
    assert clitic.get_lemma("كِتَابُهُ", "ar") == "كتاب"  # vocalized: folded first


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
    lookup = DictionaryLookupStrategy()
    assert lookup.exact_lemma("isen'e", "tr") == "isen"
    assert (
        ApostropheBoundaryStrategy(strat.get_lemma, lookup).get_lemma("isen'e", "tr")
        is None
    )
    assert strat.get_lemma("isen'e", "tr") == "isen"
    # unsupported language: no-op
    assert (
        ApostropheBoundaryStrategy(
            strat.get_lemma, DictionaryLookupStrategy()
        ).get_lemma("l'arbre", "fr")
        is None
    )


def test_dictionary_lookup_apostrophe_variant() -> None:
    """A key stored under another apostrophe variant (straight ', curly U+2019,
    modifier-letter U+02BC -- NFC does not unify them) is still found."""
    lookup = DictionaryLookupStrategy()
    assert lookup.get_lemma("виб’єш", "uk") == "вибити"  # curly
    assert lookup.get_lemma("вибʼєш", "uk") == "вибити"  # U+02BC (Ukrainian)
    assert lookup.get_lemma("виб'єш", "uk") == "вибити"  # straight
    assert lookup.get_lemma("un’", "it") == "uno"
    # Probe order preserved across variants: this glyph-mixed fi entry keeps
    # its straight-variant answer.
    assert lookup.get_lemma("Vaa'assa", "fi") == "vaaka"


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
    morpheme = MorphemeDecompositionStrategy()
    assert morpheme.get_lemma("nagbasa", "tl") == "basa"  # mag-/nag- actor focus
    assert morpheme.get_lemma("magkakatrabaho", "tl") == "trabaho"  # distributive
    assert morpheme.get_lemma("maulit", "tl") == "ulit"  # ma- stative


def test_morpheme_decomposition_tagalog_infix() -> None:
    """-um-/-in- infixes attach after the root's onset consonant."""
    morpheme = MorphemeDecompositionStrategy()
    assert morpheme.get_lemma("tumakbo", "tl") == "takbo"  # -um- infix
    assert morpheme.get_lemma("binasa", "tl") == "basa"  # -in- infix
    assert morpheme.get_lemma("umalis", "tl") == "alis"  # -um- as a plain
    # prefix when the root is vowel-initial (no onset consonant to infix after)


def test_morpheme_decomposition_tagalog_reduplication() -> None:
    """Aspect reduplication of the root's first syllable. (A further
    vowel-alternation stage -- gusto+han -> gustuhan, folding u->o back --
    was measured at <=0.3pp on one treebank with no verdict change and
    removed: not worth a config dimension.)"""
    morpheme = MorphemeDecompositionStrategy()
    assert morpheme.get_lemma("maiiwasan", "tl") == "iwas"  # ma-i-REDUP(i)-was-an


def test_morpheme_decomposition_capitalized_token() -> None:
    """A sentence-initial capitalized verb still resolves -- affix matching
    works on the lowercased form, and the dictionary lemma is lowercase."""
    morpheme = MorphemeDecompositionStrategy()
    assert morpheme.get_lemma("Nagbasa", "tl") == "basa"
    assert morpheme.get_lemma("Tumakbo", "tl") == "takbo"


def test_morpheme_decomposition_prefers_deepest_decomposition() -> None:
    """A shallower residue that happens to ALSO be a real (unrelated) dict
    entry must not win over the correctly fully-decomposed root -- measured
    regression: "maiiwasan" hit "iiwas" (a real but wrong entry) before
    reaching "iwas" when candidates were tried shallowest-first."""
    morpheme = MorphemeDecompositionStrategy()
    assert morpheme.get_lemma("maiiwasan", "tl") == "iwas"


def test_morpheme_decomposition_guards() -> None:
    """Unconfigured languages and unresolvable residues return None."""
    morpheme = MorphemeDecompositionStrategy()
    assert morpheme.get_lemma("maiiwasan", "en") is None  # not a configured lang
    assert morpheme.get_lemma("zzzznagzzzzz", "tl") is None  # no dict hit at all


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
    morpheme = MorphemeDecompositionStrategy()
    assert morpheme.get_lemma("ditingkatkan", "id") == "tingkat"  # di- + -kan
    assert morpheme.get_lemma("berdasarkan", "id") == "dasar"  # ber- + -kan
    assert morpheme.get_lemma("menceritakan", "id") == "cerita"  # men- + -kan


def test_morpheme_decomposition_indonesian_conservative_config() -> None:
    """Short/ambiguous prefixes (bare me/ke/se/pe, without their
    consonant-initial variants) were measured to overfire and are
    deliberately excluded -- only the longer, unambiguous forms ship."""
    morpheme = MorphemeDecompositionStrategy()
    # "melihat" = me- (no epenthetic consonant) + "lihat" (a real dict root) --
    # would resolve if bare "me" were configured, but it isn't.
    assert morpheme.get_lemma("melihat", "id") is None


def test_dictionary_lookup_apostrophe_variant_recased() -> None:
    """A key stored capitalized under a different apostrophe glyph is found via
    the variant + reverse-case fallback (curly, lowercased input -> straight,
    capitalized key)."""

    mapping = {"L'eau": "eau"}  # straight apostrophe, capitalized
    lookup = DictionaryLookupStrategy(dictionary_factory=FixedMapping(mapping))
    assert lookup.get_lemma("l’eau", "xx") == "eau"  # curly, lowercase
