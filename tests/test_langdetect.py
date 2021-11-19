"""Tests for Simplemma's language detection utilities."""


from simplemma import load_data
from simplemma.langdetect import in_target_language, lang_detector


def test_detection():
    langdata = load_data('de', 'en')
    results = lang_detector('Dieser Satz ist auf Deutsch.', langdata, extensive=False)
    assert results[0][0] == 'de'
    results = lang_detector('Dieser Satz ist auf Deutsch.', langdata, extensive=True)
    assert results[0][0] == 'de'
    assert in_target_language('Diese Wörter', langdata) == 1
    text = 'Test test'
    assert lang_detector(text, langdata, extensive=False) == lang_detector(text, langdata, extensive=True)
