---
title: "LemmatizationFallbackStrategy protocol"
description: "API reference for the LemmatizationFallbackStrategy protocol, which decides what a Lemmatizer returns when no strategy finds a lemma."
---

# Lemmatization Fallback Strategy

When no strategy finds a lemma, the fallback decides what happens: return something, or raise. Implement this protocol to choose for yourself.

::: simplemma.strategies.fallback.lemmatization_fallback_strategy
