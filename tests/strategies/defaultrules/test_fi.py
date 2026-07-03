from simplemma.strategies import RulesStrategy


def test_apply_fi() -> None:
    """Test Finnish rules."""
    rules_strategy = RulesStrategy()
    # -inen singular-oblique + possessive cells (-ainen handles -aisen/-aiset/-aisia)
    assert rules_strategy.get_lemma("liikenaisen", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiset", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisia", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiseksi", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiseen", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisella", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiselle", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiselta", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaiseni", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisensa", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisesta", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisenne", "fi") == "liikenainen"
    assert rules_strategy.get_lemma("liikenaisetta", "fi") == "liikenainen"
    # -isi* plural obliques (isilla/isissa/isiksi/...) dropped: they collide with
    # -isä/poliisi plurals (adoptioisilla, ajatuspoliisina) below the 99% bar.
    assert rules_strategy.get_lemma("liikenaisilla", "fi") is None
    # -us / -ys nouns (mined)
    assert rules_strategy.get_lemma("rakennuksen", "fi") == "rakennus"
    assert rules_strategy.get_lemma("hämmästyksen", "fi") == "hämmästys"
    # -tti possessive / plural partitive
    assert rules_strategy.get_lemma("zzzzztteja", "fi") == "zzzzztti"
    assert rules_strategy.get_lemma("kissa", "fi") is None
    assert rules_strategy.get_lemma("Liikenaisen", "fi") is None
