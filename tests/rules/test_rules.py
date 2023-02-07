"""Tests for rule-based behavior of the `simplemma` package."""
from simplemma.rules import APPLY_RULES


def test_apply_rules() -> None:
    """Test rules on all available languages."""
    assert APPLY_RULES["de"]("Pfifferlinge", True) == "Pfifferling"
    assert APPLY_RULES["en"]("Pfifferlinge", True) is None
    assert APPLY_RULES["de"]("atonements", False) is None
    assert APPLY_RULES["en"]("atonements", False) == "atonement"
    assert APPLY_RULES["nl"]("brieven", False) == "brief"
    assert APPLY_RULES["fi"]("liikenaisessa", False) == "liikenainen"
    assert APPLY_RULES["pl"]("pracowaliście", False) == "pracować"
    assert APPLY_RULES["ru"]("безгра́мотностью", False) == "безгра́мотность"
