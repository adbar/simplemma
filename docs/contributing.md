---
title: Contributing
description: "How to contribute to Simplemma: development setup with uv, the ruff, mypy and pytest checks CI runs, and how to build the documentation."
---

# Contributing

{%
   include-markdown "../README.md"
   start="<!-- include:contributions:start -->"
   end="<!-- include:contributions:end -->"
%}

## Development setup

The project uses [uv](https://docs.astral.sh/uv/). Before opening a pull
request, run the same checks as CI:

```sh
uv sync --extra dev --extra marisa-trie
uv run ruff check .
uv run ruff format --check simplemma training tests
uv run mypy -p simplemma -p training -p tests
uv run pytest -n auto
```

## Contributing to documentation

```sh
uv sync --extra docs
uv run mkdocs build --strict   # or `mkdocs serve` for a live preview
```
