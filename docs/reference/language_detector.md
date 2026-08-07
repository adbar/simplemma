---
title: "Language detection API for Python (langdetect)"
description: "API reference for Simplemma's LanguageDetector class plus the langdetect() and in_target_language() functions, which score text against a set of languages."
---

# Language Detector

`LanguageDetector` guesses which of several candidate languages a text is written in by lemmatizing sampled tokens and counting how many are known per language. The functions `langdetect()` and `in_target_language()` wrap it for one-off use.

::: simplemma.language_detector
