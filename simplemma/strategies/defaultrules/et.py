import re

from .generic import apply_rules

# Pruned to the cells that hold >=99% in-dict: the short elative/illative forms
# (-mist/-misse/-list/-ikus/-dus*) collide with plain nouns, and the -dus
# paradigm collapses under -dune adjective homography, so both are dropped.
# UD validation (2026-07) found the BARE forms were rightly dropped
# (list/umist stay <=72% in-dict) but several anchored variants clear the bar
# and were missing: -lise/-lisele/-lisel (>=99.2%), -iliste/-likest (100%),
# -amist (99.2%), -duses (100%), and stem-anchored -ilist (100%).
# Deliberately left out despite UD value, just under the bar or needing
# special-casing disproportionate to their size: -liste (98.5%),
# -misega (99.0, -mis noun stems), -imist (96.8, -im/-žiim loans).

DEFAULT_RULES = {
    # adjectives -line https://en.wiktionary.org/wiki/-line
    re.compile(
        r"(?:lisesse|lisest|liselt|lisele|lisil|lisel|lises|lised|lisi|lise)$"
    ): "line",
    re.compile(r"likest$"): "lik",
    re.compile(r"duses$"): "dus",
    # partitive -ilist only with >=5 stem chars: the short collisions
    # (detailist, stiilist) are all short stems
    re.compile(r"(.{5,})ilist$"): r"\1iline",
    re.compile(r"(?:iliste)$"): "iline",
    re.compile(r"(?:amist)$"): "amine",
    # verbal nouns -mine https://en.wiktionary.org/wiki/-mine
    re.compile(
        r"(?:mistesse|misteta|mistest|misteni|mistena|mistelt|mistele|misteks|mistega|misesse|mistes|mistel|miseta|misest|miseni|misena|miselt|misele|miseks|miste|mises|misel|mised|mise)$"
    ): "mine",
    # -lik/-nik nouns https://en.wiktionary.org/wiki/-lik
    re.compile(
        r"(?:ikkudele|ikkudel|ikuta|ikuni|ikuna|ikult|ikule|ikuks|ikuga|iketa|ikeni|ikena|ikelt|ikele|ikeks|ikul|ikud|ikku|ikke|iku)$"
    ): "ik",
    # -kond nouns https://en.wiktionary.org/wiki/-kond
    re.compile(
        r"(?:kondadesse|kondadest|kondadelt|kondadele|kondadega|kondades|kondadel|konnata|konnast|konnalt|konnaks|konnaga|kondade|konnas|konnal|kondi|konda)$"
    ): "kond",
}


def apply_et(token: str) -> str | None:
    "Apply pre-defined rules for Estonian."
    if len(token) < 8 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
