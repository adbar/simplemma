# Contributing

{%
   include-markdown "../README.md"
   start="<!-- include:contributions:start -->"
   end="<!-- include:contributions:end -->"
%}

## Development setup

Install the development dependencies (tests, linters and type checker) from
the project's optional-dependency groups:

```sh
pip install ".[dev]"
```

Before opening a pull request, please make sure it passes all the quality
checks that CI runs:

```sh
# Code style
black --check --diff simplemma training tests
# Linting
flake8 simplemma training tests
# Type checking
mypy -p simplemma -p training -p tests
# Tests
pytest --cov=./ --cov-report=xml
```

## Contributing to documentation

Install the documentation dependencies and build (or preview) the site
locally:

```sh
pip install ".[docs]"
mkdocs build --strict   # fails on warnings; use `mkdocs serve` for a live preview
```
