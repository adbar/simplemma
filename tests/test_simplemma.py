#!/usr/bin/env python

"""Tests for `simplemma` package."""

import pytest

import simplemma



def test_readme():
    """Test function to verify readme examples."""
    mydata = simplemma.load_data('en')
    myword = 'masks'
    assert simplemma.lemmatize(myword, mydata) == 'mask'
    mydata = simplemma.load_data('de')
    mytokens = ['Hier', 'sind', 'Vaccines', '.']
    assert [simplemma.lemmatize(t, mydata) for t in mytokens] == ['hier', 'sein', 'Vaccines', '.']
    # greediness
    assert simplemma.lemmatize('angekündigten', mydata, greedy=False) == 'angekündigt'
    assert simplemma.lemmatize('angekündigten', mydata, greedy=True) == 'ankündigen'
    # chaining
    mydata = simplemma.load_data('de', 'en')
    assert [simplemma.lemmatize(t, mydata) for t in mytokens] == ['hier', 'sein', 'vaccine', '.']
    mydata = simplemma.load_data('it')
    assert simplemma.lemmatize('spaghettis', mydata) == 'spaghettis'
    mydata = simplemma.load_data('it', 'fr')
    assert simplemma.lemmatize('spaghettis', mydata) == 'spaghetti'
    assert simplemma.lemmatize('spaghetti', mydata) == 'spaghetto'
    mydata = simplemma.load_data('it')
    assert simplemma.lemmatize('spaghettini', mydata) == 'spaghettini'
    # error
    with pytest.raises(ValueError):
        simplemma.lemmatize('スパゲッティ', mydata, silent=False)


def test_convenience():
    """Test convenience functions."""
    text = 'Nous déciderons une fois arrivées.'
    langdata = simplemma.load_data('fr')
    assert simplemma.textlemmatize(text, langdata, greedy=False) == ['lui', 'décider', 'un', 'fois', 'arrivée', '.']
    #assert simplemma.textlemmatize(text, langdata, greedy=True) == ['lui', 'décider', 'un', 'fois', 'arrivée', '.']
    text = 'Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas.'
    langdata = simplemma.load_data('es')
    assert(simplemma.textlemmatize(text, langdata, greedy=False)) == ['Pepa', 'y', 'Iván', 'son', 'uno', 'parejo', 'sentimental', ',', 'ambos', 'dedicar', 'al', 'doblaje', 'de', 'película', '.']
    assert simplemma.textlemmatize(text, langdata, greedy=True) == ['Pepa', 'y', 'Iván', 'son', 'uno', 'parejo', 'sentimental', ',', 'ambos', 'dedicar', 'al', 'doblaje', 'de', 'película', '.']

