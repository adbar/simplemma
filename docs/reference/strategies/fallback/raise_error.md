---
title: "RaiseErrorFallbackStrategy"
description: "API reference for RaiseErrorFallbackStrategy, a fallback that raises ValueError instead of guessing when no lemma is found."
---

# Raise Error Strategy

A strict fallback: raise `ValueError` instead of guessing. Useful when an unlemmatizable token should surface as an error rather than pass through.

::: simplemma.strategies.fallback.raise_error
