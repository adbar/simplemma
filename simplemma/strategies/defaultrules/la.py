import re

from .generic import apply_rules

# Latin: verb conjugation (1st principal part -o, per-conjugation thematic
# vowel: -o/-eo/-io and the compound -ro/-ero/-to/-co/-no/-lo/-go/-ico stem
# classes) and noun/adjective declension (5 declensions incl. the productive
# -turus/-urus future participle, -ndus/-andus/-endus gerundive, -tio/-io
# abstract nouns). Latin's declension system has many overlapping 3rd-
# declension classes; several short/bare alternatives were dropped after
# the combined-ruleset check surfaced cross-class collisions (e.g. the
# genitive -dos/-dorum of -dus nouns colliding with unrelated words, -onibus
# colliding with -o 3rd-declension nouns, -rat/-arim causing idempotence
# chains on rare words). Caps guard is strict: proper nouns/names are the
# bulk of Latin OOV tokens and this dictionary does not decline them.
# Trimmed to the top rule groups covering ~90% of rule firings.
# Stem classes sharing one ending paradigm are merged into single
# capture-group rules ((x|y)endings$ -> \1...), verified output-identical
# to the unmerged form over the full dictionary.
DEFAULT_RULES = {
    re.compile(
        r"(?:rassemus|rassetis|rabamus|rabatis|rabimus|rabitis|raratis|raremus|raretis|rarimus|raritis|rassent|rabant|rabunt|rarant|rarent|rarint|rarunt|rassem|rasses|rasset|rastis|ratote|ramus|rabam|rabas|rabat|rabis|rabit|ranto|raras|rarat|rarem|rares|raret|rarim|rarit|rasse|rasti|rant|rabo|raro)$"
    ): r"ro",
    re.compile(
        r"(?:erabamus|erabatis|erabimus|erabitis|eraremus|eraretis|eraratis|erarimus|eraritis|erassent|eraveram|eraveras|eraverat|eraverim|eraveris|eraverit|eravimus|eravisse|eravisti|erabant|erabunt|erarent|eratote|erarant|erarint|erarunt|erassem|erasses|erasset|erastis|eravere|eravero|eramus|eratis|erabam|erabas|erabat|erabis|erabit|eranto|erarem|erares|eraret|eraras|erarat|erarim|erarit|erasse|erasti|eravit|erant|erabo|eraro|eravi|eras|erat)$"
    ): r"ero",
    re.compile(
        r"(?:taverant|taverint|taverunt|tavissem|tavisses|tavisset|tavistis|tassemus|tassetis|tabamus|tabatis|tabimus|tabitis|taremus|taretis|taveram|taveras|taverat|taverim|taveris|taverit|tavimus|tavisse|tavisti|taratis|tarimus|taritis|tassent|tabant|tabunt|tarent|tatote|tavere|tavero|tarant|tarint|tarunt|tassem|tasses|tasset|tastis|tamus|tabam|tabas|tabat|tabis|tabit|tanto|tarem|tares|taret|tavit|taras|tarat|tarim|tarit|tasse|tasti|tant|tabo|tavi|taro|tat)$"
    ): r"to",
    re.compile(
        r"(?:cassemus|cassetis|caverant|caverint|caverunt|cavissem|cavisses|cavisset|cavistis|cabamus|cabatis|cabimus|cabitis|caratis|caremus|caretis|carimus|cassent|caveram|caveras|caverat|caverim|caveris|caverit|cavimus|cavisse|cavisti|cabant|cabunt|carant|carent|carint|carunt|cassem|casses|casset|castis|catote|cavere|cavero|cabam|cabas|cabat|cabit|camus|caras|carat|carem|cares|caret|carim|carit|casse|casti|cavit|cunto|cavi|cabo|cant|cunt|cat)$"
    ): r"co",
    re.compile(
        r"(?:nassemus|nassetis|naverant|naverint|naverunt|navissem|navisses|navisset|navistis|nabamus|nabatis|nabimus|nabitis|naratis|naremus|narimus|naritis|nassent|naveram|naveras|naverat|naverim|naveris|naverit|navimus|navisse|navisti|nabant|nabunt|narant|narent|narint|narunt|nassem|nasses|nasset|nastis|natote|navere|navero|nabam|nabas|nabat|nabis|nabit|namus|nanto|narat|naret|narim|narit|nasse|nasti|navit|nabo|nant|naro|navi|nat)$"
    ): r"no",
    re.compile(r"(?:tionibus|tionem|tiones|tionis|tionum|tione|tioni)$"): r"tio",
    re.compile(
        r"(?:gassemus|gassetis|gaverant|gaverint|gaverunt|gavissem|gavisses|gavisset|gavistis|gabamus|gabatis|gabimus|gabitis|garatis|garemus|garetis|garimus|garitis|gassent|gaveram|gaveras|gaverat|gaverim|gaveris|gaverit|gavimus|gavisse|gavisti|gabant|gabunt|garant|garent|garint|garunt|gassem|gasses|gasset|gastis|gatote|gavere|gavero|gamus|gunto|gabam|gabas|gabat|gabis|gabit|ganto|garas|garat|garem|gares|garet|garim|garit|gasse|gasti|gavit|gant|gunt|gabo|garo|gavi|gat)$"
    ): r"go",
    re.compile(
        r"(?:laverant|laverint|laverunt|lavissem|lavisses|lavisset|lavistis|lassemus|lassetis|labamus|labatis|labimus|labitis|laveram|laveras|laverat|laverim|laveris|laverit|lavimus|lavisse|lavisti|larimus|laritis|lassent|labant|labunt|latote|lavere|lavero|larint|larunt|lasset|labam|labas|labat|labit|lamus|lavit|larim|larit|lasti|lant|lat)$"
    ): r"lo",
    re.compile(
        r"(?:escebant|escendum|escerent|escamus|escatis|escebam|escebas|escebat|escemus|escerem|esceres|esceret|escetis|escunto|escant|escent|escere|escunt|escam|escas|escat|esces|escet|escis|esce)$"
    ): r"esco",
    re.compile(
        r"(?:ciebamur|ciebamus|ciebaris|ciebatis|ciebatur|ciamini|ciantur|ciebant|ciebare|ciemini|cientur|ciuntor|ciuntur|ciamur|ciamus|ciaris|ciatur|ciebam|ciebar|ciebas|ciebat|ciemur|ciemus|cieris|cietis|cietur|ciunto|ciant|ciare|cient|ciere|ciunt|ciar|ciat|ciet)$"
    ): r"cio",
    re.compile(r"(ien|tan|cen|ran|den)(?:tibus|tium|tem|tes|te|ti)$"): r"\1s",
    re.compile(
        r"(?:assemus|assetis|averant|abamus|abatis|abimus|arimus|assent|averas|averat|abant|abunt|arint|arunt|assem|asses|asset|atote|abam|abas|abat|abis|abit|arit|asse|asti|unto|abo)$"
    ): r"o",
    re.compile(r"(tur|sur)(?:orum|arum|is|ae|as|os|am|i|o|e|a)$"): r"\1us",
    re.compile(
        r"(?:abamini|abantur|abimini|abuntur|abamur|abaris|aberis|abimur|abare|abere|antor|abar|abor)$"
    ): r"or",
    re.compile(
        r"(?:andarum|andorum|andae|andam|andas|andis|andos|anda|ande)$"
    ): r"andus",
    re.compile(
        r"(?:ionibus|iebamus|iebatis|iebant|ionem|iones|ionis|ionum|iamus|iemus|iebam|iebas|iebat|iunto|ione|ioni|iant|ient|iunt|iat|iet)$"
    ): r"io",
    re.compile(r"(?:antibus|antium|ante|anti)$"): r"ans",
    re.compile(r"(?:endarum|endorum|endae|endos|enda)$"): r"endus",
    re.compile(
        r"(?:ndamini|ndamur|ndamus|ndaris|ndatis|ndatur|ndant|ndare|ndas|ndat)$"
    ): r"ndo",
    re.compile(
        r"(?:simarum|simorum|simae|simam|simas|simis|simos|sima|simi|simo)$"
    ): r"simus",
    re.compile(r"(?:ioribus|iorem|iores|ioris|iora|iore|iori)$"): r"ior",
    re.compile(r"(?:tatarum|tatorum|tatae|tatam|tatas|tatos|tata)$"): r"tatus",
    re.compile(r"(rat|cat)(?:arum|ae|as|os|am|i|a)$"): r"\1us",
    re.compile(r"(?:toribus|torem|tores|toris|tore)$"): r"tor",
    re.compile(r"(?:latarum|latae|latam|latas|latos|lati)$"): r"latus",
    re.compile(r"(?:urarum|urorum|urae|uram|uros|urum|ure|uri)$"): r"urus",
    re.compile(r"(?:atarum|atuum|atam|atos|atui)$"): r"atus",
    re.compile(r"(?:ebimus|ebitis|eamus|ebunt|etote|eant|ebit|eat|ebo)$"): r"eo",
    re.compile(r"(?:nsibus|nsium|nsem|nses|nsia|nse|nsi)$"): r"nsis",
    re.compile(r"(?:osarum|osorum|osae|osam|osas|osos|osum|osa|oso)$"): r"osus",
    re.compile(r"(?:arum)$"): r"is",
}


def apply_la(token: str) -> str | None:
    "Apply pre-defined rules for Latin."
    if len(token) < 6 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
