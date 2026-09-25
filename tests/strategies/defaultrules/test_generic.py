"""SuffixRules semantics: longest suffix wins, floors fall through, stops abstain."""

from simplemma.strategies.defaultrules.generic import SuffixRules

RULES = SuffixRules({"x": "ab ..cab", "y": "b"}, stops="zab")


def test_longest_suffix_wins() -> None:
    assert RULES.apply("wab") == "wx"  # "ab" beats "b"
    assert RULES.apply("wb") == "wy"
    assert RULES.apply("w") is None
    assert RULES.match("wab") == ("ab", "x")


def test_floor_falls_through_to_shorter_suffix() -> None:
    assert RULES.apply("wwcab") == "wwx"  # 2-char stem: "cab" fires
    assert RULES.apply("wcab") == "wcx"  # 1-char stem: "cab" skipped, "ab" fires


def test_stop_abstains() -> None:
    assert RULES.apply("wzab") is None  # "zab" beats "ab" and abstains


def test_min_stem_and_guards() -> None:
    assert SuffixRules({"x": "ab"}, min_stem=2).apply("wab") is None
    assert SuffixRules({"x": "ab"}, min_stem=2).apply("wwab") == "wwx"
    assert SuffixRules({"x": "ab"}, caps=True).apply("Wab") is None
    assert SuffixRules({"x": "ab"}, min_len=5).apply("wwab") is None
    assert SuffixRules({"x": "ab"}, hyphen=True).apply("w-ab") is None
    guarded = SuffixRules({"x": "ab"}, excluded={"wab"})
    assert guarded.apply("wab") is None
    assert guarded.match("wab") == ("ab", "x")  # match ignores the guards
