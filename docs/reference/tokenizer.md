---
title: "Tokenizer API: simple_tokenizer and RegexTokenizer"
description: "API reference for Simplemma's script-aware tokenizer: simple_tokenizer() returns a list of tokens, RegexTokenizer yields them one by one."
---

# Tokenizer

`simple_tokenizer()` splits raw text into a list of word and punctuation tokens, and `RegexTokenizer.split_text()` yields the same tokens as an iterator. The tokenizer is script-aware: in-word joiners, combining marks and number separators stay inside their token.

::: simplemma.tokenizer
