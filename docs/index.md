---
title: "Python lemmatizer, tokenizer and sentence splitter"
description: "Simplemma is a lightweight, dependency-free Python library for multilingual lemmatization, tokenization, sentence splitting and language detection."
---

# Simplemma

A lightweight Python library that reduces words to their base form in 54
languages, and ships the text processing needed to get there: a script-aware
tokenizer, a rule-based sentence splitter and dictionary-driven language
detection. No models to download, no dependencies to install, and a memory
footprint you can choose.

{%
   include-markdown "../README.md"
   start="<!-- include:pitch:start -->"
   end="<!-- include:pitch:end -->"
%}

## What it does

| Task | Entry point | Details |
| --- | --- | --- |
| Lemmatize a word or a text | `lemmatize()`, `text_lemmatizer()` | [Usage](usage.md), [Lemmatizer API](reference/lemmatizer.md) |
| Split text into tokens | `simple_tokenizer()` | [Tokenizer API](reference/tokenizer.md) |
| Split text into sentences | `split_sentences()` | [Sentences API](reference/sentences.md) |
| Detect the language of a text | `langdetect()`, `in_target_language()` | [Language Detector API](reference/language_detector.md) |
| Check a word against the data | `is_known()` | [Lemmatizer API](reference/lemmatizer.md) |

## Installation

{%
   include-markdown "../README.md"
   start="<!-- include:quickstart:start -->"
   end="<!-- include:quickstart:end -->"
%}

## Where to go next

- [Usage](usage.md) for language chaining, greedy decomposition,
  tokenization, sentence splitting, language detection and the caveats that
  come with a dictionary-based approach
- [Supported languages](supported-languages.md) for the 54 languages, their
  dictionary sizes and their measured accuracy
- [Classes and strategies](classes-and-strategies.md) to assemble your own
  lemmatizer out of strategies and dictionary factories
- [Memory usage](memory-usage.md) to trade speed for a smaller footprint
  (~50 MB per language, or ~30 MB with the optional `marisa-trie` extra)
- [Reference](reference/lemmatizer.md) for the full API
