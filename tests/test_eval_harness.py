from training.eval_harness import (
    FixedDictionaryFactory,
    build_strategy,
    load_gold_tokens,
    load_lemma_form_tsv,
    score_token,
    score_type,
)


def _conllu(sentences: list[list[tuple[int, str, str]]]) -> str:
    """Build minimal CoNLL-U text from (id, form, lemma) rows per sentence."""
    blocks = []
    for rows in sentences:
        lines = [
            "\t".join([str(i), form, lemma, "X", "_", "_", "0", "root", "_", "_"])
            for i, form, lemma in rows
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n\n"


def test_fixed_dictionary_factory_serves_the_mapping():
    factory = FixedDictionaryFactory({"dogs": "dog"})
    assert factory.get_dictionary("en")["dogs"] == "dog"


def test_token_accuracy_perfect_dictionary(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(
        _conllu([[(1, "dogs", "dog"), (2, "cats", "cat")]]), encoding="utf-8"
    )
    acc, n = score_token(
        build_strategy({"dogs": "dog", "cats": "cat"}), "en", load_gold_tokens(path)
    )
    assert acc == 1.0
    assert n == 2


def test_token_accuracy_identity_fallback_on_miss(tmp_path):
    """A form absent from the dict falls back to itself, matching gold only
    when the gold lemma equals the surface form."""
    path = tmp_path / "test.conllu"
    path.write_text(_conllu([[(1, "run", "run")]]), encoding="utf-8")
    acc, n = score_token(build_strategy({}), "en", load_gold_tokens(path))
    assert acc == 1.0  # identity fallback happens to be correct here
    assert n == 1


def test_token_accuracy_skips_underscore_lemma_and_lowercases_initial(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(
        _conllu([[(1, "Dogs", "dog"), (2, "x", "_")]]),  # sentence-initial + skip
        encoding="utf-8",
    )
    acc, n = score_token(build_strategy({"dogs": "dog"}), "en", load_gold_tokens(path))
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
    acc, n = score_token(
        build_strategy({"de": "de", "el": "el"}), "es", load_gold_tokens(path)
    )
    assert n == 2  # the MWT span row itself is not a token


def test_token_accuracy_is_frequency_weighted(tmp_path):
    """A form seen 3x and a form seen once must NOT be weighted equally at
    the token level -- the wrong prediction on the frequent form costs more."""
    path = tmp_path / "test.conllu"
    rows = [[(1, "common", "commonlemma")] for _ in range(3)] + [
        [(1, "rare", "rarelemma")]
    ]
    path.write_text(_conllu(rows), encoding="utf-8")
    mapping = {"common": "commonlemma", "rare": "WRONG"}
    acc, n = score_token(build_strategy(mapping), "en", load_gold_tokens(path))
    assert n == 4
    assert acc == 0.75  # 3 correct commons out of 4 total tokens


def test_type_accuracy_weights_repeated_form_once(tmp_path):
    """Same scenario as the token-level test above, but type-level must give
    'common' and 'rare' EQUAL weight regardless of the 3x/1x frequency."""
    path = tmp_path / "test.conllu"
    rows = [[(1, "common", "commonlemma")] for _ in range(3)] + [
        [(1, "rare", "rarelemma")]
    ]
    path.write_text(_conllu(rows), encoding="utf-8")
    mapping = {"common": "commonlemma", "rare": "WRONG"}
    acc, n = score_type(build_strategy(mapping), "en", load_gold_tokens(path))
    assert n == 2  # 2 distinct forms, not 4 occurrences
    assert acc == 0.5  # 1 of 2 distinct forms correct


def test_type_accuracy_uses_majority_gold_for_ambiguous_form(tmp_path):
    """A form with inconsistent gold lemmas across occurrences (annotation
    noise or a real homograph) is scored against its MAJORITY gold lemma."""
    path = tmp_path / "test.conllu"
    rows = [[(1, "bank", "bank_river")] for _ in range(3)] + [
        [(1, "bank", "bank_money")] for _ in range(1)
    ]
    path.write_text(_conllu(rows), encoding="utf-8")
    acc, n = score_type(
        build_strategy({"bank": "bank_river"}), "en", load_gold_tokens(path)
    )
    assert n == 1  # one distinct form
    assert acc == 1.0  # matches the majority gold (3 vs 1)


def test_load_lemma_form_tsv(tmp_path):
    path = tmp_path / "override.tsv"
    path.write_text("el\tel\nacest\taceste\n", encoding="utf-8")
    assert load_lemma_form_tsv(path) == {"el": "el", "aceste": "acest"}


def test_load_lemma_form_tsv_empty_file(tmp_path):
    path = tmp_path / "empty.tsv"
    path.write_text("", encoding="utf-8")
    assert load_lemma_form_tsv(path) == {}


def test_type_and_token_agree_when_no_repeats(tmp_path):
    """A sanity cross-check: with no repeated forms, token- and type-level
    accuracy must be identical (every form has weight 1 either way)."""
    path = tmp_path / "test.conllu"
    path.write_text(
        _conllu([[(1, "a", "a"), (2, "b", "b"), (3, "c", "WRONG")]]),
        encoding="utf-8",
    )
    mapping = {"a": "a", "b": "b", "c": "c"}
    gold_tokens = load_gold_tokens(path)
    strategy = build_strategy(mapping)
    tok_acc, tok_n = score_token(strategy, "en", gold_tokens)
    typ_acc, typ_n = score_type(strategy, "en", gold_tokens)
    assert tok_acc == typ_acc
    assert tok_n == typ_n


def test_real_affix_chain_is_exercised_not_just_dict_lookup(tmp_path):
    """Not a stub -- the real DefaultStrategy chain runs affix decomposition:
    "talossa" isn't itself in the dict, but is derivable from the anchored
    base "talo" via Finnish's -ssa suffix rule (verified directly against
    the real chain, not assumed)."""
    path = tmp_path / "test.conllu"
    path.write_text(_conllu([[(1, "talossa", "talo")]]), encoding="utf-8")
    acc, n = score_token(build_strategy({"talo": "talo"}), "fi", load_gold_tokens(path))
    assert n == 1
    assert acc == 1.0  # "talossa" is not a dict key -- only the affix chain resolves it
