from .generic import SuffixRules

# -ries/-ties dropped: -erie/-tie (brasserie, beastie)
DEFAULT_RULES = SuffixRules(
    {
        "cy": "....cies",
        "dom": "doms",
        "ism": "isms",
        "ist": "ists",
        "ment": "ments",
        "nce": "nces",
        "ship": "ships",
        "tion": "tions",
        "um": "ums",
        "ize": "ized",
        "erve": "erves",
    },
)


apply_en = DEFAULT_RULES.apply
