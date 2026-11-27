from training import rulebuilder


def test_mine_skips_suffixes_with_metacharacters(monkeypatch) -> None:
    """Abbreviation keys (hu "alma.-ek") must not yield ".-ek" cells."""
    d = {"alma.-ek": "alma.", "körte.-ek": "körte."}
    monkeypatch.setattr(rulebuilder, "proxy_dictionary", lambda lang: d)
    cells, _ = rulebuilder.mine("hu", support_min=1)
    assert cells
    assert not any(rulebuilder._META.search(s + t) for s, t in cells)
    rulebuilder.build_rules(cells)
