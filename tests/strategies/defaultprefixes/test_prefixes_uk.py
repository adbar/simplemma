from simplemma.strategies import PrefixDecompositionStrategy


def test_test_prefixes_uk():
    prefix_decomposition_strategy = PrefixDecompositionStrategy()
    assert prefix_decomposition_strategy.get_lemma("відкликала", "uk") == "відкликати"
