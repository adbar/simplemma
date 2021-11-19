"""Experimental language detection."""

import re

from collections import Counter

from .simplemma import _simple_search, _return_lemma  # load_data, LANGLIST


SPLIT_INPUT = re.compile(r'[^\W\d_]{5,}')


def prepare_text(text):
    """Extract potential words, scramble them, extract the most frequent,
       some of the rest, and return at most 1000 tokens."""
    counter = Counter(SPLIT_INPUT.findall(text))
    most_frequent = set([item[0] for item in counter.most_common(1000)])
    #rest = [t for t in set(tokens) if len(t) > 4 and t not in most_frequent][:990]
    #print(rest)
    return list(most_frequent) # + rest


def in_target_language(text, langdata):
    """Determine which proportion of the text is in the target language(s)."""
    total = 0
    in_target = 0
    for token in prepare_text(text):
        total += 1
        for language in langdata:
            candidate = _return_lemma(token, language[1], greedy=True, lang=language[0])
            if candidate is not None:
                in_target += 1
    return in_target/total


def lang_detector(text, langdata, extensive=False):
    """Determine which proportion of the text is in the target language(s)."""
    myresults = dict()
    found = set()
    tokens = prepare_text(text)
    for language in langdata:
        total = 0
        in_target = 0
        for token in tokens:
            total += 1
            if extensive is False:
                result = _simple_search(token, language[1])
            else:
                result = _return_lemma(token, language[1], greedy=True, lang=language[0])
            if result is not None:
                in_target += 1
                if token not in found:
                    found.add(token)
        myresults[language[0]] = in_target/total
    myresults['unk'] = (len(tokens)-len(found))/len(tokens)
    return sorted(myresults.items(), key=lambda kv: kv[1], reverse=True)
