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
    with open(filepath , 'r', encoding='utf-8') as filehandle:
        for line in filehandle:
            columns = line.strip().split('\t')
            if ' ' in line or '+' in line or len(columns) != 2 or \
                len(columns[0]) < 1 or len(columns[1]) < 1:
                if silent is False:
                    LOGGER.warning('wrong format: %s', line.strip())
                continue
            if columns[1] in mydict and mydict[columns[1]] != columns[0]:
                dist1, dist2 = _levenshtein_dist(columns[1], mydict[columns[1]]), \
                    _levenshtein_dist(columns[1], columns[0])
                if dist1 == 0 or dist2 < dist1:
                    mydict[columns[1]] = columns[0]
                elif silent is False:
                    LOGGER.warning('diverging: %s %s | %s %s', columns[1], mydict[columns[1]], columns[1], columns[0])
                    LOGGER.debug('distances: %s %s', dist1, dist2)
            else:
                # mydict[columns[0]] = columns[0]
                mydict[columns[1]] = columns[0]
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


def _return_lemma(token, datadict, greedy=True):
    candidate = None
    if token in datadict:
        candidate = datadict[token]
    elif token.lower() in datadict:
        candidate = datadict[token.lower()]
    # try further hops
    # not sure this is always a good idea, greediness switch added
    if candidate is not None and greedy is True:
        i = 0
        while candidate in datadict and (
            _levenshtein_dist(datadict[candidate], candidate) <= 2
            or len(datadict[candidate]) < len(candidate)
            ):
            candidate = datadict[candidate]
            i += 1
            if i >= 3:
                break
    return candidate


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


def lemmatize(token, langdata, greedy=True, silent=True):
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


def text_lemmatizer(text, langdata, greedy=True, silent=True):
    """Convenience function to lemmatize a text using a simple tokenizer.
       Returns a list of tokens and lemmata."""
    return [lemmatize(t, langdata, greedy, silent) for t in simple_tokenizer(text)]


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    for listcode in LANGLIST:
        _pickle_dict(listcode)
