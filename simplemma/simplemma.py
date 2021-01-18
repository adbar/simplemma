"""Main module."""


import lzma
import logging

from collections import OrderedDict
from pathlib import Path

import _pickle as cpickle


LOGGER = logging.getLogger(__name__)
LANGLIST = ['bg', 'ca', 'cs', 'cy', 'de', 'en', 'es', 'et', 'fa', 'fr', 'ga', 'gd', 'gl', 'gv', 'hu', 'it', 'pt', 'ro', 'ru', 'sk',  'sl', 'sv', 'uk'] # 'ast' must be checked


def _load_dict(langcode, listpath='lists'):
    mydict = dict()
    filename = listpath + '/' + langcode + '.txt'
    filepath = str(Path(__file__).parent / filename)
    with open(filepath , 'r', encoding='utf-8') as filehandle:
        for line in filehandle:
            line = line.strip()
            columns = line.split('\t')
            try:
                mydict[columns[1]] = columns[0]
            except IndexError:
                LOGGER.error(line)
    return OrderedDict(sorted(mydict.items()))


def _pickle_dict(langcode):
    mydict = _load_dict(langcode)
    LOGGER.debug('%s %s', langcode, len(mydict))
    filename = 'data/' + langcode + '.plzma'
    filepath = str(Path(__file__).parent / filename)
    with lzma.open(filepath, 'w') as filehandle:
        cpickle.dump(mydict, filehandle)


def _load_pickle(langcode):
    filename = 'data/' + langcode + '.plzma'
    filepath = str(Path(__file__).parent / filename)
    with lzma.open(filepath) as filehandle:
        return cpickle.load(filehandle)


def _return_lemma(token, datadict, greedy=True):
    candidate = None
    if token in datadict:
        candidate = datadict[token]
    elif token.lower() in datadict:
        candidate = datadict[token.lower()]
    # try further hops
    # not sure this is always a good idea, greediness switch added
    if candidate is not None and greedy is True:
        while candidate in datadict and len(datadict[candidate]) < len(candidate):
            candidate = datadict[candidate]
    return candidate


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


def lemmatize(token, lemmadata, greedy=True, silent=True):
    """Try to reduce a token to its lemma form according to the
       language list passed as input.
       Returns a string.
       Can raise ValueError by silent=False if no lemma has been found."""
    i = 1
    for language in lemmadata:
        candidate = _return_lemma(token, language, greedy)
        if candidate is not None:
            if i != 1:
                LOGGER.debug(token, candidate, 'found in %s', i)
            return candidate
        i += 1
    if silent is False:
        raise ValueError('Token not found: %s' % token)
    return token.lower()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    for listcode in LANGLIST:
        _pickle_dict(listcode)
