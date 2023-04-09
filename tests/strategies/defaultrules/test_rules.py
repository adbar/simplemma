"""Tests for rule-based behavior of the `simplemma` package."""
from simplemma.strategies.defaultrules import DEFAULT_RULES


def test_DEFAULT_RULES() -> None:
    """Test rules on all available languages."""
    assert DEFAULT_RULES["de"]("Pfifferlinge") == "Pfifferling"
    assert DEFAULT_RULES["en"]("Pfifferlinge") is None
    assert DEFAULT_RULES["de"]("atonements") is None
    assert DEFAULT_RULES["en"]("atonements") == "atonement"
    assert DEFAULT_RULES["nl"]("brieven") == "brief"
    assert DEFAULT_RULES["fi"]("liikenaisessa") == "liikenainen"
    assert DEFAULT_RULES["pl"]("pracowaliście") == "pracować"
    assert DEFAULT_RULES["ru"]("безгра́мотностью") == "безгра́мотность"
