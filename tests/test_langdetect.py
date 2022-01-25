"""Tests for Simplemma's language detection utilities."""


from simplemma import load_data
from simplemma.langdetect import in_target_language, lang_detector


def test_detection():
    langdata = load_data('de', 'en')
    # sanity checks
    assert lang_detector(' aa ', langdata, extensive=True) == [('unk', 1)]
    text = 'Test test'
    assert lang_detector(text, langdata, extensive=False) == [('unk', 1)]
    assert lang_detector(text, langdata, extensive=True) == [('unk', 1)]
    # language detection
    results = lang_detector('Dieser Satz ist auf Deutsch.', langdata, extensive=False)
    assert results[0][0] == 'de'
    results = lang_detector('Dieser Satz ist auf Deutsch.', langdata, extensive=True)
    assert results[0][0] == 'de'
    assert in_target_language('Diese Wörter', langdata) == 1

