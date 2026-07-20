# Simplemma: a simple multilingual lemmatizer for Python

[![Python package](https://img.shields.io/pypi/v/simplemma.svg)](https://pypi.python.org/pypi/simplemma)
[![Python versions](https://img.shields.io/pypi/pyversions/simplemma.svg)](https://pypi.python.org/pypi/simplemma)
[![Code Coverage](https://img.shields.io/codecov/c/github/adbar/simplemma.svg)](https://codecov.io/gh/adbar/simplemma)
[![Reference DOI: 10.5281/zenodo.4673264](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.4673264-brightgreen)](https://doi.org/10.5281/zenodo.4673264)


<!-- include:intro:start -->
## Purpose

[Lemmatization](https://en.wikipedia.org/wiki/Lemmatisation) is the
process of grouping together the inflected forms of a word so they can
be analysed as a single item, identified by the word's lemma, or
dictionary form. Unlike stemming, lemmatization outputs word units that
are still valid linguistic forms.

In modern natural language processing (NLP), this task is often
indirectly tackled by more complex systems encompassing a whole
processing pipeline. However, it appears that there is no
straightforward way to address lemmatization in Python although this
task can be crucial in fields such as information retrieval and NLP.

*Simplemma* provides a simple and multilingual approach to look for base
forms or lemmata. It may not be as powerful as full-fledged solutions
but it is generic, easy to install and straightforward to use. In
particular, it does not need morphosyntactic information and can process
a raw series of tokens or even a text with its built-in tokenizer. By
design it should be reasonably fast and work in a large majority of
cases, without being perfect.

With its comparatively small footprint it is especially useful when
speed and simplicity matter, in low-resource contexts, for educational
purposes, or as a baseline system for lemmatization and morphological
analysis.

Currently, 50 languages are partly or fully supported (see the list of supported languages).


## Installation

The current library is written in pure Python with no dependencies:
`pip install simplemma`

- `pip install -U simplemma` for updates
- `pip install git+https://github.com/adbar/simplemma` for the cutting-edge version

The last version supporting Python 3.6 and 3.7 is `simplemma==1.0.0`.


## Usage

### Word-by-word

Simplemma is used by selecting a language of interest and then applying
the data on a list of words.

``` python
>>> import simplemma
# get a word
myword = 'masks'
# decide which language to use and apply it on a word form
>>> simplemma.lemmatize(myword, lang='en')
'mask'
# apply it on a list of tokens
>>> mytokens = ['Hier', 'sind', 'Vaccines']
>>> [simplemma.lemmatize(t, lang='de') for t in mytokens]
['hier', 'sein', 'Vaccines']
```


### Chaining languages

Chaining several languages can improve coverage, they are used in
sequence:

``` python
>>> from simplemma import lemmatize
>>> lemmatize('Vaccines', lang=('de', 'en'))
'vaccine'
>>> lemmatize('spaghettis', lang='it')
'spaghettis'
>>> lemmatize('spaghettis', lang=('it', 'fr'))
'spaghetti'
>>> lemmatize('spaghetti', lang=('it', 'fr'))
'spaghetto'
```


### Greedier decomposition

For certain languages a greedier decomposition is activated by default
as it can be beneficial, mostly due to a certain capacity to address
affixes in an unsupervised way. This can be triggered manually by
setting the `greedy` parameter to `True`.

This option also triggers a stronger reduction through an additional
iteration of the search algorithm, e.g. "angekündigten" →
"angekündigt" (standard) → "ankündigen" (greedy). In some cases it
may be closer to stemming than to lemmatization.

``` python
>>> simplemma.lemmatize('angekündigten', lang='de', greedy=False)
'angekündigt' # 1 step: reduction to past participle
>>> simplemma.lemmatize('angekündigten', lang='de', greedy=True)
'ankündigen' # 2 steps: further reduction to infinitive verb
```


### is_known()

The additional function `is_known()` checks if a given word is present
in the language data:

``` python
>>> from simplemma import is_known
>>> is_known('spaghetti', lang='it')
True
```


### Tokenization

A simple tokenization function is provided for convenience:

``` python
>>> from simplemma import simple_tokenizer
>>> simple_tokenizer('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')
['Lorem', 'ipsum', 'dolor', 'sit', 'amet', ',', 'consectetur', 'adipiscing', 'elit', ',', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua', '.']
# for an iterator instead of a list, use the RegexTokenizer directly
>>> from simplemma import RegexTokenizer
>>> RegexTokenizer().split_text('Lorem ipsum dolor sit amet')
<generator object ...>
```

The functions `text_lemmatizer()` and `lemma_iterator()` chain
tokenization and lemmatization. They accept the same `greedy` argument
as `lemmatize()`:

``` python
>>> from simplemma import text_lemmatizer
>>> sentence = 'Sou o intervalo entre o que desejo ser e os outros me fizeram.'
>>> text_lemmatizer(sentence, lang='pt')
# caveat: desejo is also a noun, should be desejar here
['ser', 'o', 'intervalo', 'entre', 'o', 'que', 'desejo', 'ser', 'e', 'o', 'outro', 'me', 'fazer', '.']
# same principle, returns a generator and not a list
>>> from simplemma import lemma_iterator
>>> lemma_iterator(sentence, lang='pt')
```


### Caveats

``` python
# don't expect too much though
# this diminutive form isn't in the model data
>>> simplemma.lemmatize('spaghettini', lang='it')
'spaghettini' # should read 'spaghettino'
# the algorithm cannot choose between valid alternatives yet
>>> simplemma.lemmatize('son', lang='es')
'ser' # 3rd-person plural of 'ser'; but 'son' is also a noun (a Cuban music genre)
```

As the focus lies on overall coverage, some short frequent words
(typically: pronouns and conjunctions) may need post-processing, this
generally concerns a few dozens of tokens per language.

The current absence of morphosyntactic information is an advantage in
terms of simplicity. However, it is also an impassable frontier regarding
lemmatization accuracy, for example when it comes to disambiguating
between past participles and adjectives derived from verbs in Germanic
and Romance languages. In most cases, `simplemma` often does not change
such input words.

The greedy algorithm seldom produces invalid forms. It is designed to
work best in the low-frequency range, notably for compound words and
neologisms. Aggressive decomposition is only useful as a general
approach in the case of morphologically-rich languages, where it can
also act as a linguistically motivated stemmer.

Bug reports over the [issues
page](https://github.com/adbar/simplemma/issues) are welcome.


### Language detection

Language detection works by providing a text and a tuple `lang` consisting
of a series of languages of interest. Each score is a proportion between 0
and 1. The proportions are computed independently per language, so a token
recognized in several languages counts towards each of them and the scores
need not sum to 1.

The `langdetect()` function returns a list of language codes along
with their corresponding scores, appending "unk" for the proportion of
unknown or out-of-vocabulary tokens. The proportion of tokens that belong
to the target language(s) can also be obtained directly with the
`in_target_language()` function, which returns a single ratio.

``` python
# import necessary functions
>>> from simplemma import in_target_language, langdetect
# language detection
>>> langdetect('"Exoplaneta, též extrasolární planeta, je planeta obíhající kolem jiné hvězdy než kolem Slunce."', lang=("cs", "sk"))
[("cs", 0.75), ("sk", 0.125), ("unk", 0.25)]
# proportion of known words
>>> in_target_language("opera post physica posita (τὰ μετὰ τὰ φυσικά)", lang="la")
0.5
```

The `greedy` argument (`extensive` in past software versions) triggers
use of the greedier decomposition algorithm described above, thus
extending word coverage and recall of detection at the potential cost of
a lesser accuracy.


### Advanced usage via classes

The functions described above are suitable for simple usage, but you
can have more control by instantiating Simplemma classes and calling
their methods instead. Lemmatization is handled by the `Lemmatizer`
class, while language detection is handled by the `LanguageDetector`
class. These in turn rely on different lemmatization strategies, which
are implementations of the `LemmatizationStrategy` protocol. The
`DefaultStrategy` implementation uses a combination of different
strategies, one of which is `DictionaryLookupStrategy`. It looks up
tokens in a dictionary created by a `DictionaryFactory`.

For example, it is possible to conserve RAM by limiting the number of
cached language dictionaries (default: 8) by creating a custom
`DefaultDictionaryFactory` with a specific `cache_max_size` setting,
creating a `DefaultStrategy` using that factory, and then creating a
`Lemmatizer` and/or a `LanguageDetector` using that strategy:

``` python
# import necessary classes
>>> from simplemma import LanguageDetector, Lemmatizer
>>> from simplemma.strategies import DefaultStrategy
>>> from simplemma.strategies.dictionaries import DefaultDictionaryFactory

LANG_CACHE_SIZE = 5  # How many language dictionaries to keep in memory at once (max)
>>> dictionary_factory = DefaultDictionaryFactory(cache_max_size=LANG_CACHE_SIZE)
>>> lemmatization_strategy = DefaultStrategy(dictionary_factory=dictionary_factory)

# lemmatize using the above customized strategy
>>> lemmatizer = Lemmatizer(lemmatization_strategy=lemmatization_strategy)
>>> lemmatizer.lemmatize('doughnuts', lang='en')
'doughnut'

# detect languages using the above customized strategy
>>> language_detector = LanguageDetector('la', lemmatization_strategy=lemmatization_strategy)
>>> language_detector.proportion_in_target_languages("opera post physica posita (τὰ μετὰ τὰ φυσικά)")
0.5
```

For more information see the
[extended documentation](https://adbar.github.io/simplemma/).


### Reducing memory usage

Simplemma provides an alternative solution for situations where low
memory usage is more important than lemmatization and language
detection performance. The quickest way to opt in is the `low_memory`
flag, available on `lemmatize`, `text_lemmatizer`, `lemma_iterator`,
`is_known`, `langdetect` and `in_target_language`:

``` python
>>> from simplemma import lemmatize
>>> lemmatize('doughnuts', lang='en', low_memory=True)
'doughnut'
```

This picks the most memory-efficient dictionary backend available:
`TrieDictionaryFactory` (see below) if `marisa-trie` is installed,
otherwise the stdlib-only `StreamDictionaryFactory`. For explicit
control over which backend is used — including with `Lemmatizer` and
`LanguageDetector` instances — build a strategy directly, as described
in the rest of this section. `DefaultStrategy` also accepts the same
`low_memory` flag, but not together with an explicit
`dictionary_factory`:

``` python
>>> from simplemma import Lemmatizer
>>> from simplemma.strategies import DefaultStrategy

>>> strategy = DefaultStrategy(low_memory=True)
>>> Lemmatizer(lemmatization_strategy=strategy).lemmatize('doughnuts', lang='en')
'doughnut'
```

The `TrieDictionaryFactory` employs a trie as its underlying data
structure, rather than a Python dict. It reduces memory usage by an
average of 20x and initialization time by 100x, but this comes at the
cost of potentially reducing performance by 50% or more, depending on
the specific usage.

To use the `TrieDictionaryFactory` you have to install Simplemma with
the `marisa-trie` extra dependency (available from version 1.1.0):

```bash
pip install simplemma[marisa-trie]
```

Then create a strategy using the `TrieDictionaryFactory` and use it for
`Lemmatizer` and `LanguageDetector` instances, exactly as shown above:

``` python
>>> from simplemma import Lemmatizer
>>> from simplemma.strategies import DefaultStrategy
>>> from simplemma.strategies.dictionaries import TrieDictionaryFactory

>>> strategy = DefaultStrategy(dictionary_factory=TrieDictionaryFactory())
>>> Lemmatizer(lemmatization_strategy=strategy).lemmatize('doughnuts', lang='en')
'doughnut'
```

While memory usage and initialization time when using the
`TrieDictionaryFactory` are significantly lower compared to the
`DefaultDictionaryFactory`, that's only true if the trie dictionaries
are available on disk. That's not the case when using the
`TrieDictionaryFactory` for the first time, as Simplemma only ships
the dictionaries as Python dicts. The trie dictionaries have to be
generated once from the Python dicts. That happens on-the-fly when
using the `TrieDictionaryFactory` for the first time for a language and
will take a few seconds and use as much memory as loading the Python
dicts for the language requires. For further invocations the trie
dictionaries get cached on disk.

If the machine that will run Simplemma doesn't have enough memory to
generate the trie dictionaries, they can also be generated on another
computer with the same CPU architecture and copied over to the cache
directory.

If installing `marisa-trie` isn't an option, `StreamDictionaryFactory`
offers a similar memory/speed trade-off using only the standard library.
It reads the shipped dictionary files directly instead of loading them
into a Python dict, at the cost of much slower lookups (measured on
`de`: 46MB vs 180MB RSS, and roughly 4x slower lemmatization end-to-end
through `Lemmatizer`'s cache; the gap is wider for one-off, uncached
lookups). There's no on-disk cache to warm up, so throughput is
consistent from the first call.

``` python
>>> from simplemma import Lemmatizer
>>> from simplemma.strategies import DefaultStrategy
>>> from simplemma.strategies.dictionaries import StreamDictionaryFactory

>>> strategy = DefaultStrategy(dictionary_factory=StreamDictionaryFactory())
>>> Lemmatizer(lemmatization_strategy=strategy).lemmatize('doughnuts', lang='en')
'doughnut'
```


<!-- include:intro:end -->
## Supported languages
<!-- include:languages:start -->

The following languages are available, identified by their [BCP 47
language tag](https://en.wikipedia.org/wiki/IETF_language_tag), which
typically corresponds to the [ISO 639-1 code](
https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes).
If no such code exists, a [ISO 639-3
code](https://en.wikipedia.org/wiki/List_of_ISO_639-3_codes) is
used instead.

Available languages (2026-05-29):

The *Forms* column counts the inflected word forms stored in the
dictionary, while *Lemmata* counts the distinct base forms they map to
(both in thousands). A large gap between the two reflects rich
morphology rather than a data error.


| Code | Language | Forms (10³) | Lemm. (10³) | Acc. | Comments |
| ---- | -------- | ----------- | ------------| ---- | -------- |
| `ast` | Asturian | 154 | 36 |  |  |
| `bg` | Bulgarian | 215 | 18 | 0.84 | on UD BG-BTB |
| `ca` | Catalan | 640 | 63 | 0.89 | on UD CA-AnCora |
| `cs` | Czech | 356 | 45 | 0.91 | on UD CS-FicTree |
| `cy` | Welsh | 402 | 21 | 0.91 | on UD CY-CCG |
| `da` | Danish | 778 | 115 | 0.93 | on UD DA-DDT, alternative: [lemmy](https://github.com/sorenlind/lemmy) |
| `de` | German | 1,116 | 334 | 0.95 | on UD DE-GSD, see also [German-NLP list](https://github.com/adbar/German-NLP#Lemmatization) |
| `el` | Greek | 248 | 27 | 0.91 | on UD EL-GDT |
| `en` | English | 182 | 78 | 0.95 | on UD EN-LinES, alternative: [LemmInflect](https://github.com/bjascob/LemmInflect) |
| `enm` | Middle English | 43 | 6 |  |  |
| `eo` | Esperanto | 191 | 18 | 0.95 | on UD EO-PraGo |
| `es` | Spanish | 824 | 88 | 0.91 | on UD ES-AnCora |
| `et` | Estonian | 2,662 | 92 | 0.84 | on UD ET-EWT, low coverage |
| `fa` | Persian | 13 | 4 | 0.87 | on UD FA-Seraji, experimental |
| `fi` | Finnish | 3,549 | 125 | 0.86 | on UD FI-FTB, see [this benchmark](https://github.com/aajanki/finnish-pos-accuracy) |
| `fr` | French | 248 | 37 | 0.93 | on UD FR-Sequoia |
| `ga` | Irish | 444 | 48 | 0.89 | on UD GA-IDT |
| `gd` | Gaelic | 72 | 15 | 0.84 | on UD GD-ARCOSG |
| `gl` | Galician | 426 | 43 | 0.88 | on UD GL-CTG |
| `gv` | Manx | 77 | 14 | 0.84 | on UD GV-Cadhan |
| `hbs` | Serbo-Croatian | 674 | 52 |  | Croatian and Serbian lists to be added later |
| `hi` | Hindi | 58 | 11 | 0.93 | on UD HI-HDTB, experimental |
| `hu` | Hungarian | 492 | 36 | 0.85 | on UD HU-Szeged |
| `hy` | Armenian | 467 | 17 | 0.88 | on UD HY-BSUT |
| `id` | Indonesian | 21 | 4 | 0.93 | on UD ID-CSUI |
| `is` | Icelandic | 208 | 17 | 0.78 | on UD IS-GC |
| `it` | Italian | 357 | 28 | 0.93 | on UD IT-ISDT |
| `ka` | Georgian | 448 | 16 | 0.82 | on UD KA-GLC |
| `la` | Latin | 1,223 | 64 | 0.85 | on UD LA-PROIEL |
| `lb` | Luxembourgish | 306 | 79 |  | only a <1k-token UD treebank available |
| `lt` | Lithuanian | 415 | 29 | 0.82 | on UD LT-ALKSNIS |
| `lv` | Latvian | 177 | 14 | 0.78 | on UD LV-LVTB |
| `mk` | Macedonian | 551 | 39 | 0.73 | on UD MK-MTB |
| `ms` | Malay | 18 | 4 |  |  |
| `nb` | Norwegian (Bokmål) | 618 | 134 | 0.81 | on UD NO-Bokmaal |
| `nl` | Dutch | 369 | 125 | 0.92 | on UD NL-Alpino, excl. underscore-joined compound lemmas |
| `nn` | Norwegian (Nynorsk) | 68 | 18 | 0.76 | on UD NO-Nynorsk |
| `pl` | Polish | 3,671 | 264 | 0.93 | on UD PL-LFG |
| `pt` | Portuguese | 926 | 95 | 0.92 | on UD PT-GSD |
| `ro` | Romanian | 342 | 36 | 0.92 | on UD RO-RRT |
| `ru` | Russian | 1,318 | 128 | 0.89 | on UD RU-SynTagRus, alternative: [pymorphy2](https://github.com/kmike/pymorphy2/) |
| `se` | Northern Sámi | 115 | 7 | 0.95 | on UD SME-Giella |
| `sk` | Slovak | 907 | 73 | 0.93 | on UD SK-SNK |
| `sl` | Slovene | 165 | 30 | 0.92 | on UD SL-SSJ |
| `sq` | Albanian | 96 | 10 | 0.72 | on UD SQ-STAF |
| `sv` | Swedish | 871 | 114 | 0.91 | on UD SV-Talbanken, alternative: [lemmy](https://github.com/sorenlind/lemmy) |
| `sw` | Swahili | 4,870 | 4 |  | experimental |
| `tl` | Tagalog | 39 | 8 | 0.67 | on UD TL-Ugnayan, experimental |
| `tr` | Turkish | 1,236 | 40 | 0.91 | on UD TR-KeNet |
| `uk` | Ukrainian | 616 | 37 | 0.90 | on UD UK-IU, alternative: [pymorphy2](https://github.com/kmike/pymorphy2/) |


Languages marked as having low coverage may be better suited to
language-specific libraries, but Simplemma can still provide limited
functionality. Where possible, open-source Python alternatives are
referenced.

*Experimental* mentions indicate that the language remains untested or
that there could be issues with the underlying data or lemmatization
process.

The scores are calculated on [Universal
Dependencies](https://universaldependencies.org/) treebanks on single
word tokens (including some contractions but not merged prepositions),
they describe to what extent simplemma can accurately map tokens to
their lemma form. For each language the figure is the accuracy on its
best-performing general-purpose treebank (parallel, spoken, learner,
historical and other narrow-domain treebanks are excluded). The Dutch
(`nl`) figure excludes gold lemmas that are underscore-joined compounds
(e.g. `klooster_orde`), a UD-Alpino annotation convention that
simplemma's single-token output cannot match; without that exclusion it
is ≈0.88. See the `training/` folder of the code repository for more
information.

This library is particularly relevant as regards the lemmatization of
less frequent words. Its performance in this case is only incidentally
captured by the benchmark above. In some languages, a fixed number of
words such as pronouns can be further mapped by hand to enhance
performance.


<!-- include:languages:end -->
## Speed

The following orders of magnitude are provided for reference only and
were measured on an old laptop to establish a lower bound:

-   Tokenization: > 1 million tokens/sec
-   Lemmatization: > 250,000 words/sec

Using the most recent Python version (i.e. with `pyenv`) can make the
package run faster.


## Roadmap

- [x] Add further lemmatization lists
- [ ] Grammatical categories as option
- [ ] Function as a meta-package?
- [ ] Integrate optional, more complex models?


## Credits and licenses
<!-- include:credits:start -->

The software is licensed under the MIT license. For information on the
licenses of the linguistic information databases, see the `licenses` folder.

The surface lookups (non-greedy mode) rely on lemmatization lists derived
from the following sources, listed in order of relative importance:

-   [Lemmatization
    lists](https://github.com/michmech/lemmatization-lists) by Michal
    Měchura (Open Database License)
-   Wiktionary entries packaged by the [Kaikki
    project](https://kaikki.org/)
-   [FreeLing project](https://github.com/TALP-UPC/FreeLing)
-   [spaCy lookups
    data](https://github.com/explosion/spacy-lookups-data)
-   [Unimorph Project](https://unimorph.github.io/)
-   [Wikinflection
    corpus](https://github.com/lenakmeth/Wikinflection-Corpus) by Eleni
    Metheniti (CC BY 4.0 License)


<!-- include:credits:end -->
## Contributions
<!-- include:contributions:start -->

This package has been first created and published by Adrien Barbaresi.
It has then benefited from extensive refactoring by Juanjo Diaz (especially the new classes).
See the [full list of contributors](https://github.com/adbar/simplemma/graphs/contributors)
to the repository.

Feel free to contribute, notably by [filing
issues](https://github.com/adbar/simplemma/issues/) for feedback, bug
reports, or links to further lemmatization lists, rules and tests.

Contributions by pull requests ought to follow the following
conventions: code style and linting with [ruff](https://github.com/astral-sh/ruff), type
hinting with [mypy](https://github.com/python/mypy), included tests with
[pytest](https://pytest.org).

Running `pytest` after a plain `pip install ".[dev]"` skips the `marisa-trie`
test module and under-reports coverage; install the extra as well
(`pip install ".[dev,marisa-trie]"` or `uv sync --extra dev --extra marisa-trie`)
to run the full suite and match CI's coverage numbers.


<!-- include:contributions:end -->
## Other solutions

See lists: [German-NLP](https://github.com/adbar/German-NLP) and [other
awesome-NLP lists](https://github.com/adbar/German-NLP#More-lists).

For another approach in Python see Spacy's
[edit tree lemmatizer](https://spacy.io/api/edittreelemmatizer).


## References

To cite this software:

[![Reference DOI: 10.5281/zenodo.4673264](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.4673264-brightgreen)](https://doi.org/10.5281/zenodo.4673264)

Barbaresi A. (*year*). Simplemma: a simple multilingual lemmatizer for
Python [Computer software] (Version *version number*). Available from
<https://github.com/adbar/simplemma> DOI: 10.5281/zenodo.4673264

This work draws from lexical analysis algorithms used in:

-   Barbaresi, A., & Hein, K. (2017). [Data-driven identification of
    German phrasal
    compounds](https://hal.archives-ouvertes.fr/hal-01575651/document).
    In International Conference on Text, Speech, and Dialogue Springer,
    pp. 192-200.
-   Barbaresi, A. (2016). [An unsupervised morphological criterion for
    discriminating similar
    languages](https://aclanthology.org/W16-4827/). In 3rd Workshop on
    NLP for Similar Languages, Varieties and Dialects (VarDial 2016),
    Association for Computational Linguistics, pp. 212-220.
-   Barbaresi, A. (2016). [Bootstrapped OCR error detection for a
    less-resourced language
    variant](https://hal.archives-ouvertes.fr/hal-01371689/document). In
    13th Conference on Natural Language Processing (KONVENS 2016), pp.
    21-26.
