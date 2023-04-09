from simplemma.strategies.defaultrules import DEFAULT_RULES


def test_apply_nl() -> None:
    """Test Dutch rules."""
    assert DEFAULT_RULES["nl"]("achterpagina's") == "achterpagina"
    assert DEFAULT_RULES["nl"]("mogelijkheden") == "mogelijkheid"
    assert DEFAULT_RULES["nl"]("boerderijen") == "boerderij"
    assert DEFAULT_RULES["nl"]("brieven") == "brief"
