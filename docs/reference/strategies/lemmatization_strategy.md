---
title: "LemmatizationStrategy protocol"
description: "API reference for the LemmatizationStrategy protocol, the single interface every Simplemma lemmatization strategy implements."
---

# Lemmatization Strategy

Every lemmatization strategy implements this protocol: one method that takes a token and a language code and returns a lemma or `None`. Implement it to plug your own logic into a `Lemmatizer`.

::: simplemma.strategies.lemmatization_strategy
