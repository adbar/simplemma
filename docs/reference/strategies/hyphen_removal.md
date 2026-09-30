---
title: "HyphenRemovalStrategy: hyphenated compounds"
description: "API reference for HyphenRemovalStrategy, which resolves hyphenated compounds by looking up the part after the last hyphen."
---

# Hyphen removal Strategy

Resolves hyphenated tokens by looking up the part after the last hyphen or underscore and keeping the head as typed (`Mail-Clients` -> `Mail-Client`). This catches compounds and ad-hoc coinages that no dictionary lists whole. A head made of hyphens only is dropped (`-ce` -> `ce`).

::: simplemma.strategies.hyphen_removal
