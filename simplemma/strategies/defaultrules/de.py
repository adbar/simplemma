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

# Verb participles whose bare form is NOT its own dict lemma (dict itself
# redirects to the verb infinitive, e.g. abgespeckt -> abspecken), so
# PP_DE's "keep the bare participle as an adjective" default is wrong for
# these specific verbs -- unlike aufgebracht/eingebaut, which the dict
# treats as genuinely lexicalized adjectives (own entry, no redirect).
# Evidence: training/review_ladder.py rung "bespoke de" on pooled de_gsd/
# de_hdt/de_lit/de_pud, 2026-07.
PP_VERB_STOPS_DE = frozenset(
    {"abgespeckt", "mitgeliefert", "angewandt", "herausgebracht", "angekratzt"}
)

# feminine agent plural -erinnen -> -erin (Lehrerinnen -> Lehrerin). Only the
# -erinnen sub-pattern is handled: it is the productive deverbal agent suffix
# (streamen -> Streamer -> Streamerin -> Streamerinnen), so it captures the
# neologisms that are actually OOV, and it collides with almost no non-agent
# (the Rinne/Sinn/Kinn/Linnen/Beginn roots that make bare -innen ambiguous
# are -Xrinnen/-sinnen/-kinnen/... not -erinnen). Deliberately dropped: the
# -in/-or/-tin agents (Ärztinnen, Autorinnen, Studentinnen) -- an open
# homograph class with the noun roots above that needed a 43-entry stop-list
# for ~0 pipeline value (every common such agent is already in the
# dictionary; only the rare OOV one reaches the rules). -erinnen needs just
# the two dict-confirmed collisions below. Evidence: training/review_ladder.py
# rung "bespoke de" + a full-dictionary -erinnen scan (99.92%), 2026-07.
ERINNEN_STOPS_DE = frozenset({"Bardierinnen", "Gerinnen"})

# present-participle adjective declension: bedeutendem -> bedeutend. Only the
# -em/-es/-er endings, which German verbs never take -- the bare -e/-en would
# also strip the infinitive/1sg of -nd-stem verbs (versenden, verwende), an
# unresolvable homograph (absende vs wachsende), so they are left alone.
PART_END_DE = re.compile(r"^(.{2,}end)(?:em|es|er)$")

# Lexicalized agent-noun roots that collide with PART_END_DE: Anwender
# ("user", <- anwenden) and Vorsitzender ("chair(person)", <- vorsitzen)
# compound freely with any prefix (GSM-/Mac-/Windows-/Landesbezirks-/
# Vorstands-Anwender/Vorsitzender, ...) and are nouns, never participle-
# adjectives, in every attested form. Evidence: training/review_ladder.py
# rung "bespoke de" (10 of 19 real PART_END misses on pooled de_gsd/de_hdt/
# de_lit/de_pud, 2026-07).
PART_END_NOUN_STOPS_DE = ("anwend", "vorsitzend")

ENDING_CHARS_DE = {"e", "m", "n", "r", "s"}

# Named collisions between NOUN_ENDINGS_DE and specific proper/loan nouns
# whose citation form IS the surface form: -lingen toponyms (Reutlingen,
# Tuttlingen, ...) collide with the "-ling" agent-noun cell, Kaufbeuren
# (toponym) with "-eur", Ländereien (fixed collective plural) and
# Départements (French loanword, plural kept as lemma) with "-erei"/"-ment".
# Evidence: training/review_ladder.py rung 3 (de_gsd consistency scan).
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
            # apply pattern; no inflectional group -> claim the token as its own
            # lemma (citation-form noun), don't strip
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
