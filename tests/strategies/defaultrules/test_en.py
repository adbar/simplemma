from simplemma.strategies import RulesStrategy


def test_apply_en() -> None:
    """Test English rules."""
    rules_strategy = RulesStrategy()
    # doesn't exist
    assert rules_strategy.get_lemma("Whatawordicantbelieveit", "en") is None
    # nouns
    assert rules_strategy.get_lemma("delicacies", "en") == "delicacy"
    assert rules_strategy.get_lemma("nurseries", "en") == "nursery"
    assert rules_strategy.get_lemma("realities", "en") == "reality"
    assert rules_strategy.get_lemma("kingdoms", "en") == "kingdom"
    assert rules_strategy.get_lemma("mistresses", "en") == "mistress"
    assert rules_strategy.get_lemma("realisms", "en") == "realism"
    assert rules_strategy.get_lemma("naturists", "en") == "naturist"
    assert rules_strategy.get_lemma("atonements", "en") == "atonement"
    assert rules_strategy.get_lemma("nonces", "en") == "nonce"
    assert rules_strategy.get_lemma("hardships", "en") == "hardship"
    assert rules_strategy.get_lemma("atonements", "en") == "atonement"
    assert rules_strategy.get_lemma("nations", "en") == "nation"
    # assert rules_strategy.get_lemma("nerves", "en") == "nerve"
    # assert rules_strategy.get_lemma("dwarves", "en") == "dwarf"
    # assert rules_strategy.get_lemma("matrices", "en") == "matrix"
    # adjectives / verb forms
    # assert rules_strategy.get_lemma("vindicated", "en") == "vindicate"
    # assert rules_strategy.get_lemma("fastened", "en") == "fasten"
    # assert rules_strategy.get_lemma("dignified", "en") == "dignify"
    # assert rules_strategy.get_lemma("realized", "en") == "realize"
    # assert rules_strategy.get_lemma("complies", "en") == "comply"
    # assert rules_strategy.get_lemma("pinches", "en") == "pinch"
    # assert rules_strategy.get_lemma("dignified", "en") == "dignify"
    # assert rules_strategy.get_lemma('realised', "en") == 'realise'
