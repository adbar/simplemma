from .generic import SuffixRules

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
)


apply_is = DEFAULT_RULES.apply
