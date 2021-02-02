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
    assert simplemma.lemmatize('spaghettini', mydata) == 'spaghettini'
    mydata = simplemma.load_data('it', 'fr')
    assert simplemma.lemmatize('spaghettis', mydata) == 'spaghetti'
    assert simplemma.lemmatize('spaghetti', mydata) == 'spaghetto'
    assert simplemma.lemmatize('spaghettis', mydata, greedy=True) == 'spaghetto'
    # tokenization and chaining
    assert simplemma.simple_tokenizer('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.') == ['Lorem', 'ipsum', 'dolor', 'sit', 'amet', ',', 'consectetur', 'adipiscing', 'elit', ',', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua', '.']
    mydata = simplemma.load_data('pt')
    assert simplemma.text_lemmatizer('Sou o intervalo entre o que desejo ser e os outros me fizeram.', mydata) == ['ser', 'o', 'intervalo', 'entre', 'o', 'que', 'desejo', 'ser', 'e', 'os', 'outro', 'me', 'fazer', '.']
    # error
    with pytest.raises(ValueError):
        simplemma.lemmatize('スパゲッティ', mydata, silent=False)


def test_convenience():
    """Test convenience functions."""
    # known words
    langdata = simplemma.load_data('en')
    assert simplemma.is_known('FanCY', langdata) is True
    assert simplemma.is_known('Fancy-String', langdata) is False
    # text lemmatization
    text = 'Nous déciderons une fois arrivées.'
    langdata = simplemma.load_data('fr')
    # print(simplemma.text_lemmatizer(text, langdata, greedy=True))
    assert simplemma.text_lemmatizer(text, langdata, greedy=False) == ['nous', 'décider', 'un', 'fois', 'arrivée', '.']
    text = 'Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas.'
    langdata = simplemma.load_data('es')
    assert(simplemma.text_lemmatizer(text, langdata, greedy=False)) == ['Pepa', 'y', 'Iván', 'son', 'uno', 'parejo', 'sentimental', ',', 'ambos', 'dedicar', 'al', 'doblaje', 'de', 'película', '.']
    assert simplemma.text_lemmatizer(text, langdata, greedy=True) == ['Pepa', 'y', 'Iván', 'son', 'uno', 'parejo', 'sentimental', ',', 'ambos', 'dedicar', 'al', 'doblaje', 'de', 'película', '.']


def test_subwords():
    """Test recognition and conversion of subword units."""
    mydata = simplemma.load_data('de')
    myword = 'mRNA-Impfstoffe'
    assert simplemma.lemmatize(myword, mydata, greedy=False) == 'mRNA-Impfstoff'
    myword = 'mRNA-impfstoffe'
    assert simplemma.lemmatize(myword, mydata, greedy=False) == 'mRNA-Impfstoff'
    # greedy subword
    myword = 'Impftermine'
    assert simplemma.lemmatize(myword, mydata, greedy=False) == 'Impftermine'
    assert simplemma.lemmatize(myword, mydata, greedy=True) == 'Impftermin'
    myword = 'Impfbeginn'
    assert simplemma.lemmatize(myword, mydata, greedy=False) == 'Impfbeginn'
    assert simplemma.lemmatize(myword, mydata, greedy=True) == 'Impfbeginn'
    myword = 'Hoffnungsmaschinen'
    assert simplemma.lemmatize(myword, mydata, greedy=False) == 'Hoffnungsmaschinen'
    assert simplemma.lemmatize(myword, mydata, greedy=True) == 'Hoffnungsmaschine'
    assert simplemma.lemmatize('börsennotierter', mydata, greedy=True) == 'börsennotiert'
    assert simplemma.lemmatize('journalistischer', mydata, greedy=True) == 'journalistisch'
    assert simplemma.lemmatize('rekordverdächtige', mydata, greedy=True) == 'rekordverdächtig'
    assert simplemma.lemmatize('Delegiertenstimmen', mydata, greedy=True) == 'Delegiertenstimme'
    assert simplemma.lemmatize('Koalitionskreisen', mydata, greedy=True) == 'Koalitionskreis'
    assert simplemma.lemmatize('Infektionsfälle', mydata, greedy=True) == 'Infektionsfall'
    assert simplemma.lemmatize('Corona-Einsatzstabes', mydata, greedy=True) == 'Corona-Einsatzstab'
    assert simplemma.lemmatize('venezolanische', mydata, greedy=True) == 'venezolanisch'
    #assert simplemma.lemmatize('wiederverwendbaren', mydata, greedy=True) == 'wiederverwendbar'
    #assert simplemma.lemmatize('Anspruchsberechtigten', mydata, greedy=True) == 'Anspruchsberechtigten'
    #assert simplemma.lemmatize('Beginn', mydata, greedy=True) == 'Beginn'
    #geheimdienstlich
