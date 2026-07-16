from simplemma.strategies import PrefixDecompositionStrategy


def test_prefixes_uk() -> None:
    prefix_decomposition_strategy = PrefixDecompositionStrategy()
    assert prefix_decomposition_strategy.get_lemma("відкликала", "uk") == "відкликати"
