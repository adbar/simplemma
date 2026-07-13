from simplemma.strategies import (
    AffixDecompositionStrategy,
    ApostropheBoundaryStrategy,
    CliticDecompositionStrategy,
    DefaultStrategy,
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

    assert DefaultStrategy().get_lemma("Gender-Sternchens", "de") == "Gendersternchen"
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

    assert AffixDecompositionStrategy(greedy=True).get_lemma("ccc", "de") is None

    # tokens over the safety cap are rejected outright (quadratic blow-up guard)
    affix = AffixDecompositionStrategy(greedy=True)
    assert affix.get_lemma("a" * 101, "fi") is None
    assert affix.get_lemma("a" * 100000, "fi") is None

    assert PrefixDecompositionStrategy().get_lemma("auf", "de") is None


def test_affix_decomposition() -> None:
    """Single-pass affix decomposition resolves multi-character affixes."""
    affix = AffixDecompositionStrategy(greedy=True)
    assert affix.get_lemma("kissammeko", "fi") == "kissa"  # FI "and our cat?" -> cat
    assert affix.get_lemma("könyveiteket", "hu") == "könyv"  # HU "your books" -> book
    assert affix.get_lemma("raamatutest", "et") == "raamat"  # ET "from books" -> book


def test_affix_decomposition_et_affix_len_override() -> None:
    """et's max_affix_len=3 avoids over-stripping the "-konna" genitive."""
    affix = AffixDecompositionStrategy(greedy=True)
    assert affix.get_lemma("raamatutest", "et") == "raamat"
    assert affix.get_lemma("laudkonna", "et") is None


def test_affix_decomposition_da_membership() -> None:
    """da is UD-validated and enabled in non-greedy mode via AFFIX_LANGS."""
    affix = AffixDecompositionStrategy(greedy=False)
    assert affix.get_lemma("drabsdagen", "da") == "drabsdag"
    assert affix.get_lemma("menighedsrådsvalget", "da") == "menighedsrådsvalg"


def test_affix_decomposition_nn_membership() -> None:
    """nn is UD-validated and enabled in non-greedy mode via AFFIX_LANGS."""
    affix = AffixDecompositionStrategy(greedy=False)
    assert affix.get_lemma("pastasalaten", "nn") == "pastasalat"
    assert affix.get_lemma("underleverandørane", "nn") == "underleverandør"


def test_affix_decomposition_lt_gate() -> None:
    """lt's entry gate is 7, not the default 8, admitting 8-char forms."""
    assert greedy_min_length("lt") == 7
    assert greedy_min_length("bg") == 6
    assert greedy_min_length("xx") == 8
    affix = AffixDecompositionStrategy(greedy=False)
    assert affix.get_lemma("rengiami", "lt") == "rengti"
    assert affix.get_lemma("teikiant", "lt") == "teikti"


def test_affix_decomposition_greedy_exclude() -> None:
    """GREEDY_EXCLUDE languages skip decomposition entirely in greedy mode."""
    affix = AffixDecompositionStrategy(greedy=True)
    # the sub-strategy would fire garbage; the entry gate prevents it
    assert affix._suffix_decomposition("-changanya", "sw", 4) is not None
    assert affix.get_lemma("-changanya", "sw") is None
    assert affix.get_lemma("supostamente", "pt") is None
    assert affix.get_lemma("virtualmente", "gl") is None
    # non-excluded languages still decompose in greedy mode
    assert affix.get_lemma("kissammeko", "fi") == "kissa"


def test_affix_decomposition_es_membership() -> None:
    """es was re-validated on UD v2.18 (es_gsd + es_ancora, both modes)
    and admitted; the old rejection was an es_gsd PROPN-convention
    artifact fixed upstream."""
    affix = AffixDecompositionStrategy(greedy=False)
    assert affix.get_lemma("microrregiones", "es") == "microrregión"
    assert affix.get_lemma("estanquillas", "es") == "estanquilla"


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


def test_apostrophe_boundary() -> None:
    """Turkish marks a fixed proper-noun/suffix boundary with an
    apostrophe; the head is lemmatized via the full pipeline."""
    strat = DefaultStrategy()
    assert strat.get_lemma("İstanbul'da", "tr") == "İstanbul"
    assert strat.get_lemma("Erdoğan'ın", "tr") == "Erdoğan"
    # curly apostrophes (smart quotes) mark the same boundary
    assert strat.get_lemma("Erdoğan’ın", "tr") == "Erdoğan"
    # unsupported language: no-op
    assert (
        ApostropheBoundaryStrategy(
            strat.get_lemma, DictionaryLookupStrategy()
        ).get_lemma("l'arbre", "fr")
        is None
    )


def test_dictionary_lookup_apostrophe_variant() -> None:
    """A dictionary key using the other apostrophe variant (straight vs
    curly -- NFC does not unify them) is still found."""
    lookup = DictionaryLookupStrategy()
    assert lookup.get_lemma("виб’єш", "uk") == "вибити"
    assert lookup.get_lemma("un’", "it") == "uno"
