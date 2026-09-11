from .generic import SuffixRules

# invariant words, proper nouns (no letter case to guard on), colliding verb
# forms, and stem-final -თა nouns; large because the -ას dative cell is worth
# >1000 correct UD tokens and its collisions proved finite
_EXCLUDED = frozenset(
    (
        "სანამ მხოლოდ მაგრამ საერთოდ სრულიად მუდამ საკმაოდ წერს გურამ დგას "
        "ზურგჩანთა ჩანთა ბალთა კალთა ამას იმას იქნას ათას ითქვას წარმოქმნას "
        "შეიქმნას ძვირფას აიხსნას თქვას გახსნას წარმოიქმნას დაგვირგვინას მიგნას "
        "შედარას დაატრიალას ააშენას დასურათას ჩაიხუტას მოგეტყნას მოგვეტყნას "
        "მოეტყნას მომეტყნას მოტყნას დაუკრას გაუშვას ზემოდ კერძოდ კონცერნი მანამ "
        "მჭიდროდ რათა საავტორო სადღეისოდ სატურნი უგზოუკვლოდ უშუალოდ ფერმა შოთა "
        "შორს წყვეტს პერიოდ მეთოდ ეპიზოდ უილიამ ვინემ უილემ ფრთა აღწერს მოიხმარს "
        "გაიმართა".split()
    )
)

# Georgian nominal declension, anchored on the stem's final cluster (bare
# case markers are too ambiguous). ედ/ევ/ომ dropped (gold restores the
# nominative -ი, unreachable by stripping); colliding verbs are stoplisted
# rather than cells dropped (they would just cascade to broader cells).
DEFAULT_RULES = SuffixRules(
    {
        "ტი": "ტთა ტმა ტნი ტნო ტს",
        "ლი": "ლთა ლმა ლნი ლნო ლს",
        "რი": "რთა რნი რნო რს",
        "ო": "ოთა ოდ ოვ",
        "ორი": "ორთა ორნი ორნო ორო ორს",
        "სტი": "სტთა სტმა სტნი სტნო სტს",
        "ია": "იათა იად იავ იამ იას",
        "ელი": "ელთა ელმა ელნი ელნო ელს",
        "სი": "სთა სნი სნო სს",
        "ერი": "ერთა ერმა ერნი ერნო ერს",
        "არი": "ართა არმა არნი არნო არს",
        "ე": "ემ",
        "რა": "რამ რას",
        "ა": "ათა ამ ას",
        "ნი": "ნთა ნმა ნნი ნნო",
    },
    # -ისას (genitive + adverbial) is out of reach for the case cells -- abstain
    stops="ისას",
    min_len=4,
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_ka = DEFAULT_RULES.apply
