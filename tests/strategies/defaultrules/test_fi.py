from simplemma.strategies.defaultrules import DEFAULT_RULES


def test_apply_fi() -> None:
    """Test Finnish rules."""
    # common -inen cases
    assert DEFAULT_RULES["fi"]("liikenaisen") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaiset") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisia") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisissa") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisista") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaiseksi") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaiseen") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisella") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaiselle") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaiselta") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaiseni") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisensa") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisesta") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisien") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisiksi") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisilla") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisilta") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisille") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisina") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisineen") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisitta") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisemme") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisenne") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisille") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaiselta") == "liikenainen"
    assert DEFAULT_RULES["fi"]("liikenaisetta") == "liikenainen"
    # other cases
    assert DEFAULT_RULES["fi"]("zzzzztteja") == "zzzzztti"
