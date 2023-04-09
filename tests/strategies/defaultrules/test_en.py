from simplemma.strategies.defaultrules import DEFAULT_RULES


def test_apply_en() -> None:
    """Test English rules."""
    # doesn't exist
    assert DEFAULT_RULES["en"]("Whatawordicantbelieveit") is None
    # nouns
    assert DEFAULT_RULES["en"]("delicacies") == "delicacy"
    assert DEFAULT_RULES["en"]("nurseries") == "nursery"
    assert DEFAULT_RULES["en"]("realities") == "reality"
    assert DEFAULT_RULES["en"]("kingdoms") == "kingdom"
    assert DEFAULT_RULES["en"]("mistresses") == "mistress"
    assert DEFAULT_RULES["en"]("realisms") == "realism"
    assert DEFAULT_RULES["en"]("naturists") == "naturist"
    assert DEFAULT_RULES["en"]("atonements") == "atonement"
    assert DEFAULT_RULES["en"]("nonces") == "nonce"
    assert DEFAULT_RULES["en"]("hardships") == "hardship"
    assert DEFAULT_RULES["en"]("atonements") == "atonement"
    assert DEFAULT_RULES["en"]("nations") == "nation"
    # assert DEFAULT_RULES["en"]("nerves") == "nerve"
    # assert DEFAULT_RULES["en"]("dwarves") == "dwarf"
    # assert DEFAULT_RULES["en"]("matrices") == "matrix"
    # adjectives / verb forms
    # assert DEFAULT_RULES["en"]("vindicated") == "vindicate"
    # assert DEFAULT_RULES["en"]("fastened") == "fasten"
    # assert DEFAULT_RULES["en"]("dignified") == "dignify"
    # assert DEFAULT_RULES["en"]("realized") == "realize"
    # assert DEFAULT_RULES["en"]("complies") == "comply"
    # assert DEFAULT_RULES["en"]("pinches") == "pinch"
    # assert DEFAULT_RULES["en"]("dignified") == "dignify"
    # assert DEFAULT_RULES["en"]('realised') == 'realise'
