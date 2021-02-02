"""Main module."""


import lzma
import logging
import re

from collections import OrderedDict
from difflib import ndiff
from functools import lru_cache
from pathlib import Path

import _pickle as cpickle

LOGGER = logging.getLogger(__name__)

LANGLIST = ['bg', 'ca', 'cs', 'cy', 'da', 'de', 'en', 'es', 'et', 'fa', 'fi', 'fr', 'ga', 'gd', 'gl', 'gv', 'hu', 'id', 'it', 'ka', 'la', 'lb', 'lt', 'lv', 'nl', 'pt', 'ro', 'ru', 'sk', 'sl', 'sv', 'tr', 'uk', 'ur']

TOKREGEX = re.compile(r'(?:[\$§]? ?[\d\.,]+€?|\w[\w*-]*|[,;:\.?!¿¡‽⸮…()\[\]–{}—/‒_“„”’′″‘’“”\'"«»=+−×÷•·])')


def _load_dict(langcode, listpath='lists', silent=True):
    mydict, i = dict(), 0
    filename = listpath + '/' + langcode + '.txt'
    filepath = str(Path(__file__).parent / filename)
    leftlimit = 2
    if langcode in ('es', 'sk'):
        leftlimit = 1
    # load data from list
    with open(filepath , 'r', encoding='utf-8') as filehandle:
        for line in filehandle:
            columns = line.strip().split('\t')
            # invalid: remove noise
            if len(columns) != 2 or len(columns[0]) < leftlimit or \
            line.startswith('-') or re.search(r'[+_]|[^ ]+ [^ ]+ [^ ]+', line):
                # or len(columns[1]) < 2:
                if silent is False:
                    LOGGER.warning('wrong format: %s', line.strip())
                continue
            # process
            if columns[1] in mydict and mydict[columns[1]] != columns[0]:
                # capitalized vs rest
                #if mydict[columns[1]] == columns[0].capitalize():
                #    mydict[columns[1]] = columns[0]
                #    continue
                # prevent mistakes and noise coming from the lists
                dist1, dist2 = _levenshtein_dist(columns[1], mydict[columns[1]]), \
                    _levenshtein_dist(columns[1], columns[0])
                if dist1 == 0  or dist2 < dist1: # dist1 < 2
                    mydict[columns[1]] = columns[0]
                elif silent is False:
                    LOGGER.warning('diverging: %s %s | %s %s', columns[1], mydict[columns[1]], columns[1], columns[0])
                    LOGGER.debug('distances: %s %s', dist1, dist2)
            else:
                mydict[columns[1]] = columns[0]
                if columns[0] not in mydict:
                    mydict[columns[0]] = columns[0]
                i += 1
    LOGGER.debug('%s %s', langcode, i)
    return OrderedDict(sorted(mydict.items()))


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
    candidate = None
    if token in datadict:
        candidate = datadict[token]
    elif token.lower() in datadict:
        candidate = datadict[token.lower()]
    elif token.capitalize() in datadict:
        candidate = datadict[token.capitalize()]
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
    candidate = None
    for count, prefix in enumerate(token, start=1):
        length = count + affixlen
        if len(token[:-length]) == 0:
            continue
        part1, part2 = _simple_search(token[:-length], datadict), \
                       _simple_search(token[-count:].capitalize(), datadict)
        if part1 is not None:
            # print(part1, part2, affixlen, count)
            # maybe an affix? discard it
            if affixlen == 0 and count <= 2:
                candidate = part1
                break
            elif part2 is not None:
                newcandidate = _greedy_search(part2, datadict, steps=2, distance=4)
                # shorten the second known part of the token
                if len(newcandidate) < len(token[-count:]):
                    candidate = ''.join([token[:-count], newcandidate.lower()])
                else:
                    newcandidate = _greedy_search(part2.capitalize(), datadict, steps=2, distance=4)
                    # shorten the second known part of the token
                    if len(newcandidate) < len(token[-count:]):
                        candidate = ''.join([token[:-count], newcandidate.lower()])
                    else:
                        # don't destroy anything more
                        candidate = token
                break
    return candidate


def _return_lemma(token, datadict, greedy=True):
    candidate = _simple_search(token, datadict)
    # decompose
    if candidate is None: # and greedy is True
        splitted = re.split('([_-])', token)
        if len(splitted) > 1 and len(splitted[-1]) > 0:
            subcandidate = _simple_search(splitted[-1], datadict)
            if subcandidate is not None:
                splitted[-1] = subcandidate
                candidate = ''.join(splitted)
            elif greedy is True:
                subcandidate = _decompose(splitted[-1], datadict, affixlen=0)
                if subcandidate is not None:
                    splitted[-1] = subcandidate
                    candidate = ''.join(splitted)
    # stop here in some cases
    if len(token) <= 9 or greedy is False:
        #if candidate is None and len(token) <= 3:
        #if not 'de' in langdata and not 'fr' in langdata:
        #    candidate = token.lower()
        return candidate
    # greedy subword decomposition: suffix search
    if candidate is None:
        # find break point
        candidate = _decompose(token, datadict, affixlen=0)
        # greedier subword decomposition: suffix search with character in between
        if candidate is None:
             candidate = _decompose(token, datadict, affixlen=1)
    # try further hops, not sure this is always a good idea
    else:
        candidate = _greedy_search(candidate, datadict)
    return candidate


def is_known(token, langdata):
    """Tell if a token is present in one of the loaded dictionaries.
       Case-insensitive, whole word forms only. Returns True or False."""
    for language in langdata:
        if _simple_search(token, language) is not None:
            return True
    return False


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
        mylist.append(_load_pickle(lang))
    return mylist


def lemmatize(token, langdata, greedy=False, silent=True):
    """Try to reduce a token to its lemma form according to the
       language list passed as input.
       Returns a string.
       Can raise ValueError by silent=False if no lemma has been found."""
    i = 1
    for language in langdata:
        # determine default greediness
        #if greedy is None:
        #    greedy = _define_greediness(language)
        # determine lemma
        candidate = _return_lemma(token, language, greedy)
        if candidate is not None:
            if i != 1:
                LOGGER.debug(token, candidate, 'found in %s', i)
            return candidate
        i += 1
    if silent is False:
        raise ValueError('Token not found: %s' % token)
    return token


def text_lemmatizer(text, langdata, greedy=False, silent=True):
    """Convenience function to lemmatize a text using a simple tokenizer.
       Returns a list of tokens and lemmata."""
    return [lemmatize(t, langdata, greedy, silent) for t in simple_tokenizer(text)]


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    for listcode in LANGLIST:
        _pickle_dict(listcode)
