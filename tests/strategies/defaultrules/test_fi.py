from simplemma.strategies import RulesStrategy


def test_apply_fi() -> None:
    """Test Finnish rules."""
    rules_strategy = RulesStrategy()
    # common -inen cases
    assert rules_strategy.get_lemma("liikenaisen", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiset", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisia", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisissa", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisista", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiseksi", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiseen", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisella", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiselle", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiselta", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiseni", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisensa", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisesta", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisien", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisiksi", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisilla", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisilta", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisille", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisina", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisineen", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisitta", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisemme", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisenne", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisille", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiselta", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisetta", "fi") == "liikenainen"
    # other cases
    assert rules_strategy.get_lemma("zzzzztteja", "fi") == "zzzzztti"
