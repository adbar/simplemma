from .generic import SuffixRules

# after https://github.com/clips/pattern/blob/master/pattern/text/nl/inflect.py
DEFAULT_RULES = SuffixRules(
    {
        # rules see the raw token, so every apostrophe glyph
        "": "'s ’s ʼs",
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
