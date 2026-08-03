---
title: "MorphemeDecompositionStrategy: compositional morphology"
description: "API reference for MorphemeDecompositionStrategy, which strips stacked prefixes, infixes and reduplication for Tagalog and Indonesian."
---

# Morpheme Decomposition Strategy

For languages whose inflection is compositional, several affixes stack on one root and all of them must go together to reach the lemma. This strategy searches prefix, infix, reduplication and suffix combinations and accepts one only if the residue is an attested dictionary entry. Tagalog and Indonesian are the current targets.

::: simplemma.strategies.morpheme_decomposition
