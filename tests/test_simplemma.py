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
    assert simplemma.text_lemmatizer('Sou o intervalo entre o que desejo ser e os outros me fizeram.', mydata) == ['ser', 'o', 'intervalo', 'entre', 'o', 'que', 'desejo', 'ser', 'e', 'o', 'outro', 'me', 'fazer', '.']
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
    assert(simplemma.text_lemmatizer(text, langdata, greedy=False)) == ['pepa', 'y', 'iván', 'son', 'uno', 'parejo', 'sentimental', ',', 'ambos', 'dedicar', 'al', 'doblaje', 'de', 'película', '.']
    assert simplemma.text_lemmatizer(text, langdata, greedy=True) == ['pepa', 'y', 'iván', 'son', 'uno', 'parejo', 'sentimental', ',', 'ambos', 'dedicar', 'al', 'doblaje', 'de', 'película', '.']


def test_subwords():
    """Test recognition and conversion of subword units."""
    mydata = simplemma.load_data('de')
    assert simplemma.lemmatize('OBI', mydata, greedy=True) == 'OBI'
    assert simplemma.lemmatize('mRNA-Impfstoffe', mydata, greedy=False) == 'mRNA-Impfstoff'
    assert simplemma.lemmatize('mRNA-impfstoffe', mydata, greedy=True) == 'mRNA-Impfstoff'
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
    assert simplemma.lemmatize('Delegiertenstimmen', mydata, greedy=True) == 'Delegiertenstimme'
    assert simplemma.lemmatize('Koalitionskreisen', mydata, greedy=True) == 'Koalitionskreis'
    assert simplemma.lemmatize('Infektionsfälle', mydata, greedy=True) == 'Infektionsfall'
    assert simplemma.lemmatize('Corona-Einsatzstabes', mydata, greedy=True) == 'Corona-Einsatzstab'
    assert simplemma.lemmatize('Clearinghäusern', mydata, greedy=True) == 'Clearinghaus'
    assert simplemma.lemmatize('Mittelstreckenjets', mydata, greedy=True) == 'Mittelstreckenjet'
    assert simplemma.lemmatize('Länderministerien', mydata, greedy=True) == 'Länderministerium'
    assert simplemma.lemmatize('Gesundheitsschutzkontrollen', mydata, greedy=True) == 'Gesundheitsschutzkontrolle'
    assert simplemma.lemmatize('Nachkriegsjuristen', mydata, greedy=True) == 'Nachkriegsjurist'
    assert simplemma.lemmatize('insulinproduzierende', mydata, greedy=True) == 'insulinproduzierend'
    assert simplemma.lemmatize('Qualifikationsrunde', mydata, greedy=True) == 'Qualifikationsrunde'
    assert simplemma.lemmatize('krisensichere', mydata, greedy=True) == 'krisensicher'
    assert simplemma.lemmatize('ironischerweise', mydata, greedy=True) == 'ironischerweise'
    assert simplemma.lemmatize('Landespressedienstes', mydata, greedy=True) == 'Landespressedienst'
    assert simplemma.lemmatize('Lehrerverbänden', mydata, greedy=True) == 'Lehrerverband'
    assert simplemma.lemmatize('Terminvergaberunden', mydata, greedy=True) == 'Terminvergaberunde'
    assert simplemma.lemmatize('Gen-Sequenzierungen', mydata, greedy=True) == 'Gen-Sequenzierung'
    assert simplemma.lemmatize('wiederverwendbaren', mydata, greedy=True) == 'wiederverwendbar'
    assert simplemma.lemmatize('Spitzenposten', mydata, greedy=True) == 'Spitzenposten'
    assert simplemma.lemmatize('I-Pace', mydata, greedy=True) == 'I-Pace'
    #assert simplemma.lemmatize('Anspruchsberechtigten', mydata, greedy=True) == 'Anspruchsberechtigter'
    #assert simplemma.lemmatize('Lichtbild-Ausweis', mydata, greedy=True) == 'Lichtbildausweis'
    #assert simplemma.lemmatize('zweitstärkster', mydata, greedy=True) == 'zweitstärkste'
    #assert simplemma.lemmatize('Bürgerschaftsabgeordneter', mydata, greedy=True) == 'Bürgerschaftsabgeordneter'
    #assert simplemma.lemmatize('Grünenvorsitzende', mydata, greedy=True) == 'Grünenvorsitzende'
    #assert simplemma.lemmatize('Pharmagrößen', mydata, greedy=True) == 'Pharmagroßer'


def test_tokenizer():
    # tokenization and chaining
    # problem here
    assert simplemma.simple_tokenizer('200er-Inzidenz 1.000er-Inzidenz') == ['200er-Inzidenz', ' 1.', '000er-Inzidenz']


