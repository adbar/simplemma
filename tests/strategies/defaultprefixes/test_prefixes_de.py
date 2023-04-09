from simplemma.strategies.defaultprefixes import DEFAULT_KNOWN_PREFIXES


def test_test_prefixes_de():
    assert DEFAULT_KNOWN_PREFIXES["de"].match("zerlemmatisiertes")[1] == "zer"
    assert DEFAULT_KNOWN_PREFIXES["de"].match("abzugshaube") == None
