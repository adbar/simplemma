import re

from .generic import apply_rules

# Georgian nominal declension: case/number markers attach to the bare stem;
# cells are anchored on the stem's final cluster since the bare markers are
# too ambiguous across stem classes. Dropped after per-alternative UD
# measurement: ედ/ევ/ომ (clipped bare-stem nominals whose gold RESTORES the
# nominative -ი, unreachable by suffix stripping). Kept with stoplisted
# collisions: ოდ (3 Greek loanwords), ემ (100% in-dict), რთა/რს (colliding
# verbs would just cascade to broader alternatives if the cells were
# dropped, so stoplisting is the only fix that removes the wrong outputs).
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

# Invariant adverbs/conjunctions, proper nouns (Georgian script has no
# letter case to guard on), verb forms colliding with nominal case endings,
# and lexicalized -ნთა/-ლთა nouns (ჩანთა, კალთა, ბალთა: stem-final -თა, not a
# case ending). Larger than the usual exception budget
# because the "-ას" dative cell is worth >1000 correct UD tokens (dropping
# it: 0 improved / 226 worsened) and its collisions proved finite -- the
# hybrid keep-with-stoplist rule, see training/README.rst.
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
    # -ისას (genitive + adverbial) needs the whole sequence replaced to
    # reach the citation form; a dedicated cell measures 97.3% -- abstain.
    if token.endswith("ისას"):
        return None
    return apply_rules(token, DEFAULT_RULES, min_len=4, hyphen=True, excluded=_EXCLUDED)
