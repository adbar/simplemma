"""Experimental language detection."""

import re

from collections import Counter
from operator import itemgetter
from typing import List, Optional, Tuple, Union

from .simplemma import LANG_DATA, _control_lang, _load_data, _return_lemma


SPLIT_INPUT = re.compile(r"[^\W\d_]{3,}")


def _update_lang_data(lang: Optional[Union[str, Tuple[str]]]) -> None:
    # convert string
    lang = _control_lang(lang)
    # load corresponding data
    global LANG_DATA
    if not LANG_DATA or tuple(l.code for l in LANG_DATA) != lang:
        LANG_DATA = _load_data(lang)


def prepare_text(text: str) -> List[str]:
    """Extract potential words, scramble them, extract the most frequent,
    some of the rest, and return at most 1000 tokens."""
    # generator expression to split the text
    counter = Counter(
        match[0] for match in SPLIT_INPUT.finditer(text) if not match[0].isupper()
    )
    # total = sum(counter.values())
    # if total > 100:
    #    # take about 10% of the tokens
    #    limit = int(sum(counter.values())/10)
    # else:
    #    limit = total
    # most_frequent_short = [item[0] for item in counter.most_common(10)]
    # rest = [t for t in set(tokens) if len(t) > 4 and t not in most_frequent][:990]
    return [item[0] for item in counter.most_common(1000)]


def in_target_language(text: str, lang: Optional[Tuple[str]] = None) -> float:
    """Determine which proportion of the text is in the target language(s)."""
    total = 0
    in_target = 0
    _update_lang_data(lang)
    for token in prepare_text(text):
        total += 1
        for l in LANG_DATA:
            candidate = _return_lemma(token, l.dict, greedy=True, lang=l.code)
            if candidate is not None:
                in_target += 1
                break
    if total > 0 and in_target > 0:
        return in_target / total
    return 0


def _return_default() -> List[Tuple[str, float]]:
    # todo: None if 'unk'?
    return [("unk", 1)]


def lang_detector(
    text: str, lang: Optional[Tuple[str]] = None, extensive: bool = False
) -> List[Tuple[str, float]]:
    """Determine which proportion of the text is in the target language(s)."""
    myresults = {}  # Dict[str, float]
    tokens = prepare_text(text)
    total_tokens = len(tokens)
    if total_tokens == 0:
        return _return_default()
    # iterate
    _update_lang_data(lang)
    for l in LANG_DATA:
        in_target = 0
        for token in tokens:
            candidate = _return_lemma(token, l.dict, greedy=extensive, lang=l.code)
            if candidate is not None:
                in_target += 1
        # compute results
        found_ratio = in_target / total_tokens
        myresults[l.code] = found_ratio
        unknown = 1 - found_ratio or 0.0
        if myresults.get("unk") is None or unknown < myresults["unk"]:
            myresults["unk"] = unknown
    results = sorted(myresults.items(), key=itemgetter(1), reverse=True)
    # post-processing
    if len(results) > 1:
        # in case of ex-aequo
        if extensive is False and results[0][1] == results[1][1]:
            results = lang_detector(text, lang=lang, extensive=True)
        # fallback
        if len(results) > 1 and results[0][1] == results[1][1]:
            return _return_default()
    return results
