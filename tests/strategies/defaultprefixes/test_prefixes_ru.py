from simplemma.strategies import PrefixDecompositionStrategy


def test_test_prefixes_ru():
    prefix_decomposition_strategy = PrefixDecompositionStrategy()
    assert (
        prefix_decomposition_strategy.get_lemma("зафиксированные", "ru")
        == "зафиксированный"
    )
