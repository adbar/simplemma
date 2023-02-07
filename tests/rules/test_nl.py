from simplemma.rules import APPLY_RULES


def test_apply_nl() -> None:
    """Test Dutch rules."""
    assert APPLY_RULES["nl"]("achterpagina's", False) == "achterpagina"
    assert APPLY_RULES["nl"]("mogelijkheden", False) == "mogelijkheid"
    assert APPLY_RULES["nl"]("boerderijen", False) == "boerderij"
    assert APPLY_RULES["nl"]("brieven", False) == "brief"
