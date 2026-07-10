import re

from .generic import apply_rules

# Georgian nominal declension, anchored on the stem's final cluster (bare
# case markers are too ambiguous). ედ/ევ/ომ dropped (gold restores the
# nominative -ი, unreachable by stripping); colliding verbs are stoplisted
# rather than cells dropped (they would just cascade to broader cells).
DEFAULT_RULES = {
    re.compile(r"(?:ტთა|ტმა|ტნი|ტნო|ტს)$"): "ტი",
    re.compile(r"(?:ლთა|ლმა|ლნი|ლნო|ლს)$"): "ლი",
    re.compile(r"(?:რთა|რნი|რნო|რს)$"): "რი",
    re.compile(r"(?:ოთა|ოდ|ოვ)$"): "ო",
    re.compile(r"(?:ორთა|ორნი|ორნო|ორო|ორს)$"): "ორი",
    re.compile(r"(?:სტთა|სტმა|სტნი|სტნო|სტს)$"): "სტი",
    re.compile(r"(?:იათა|იად|იავ|იამ|იას)$"): "ია",
    re.compile(r"(?:ელთა|ელმა|ელნი|ელნო|ელს)$"): "ელი",
    re.compile(r"(?:სთა|სნი|სნო|სს)$"): "სი",
    re.compile(r"(?:ერთა|ერმა|ერნი|ერნო|ერს)$"): "ერი",
    re.compile(r"(?:ართა|არმა|არნი|არნო|არს)$"): "არი",
    re.compile(r"(?:ემ)$"): "ე",
    re.compile(r"(?:რამ|რას)$"): "რა",
    re.compile(r"(?:ათა|ამ|ას)$"): "ა",
    re.compile(r"(?:ნთა|ნმა|ნნი|ნნო)$"): "ნი",
}

# invariant words, proper nouns (no letter case to guard on), colliding verb
# forms, and stem-final -თა nouns; large because the -ას dative cell is worth
# >1000 correct UD tokens and its collisions proved finite
_EXCLUDED = frozenset(
    {
        "სანამ",
        "მხოლოდ",
        "მაგრამ",
        "საერთოდ",
        "სრულიად",
        "მუდამ",
        "საკმაოდ",
        "წერს",
        "გურამ",
        "დგას",
        "ზურგჩანთა",
        "ჩანთა",
        "ბალთა",
        "კალთა",
        "ამას",
        "იმას",
        "იქნას",
        "ათას",
        "ითქვას",
        "წარმოქმნას",
        "შეიქმნას",
        "ძვირფას",
        "აიხსნას",
        "თქვას",
        "გახსნას",
        "წარმოიქმნას",
        "დაგვირგვინას",
        "მიგნას",
        "შედარას",
        "დაატრიალას",
        "ააშენას",
        "დასურათას",
        "ჩაიხუტას",
        "მოგეტყნას",
        "მოგვეტყნას",
        "მოეტყნას",
        "მომეტყნას",
        "მოტყნას",
        "დაუკრას",
        "გაუშვას",
        "ზემოდ",
        "კერძოდ",
        "კონცერნი",
        "მანამ",
        "მჭიდროდ",
        "რათა",
        "საავტორო",
        "სადღეისოდ",
        "სატურნი",
        "უგზოუკვლოდ",
        "უშუალოდ",
        "ფერმა",
        "შოთა",
        "შორს",
        "წყვეტს",
        "პერიოდ",
        "მეთოდ",
        "ეპიზოდ",
        "უილიამ",
        "ვინემ",
        "უილემ",
        "ფრთა",
        "აღწერს",
        "მოიხმარს",
        "გაიმართა",
    }
)


def apply_ka(token: str) -> str | None:
    "Apply pre-defined rules for Georgian."
    # -ისას (genitive + adverbial) is out of reach for the case cells -- abstain
    if token.endswith("ისას"):
        return None
    return apply_rules(token, DEFAULT_RULES, min_len=4, hyphen=True, excluded=_EXCLUDED)
