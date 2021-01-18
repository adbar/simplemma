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
    

