from .generic import SuffixRules

# -ries/-ties dropped: -erie/-tie (brasserie, beastie). -ships dropped: 96.7%
# in-dict (amidships, midships)
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
