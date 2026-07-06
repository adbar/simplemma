import re

from .generic import apply_rules

# Pruned to the cells that hold >=99% in-dict: short elative/illative forms
# collide with plain nouns and the -dus paradigm with -dune adjectives, so
# both are dropped; only anchored variants that clear the bar are kept.
# Left out despite UD value (just under the bar): -liste, -misega, -imist.

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
    # UD gold for hyphenated compounds uses morpheme-boundary markers a
    # suffix rule can never reproduce (44% on real text) -- skip
    return apply_rules(token, DEFAULT_RULES, min_len=8, caps=True, hyphen=True)
