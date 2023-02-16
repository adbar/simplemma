from simplemma.rules import APPLY_RULES


def test_apply_nl() -> None:
    """Test Dutch rules."""
    assert APPLY_RULES["nl"]("achterpagina's") == "achterpagina"
    assert APPLY_RULES["nl"]("mogelijkheden") == "mogelijkheid"
    assert APPLY_RULES["nl"]("boerderijen") == "boerderij"
    assert APPLY_RULES["nl"]("brieven") == "brief"
