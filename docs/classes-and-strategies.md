---
title: "Custom lemmatizer classes and strategies"
description: "Build a custom Python lemmatizer with Simplemma's Lemmatizer and LanguageDetector classes, lemmatization strategies and dictionary factories."
---

# Classes and strategies

The functions shown in [Usage](usage.md) cover simple usage. Instantiating the classes gives more control.
`Lemmatizer` handles lemmatization and `LanguageDetector` language detection,
both through an implementation of the `LemmatizationStrategy` protocol.
`DefaultStrategy` combines several such strategies, among them
`DictionaryLookupStrategy`, which looks tokens up in a dictionary built by a
`DictionaryFactory`.

For example, to conserve RAM by limiting how many language dictionaries
stay cached (default: 8), pass a `cache_max_size` to
`DefaultDictionaryFactory`, wrap it in a `DefaultStrategy`, and hand that
to a `Lemmatizer` and/or `LanguageDetector`:

``` python
>>> from simplemma import LanguageDetector, Lemmatizer
>>> from simplemma.strategies import DefaultStrategy
>>> from simplemma.strategies.dictionaries import DefaultDictionaryFactory

>>> strategy = DefaultStrategy(dictionary_factory=DefaultDictionaryFactory(cache_max_size=5))
>>> Lemmatizer(lemmatization_strategy=strategy).lemmatize('doughnuts', lang='en')
'doughnut'
>>> LanguageDetector('la', lemmatization_strategy=strategy).proportion_in_target_languages("opera post physica posita (τὰ μετὰ τὰ φυσικά)")
0.6666666666666666
```

When no strategy finds a lemma, `Lemmatizer` calls its `fallback`, a plain
`(token, lang) -> str` function that gets the first requested language.
The default returns the token as-is (lowercased for bg and sk). To raise
on unknown tokens instead:

``` python
>>> def strict(token, lang):
...     raise ValueError(f"{token!r} not found for {lang}")
>>> lemmatizer = Lemmatizer(fallback=strict)
>>> lemmatizer.lemmatize('doughnuts', lang='en')
'doughnut'
>>> lemmatizer.lemmatize('qwxz', lang=('en', 'de'))
Traceback (most recent call last):
ValueError: 'qwxz' not found for en
```

Each strategy and factory has its own API page under
[Reference](reference/strategies/lemmatization_strategy.md). For the
low-memory dictionary backends and their memory/speed trade-offs, see
[Memory usage](memory-usage.md).
