"""Tests for Simplemma's language detection utilities."""


from simplemma import load_data
from simplemma.langdetect import lang_detector


def test_detection():
    langdata = load_data('de', 'en')
    results = lang_detector('Dieser Satz ist auf Deutsch.', langdata, extensive=False)
    assert results[0][0] == 'de'
    results = lang_detector('Dieser Satz ist auf Deutsch.', langdata, extensive=True)
    assert results[0][0] == 'de'
