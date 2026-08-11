---
title: "ApostropheBoundaryStrategy: split on apostrophes"
description: "API reference for ApostropheBoundaryStrategy, which splits at an apostrophe that marks a fixed morpheme boundary, as in Turkish Istanbul'da."
---

# Apostrophe Boundary Strategy

Some orthographies mark a fixed morpheme boundary with an apostrophe, such as the Turkish proper-noun and suffix boundary in `Istanbul'da`. This strategy splits there and looks up what precedes it.

::: simplemma.strategies.apostrophe_boundary
