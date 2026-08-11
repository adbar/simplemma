---
title: "AffixDecompositionStrategy: unsupervised affix search"
description: "API reference for AffixDecompositionStrategy, the greedy affix search behind Simplemma's decomposition of compounds and unknown words."
---

# Affix Decomposition Strategy

Searches for a dictionary-attested split of an unknown word, which is how compounds and neologisms get lemmatized without being listed. This is the strategy the `greedy` argument reaches for.

::: simplemma.strategies.affix_decomposition
