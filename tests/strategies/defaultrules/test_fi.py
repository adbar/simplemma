from simplemma.strategies import RulesStrategy


def test_apply_fi() -> None:
    """Test Finnish rules."""
    rules_strategy = RulesStrategy()
    # -inen possessive cells
    assert rules_strategy.get_lemma("aakkoselliseen", "fi") == "aakkosellinen"
    assert rules_strategy.get_lemma("aakkoselliseksi", "fi") == "aakkosellinen"
    assert rules_strategy.get_lemma("aakkosellisella", "fi") == "aakkosellinen"
    # -us / -ys nouns
    assert rules_strategy.get_lemma("kirjoituksen", "fi") == "kirjoitus"
    assert rules_strategy.get_lemma("ystävyyden", "fi") == "ystävyys"
    # -uus abstract nouns
    assert rules_strategy.get_lemma("kirjallisuuden", "fi") == "kirjallisuus"
    assert rules_strategy.get_lemma("kalastuksen", "fi") == "kalastus"
    assert rules_strategy.get_lemma("kissa", "fi") is None
    assert rules_strategy.get_lemma("Liikenaisen", "fi") is None
