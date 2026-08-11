---
title: "Reducing memory usage of a Python lemmatizer"
description: "Reduce the memory footprint of multilingual lemmatization in Python with Simplemma's low_memory flag and its trie and stream dictionary backends."
---

# Memory usage

Where low memory usage matters more than lemmatization and detection
speed, the quickest way in is the `low_memory` flag, available on
`lemmatize`, `text_lemmatizer`, `lemma_iterator`, `is_known`, `langdetect`
and `in_target_language`:

``` python
>>> from simplemma import lemmatize
>>> lemmatize('doughnuts', lang='en', low_memory=True)
'doughnut'
```

This selects the stdlib-only `StreamDictionaryFactory`: the most
memory-frugal backend, reading the dictionary stream directly with no
full-dict build spike and no on-disk cache. `TrieDictionaryFactory` reaches
a lower *steady-state* footprint but spikes and writes to disk on first
use, so it is never auto-selected. Request it explicitly (see below).
`DefaultStrategy` accepts the same flag, though not together with an
explicit `dictionary_factory`:

``` python
>>> from simplemma import Lemmatizer
>>> from simplemma.strategies import DefaultStrategy

>>> strategy = DefaultStrategy(low_memory=True)
>>> Lemmatizer(lemmatization_strategy=strategy).lemmatize('doughnuts', lang='en')
'doughnut'
```

The three backends trade memory against speed as follows (German, ~1.1M
dictionary entries, with figures varying by language and hardware). Lookups are
single and uncached, then end-to-end through `Lemmatizer`'s result cache
over the German UD-HDT treebank (3.5M tokens, 200k unique):

| Backend | Peak RAM | Load time | Uncached lookup | Cached lookup | Extra dependency |
| --- | --- | --- | --- | --- | --- |
| `DefaultDictionaryFactory` | ~175 MB | ~0.6 s | fastest (baseline) | fastest (baseline) | none |
| `TrieDictionaryFactory` | ~30 MB | ~1 ms warm¹ | ~2.5× slower | ~1.2× slower | `marisa-trie` |
| `StreamDictionaryFactory` | ~50 MB | ~0.6 s | ~18× slower | ~6× slower | none |

¹ The first use of a language builds its trie from the shipped dictionary,
taking a few seconds and briefly needing as much memory as
`DefaultDictionaryFactory` would, then caches it on disk. On a machine
without enough memory to build it, build it elsewhere on the same CPU
architecture and copy the cache directory over.

The RAM saving compounds with every additional language kept loaded, since
`DefaultDictionaryFactory` holds each cached language's full dict in memory.
German is near the largest shipped dictionary though, and the figures include
a fixed Python baseline, so smaller languages add less than the absolute
numbers suggest.

To force a backend instead of relying on `low_memory=True`, pass it
explicitly: `DefaultStrategy(dictionary_factory=TrieDictionaryFactory())`
or `DefaultStrategy(dictionary_factory=StreamDictionaryFactory())`, both
importable from `simplemma.strategies.dictionaries`.

For the classes these backends plug into, see
[Classes and strategies](classes-and-strategies.md).
