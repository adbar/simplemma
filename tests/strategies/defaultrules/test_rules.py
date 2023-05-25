from simplemma.strategies import RulesStrategy


def test_DEFAULT_RULES() -> None:
    """Test rules on all available languages."""
    rules_strategy = RulesStrategy()
    assert rules_strategy.get_lemma("Pfifferlinge", "de") == "Pfifferling"
    assert rules_strategy.get_lemma("Pfifferlinge", "en") is None
    assert rules_strategy.get_lemma("atonements", "de") is None
    assert rules_strategy.get_lemma("atonements", "en") == "atonement"
    assert rules_strategy.get_lemma("brieven", "nl") == "brief"
    assert rules_strategy.get_lemma("liikenaisessa", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("pracowaliście", "pl") == "pracować"
    assert rules_strategy.get_lemma("безгра́мотностью", "ru") == "безгра́мотность"
