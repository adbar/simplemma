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

# feminine agent plural -innen -> -in (Lehrerinnen -> Lehrerin). A word ends
# -innen for two unrelated reasons, so non-agents are kept out two ways: the
# productive -inn/-inne roots (Spinne, Gewinn, Dschinn) matched as suffixes,
# plus a closed set of Rinne/Sinn/Beginn/Kinn/Linnen compounds whose dative
# plural collides with the agent suffix. (Broad -rinnen/-sinnen/-ginnen stops
# were dropped: they blocked ~440 real agents -- Autorinnen, Königinnen,
# Archäologinnen -- to protect the ~40 non-agents now listed explicitly.)
INNEN_STOPS_DE = ("spinnen", "winnen", "dschinnen")
_INNEN_NONAGENT_DE = frozenset(
    {
        "Abflussrinnen",
        "Ansinnen",
        "Bardierinnen",
        "Beginnen",
        "Besinnen",
        "Bettlinnen",
        "Brautlinnen",
        "Dachrinnen",
        "Doppelkinnen",
        "Entrinnen",
        "Entsinnen",
        "Ersinnen",
        "Fahrrinnen",
        "Fernsinnen",
        "Frohsinnen",
        "Frühlingsbeginnen",
        "Gehörsinnen",
        "Gerinnen",
        "Geruchssinnen",
        "Geschmackssinnen",
        "Jahresbeginnen",
        "Kursbeginnen",
        "Linksinnen",
        "Nachsinnen",
        "Nahsinnen",
        "Nebensinnen",
        "Pinkelrinnen",
        "Pissrinnen",
        "Regenrinnen",
        "Saisonbeginnen",
        "Schulbeginnen",
        "Schwachsinnen",
        "Sehsinnen",
        "Semesterbeginnen",
        "Spurrinnen",
        "Unterkinnen",
        "Verkehrssinnen",
        "Verrinnen",
        "Wochenbeginnen",
        "Zerrinnen",
    }
)

# present-participle adjective declension: bedeutendem -> bedeutend. Only the
# -em/-es/-er endings, which German verbs never take -- the bare -e/-en would
# also strip the infinitive/1sg of -nd-stem verbs (versenden, verwende), an
# unresolvable homograph (absende vs wachsende), so they are left alone.
PART_END_DE = re.compile(r"^(.{2,}end)(?:em|es|er)$")

ENDING_CHARS_DE = {"e", "m", "n", "r", "s"}


def apply_de(token: str) -> str | None:
    "Apply pre-defined rules for German."
    if len(token) < 7:
        return None

    # nouns
    if token[0].isupper():
        # noun endings/suffixes: regex search
        if match := NOUN_ENDINGS_DE.search(token):
            # apply pattern; no inflectional group -> claim the token as its own
            # lemma (citation-form noun), don't strip
            ending = next((g for g in match.groups() if g), None)
            return token[: -len(ending)] if ending else token
        # inclusive speech
        # Binnen-I: ArbeitnehmerInnenschutzgesetz?
        if PLUR_ORTH_DE.search(token):
            return PLUR_ORTH_DE.sub(":innen", token)
        # feminine agent plural: Lehrerinnen -> Lehrerin
        if token.endswith("innen") and not (
            token.lower().endswith(INNEN_STOPS_DE) or token in _INNEN_NONAGENT_DE
        ):
            return token[:-3]

    # mostly adjectives and verbs
    elif token[-1] in ENDING_CHARS_DE:
        if adj_match := ADJ_ENDINGS_DE.match(token):
            return (adj_match[1] + adj_match[2]).lower()
        if pp_match := PP_DE.match(token):
            return pp_match[1].lower()
        if part_match := PART_END_DE.match(token):
            return part_match[1]

    return None
