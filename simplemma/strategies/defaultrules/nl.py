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
        # boerderijen => boerderij (vrijen/vlijen are verb infinitives)
        if token.endswith("ijen") and not token.endswith(("vrijen", "vlijen")):
            return token[:-2]
        # below the 99% bar, left out:
        # "ieven"->[:-3]+"f" 96% (-ieve adjective plurals: executieven, retrospectieven)
        # "iën"->[:-2]+"e", "essen"->[:-3], "ezen"->[:-4]+"ees", "bele"->[:-1]
    return None
