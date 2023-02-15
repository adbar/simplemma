"""Tests for rule-based behavior of the `simplemma` package."""
from simplemma.rules import APPLY_RULES


def test_apply_rules() -> None:
    """Test rules on all available languages."""
    assert APPLY_RULES["de"]("Pfifferlinge") == "Pfifferling"
    assert APPLY_RULES["en"]("Pfifferlinge") is None
    assert APPLY_RULES["de"]("atonements") is None
    assert APPLY_RULES["en"]("atonements") == "atonement"
    assert APPLY_RULES["nl"]("brieven") == "brief"
    assert APPLY_RULES["fi"]("liikenaisessa") == "liikenainen"
    assert APPLY_RULES["pl"]("pracowaliście") == "pracować"
    assert APPLY_RULES["ru"]("безгра́мотностью") == "безгра́мотность"
