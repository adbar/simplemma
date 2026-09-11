from .generic import SuffixRules

# after https://github.com/clips/pattern/blob/master/pattern/text/nl/inflect.py
DEFAULT_RULES = SuffixRules(
    {
        "": "'s",
        "heid": "heden",
        "ij": "ijen",
    },
    # -scheden nouns, -ijen infinitives and -ije nouns
    stops=(
        "scheden vrijen vlijen benedijen betijen gedijen uitdijen verdijen "
        "vermaledijen balijen librijen"
    ),
    min_len=7,
)


apply_nl = DEFAULT_RULES.apply
