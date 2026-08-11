import pytest

from simplemma import Lemmatizer
from simplemma.strategies import clitic_decomposition
from simplemma.strategies.default import DefaultStrategy
from training.eval_harness import (
    FixedDictionaryFactory,
    accuracy,
    build_strategy,
    gold_types,
    iter_real_word_tokens,
    load_gold_tokens,
    mechanism_disabled,
)

from .conftest import conllu as _conllu


def score_type(strategy, lang, gold_tokens):
    return accuracy(strategy, lang, gold_types(gold_tokens))


def _ar(word):
    """Lemmatize with a fresh default pipeline (re-reads the patched tables)."""
    return Lemmatizer(lemmatization_strategy=DefaultStrategy()).lemmatize(
        word, lang="ar"
    )


def test_fixed_dictionary_factory_serves_the_mapping():
    factory = FixedDictionaryFactory({"dogs": "dog"})
    assert factory.get_dictionary("en")["dogs"] == "dog"


def test_token_accuracy_perfect_dictionary(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(
        _conllu([[(1, "dogs", "dog"), (2, "cats", "cat")]]), encoding="utf-8"
    )
    acc, n = accuracy(
        build_strategy({"dogs": "dog", "cats": "cat"}),
        "en",
        load_gold_tokens(path, "en"),
    )
    assert acc == 1.0
    assert n == 2


def test_token_accuracy_identity_fallback_on_miss(tmp_path):
    """A form absent from the dict falls back to itself, matching gold only when equal."""
    path = tmp_path / "test.conllu"
    path.write_text(_conllu([[(1, "run", "run")]]), encoding="utf-8")
    acc, n = accuracy(build_strategy({}), "en", load_gold_tokens(path, "en"))
    assert acc == 1.0  # identity fallback happens to be correct here
    assert n == 1


def test_token_accuracy_skips_underscore_lemma_and_lowercases_initial(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(
        _conllu([[(1, "Dogs", "dog"), (2, "x", "_")]]),  # sentence-initial + skip
        encoding="utf-8",
    )
    acc, n = accuracy(
        build_strategy({"dogs": "dog"}), "en", load_gold_tokens(path, "en")
    )
    assert n == 1  # the lemma=='_' token is excluded
    assert acc == 1.0  # "Dogs" was lowercased to "dogs" before lookup


def test_token_accuracy_skips_multiword_tokens(tmp_path):
    path = tmp_path / "test.conllu"
    text = (
        "1-2\tdel\t_\t_\t_\t_\t_\t_\t_\t_\n"
        "1\tde\tde\tX\t_\t_\t0\troot\t_\t_\n"
        "2\tel\tel\tX\t_\t_\t0\troot\t_\t_\n\n"
    )
    path.write_text(text, encoding="utf-8")
    acc, n = accuracy(
        build_strategy({"de": "de", "el": "el"}), "es", load_gold_tokens(path, "es")
    )
    assert n == 2  # the MWT span row itself is not a token


def test_token_accuracy_is_frequency_weighted(tmp_path):
    """Token-level weighting is by occurrence count, not distinct form."""
    path = tmp_path / "test.conllu"
    rows = [[(1, "common", "commonlemma")] for _ in range(3)] + [
        [(1, "rare", "rarelemma")]
    ]
    path.write_text(_conllu(rows), encoding="utf-8")
    mapping = {"common": "commonlemma", "rare": "WRONG"}
    acc, n = accuracy(build_strategy(mapping), "en", load_gold_tokens(path, "en"))
    assert n == 4
    assert acc == 0.75  # 3 correct commons out of 4 total tokens


def test_type_accuracy_weights_repeated_form_once(tmp_path):
    """Type-level gives 'common' and 'rare' equal weight, unlike token-level."""
    path = tmp_path / "test.conllu"
    rows = [[(1, "common", "commonlemma")] for _ in range(3)] + [
        [(1, "rare", "rarelemma")]
    ]
    path.write_text(_conllu(rows), encoding="utf-8")
    mapping = {"common": "commonlemma", "rare": "WRONG"}
    acc, n = score_type(build_strategy(mapping), "en", load_gold_tokens(path, "en"))
    assert n == 2  # 2 distinct forms, not 4 occurrences
    assert acc == 0.5  # 1 of 2 distinct forms correct


def test_type_accuracy_uses_majority_gold_for_ambiguous_form(tmp_path):
    """A form with inconsistent gold lemmas is scored against its majority gold lemma."""
    path = tmp_path / "test.conllu"
    rows = [[(1, "bank", "bank_river")] for _ in range(3)] + [
        [(1, "bank", "bank_money")] for _ in range(1)
    ]
    path.write_text(_conllu(rows), encoding="utf-8")
    acc, n = score_type(
        build_strategy({"bank": "bank_river"}), "en", load_gold_tokens(path, "en")
    )
    assert n == 1  # one distinct form
    assert acc == 1.0  # matches the majority gold (3 vs 1)


def test_type_and_token_agree_when_no_repeats(tmp_path):
    """With no repeated forms, token- and type-level accuracy must be identical."""
    path = tmp_path / "test.conllu"
    path.write_text(
        _conllu([[(1, "a", "a"), (2, "b", "b"), (3, "c", "WRONG")]]),
        encoding="utf-8",
    )
    mapping = {"a": "a", "b": "b", "c": "c"}
    gold_tokens = load_gold_tokens(path, "en")
    strategy = build_strategy(mapping)
    tok_acc, tok_n = accuracy(strategy, "en", gold_tokens)
    typ_acc, typ_n = score_type(strategy, "en", gold_tokens)
    assert tok_acc == typ_acc
    assert tok_n == typ_n


def test_real_affix_chain_is_exercised_not_just_dict_lookup(tmp_path):
    """Exercises the real DefaultStrategy affix chain: "talossa" isn't in the dict
    but is derivable from "talo" via Finnish's -ssa suffix rule."""
    path = tmp_path / "test.conllu"
    path.write_text(_conllu([[(1, "talossa", "talo")]]), encoding="utf-8")
    acc, n = accuracy(
        build_strategy({"talo": "talo"}), "fi", load_gold_tokens(path, "fi")
    )
    assert n == 1
    assert acc == 1.0  # "talossa" is not a dict key -- only the affix chain resolves it


def test_load_gold_tokens_canonicalizes_gold_lemma_for_ar(tmp_path):
    """PADT gold lemmas are vocalized; the dict is built from unvocalized
    forms, so the gold lemma must be canonicalized or every ar content lemma
    mismatches."""
    path = tmp_path / "test.conllu"
    path.write_text(_conllu([[(1, "كتاب", "كِتَاب")]]), encoding="utf-8")
    ((form, gold),) = load_gold_tokens(path, "ar")
    assert gold == "كتاب"  # vocalization stripped
    acc, n = accuracy(
        build_strategy({"كتاب": "كتاب"}), "ar", load_gold_tokens(path, "ar")
    )
    assert acc == 1.0


def test_load_gold_tokens_leaves_other_langs_unaffected(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(_conllu([[(1, "dogs", "dog")]]), encoding="utf-8")
    ((form, gold),) = load_gold_tokens(path, "en")
    assert gold == "dog"


# A fused MWT span (proclitic ש + content יכולת) alongside one plain token.
REAL_WORD_CONLLU = (
    "1-2\tשיכולת\t_\t_\t_\t_\t_\t_\t_\t_\n"
    "1\tש\tש\tSCONJ\t_\t_\t2\tmark\t_\t_\n"
    "2\tיכולת\tיכולת\tNOUN\t_\t_\t0\troot\t_\t_\n"
    "3\tdog\tdog\tNOUN\t_\t_\t0\troot\t_\t_\n\n"
)


def test_iter_real_word_tokens_collapses_span_to_content_gold(tmp_path):
    """A fused span is yielded as ITS OWN whole surface form, scored against
    the CONTENT sub-token's gold lemma -- not the proclitic's, and not split
    into two separate tokens the way iter_word_tokens would."""
    path = tmp_path / "test.conllu"
    path.write_text(REAL_WORD_CONLLU, encoding="utf-8")
    pairs = list(iter_real_word_tokens(path, "he"))
    assert pairs == [("שיכולת", "יכולת"), ("dog", "dog")]


def test_iter_real_word_tokens_canonicalizes_gold_for_ar(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(_conllu([[(1, "كتاب", "كِتَاب")]]), encoding="utf-8")
    assert list(iter_real_word_tokens(path, "ar")) == [("كتاب", "كتاب")]


def test_mechanism_disabled_clitic_targets_the_derived_cache():
    """The false-+0.00pp trap: the clitic lookup reads _CLITIC_SUFFIXES (a
    precomputed cache), not CLITIC_LANGS. mechanism_disabled must patch the
    cache so the A/B actually changes behavior."""
    assert _ar("كتابه") == "كتاب"  # baseline: ar enclitic strips
    with mechanism_disabled("clitic", "ar"):
        assert _ar("كتابه") != "كتاب"  # strip disabled
    assert _ar("كتابه") == "كتاب"  # restored


def test_mechanism_disabled_prefix_targets_the_bound_default():
    """The other trap: PrefixDecomposition binds DEFAULT_KNOWN_PREFIXES once as
    a default arg. mechanism_disabled mutates that object in place."""
    assert _ar("بالبيت") == "بيت"
    with mechanism_disabled("prefix", "ar"):
        assert _ar("بالبيت") != "بيت"
    assert _ar("بالبيت") == "بيت"


def test_mechanism_disabled_canon_targets_the_fold_table():
    """canonicalize_token reads _CANON_TABLES: disabling must stop the fold."""
    # baseline: vocalized ar folds to the unvocalized dict entry
    assert _ar("بِيت") == "بيت"
    with mechanism_disabled("canon", "ar"):
        assert _ar("بِيت") != "بيت"
    assert _ar("بِيت") == "بيت"


def test_mechanism_disabled_canon_also_narrows_clitic_snapshot():
    """canon has a SECOND reader: clitic_decomposition gates on a CANON_LANGS
    frozenset snapshot, not _CANON_TABLES. Disabling must narrow it too (else
    the A/B measures a mixed state) and restore it on exit."""
    before = clitic_decomposition.CANON_LANGS
    assert "ar" in before
    with mechanism_disabled("canon", "ar"):
        assert "ar" not in clitic_decomposition.CANON_LANGS
    # equality, not identity: the harness re-derives the snapshot on restore
    assert clitic_decomposition.CANON_LANGS == before


def test_mechanism_disabled_raises_on_noop_disable():
    """Disabling a lang absent from the table would silently measure the same
    config twice -- it must raise instead."""
    with pytest.raises(KeyError):
        with mechanism_disabled("prefix", "xx"):
            pass
    with pytest.raises(ValueError):
        with mechanism_disabled("bogus", "ar"):
            pass
