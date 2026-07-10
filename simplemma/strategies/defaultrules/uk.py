import re

from .generic import apply_rules

# Ukrainian verb conjugation and adjective declension, mined lemma-first
# (99.69% in-dict).
DEFAULT_RULES = {
    re.compile(r"(?:аймо|айте)$"): r"ати",
    re.compile(
        r"(?:тиметься|тимуться|тимемось|тимемося|тиметесь|тиметеся|тимемся"
        r"|тимешся|тимусь|тимуся)$"
    ): r"тися",
    re.compile(
        r"(?:́тимуть|́тимемо|́тимете|тимуть|тимемо|тимете|́тимем|́тимеш|тимем"
        r"|тимеш|́тиме|́тиму|тиме|тиму)$"
    ): r"ти",
    re.compile(
        r"(?:ува́ть|ува́ла|ува́ло|ува́ли|увала|ували|ува́в|ують|уєте|уймо|уйте"
        r"|уємо|уючи|у́єм|у́єш|уєш|уєм|у́й|у́ю|у́є|ує|уй)$"
    ): r"увати",
    re.compile(r"(?:ва́вши|вавши|вало|вать|вав)$"): r"вати",
    re.compile(r"(?:чнім|чним|чною|чній|чна|чне|чну|чні)$"): r"чний",
    re.compile(r"(?:ького|ькому|ьким|ької|ькій|ькім|ьке|ькі)$"): r"ький",
    re.compile(r"(?:ннями|нням|ннях)$"): r"ння",
    re.compile(r"(?:ності|носте)$"): r"ність",
    re.compile(r"(?:ними|ного|ному|них|ної|ная|неє)$"): r"ний",
    re.compile(r"(?:кими|ких|кая|кеє|кії)$"): r"кий",
    re.compile(r"(?:ивши|или)$"): r"ити",
    re.compile(r"(?:цію|ціє)$"): r"ція",
    re.compile(r"(?:иком|иків)$"): r"ик",
    re.compile(r"(?:істю)$"): r"ість",
    re.compile(r"(?:енню)$"): r"ення",
    re.compile(r"(?:ією)$"): r"ія",
}

# invariant adverbs whose own dictionary lemma is themselves
_EXCLUDED = frozenset({"повністю", "вручну"})


def apply_uk(token: str) -> str | None:
    "Apply pre-defined rules for Ukrainian."
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
