from simplemma.strategies import RulesStrategy


def test_apply_pl() -> None:
    """Test Polish rules."""
    rules_strategy = RulesStrategy()
    assert rules_strategy.get_lemma("wolnościach", "pl") == "wolność"
    assert rules_strategy.get_lemma("malowałbym", "pl") == "malować"
    assert rules_strategy.get_lemma("czytalibyśmy", "pl") == "czytać"
    assert rules_strategy.get_lemma("robilibyście", "pl") == "robić"
    assert rules_strategy.get_lemma("zmyłybyśmy", "pl") == "zmyć"
    assert rules_strategy.get_lemma("kotów", "pl") is None
    assert rules_strategy.get_lemma("Wolnościach", "pl") is None
