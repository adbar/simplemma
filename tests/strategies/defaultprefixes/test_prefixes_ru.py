from simplemma.strategies.defaultprefixes import DEFAULT_KNOWN_PREFIXES


def test_test_prefixes_ru():
    assert DEFAULT_KNOWN_PREFIXES["ru"].match("зафиксированные")[1] == "за"
