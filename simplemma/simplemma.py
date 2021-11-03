"""Main module."""


import lzma
import logging
import re

from difflib import ndiff
from functools import lru_cache
from pathlib import Path

import _pickle as cpickle

try: # as from __main__
    from .rules import apply_rules
    from .tokenizer import TOKREGEX
except ImportError:  # ModuleNotFoundError, Python >= 3.6
    pass


LOGGER = logging.getLogger(__name__)

LANGLIST = ['bg', 'ca', 'cs', 'cy', 'da', 'de', 'el', 'en', 'es', 'et', 'fa', 'fi', 'fr', 'ga', 'gd', 'gl', 'gv', 'hu', 'hy', 'id', 'it', 'ka', 'la', 'lb', 'lt', 'lv', 'mk', 'nb', 'nl', 'pl', 'pt', 'ro', 'ru', 'sk', 'sl', 'sv', 'tr', 'uk']

AFFIXLEN = 2 # >6 better for et, fi, hu, lt, ru, sk, tr
MINCOMPLEN = 4
MAXLENGTH = 20

SAFE_LIMIT = {'en', 'es', 'fr', 'ga', 'hu', 'it', 'pl', 'pt', 'ru', 'sk', 'tr'}
BETTER_LOWER = {'es', 'lt', 'pt', 'sk'}
# -PRO: 'et', 'fi'?


def _determine_path(listpath, langcode):
    filename = listpath + '/' + langcode + '.txt'
    return str(Path(__file__).parent / filename)


def _load_dict(langcode, listpath='lists', silent=True):
    filepath = _determine_path(listpath, langcode)
    return _read_dict(filepath, langcode, silent)


def _read_dict(filepath, langcode, silent):
    mydict, myadditions, i = {}, [], 0
    leftlimit = 2
    if langcode in SAFE_LIMIT:
        leftlimit = 1
    # load data from list
    with open(filepath , 'r', encoding='utf-8') as filehandle:
        for line in filehandle:
            columns = line.strip().split('\t')
            # invalid: remove noise
            # todo: exclude columns with punctuation!
            if len(columns) != 2 or len(columns[0]) < leftlimit or \
            line.startswith('-') or re.search(r'[+_]|[^ ]+ [^ ]+ [^ ]+', line) or \
            ':' in columns[1]:
                # or len(columns[1]) < 2:
                if silent is False:
                    LOGGER.warning('wrong format: %s', line.strip())
                continue
            # too long
            #if len(columns[1]) > MAXLENGTH:
            #    continue
            # process
            if columns[1] in mydict and mydict[columns[1]] != columns[0]:
                # prevent mistakes and noise coming from the lists
                dist1, dist2 = _levenshtein_dist(columns[1], mydict[columns[1]]), \
                    _levenshtein_dist(columns[1], columns[0])
                # fail-safe: delete potential false entry
                #if dist1 >= len(columns[1]) and dist2 >= len(columns[1]):
                #    del mydict[columns[1]]
                #    continue
                if dist1 == 0 or dist2 < dist1: # dist1 < 2
                    mydict[columns[1]] = columns[0]
                elif silent is False:
                    LOGGER.warning('diverging: %s %s | %s %s', columns[1], mydict[columns[1]], columns[1], columns[0])
                    LOGGER.debug('distances: %s %s', dist1, dist2)
            else:
                mydict[columns[1]] = columns[0]
                # deal with verbal forms (mostly)
                if langcode in ('es', 'et', 'fi', 'fr', 'it', 'lt'):
                    myadditions.append(columns[0])
                elif columns[0] not in mydict:
                    mydict[columns[0]] = columns[0]
                i += 1
    # overwrite
    for word in myadditions:
        mydict[word] = word
    LOGGER.debug('%s %s', langcode, i)
    return dict(sorted(mydict.items()))


def _pickle_dict(langcode):
    mydict = _load_dict(langcode)
    filename = 'data/' + langcode + '.plzma'
    filepath = str(Path(__file__).parent / filename)
    with lzma.open(filepath, 'w') as filehandle: # , filters=my_filters
        cpickle.dump(mydict, filehandle, protocol=4)
    LOGGER.debug('%s %s', langcode, len(mydict))


def _load_pickle(langcode):
    filename = 'data/' + langcode + '.plzma'
    filepath = str(Path(__file__).parent / filename)
    with lzma.open(filepath) as filehandle:
        return cpickle.load(filehandle)


@lru_cache(maxsize=4096)
def _levenshtein_dist(str1, str2):
    # https://codereview.stackexchange.com/questions/217065/calculate-levenshtein-distance-between-two-strings-in-python
    counter = {"+": 0, "-": 0}
    distance = 0
    for edit_code, *_ in ndiff(str1, str2):
        if edit_code == " ":
            distance += max(counter.values())
            counter = {"+": 0, "-": 0}
        else:
            counter[edit_code] += 1
    distance += max(counter.values())
    return distance


#def _define_greediness(langcode):
#    if langcode in ('bg', 'es', 'fr', 'ru', 'uk'):
#        return False
#    return True


def _simple_search(token, datadict):
    candidate = datadict.get(token)
    if candidate is None:
        # try upper or lowercase
        if token[0].isupper():
            candidate = datadict.get(token.lower())
        else:
            candidate = datadict.get(token.capitalize())
    return candidate


def _greedy_search(candidate, datadict, steps=2, distance=4):
    i = 0
    while candidate in datadict and (
        len(datadict[candidate]) < len(candidate) and
        _levenshtein_dist(datadict[candidate], candidate) <= distance
        ):
        candidate = datadict[candidate]
        i += 1
        if i >= steps:
            break
    return candidate


def _decompose(token, datadict, affixlen=0):
    candidate, plan_b = None, None
    if affixlen == 0:
        affixlen = AFFIXLEN
    # this only makes sense for languages written from left to right
    # AFFIXLEN or MINCOMPLEN can spare time for some languages
    for count in range(1, len(token)-(MINCOMPLEN-1)):
        part1, part1_aff, part2 = token[:-count], token[:-(count + affixlen)], token[-count:]
        lempart1 = _simple_search(part1, datadict)
        if lempart1 is not None:
            # maybe an affix? discard it
            if count <= affixlen:
                candidate = lempart1
                break
            # account for case before looking for second part
            if token[0].isupper():
                part2 = part2.capitalize()
            lempart2 = _simple_search(part2, datadict)
            if lempart2 is not None:
                #print('#', part1, part2, affixlen, count)
                # candidate must be shorter
                # try original case, then substitute
                if lempart2[0].isupper():
                    substitute = part2.lower()
                else:
                    substitute = part2.capitalize()
                # try other case
                newcandidate = _greedy_search(substitute, datadict)
                # shorten the second known part of the token
                if newcandidate and len(newcandidate) < len(part2):
                    candidate = part1 + newcandidate.lower()
                # backup: equal length or further candidates accepted
                if candidate is None:
                    # try without capitalizing
                    newcandidate = _simple_search(part2, datadict)
                    if newcandidate and len(newcandidate) <= len(part2):
                        candidate = part1 + newcandidate.lower()
                    # even greedier
                    # with capital letter?
                    elif len(lempart2) < len(part2) + affixlen:
                        plan_b = part1 + lempart2.lower()
                        #print(part1, part2, affixlen, count, newcandidate, planb)
                    #elif newcandidate and len(newcandidate) < len(part2) + affixlen:
                        #plan_b = part1 + newcandidate.lower()
                        #print(part1, part2, affixlen, count, newcandidate, planb)
                    #else:
                    #    print(part1, part2, affixlen, count, newcandidate)
                break
    return candidate, plan_b


def _dehyphen(token, datadict, greedy):
    splitted = re.split('([_-])', token)
    if len(splitted) > 1 and len(splitted[-1]) > 0:
        # try to find a word form without hyphen
        subcandidate = ''.join([t.lower() for t in splitted if t not in ('-', '_')])
        if token[0].isupper():
            subcandidate = subcandidate.capitalize()
        if subcandidate in datadict:
            return datadict[subcandidate]
        # decompose
        subcandidate = _simple_search(splitted[-1], datadict)
        # search further
        if subcandidate is None and greedy is True:
            subcandidate = _affix_search(splitted[-1], datadict)
        # return
        if subcandidate is not None:
            splitted[-1] = subcandidate
            return ''.join(splitted)
    return None


def _affix_search(wordform, datadict):
    for l in range(AFFIXLEN+1):
        candidate, plan_b = _decompose(wordform, datadict, affixlen=l)
        if candidate is not None:
            break
    # exceptionally accept a longer solution
    if candidate is None and plan_b is not None:
        candidate = plan_b
    return candidate


def _suffix_search(token, datadict):
    lastcount = 0
    for count in range(MINCOMPLEN, len(token)-(MINCOMPLEN-1)):
        #print(token[-count:], token[:-count], lastpart)
        part = _simple_search(token[-count:].capitalize(), datadict)
        if part is not None and len(part) <= len(token[-count:]):
            lastpart, lastcount = part, count
    if lastcount > 0:
        return token[:-lastcount] + lastpart.lower()
    return None


def _return_lemma(token, datadict, greedy=True, lang=None):
    # filters
    if token.isnumeric():
        return token
    # dictionary search
    candidate = _simple_search(token, datadict)
    # simple rules
    if candidate is None:
        candidate = apply_rules(token, lang)
    # decomposition
    if candidate is None: # and greedy is True
        candidate = _dehyphen(token, datadict, greedy)
    else:
        newcandidate = _dehyphen(candidate, datadict, greedy)
        if newcandidate is not None:
            candidate = newcandidate
    # stop here in some cases
    if len(token) <= 8 or greedy is False:
        return candidate
    # greedy subword decomposition: suffix/affix search
    if candidate is None:
        # greedier subword decomposition: suffix search with character in between
        candidate = _affix_search(token, datadict)
        # try something else
        if candidate is None:
            candidate = _suffix_search(token, datadict)
    # try further hops, not sure this is always a good idea
    else:
        candidate = _greedy_search(candidate, datadict)
    return candidate


def is_known(token, langdata):
    """Tell if a token is present in one of the loaded dictionaries.
       Case-insensitive, whole word forms only. Returns True or False."""
    for language in langdata:
        if _simple_search(token, language[1]) is not None:
            return True
    return False
    # suggestion:
    #return any(
    #    _simple_search(token, language[1]) is not None for language in langdata
    #)


def simple_tokenizer(text):
    """Simple regular expression adapted from NLTK.
       Takes a string as input and returns a list of tokens.
       Provided for convenience and educational purposes."""
    return TOKREGEX.findall(text)


def load_data(*langs):
    """Decompress und unpickle lemmatization rules.
       Takes one or several ISO 639-1 code language code as input.
       Returns a list of dictionaries."""
    mylist = []
    for lang in langs:
        if lang not in LANGLIST:
            LOGGER.error('language not supported: %s', lang)
            continue
        LOGGER.debug('loading %s', lang)
        mylist.append((lang, _load_pickle(lang)))
    return mylist


def lemmatize(token, langdata, greedy=False, silent=True):
    """Try to reduce a token to its lemma form according to the
       language list passed as input.
       Returns a string.
       Can raise ValueError by silent=False if no lemma has been found."""
    for i, language in enumerate(langdata, start=1):
        # determine default greediness
        #if greedy is None:
        #    greedy = _define_greediness(language)
        # determine lemma
        candidate = _return_lemma(token, language[1], greedy=greedy, lang=language[0])
        if candidate is not None:
            if i != 1:
                LOGGER.debug(token, candidate, 'found in %s', i)
            return candidate
    if silent is False:
        raise ValueError('Token not found: %s' % token)
    # try to simply lowercase and len(token) < 10
    if candidate is None and language[0] in BETTER_LOWER:
        return token.lower()
    return token


def text_lemmatizer(text, langdata, greedy=False, silent=True):
    """Convenience function to lemmatize a text using a simple tokenizer.
       Returns a list of tokens and lemmata."""
    return [lemmatize(t, langdata, greedy, silent) for t in simple_tokenizer(text)]


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    for listcode in LANGLIST:
        _pickle_dict(listcode)
