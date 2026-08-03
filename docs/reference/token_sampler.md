---
title: "TokenSampler API for language detection"
description: "API reference for Simplemma's token samplers, which pick the tokens that language detection scores, including the most-common-token samplers."
---

# TokenSampler

Language detection does not score every token in a text, it scores a sample. Token samplers decide which tokens make up that sample, trading coverage against speed.

::: simplemma.token_sampler
