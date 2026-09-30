from .generic import SuffixRules

# no -ries, -ties or -ships cells on purpose (brasserie, beastie, amidships)
DEFAULT_RULES = SuffixRules(
    {
        "cy": "....cies",
        "dom": "doms",
        "ism": "isms",
        "ist": "ists",
        "ment": "ments",
        "nce": "nces",
        "tion": "tions",
        "um": "ums",
        "ize": "ized",
        "erve": "erves",
    },
)


apply_en = DEFAULT_RULES.apply
