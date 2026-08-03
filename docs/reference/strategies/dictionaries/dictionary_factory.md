---
title: "DictionaryFactory API and the default backend"
description: "API reference for the DictionaryFactory protocol and DefaultDictionaryFactory, which loads the shipped lemmatization dictionaries into memory."
---

# Dictionary Factory

A `DictionaryFactory` supplies the form-to-lemma mapping for one language. `DefaultDictionaryFactory` loads the shipped dictionaries into plain dicts and caches a bounded number of languages at a time. See [Memory usage](../../../memory-usage.md) for the alternatives.

::: simplemma.strategies.dictionaries.dictionary_factory
