---
title: "DefaultStrategy: the default lemmatization pipeline"
description: "API reference for DefaultStrategy, which chains dictionary lookup, clitic, apostrophe, hyphen, prefix, affix and morpheme strategies plus rules."
---

# Default Strategy

The pipeline used unless you build your own: dictionary lookup first, then clitic, apostrophe, hyphen, prefix, affix and morpheme decomposition, then per-language rules. Accepts a `dictionary_factory` or the `low_memory` flag.

::: simplemma.strategies.default
