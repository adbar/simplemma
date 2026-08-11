---
title: "CliticDecompositionStrategy: strip clitics"
description: "API reference for CliticDecompositionStrategy, which strips enclitic and proclitic chains and looks up the remaining stem."
---

# Clitic Decomposition Strategy

Strips clitic chains from a token and looks up the stem alone, since the clitic is not part of the lemma: Catalan `portar-lo` to `portar`, Spanish `transmitiéndose` to `transmitir`.

::: simplemma.strategies.clitic_decomposition
