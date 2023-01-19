"""Experimental language detection."""

import re

from collections import Counter
from operator import itemgetter
from typing import List, Optional, Tuple

from .lemmatizer import Lemmatizer
from .dictionary_factory import DictionaryFactory

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
    def __init__(self, dictionaryFactory: Optional[DictionaryFactory] = None) -> None:
        if dictionaryFactory == None:
            dictionaryFactory = DictionaryFactory()
        assert isinstance(dictionaryFactory, DictionaryFactory)
        self.dictionaryFactory: DictionaryFactory = dictionaryFactory
        self.lemmatizer = Lemmatizer(self.dictionaryFactory)

    def detect_coverage_of_languages(
        self, text: str, lang: Optional[Tuple[str]] = None, sample_size: int = 1000
    ) -> float:
        """Determine which proportion of the text is in the target language(s)."""
        total = 0
        in_target = 0
        dictionaries = self.dictionaryFactory.get_dictionaries(lang)
        for token in prepare_text(text, sample_size):
            total += 1
            for lang_code, dictionary in dictionaries.items():
                candidate = self.lemmatizer._return_lemma(
                    token, dictionary, greedy=True, lang=lang_code
                )
                if candidate is not None:
                    in_target += 1
                    break
        if total > 0 and in_target > 0:
            return in_target / total
        return 0

    def detect_languages(
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
        dictionaries = self.dictionaryFactory.get_dictionaries(lang)
        for lang_code, dictionary in dictionaries.items():
            in_target = 0
            for token in tokens:
                candidate = self.lemmatizer._return_lemma(
                    token, dictionary, greedy=extensive, lang=lang_code
                )
                if candidate is not None:
                    in_target += 1
            # compute results
            found_ratio = in_target / total_tokens
            myresults[lang_code] = found_ratio
            unknown = 1 - found_ratio or 0.0
            if myresults.get("unk") is None or unknown < myresults["unk"]:
                myresults["unk"] = unknown
        results = sorted(myresults.items(), key=itemgetter(1), reverse=True)
        # post-processing
        if len(results) > 1:
            # in case of ex-aequo
            if extensive is False and results[0][1] == results[1][1]:
                results = self.detect_languages(text, lang=lang, extensive=True)
            # fallback
            if len(results) > 1 and results[0][1] == results[1][1]:
                return _return_default()
        return results
