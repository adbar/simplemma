---
title: "Casing: sentence-initial lowering and acronyms"
description: "API reference for Simplemma's casing heuristics: lowering sentence-initial capitals before lookup and keeping ALL-CAPS acronyms verbatim."
---

# Casing

A capital at the start of a sentence is positional rather than lexical, so full-text lemmatization lowers it before looking the word up. This module holds that heuristic, the per-language gate that spares probable proper nouns, and the rule that keeps ALL-CAPS acronyms verbatim.

::: simplemma.casing
