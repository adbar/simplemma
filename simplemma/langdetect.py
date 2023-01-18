"""Experimental language detection."""

import re

from collections import Counter
from operator import itemgetter
from typing import List, Optional, Tuple

from .simplemma import Lemmatizer
from .dictionaries import DictionaryCache

SPLIT_INPUT = re.compile(r"[^\W\d_]{3,}")


def prepare_text(text: str, sample_size: int = 1000) -> List[str]:
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
    return [item[0] for item in counter.most_common(sample_size)]


def _return_default() -> List[Tuple[str, float]]:
    # todo: None if 'unk'?
    return [("unk", 1)]


class LaguageDetector:
    def __init__(self, dictionaryCache: Optional[DictionaryCache] = None) -> None:
        if dictionaryCache == None:
            dictionaryCache = DictionaryCache()
        assert isinstance(dictionaryCache, DictionaryCache)
        self.dictionaryCache: DictionaryCache = dictionaryCache
        self.lemmatizer = Lemmatizer(self.dictionaryCache)

    def in_target_language(
        self, text: str, lang: Optional[Tuple[str]] = None, sample_size: int = 1000
    ) -> float:
        """Determine which proportion of the text is in the target language(s)."""
        total = 0
        in_target = 0
        self.dictionaryCache.update_lang_data(lang)
        for token in prepare_text(text, sample_size):
            total += 1
            for l in self.dictionaryCache.data:
                candidate = self.lemmatizer._return_lemma(
                    token, l.dict, greedy=True, lang=l.code
                )
                if candidate is not None:
                    in_target += 1
                    break
        if total > 0 and in_target > 0:
            return in_target / total
        return 0

    def lang_detector(
        self,
        text: str,
        lang: Optional[Tuple[str]] = None,
        extensive: bool = False,
        sample_size: int = 1000,
    ) -> List[Tuple[str, float]]:
        """Determine which proportion of the text is in the target language(s)."""
        myresults = {}  # Dict[str, float]
        tokens = prepare_text(text, sample_size)
        total_tokens = len(tokens)
        if total_tokens == 0:
            return _return_default()
        # iterate
        self.dictionaryCache.update_lang_data(lang)
        for l in self.dictionaryCache.data:
            in_target = 0
            for token in tokens:
                candidate = self.lemmatizer._return_lemma(
                    token, l.dict, greedy=extensive, lang=l.code
                )
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
                results = self.lang_detector(text, lang=lang, extensive=True)
            # fallback
            if len(results) > 1 and results[0][1] == results[1][1]:
                return _return_default()
        return results
