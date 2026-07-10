import re

NOUN_ENDINGS_DE = re.compile(
    r"(?:erei|heit|keit|ion|schaft|tät|[^jlz]ung)(en)?$|"
    r"(?:euse|icen|logie)(n)?$|"
    r"(?:bold|[^hkl]ling|ment)(e?[ns]?)?$|"
    r"(?:ikus)(sen?)?$|"
    r"(?:erl|iker|[^e]iter)([ns])?$|"
    r"(?:gramm|[^ä]nom)(e?s|en)?$|"
    r"(?:eur)(en?|s)?$|"
    r"(?:ar|lein|stan|um)(s)?$",
    re.I,
)


ADJ_ENDINGS_DE = re.compile(
    r"^(.{4,})"
    r"(artig|esk|oid|op|phil|phob|selig|schig)"
    r"(?:er|e?st)?(?:e|em|en|er|es)?$"
)

PLUR_ORTH_DE = re.compile(r"(?:Innen|\*innen|\*Innen|-innen|_innen)$")

PP_DE = re.compile(r"^(.{2,}ge.+?[^aes]t)(?:e|em|er|es)$")

# participles whose dict lemma is the verb infinitive (abgespeckt -> abspecken),
# so PP_DE's keep-as-adjective output is wrong for them
PP_VERB_STOPS_DE = frozenset(
    {"abgespeckt", "mitgeliefert", "angewandt", "herausgebracht", "angekratzt"}
)

# feminine agent plural -erinnen -> -erin (Lehrerinnen -> Lehrerin); the broader
# -innen agents (Ärztinnen) are an open homograph class and left to the dictionary
ERINNEN_STOPS_DE = frozenset({"Bardierinnen", "Gerinnen"})

# present-participle adjective declension (bedeutendem -> bedeutend); only
# -em/-es/-er, which verbs never take -- bare -e/-en would strip -nd-stem verbs
PART_END_DE = re.compile(r"^(.{2,}end)(?:em|es|er)$")

# agent-noun roots that compound freely and are never participle-adjectives
PART_END_NOUN_STOPS_DE = ("anwend", "vorsitzend")

ENDING_CHARS_DE = {"e", "m", "n", "r", "s"}

# proper/loan nouns whose citation form IS the surface form (-lingen toponyms
# vs the -ling cell, Kaufbeuren vs -eur, Ländereien/Départements fixed plurals)
_NOUN_STOPS_DE = frozenset(
    {
        "Reutlingen",
        "Solingen",
        "Flözlingen",
        "Überlingen",
        "Tuttlingen",
        "Kaufbeuren",
        "Ländereien",
        "Départements",
    }
)


def apply_de(token: str) -> str | None:
    "Apply pre-defined rules for German."
    if len(token) < 7:
        return None

    # nouns
    if token[0].isupper():
        if token in _NOUN_STOPS_DE:
            return None
        # noun endings/suffixes: regex search
        if match := NOUN_ENDINGS_DE.search(token):
            # no inflectional group -> the token is its own lemma
            ending = next((g for g in match.groups() if g), None)
            return token[: -len(ending)] if ending else token
        # inclusive speech
        # Binnen-I: ArbeitnehmerInnenschutzgesetz?
        if PLUR_ORTH_DE.search(token):
            return PLUR_ORTH_DE.sub(":innen", token)
        # feminine agent plural: Lehrerinnen -> Lehrerin
        if token.endswith("erinnen") and token not in ERINNEN_STOPS_DE:
            return token[:-3]

    # mostly adjectives and verbs
    elif token[-1] in ENDING_CHARS_DE:
        if adj_match := ADJ_ENDINGS_DE.match(token):
            return (adj_match[1] + adj_match[2]).lower()
        if pp_match := PP_DE.match(token):
            stem = pp_match[1].lower()
            if stem not in PP_VERB_STOPS_DE:
                return stem
        if part_match := PART_END_DE.match(token):
            if not part_match[1].lower().endswith(PART_END_NOUN_STOPS_DE):
                return part_match[1]

    return None
