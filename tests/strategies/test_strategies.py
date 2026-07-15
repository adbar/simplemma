from collections.abc import Mapping

import pytest

from simplemma.strategies import (
    AffixDecompositionStrategy,
    ApostropheBoundaryStrategy,
    CliticDecompositionStrategy,
    DefaultStrategy,
    DictionaryFactory,
    DictionaryLookupStrategy,
    GreedyDictionaryLookupStrategy,
    HyphenRemovalStrategy,
    PrefixDecompositionStrategy,
)
from simplemma.strategies.greedy_dictionary_lookup import greedy_min_length


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
        ("nn", False, "underleverandørane", "underleverandør"),
        # es re-admitted on UD v2.18 (old es_gsd PROPN-convention artifact fixed)
        ("es", False, "microrregiones", "microrregión"),
        ("es", False, "estanquillas", "estanquilla"),
        # lt's entry gate is lowered to 7, admitting these 8-char forms
        ("lt", False, "rengiami", "rengti"),
        ("lt", False, "teikiant", "teikti"),
        # None: gated-out languages and unresolvable forms
        # affix leaves the et -kond family alone (no over-strip); laudkonna's
        # stem is now a fill entry, so aadelkond is the stable canary here.
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


def test_dictionary_lookup_apostrophe_variant_recased() -> None:
    """A key stored capitalized under a different apostrophe glyph is found via
    the variant + reverse-case fallback (curly, lowercased input -> straight,
    capitalized key)."""

    class F(DictionaryFactory):
        def get_dictionary(self, lang: str) -> Mapping[str, str]:
            return {"L'eau": "eau"}  # straight apostrophe, capitalized

    lookup = DictionaryLookupStrategy(dictionary_factory=F())
    assert lookup.get_lemma("l’eau", "xx") == "eau"  # curly, lowercase
