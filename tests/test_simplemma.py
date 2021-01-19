#!/usr/bin/env python

"""Tests for `simplemma` package."""

import pytest

import simplemma



def test_readme():
    """Test function to verify readme examples."""
    mydata = simplemma.load_data('de')
    mytokens = ['Hier', 'sind', 'Tokens']
    myoutput = [simplemma.lemmatize(t, mydata) for t in mytokens]
    assert myoutput == ['hier', 'sein', 'tokens']
    # greediness
    assert simplemma.lemmatize('angekündigten', mydata, greedy=False) == 'angekündigt'
    assert simplemma.lemmatize('angekündigten', mydata, greedy=True) == 'ankündigen'
    # chaining
    mydata = simplemma.load_data('de', 'en')
    assert simplemma.lemmatize('Tokens', mydata) == 'token'
    mydata = simplemma.load_data('en')
    assert simplemma.lemmatize('spaghetti', mydata) == 'spaghetti'
    mydata = simplemma.load_data('en', 'it')
    assert simplemma.lemmatize('spaghetti', mydata) == 'spaghetto'
    mydata = simplemma.load_data('en', 'it')
    assert simplemma.lemmatize('spaghettini', mydata) == 'spaghettini'
    # error
    with pytest.raises(ValueError):
        simplemma.lemmatize('スパゲッティ', mydata, silent=False)


def test_convenience():
    """Test convenience functions."""
    text = 'Nous déciderons une fois arrivées.'
    langdata = simplemma.load_data('fr')
    assert simplemma.textlemmatize(text, langdata, greedy=False) == ['se', 'décider', 'un', 'fois', 'arriver', '.']
    #assert simplemma.textlemmatize(text, langdata) == simplemma.textlemmatize(text, langdata, greedy=False)
    text = 'Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas.'
    langdata = simplemma.load_data('es')
    print(simplemma.textlemmatize(text, langdata))
    assert simplemma.textlemmatize(text, langdata) == ['pepa', '-er', 'iván', 'ser', 'uno', 'parejo', 'sentimental', ',', 'ambos', 'dedicarse', 'al', 'doblaje', 'dar', 'película', '.'] # dedicar/dedicarse

