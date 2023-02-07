from simplemma.rules import APPLY_RULES


def test_apply_en() -> None:
    """Test English rules."""
    # doesn't exist
    assert APPLY_RULES["en"]("Whatawordicantbelieveit", False) is None
    # nouns
    assert APPLY_RULES["en"]("delicacies", False) == "delicacy"
    assert APPLY_RULES["en"]("nurseries", False) == "nursery"
    assert APPLY_RULES["en"]("realities", False) == "reality"
    assert APPLY_RULES["en"]("kingdoms", False) == "kingdom"
    assert APPLY_RULES["en"]("mistresses", False) == "mistress"
    assert APPLY_RULES["en"]("realisms", False) == "realism"
    assert APPLY_RULES["en"]("naturists", False) == "naturist"
    assert APPLY_RULES["en"]("atonements", False) == "atonement"
    assert APPLY_RULES["en"]("nonces", False) == "nonce"
    assert APPLY_RULES["en"]("hardships", False) == "hardship"
    assert APPLY_RULES["en"]("atonements", False) == "atonement"
    assert APPLY_RULES["en"]("nations", False) == "nation"
    # assert APPLY_RULES["en"]("nerves", False) == "nerve"
    # assert APPLY_RULES["en"]("dwarves", False) == "dwarf"
    # assert APPLY_RULES["en"]("matrices", False) == "matrix"
    # adjectives / verb forms
    # assert APPLY_RULES["en"]("vindicated", False) == "vindicate"
    # assert APPLY_RULES["en"]("fastened", False) == "fasten"
    # assert APPLY_RULES["en"]("dignified", False) == "dignify"
    # assert APPLY_RULES["en"]("realized", False) == "realize"
    # assert APPLY_RULES["en"]("complies", False) == "comply"
    # assert APPLY_RULES["en"]("pinches", False) == "pinch"
    # assert APPLY_RULES["en"]("dignified", False) == "dignify"
    # assert APPLY_RULES["en"]('realised', False) == 'realise'
