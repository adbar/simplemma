import re

from .generic import apply_rules

# Icelandic: adjective declension/comparison (-egur/-legur/-gur/-skur/-kur
# families, matching lb.py's shape) and definite-article-suffixed noun
# forms (Icelandic postpositive article: -inn/-sins/-unin/...).
#
# Only "-sins" (bare genitive-definite marker) was dropped via the
# automated drop-bad-cells loop -- this file needed almost no cleanup,
# unlike the Romance builds.
#
# is_modern's own dict-convention agreement is only ~59% (see
# ud_eval.reliability), so absolute UD accuracy is not a meaningful
# validation signal here -- only the old-vs-new diff-token audit is
# (training/diff_audit.py --worktree). No known rules-level collision with
# the "-lega" adverb class that blocks is's AFFIX_LANGS membership (see
# affix-langs-audit notes) -- that decision is independent of this file.
DEFAULT_RULES = {
    re.compile(
        r"(?:egastrar|egastan|egastar|egastir|egastra|egastri|egastur|egustum|egasta|egasti|egasts|egustu|egrar|egust|egan|egir|egra|egri|egs|egt|egu|eg)$"
    ): r"egur",
    re.compile(
        r"(?:legastan|legastar|legastir|legastra|legastri|legastur|legasta|legasti|legasts|legrar|legan|legir|legra|legri|legi|legs|legt|leg)$"
    ): r"legur",
    re.compile(
        r"(?:skastrar|skastan|skastar|skastir|skastra|skastri|skastur|skasta|skasti|skasts|skrar|skara|skari|skir|skri|skt)$"
    ): r"skur",
    re.compile(r"(?:ingarnar|ingunni|inguna|ingin|ingu)$"): r"ing",
    re.compile(
        r"(?:mannanna|manninum|mannsins|mönnunum|manninn|mennina|mönnum|manni|manns|menn)$"
    ): r"maður",
    re.compile(
        r"(?:gastrar|gastan|gastar|gastir|gastra|gastri|gastur|gurinn|gasta|gasti|gasts)$"
    ): r"gur",
    re.compile(r"(?:tandist|tanna|tisti|tiði|tan)$"): r"ta",
    re.compile(
        r"(?:kastrar|kastan|kastar|kastir|kastra|kastri|kastur|kurinn|krar|kri)$"
    ): r"kur",
    re.compile(r"(?:landist|lnanna|lanna|laðu|lan)$"): r"la",
    re.compile(r"(?:anninum|ennina|enn)$"): r"aður",
    re.compile(r"(?:ngarnar)$"): r"ng",
    re.compile(r"(?:andist|astu|aðu|an)$"): r"a",
    re.compile(r"(?:naðrar|nanna|nandi|naðan|naðra|naðs|naðu|nan)$"): r"na",
    re.compile(r"(?:junnar|jurnar|janna|junum|junni|juna|jum|jan|jur|ju)$"): r"ja",
    re.compile(r"(?:ursins|urinn|urs)$"): r"ur",
    re.compile(r"(?:uninni|unina|unin)$"): r"un",
    re.compile(r"(?:aranum|arann|arans)$"): r"ari",
    re.compile(r"(?:ðurinn)$"): r"ður",
    re.compile(r"(?:turinn)$"): r"tur",
    re.compile(r"(?:ingnum)$"): r"ingur",
    re.compile(r"(?:isins|inu)$"): r"i",
    re.compile(r"(?:tsins|ts)$"): r"t",
    re.compile(r"(?:ðsins|ðs)$"): r"ð",
    re.compile(r"(?:rsins|rs)$"): r"r",
    re.compile(r"(?:kandi|kaðu|kan)$"): r"ka",
    re.compile(r"(?:gsins)$"): r"g",
    re.compile(r"(?:ksins)$"): r"k",
    re.compile(r"(?:kanum|kann)$"): r"ki",
    re.compile(r"(?:skan)$"): r"ska",
    re.compile(r"(?:ðiði)$"): r"ða",
    re.compile(r"(?:ran)$"): r"ra",
}


# Closed-class collisions found via UD validation: invariant directional/
# manner adverbs ending in -an (norðan "from the north", hvaðan "whence",
# framan, austan, sunnan, framundan, gjarnan "willingly"), present-
# participle-derived invariant adjectives/adverbs (mismunandi "various",
# vonandi "hopefully"), loksins "finally" (a narrow -ksins alt distinct
# from the dropped bare -sins cell), and a few compound nouns without an
# established simpler form (reiknilíkan, millitekjur, vellíðan).
_EXCLUDED = frozenset(
    {
        "mismunandi",
        "vonandi",
        "tilvonandi",
        "gjarnan",
        "norðan",
        "hvaðan",
        "loksins",
        "framan",
        "framundan",
        "austan",
        "reiknilíkan",
        "millitekjur",
        "vellíðan",
        "sunnan",
    }
)


def apply_is(token: str) -> str | None:
    "Apply pre-defined rules for Icelandic."
    if len(token) < 6 or token[0].isupper() or "-" in token or token in _EXCLUDED:
        return None

    return apply_rules(token, DEFAULT_RULES)
