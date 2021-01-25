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
    # tokenization and chaining
    assert simplemma.simple_tokenizer('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.') == ['Lorem', 'ipsum', 'dolor', 'sit', 'amet', ',', 'consectetur', 'adipiscing', 'elit', ',', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua', '.']
    mydata = simplemma.load_data('pt')
    assert simplemma.text_lemmatizer('Sou o intervalo entre o que desejo ser e os outros me fizeram.', mydata) == ['ser', 'o', 'intervalo', 'entre', 'o', 'que', 'desejo', 'ser', 'e', 'o', 'outro', 'me', 'fazer', '.']
    # error
    with pytest.raises(ValueError):
        simplemma.lemmatize('スパゲッティ', mydata, silent=False)


def test_convenience():
    """Test convenience functions."""
    text = 'Nous déciderons une fois arrivées.'
    langdata = simplemma.load_data('fr')
    # print(simplemma.text_lemmatizer(text, langdata, greedy=True))
    assert simplemma.text_lemmatizer(text, langdata, greedy=False) == ['lui', 'décider', 'un', 'fois', 'arrivée', '.']
    #assert simplemma.text_lemmatizer(text, langdata, greedy=True) == ['lui', 'décider', 'un', 'fois', 'arrivée', '.']
    text = 'Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas.'
    langdata = simplemma.load_data('es')
    assert(simplemma.text_lemmatizer(text, langdata, greedy=False)) == ['Pepa', 'y', 'Iván', 'son', 'uno', 'parejo', 'sentimental', ',', 'ambos', 'dedicar', 'al', 'doblaje', 'de', 'película', '.']
    assert simplemma.text_lemmatizer(text, langdata, greedy=True) == ['Pepa', 'y', 'Iván', 'son', 'uno', 'parejo', 'sentimental', ',', 'ambos', 'dedicar', 'al', 'doblaje', 'de', 'película', '.']

