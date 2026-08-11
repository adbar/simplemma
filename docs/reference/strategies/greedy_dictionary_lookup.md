---
title: "GreedyDictionaryLookupStrategy: iterated lookup"
description: "API reference for GreedyDictionaryLookupStrategy, which repeats dictionary lookup on its own output to reach a shorter base form."
---

# Greedy Dictionary Lookup Strategy

Applies dictionary lookup repeatedly, feeding each result back in to reach a shorter base form, for instance a German past participle down to its infinitive. Closer to stemming than the plain lookup, and bounded by length and distance limits.

::: simplemma.strategies.greedy_dictionary_lookup
