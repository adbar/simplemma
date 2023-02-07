from simplemma.rules import FIND_KNOWN_PREFIXES


def test_test_prefixes_ru():
    assert FIND_KNOWN_PREFIXES["ru"]("зафиксированные") == "за"
