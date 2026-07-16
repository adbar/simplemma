from simplemma.strategies import PrefixDecompositionStrategy


def test_prefixes_de() -> None:
    prefix_decomposition_strategy = PrefixDecompositionStrategy()
    assert (
        prefix_decomposition_strategy.get_lemma("zerlemmatisiertes", "de")
        == "zerlemmatisiert"
    )
    assert prefix_decomposition_strategy.get_lemma("abzugshaube", "de") is None
