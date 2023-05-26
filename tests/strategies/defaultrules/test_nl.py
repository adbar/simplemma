from simplemma.strategies import RulesStrategy


def test_apply_nl() -> None:
    """Test Dutch rules."""
    rules_strategy = RulesStrategy()
    assert rules_strategy.get_lemma("achterpagina's", "nl") == "achterpagina"
    assert rules_strategy.get_lemma("mogelijkheden", "nl") == "mogelijkheid"
    assert rules_strategy.get_lemma("boerderijen", "nl") == "boerderij"
    assert rules_strategy.get_lemma("brieven", "nl") == "brief"
