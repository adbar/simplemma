from typing import Optional


def apply_nl(token: str) -> Optional[str]:
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
        if token.endswith("ijen"):
            return token[:-2]
        # brieven => brief
        if token.endswith("ieven"):
            return token[:-3] + "f"
        # too much noise:
        # bacteriën => bacterie
        # if token.endswith("iën"):
        #    return token[:-2] + "e"
        # flessen => fles
        # if token.endswith("essen"):
        #    return token[:-3]
        # chinezen => chinees
        # if token.endswith("ezen") and token[-5] not in VOWELS:
        #    return token[:-4] + "ees"
        # if token.endswith("bele"):
        #    return token[:-1]
    return None
