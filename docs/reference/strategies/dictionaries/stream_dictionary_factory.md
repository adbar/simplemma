---
title: "StreamDictionaryFactory: low-memory, no dependencies"
description: "API reference for StreamDictionaryFactory, a stdlib-only low-memory backend that reads the shipped dictionary streams instead of loading them into RAM."
---

# Stream Dictionary Factory

The backend behind `low_memory=True`: it reads the shipped front-coded dictionary stream directly instead of building a full dict in RAM, using only the standard library and no on-disk cache.

::: simplemma.strategies.dictionaries.stream_dictionary_factory
