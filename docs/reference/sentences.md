---
title: "Sentence splitting API for Python (split_sentences)"
description: "API reference for split_sentences(), a dependency-free rule-based sentence splitter with per-language abbreviation lists for Czech, German, English, French, Dutch, Polish and Portuguese."
---

# Sentences

`split_sentences()` segments raw text into sentences using punctuation rules plus per-language abbreviation lists, with no external dependency. The returned sentences are slices of the input with surrounding whitespace removed, never rewritten.

::: simplemma.sentences
