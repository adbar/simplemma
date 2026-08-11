---
title: "TrieDictionaryFactory: lowest steady-state memory"
description: "API reference for TrieDictionaryFactory, which stores the dictionaries in MARISA tries for the lowest steady-state memory footprint."
---

# Trie Dictionary Factory

Stores each dictionary in a MARISA trie for the lowest steady-state memory footprint, at the cost of the `marisa-trie` extra and a one-off build that is cached on disk. Request it explicitly, it is never selected automatically.

::: simplemma.strategies.dictionaries.trie_dictionary_factory
