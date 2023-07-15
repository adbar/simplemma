## Contributions

### Issues, bugs & improvment ideas

Feel free to contribute, notably by [filing issues](https://github.com/adbar/simplemma/issues) for feedback, bug reports, or links to further lemmatization lists, rules and tests.

You can also contribute to this [lemmatization list repository](https://github.com/michmech/lemmatization-lists).

### Contributing to the code

Pull requests are welcome.

Before creating the pull request, please ensure that it pass all the quality checks:

```sh
# Install dev dependencies
pip install -r requirements.dev.txt
# Check code style
black --check --diff simplemma training tests
# Check typings
mypy -p simplemma -p training -p tests
# Run tests
pytest --cov=./ --cov-report=xml

```

Also, if your PR changes needs documentation changes, see the next section.

### Contributing to documentation

```sh
# Install dev dependencies
pip install -r requirements.docs.txt
# Build mkdocs
mkdocs build
# Check typings
mypy -p simplemma -p training -p tests
# Run tests
pytest --cov=./ --cov-report=xml
