# closed set of -ijen tokens whose -ij strip is wrong: verb infinitives
# (vrijen) and -ije nouns (balijen)
NL_IJEN_STOPS = (
    "vrijen",
    "vlijen",
    "benedijen",
    "betijen",
    "gedijen",
    "uitdijen",
    "verdijen",
    "vermaledijen",
    "balijen",
    "librijen",
)


def apply_nl(token: str) -> str | None:
    "Apply pre-defined rules for Dutch."
    # inspired by:
    # https://github.com/clips/pattern/blob/master/pattern/text/nl/inflect.py
    # nouns
    if len(token) > 6:
        # achterpagina's => achterpagina
        if token.endswith("'s"):
            return token[:-2]
        # mogelijkheden => mogelijkheid
        if token.endswith("heden") and "scheden" not in token:
            return token[:-5] + "heid"
        # boerderijen => boerderij
        if token.endswith("ijen") and not token.endswith(NL_IJEN_STOPS):
            return token[:-2]
    return None
