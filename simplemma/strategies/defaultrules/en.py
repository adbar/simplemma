from typing import Optional

ENGLISH_IES_ENDING = ("cies", "ries", "ties", "qies")
ENGLISH_S_ENDING = ("doms", "isms", "ists", "ments", "nces", "ships", "tions", "ums")


def apply_en(token: str) -> Optional[str]:
    "Apply pre-defined rules for English."
    # nouns
    if len(token) > 7 and token.endswith(ENGLISH_IES_ENDING):
        return token[:-3] + "y"
    if token.endswith(ENGLISH_S_ENDING):
        return token[:-1]
    if token.endswith("esses"):
        return token[:-2]
    if token.endswith("trices"):
        return token[:-3] + "x"
    # too much noise
    # if token.endswith("ae"):  # or token.endswith("as")
    #    return token[:-1]
    # if token.endswith("oes"):
    #    return token[:-2]
    # Pattern rules
    # if token.endswith("ies") and len(token) > 3 and token[-4] not in VOWELS:
    #    return token[:-3] + "y"  # complies => comply
    # if token.endswith(("sses", "shes", "ches", "xes")):
    #    return token[:-2]  # kisses => kiss
    # if token.endswith("erves"):
    #    return token[:-1]
    # if token.endswith("arves"):
    #    return token[:-3] + "f"

    # verbs endswith("ed"):
    #   if token.endswith("ated"):
    #       return token[:-4] + "ate"
    #   if token.endswith("ened"):
    #       return token[:-4] + "en"
    #   if token.endswith("fied"):
    #       return token[:-4] + "fy"
    #   if token.endswith("ized"):
    #       return token[:-4] + "ize"
    #   # Pattern rules
    #   if token.endswith("ied"):
    #       return token[:-3] + "y"  # envied => envy
    #   # -ed could be added
    return None
