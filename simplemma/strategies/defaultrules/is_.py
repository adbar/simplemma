from .generic import SuffixRules

# Icelandic adjective declension/comparison and definite noun forms, mined
# lemma-first (99.70% in-dict).
DEFAULT_RULES = SuffixRules(
    {
        "egur": (
            "egastrar egastur egastan egastar egastir egastra egastri egustum"
            " egasta egasti egasts egustu egrar egust egri egan egir egra egt egu"
            " egs eg"
        ),
        "ing": "ingunni inguna ingin ingu",
        "gur": "gurinn",
        "r": "rsins",
        "legur": "legi",
        "un": "unin",
        "a": "aðu",
    },
    min_len=6,
    caps=True,
    hyphen=True,
)


apply_is = DEFAULT_RULES.apply
