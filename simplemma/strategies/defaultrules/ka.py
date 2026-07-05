import re

from .generic import apply_rules

# Georgian nominal declension: case/number markers (-ს, -მა, -ნი, -ნო, -თა, ...)
# attach directly to the bare stem, and the nominative citation form restores
# the stem-final vowel. Anchored to the stem's own final consonant/vowel
# cluster: the bare case markers alone (-ს, -მა, -ნო, ...) are too ambiguous,
# since Georgian nouns fall into several historical stem classes that are not
# predictable from the surface form without lexical knowledge.
DEFAULT_RULES = {
    re.compile(r"(?:ტთა|ტმა|ტნი|ტნო|ტს)$"): "ტი",
    re.compile(r"(?:ლთა|ლმა|ლნი|ლნო|ლს)$"): "ლი",
    re.compile(r"(?:რთა|რნი|რნო|რს)$"): "რი",
    re.compile(r"(?:ოთა|ოდ|ოვ|ომ)$"): "ო",
    re.compile(r"(?:ორთა|ორნი|ორნო|ორო|ორს)$"): "ორი",
    re.compile(r"(?:სტთა|სტმა|სტნი|სტნო|სტს)$"): "სტი",
    re.compile(r"(?:იათა|იად|იავ|იამ|იას)$"): "ია",
    re.compile(r"(?:ელთა|ელმა|ელნი|ელნო|ელს)$"): "ელი",
    re.compile(r"(?:სთა|სნი|სნო|სს)$"): "სი",
    re.compile(r"(?:ერთა|ერმა|ერნი|ერნო|ერს)$"): "ერი",
    re.compile(r"(?:ართა|არმა|არნი|არნო|არს)$"): "არი",
    re.compile(r"(?:ედ|ევ|ემ)$"): "ე",
    re.compile(r"(?:რამ|რას)$"): "რა",
    re.compile(r"(?:ათა|ამ|ას)$"): "ა",
    re.compile(r"(?:ნთა|ნმა|ნნი|ნნო)$"): "ნი",
}

# invariant adverbs/conjunctions whose tail happens to match a bare case
# marker (UD validation, 2026-07 -- e.g. "მაგრამ" [but] was being stripped to
# "მაგრა" by the -ამ case-ending rule); proper nouns coinciding with a case
# shape (Georgian has no letter-case to guard on, unlike Latin/Cyrillic
# scripts, so PROPN forms stay in-scope); and a few verb 3rd-person-present
# forms whose bare stem coincidentally matches a nominal case ending. The
# causative/statal "-ოებ-" verb conjugation (აწარმოებს, საჭიროებს, ...),
# which used to collide with the "-ო" noun class's dative plural and was
# the single biggest driver of this list's growth, was fixed by dropping
# those four endings from the rule instead of stoplisting instances (an
# open-ended class, not a finite list) -- see the DEFAULT_RULES comment.
_EXCLUDED = frozenset(
    {
        "სანამ",
        "მხოლოდ",
        "მაგრამ",
        "ამიტომ",
        "სწორედ",
        "იმიტომ",
        "საერთოდ",
        "სრულიად",
        "არამედ",
        "კიდევ",
        "მუდამ",
        "საკმაოდ",
        "წერს",
        "გურამ",
        "დგას",
        "ვინემ",
        "ზემოდ",
        "ისევ",
        "კერძოდ",
        "კონცერნი",
        "მანამ",
        "მჭიდროდ",
        "ნაწარმოები",
        "რათა",
        "რატომ",
        "საავტორო",
        "სადღეისოდ",
        "სატურნი",
        "უგზოუკვლოდ",
        "უილემ",
        "უშუალოდ",
        "ფერმა",
        "ფრთა",
        "შემდგომ",
        "შოთა",
        "შორს",
        "წყვეტს",
    }
)


def apply_ka(token: str) -> str | None:
    "Apply pre-defined rules for Georgian."
    if len(token) < 4 or "-" in token or token in _EXCLUDED:
        return None

    return apply_rules(token, DEFAULT_RULES)
