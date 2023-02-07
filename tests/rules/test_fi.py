from simplemma.rules import APPLY_RULES


def test_apply_fi() -> None:
    """Test Finnish rules."""
    # common -inen cases
    assert APPLY_RULES["fi"]("liikenaisen", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiset", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisia", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisissa", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisista", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiseksi", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiseen", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisella", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiselle", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiselta", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiseni", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisensa", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisesta", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisien", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisiksi", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisilla", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisilta", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisille", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisina", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisineen", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisitta", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisemme", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisenne", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisille", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiselta", False) == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisetta", False) == "liikenainen"
    # other cases
    assert APPLY_RULES["fi"]("zzzzztteja", False) == "zzzzztti"
