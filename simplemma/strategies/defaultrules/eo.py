from .generic import SuffixRules

# invariant words whose tail matches a grammatical ending
_EXCLUDED = frozenset({"tamen", "neniu", "konstanta"})

# caps: foreign proper nouns collide with the endings (London -> *Londo)
DEFAULT_RULES = SuffixRules(
    {
        "i": "..ante ..inte ..onte ...ate ...ite ...ote ..anta ..inta ..onta as is os us u",
        "o": "ojn oj on",
        "a": "ajn aj an",
        "e": "en",
    },
    min_len=4,
    caps=True,
    excluded=_EXCLUDED,
)


apply_eo = DEFAULT_RULES.apply
