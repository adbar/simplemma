ENGLISH_IES_ENDING = ("cies",)  # ries/ties dropped: -erie/-tie (brasserie, beastie)
ENGLISH_S_ENDING = ("doms", "isms", "ists", "ments", "nces", "ships", "tions", "ums")


def apply_en(token: str) -> str | None:
    "Apply pre-defined rules for English."
    # nouns
    if len(token) > 7 and token.endswith(ENGLISH_IES_ENDING):
        return token[:-3] + "y"
    if token.endswith(ENGLISH_S_ENDING):
        return token[:-1]
    # verbs
    if token.endswith("ized"):
        return token[:-4] + "ize"
    if token.endswith("erves"):
        return token[:-1]
    # below the 99% bar, left out:
    # "esses"->[:-2] 98.9% (finesse/outfinesse loanword plurals, no clean stop)
    # "trices"->[:-3]+"x" (dict noise, n=4)
    # "fied"->[:-4]+"fy" 98.8% (archaic -fie golds: calefie, exemplifie)
    # "ated"/"ened"/"ied"/"ae"/"oes"/"sses|shes|ches|xes" all <99
    return None
