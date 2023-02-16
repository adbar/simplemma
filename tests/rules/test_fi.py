from simplemma.rules import APPLY_RULES


def test_apply_fi() -> None:
    """Test Finnish rules."""
    # common -inen cases
    assert APPLY_RULES["fi"]("liikenaisen") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiset") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisia") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisissa") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisista") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiseksi") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiseen") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisella") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiselle") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiselta") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiseni") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisensa") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisesta") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisien") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisiksi") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisilla") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisilta") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisille") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisina") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisineen") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisitta") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisemme") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisenne") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisille") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaiselta") == "liikenainen"
    assert APPLY_RULES["fi"]("liikenaisetta") == "liikenainen"
    # other cases
    assert APPLY_RULES["fi"]("zzzzztteja") == "zzzzztti"
