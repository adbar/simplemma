from simplemma.rules import APPLY_RULES


def test_apply_en() -> None:
    """Test English rules."""
    # doesn't exist
    assert APPLY_RULES["en"]("Whatawordicantbelieveit") is None
    # nouns
    assert APPLY_RULES["en"]("delicacies") == "delicacy"
    assert APPLY_RULES["en"]("nurseries") == "nursery"
    assert APPLY_RULES["en"]("realities") == "reality"
    assert APPLY_RULES["en"]("kingdoms") == "kingdom"
    assert APPLY_RULES["en"]("mistresses") == "mistress"
    assert APPLY_RULES["en"]("realisms") == "realism"
    assert APPLY_RULES["en"]("naturists") == "naturist"
    assert APPLY_RULES["en"]("atonements") == "atonement"
    assert APPLY_RULES["en"]("nonces") == "nonce"
    assert APPLY_RULES["en"]("hardships") == "hardship"
    assert APPLY_RULES["en"]("atonements") == "atonement"
    assert APPLY_RULES["en"]("nations") == "nation"
    # assert APPLY_RULES["en"]("nerves") == "nerve"
    # assert APPLY_RULES["en"]("dwarves") == "dwarf"
    # assert APPLY_RULES["en"]("matrices") == "matrix"
    # adjectives / verb forms
    # assert APPLY_RULES["en"]("vindicated") == "vindicate"
    # assert APPLY_RULES["en"]("fastened") == "fasten"
    # assert APPLY_RULES["en"]("dignified") == "dignify"
    # assert APPLY_RULES["en"]("realized") == "realize"
    # assert APPLY_RULES["en"]("complies") == "comply"
    # assert APPLY_RULES["en"]("pinches") == "pinch"
    # assert APPLY_RULES["en"]("dignified") == "dignify"
    # assert APPLY_RULES["en"]('realised') == 'realise'
