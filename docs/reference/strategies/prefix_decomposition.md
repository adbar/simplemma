---
title: "PrefixDecompositionStrategy: strip known prefixes"
description: "API reference for PrefixDecompositionStrategy, which strips a prefix from a per-language list and lemmatizes the remainder."
---

# Prefix Decomposition Strategy

Strips one prefix from a per-language list and lemmatizes the remainder, then reattaches nothing: the prefix is part of the lemma only when the dictionary says so. Useful for German, Russian and Ukrainian verb prefixes.

::: simplemma.strategies.prefix_decomposition
