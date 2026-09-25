from .generic import SuffixRules

# OOV invariants plus one pluralia-tantum conflict
_EXCLUDED = frozenset({"eventualno", "epiduralno", "totalno", "počitnice"})

# Slovenian adjective declension and a handful of noun/verb suffixes,
# mined lemma-first (99.73% in-dict).
DEFAULT_RULES = SuffixRules(
    {
        "nski": "nska",
        "jen": "jenih",
        "ski": "skega skimi skemu skima skem skim",
        "ten": "tnega tnih tni tne",
        "an": "anega anih",
        "en": "enega enimi",
        "čen": "čnega čnih",
        "nik": "nikom niku",
        "ost": "ostjo",
        "ati": "ajte ajmo ajta ajva amo",
        "nica": "nice nici nic",
        "cija": "cije cijo ciji",
        "anje": "anju",
        "alen": "alni alne alno",
        "jati": "jali jajo",
        "ka": "kami",
        "itev": "itve",
        "ik": "ikih",
        "ica": "ico",
        "tvo": "tva",
    },
    min_len=6,
    caps=True,
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_sl = DEFAULT_RULES.apply
