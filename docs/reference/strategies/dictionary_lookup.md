---
title: "DictionaryLookupStrategy: dictionary-based lemmatization"
description: "API reference for DictionaryLookupStrategy, which looks a token up in a language's dictionary, with case and apostrophe fallbacks."
---

# Dictionary Lookup Strategy

The primary strategy: look the token up in the language's dictionary, with fallbacks for casing and apostrophe variants. Everything else in the pipeline exists to handle what this one misses.

::: simplemma.strategies.dictionary_lookup
