# Simplemma: a simple multilingual lemmatizer for Python

[![Python package](https://img.shields.io/pypi/v/simplemma.svg)](https://pypi.python.org/pypi/simplemma)
[![Python versions](https://img.shields.io/pypi/pyversions/simplemma.svg)](https://pypi.python.org/pypi/simplemma)
[![Code Coverage](https://img.shields.io/codecov/c/github/adbar/simplemma.svg)](https://codecov.io/gh/adbar/simplemma)
[![Reference DOI: 10.5281/zenodo.4673264](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.4673264-brightgreen)](https://doi.org/10.5281/zenodo.4673264)


<!-- include:intro:start -->
## Purpose

[Lemmatization](https://en.wikipedia.org/wiki/Lemmatisation) groups the
inflected forms of a word so they can be analysed as a single item,
identified by the word's lemma, or dictionary form. Unlike stemming, it
outputs word units that are still valid linguistic forms. In modern NLP
the task is usually handled indirectly, inside a whole processing
pipeline, although it can be crucial on its own for information
retrieval.

*Simplemma* provides a simple and multilingual approach to looking for
base forms. It needs no morphosyntactic information and processes a raw
series of tokens, or a text through its built-in tokenizer. It is not as
powerful as full-fledged solutions, but it is generic, easy to install
and fast, and its small footprint suits contexts where speed and
simplicity matter: low-resource settings, teaching, or a baseline for
lemmatization and morphological analysis.

Currently, 54 languages are partly or fully supported (see the list below).


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

The tokenizer is script-aware: in-word joiners stay inside their word
(`l'homme`, `2020'de`, `col·legis`, `ש"ח`, `בית־ספר`, `Մի՞թե`), as do the
combining marks of Hebrew, Arabic, Devanagari and Malayalam. Punctuation
becomes its own token, but a run of the same character stays whole (`...`,
`--`), and numbers keep their separators and currency symbol (`3,50 €`,
`R$ 659`). Characters outside the word and punctuation sets — emoji,
arrows and similar symbols — are not emitted as tokens.

Measured against Universal Dependencies gold, token-level F1 is 0.97 to
0.998 for most languages (median 0.99), lower for French, Catalan and
Italian (0.93 to 0.96), where UD splits elided articles (`l'homme` →
`l'` + `homme`) and simplemma keeps them whole.

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


### Sentence splitting

`split_sentences()` segments raw text into sentences, using rules plus
per-language abbreviation data where it measurably pays (currently `cs`,
`de`, `en`, `fr`, `nl`, `pl`, `pt`); other codes use the generic rules,
which stay close in quality. `lang='el'` additionally treats `;` as a
question mark, and a blank line always starts a new sentence. On Universal
Dependencies data the splitter matches or beats NLTK's punkt on 6 of 7
evaluated languages, at a fraction of its runtime and with no dependency.

``` python
>>> from simplemma import split_sentences
>>> split_sentences('Das Tor fiel in der 95. Minute. Das Spiel war aus.', lang='de')
['Das Tor fiel in der 95. Minute.', 'Das Spiel war aus.']
```

The sentences are slices of the input with surrounding whitespace removed:
nothing is normalized or rewritten. `lang` also accepts a tuple, like the
other entry points, and pre-tokenized or OCR-style text whose punctuation
is spaced out (`Le prix est bas .`) still splits correctly.

On the held-out PUD corpora — the same 1000 professionally translated
sentences per language — sentence-boundary F1 is 0.98 to 0.998. Register
matters far more than language: text without reliable terminal punctuation,
social media in particular, is much harder, since a rule-based splitter
cannot recover a boundary that was never marked.


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
(typically pronouns and conjunctions) may need post-processing — generally
a few dozen tokens per language.

Working without morphosyntactic information keeps things simple but sets a
hard ceiling on accuracy, for instance when disambiguating past participles
from verb-derived adjectives in Germanic and Romance languages; `simplemma`
usually leaves such words unchanged.

The greedy algorithm seldom produces invalid forms. It works best in the
low-frequency range, notably for compound words and neologisms. Aggressive
decomposition is only useful as a general approach for morphologically-rich
languages, where it can act as a linguistically motivated stemmer.

Bug reports over the [issues
page](https://github.com/adbar/simplemma/issues) are welcome.


### Language detection

Language detection takes a text and a tuple `lang` of languages of
interest. `langdetect()` returns each language code with its score, plus
"unk" for the proportion of unknown tokens; `in_target_language()` returns
the single ratio of tokens belonging to the target language(s). Scores are
proportions between 0 and 1, computed independently per language, so a
token recognized in several counts towards each and they need not sum to 1.

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

The functions above cover simple usage; instantiating the classes gives
more control. `Lemmatizer` handles lemmatization and `LanguageDetector`
language detection, both through an implementation of the
`LemmatizationStrategy` protocol. `DefaultStrategy` combines several such
strategies, among them `DictionaryLookupStrategy`, which looks tokens up in
a dictionary built by a `DictionaryFactory`.

For example, to conserve RAM by limiting how many language dictionaries
stay cached (default: 8), pass a `cache_max_size` to
`DefaultDictionaryFactory`, wrap it in a `DefaultStrategy`, and hand that
to a `Lemmatizer` and/or `LanguageDetector`:

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

Where low memory usage matters more than lemmatization and detection
speed, the quickest way in is the `low_memory` flag, available on
`lemmatize`, `text_lemmatizer`, `lemma_iterator`, `is_known`, `langdetect`
and `in_target_language`:

``` python
>>> from simplemma import lemmatize
>>> lemmatize('doughnuts', lang='en', low_memory=True)
'doughnut'
```

This selects the stdlib-only `StreamDictionaryFactory`: the most
memory-frugal backend, reading the dictionary stream directly with no
full-dict build spike and no on-disk cache. `TrieDictionaryFactory` reaches
a lower *steady-state* footprint but spikes and writes to disk on first
use, so it is never auto-selected — request it explicitly (see below).
`DefaultStrategy` accepts the same flag, though not together with an
explicit `dictionary_factory`:

``` python
>>> from simplemma import Lemmatizer
>>> from simplemma.strategies import DefaultStrategy

>>> strategy = DefaultStrategy(low_memory=True)
>>> Lemmatizer(lemmatization_strategy=strategy).lemmatize('doughnuts', lang='en')
'doughnut'
```

The three backends trade memory against speed as follows (German, ~1.1M
dictionary entries; figures vary by language and hardware):

| Backend | Peak RAM | Load time | Uncached lookup² | Cached lookup³ | Extra dependency |
| --- | --- | --- | --- | --- | --- |
| `DefaultDictionaryFactory` | ~175 MB | ~0.6 s | fastest (baseline) | fastest (baseline) | none |
| `TrieDictionaryFactory` | ~30 MB | ~1 ms (warm)¹ | ~2.5× slower | ~1.2× slower | `marisa-trie` |
| `StreamDictionaryFactory` | ~50 MB | ~0.6 s | ~18× slower | ~6× slower | none |

¹ Warm load. The first use of a language builds its trie from the shipped
dictionary, taking a few seconds and briefly needing as much memory as
`DefaultDictionaryFactory` would, then caches it on disk. On a machine
without enough memory to build it, build it elsewhere on the same CPU
architecture and copy the cache directory over.
² Per single lookup, bypassing any cache.
³ End-to-end through `Lemmatizer`'s result cache, over the German UD-HDT
treebank (3.5M tokens, 200k unique). The gap shrinks toward parity on
texts whose vocabulary fits the cache, and toward the uncached figure on
large, low-repetition corpora.

Pick `DefaultDictionaryFactory` when throughput matters and memory does
not; `TrieDictionaryFactory` for the best RAM/speed trade-off, if the
`marisa-trie` extra can be installed (`pip install simplemma[marisa-trie]`,
from version 1.1.0); `StreamDictionaryFactory` for the same low RAM with no
extra dependency and no cache to warm up, at a bigger speed cost. The RAM
saving compounds with every additional language kept loaded, since
`DefaultDictionaryFactory` holds each cached language's full dict in
memory — though German is near the largest shipped dictionary and the
figures include a fixed Python baseline, so smaller languages add less than
the absolute numbers suggest.

To force a backend instead of relying on `low_memory=True`, pass it
explicitly: `DefaultStrategy(dictionary_factory=TrieDictionaryFactory())`
or `DefaultStrategy(dictionary_factory=StreamDictionaryFactory())`, both
importable from `simplemma.strategies.dictionaries`.

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
| `ar` | Arabic | 297 | 49 | 0.77 | on UD AR-PADT; real-world (unsegmented) input scores ≈0.74, see note below |
| `ast` | Asturian | 154 | 36 |  |  |
| `bg` | Bulgarian | 139 | 18 | 0.85 | on UD BG-BTB |
| `ca` | Catalan | 640 | 63 | 0.89 | on UD CA-AnCora |
| `cs` | Czech | 355 | 44 | 0.91 | on UD CS-FicTree |
| `cy` | Welsh | 402 | 21 | 0.91 | on UD CY-CCG |
| `da` | Danish | 778 | 115 | 0.93 | on UD DA-DDT, alternative: [lemmy](https://github.com/sorenlind/lemmy) |
| `de` | German | 1,115 | 334 | 0.95 | on UD DE-GSD, see also [German-NLP list](https://github.com/adbar/German-NLP#Lemmatization) |
| `el` | Greek | 248 | 27 | 0.91 | on UD EL-GDT |
| `en` | English | 181 | 77 | 0.95 | on UD EN-LinES, alternative: [LemmInflect](https://github.com/bjascob/LemmInflect) |
| `enm` | Middle English | 43 | 6 |  |  |
| `eo` | Esperanto | 191 | 18 | 0.95 | on UD EO-PraGo |
| `es` | Spanish | 823 | 88 | 0.91 | on UD ES-AnCora |
| `et` | Estonian | 2,662 | 92 | 0.84 | on UD ET-EWT, low coverage |
| `fa` | Persian | 17 | 4 | 0.89 | on UD FA-Seraji |
| `fi` | Finnish | 3,547 | 125 | 0.86 | on UD FI-FTB, see [this benchmark](https://github.com/aajanki/finnish-pos-accuracy) |
| `fr` | French | 248 | 37 | 0.93 | on UD FR-Sequoia |
| `ga` | Irish | 444 | 48 | 0.89 | on UD GA-IDT |
| `gd` | Gaelic | 72 | 15 | 0.84 | on UD GD-ARCOSG |
| `gl` | Galician | 426 | 43 | 0.88 | on UD GL-CTG |
| `grc` | Ancient Greek | 849 | 22 | 0.76 | on UD GRC-PROIEL (best available; no general-register grc treebank exists) |
| `gv` | Manx | 77 | 14 | 0.84 | on UD GV-Cadhan |
| `hbs` | Serbo-Croatian | 610 | 49 | 0.87 | on UD HR-SET + SR-SET (token-weighted); Croatian and Serbian lists to be added later |
| `he` | Hebrew | 104 | 10 | 0.88 | on UD HE-HTB; real-world (unsegmented) input scores ≈0.77, see note below |
| `hi` | Hindi | 53 | 11 | 0.93 | on UD HI-HDTB |
| `hu` | Hungarian | 492 | 36 | 0.85 | on UD HU-Szeged |
| `hy` | Armenian | 467 | 17 | 0.88 | on UD HY-BSUT |
| `id` | Indonesian | 21 | 4 | 0.93 | on UD ID-CSUI |
| `is` | Icelandic | 208 | 17 | 0.78 | on UD IS-GC |
| `it` | Italian | 357 | 28 | 0.93 | on UD IT-ISDT |
| `ka` | Georgian | 448 | 16 | 0.82 | on UD KA-GLC |
| `la` | Latin | 1,144 | 63 | 0.85 | on UD LA-PROIEL |
| `lb` | Luxembourgish | 306 | 79 |  | only a <1k-token UD treebank available |
| `lt` | Lithuanian | 365 | 28 | 0.84 | on UD LT-ALKSNIS |
| `lv` | Latvian | 177 | 14 | 0.78 | on UD LV-LVTB |
| `mk` | Macedonian | 551 | 39 | 0.73 | on UD MK-MTB |
| `ml` | Malayalam | 746 | 64 | 0.69 | on UD ML-UFAL (small treebank), experimental |
| `ms` | Malay | 17 | 4 |  |  |
| `nb` | Norwegian (Bokmål) | 633 | 138 | 0.81 | on UD NO-Bokmaal |
| `nl` | Dutch | 369 | 125 | 0.92 | on UD NL-Alpino, excl. underscore-joined compound lemmas |
| `nn` | Norwegian (Nynorsk) | 137 | 36 | 0.76 | on UD NO-Nynorsk |
| `pl` | Polish | 3,670 | 264 | 0.93 | on UD PL-LFG |
| `pt` | Portuguese | 926 | 95 | 0.92 | on UD PT-GSD |
| `ro` | Romanian | 342 | 36 | 0.92 | on UD RO-RRT |
| `ru` | Russian | 1,357 | 128 | 0.89 | on UD RU-SynTagRus, alternative: [pymorphy2](https://github.com/kmike/pymorphy2/) |
| `se` | Northern Sámi | 115 | 7 | 0.95 | on UD SME-Giella |
| `sk` | Slovak | 908 | 73 | 0.93 | on UD SK-SNK |
| `sl` | Slovene | 147 | 30 | 0.92 | on UD SL-SSJ |
| `sq` | Albanian | 96 | 10 | 0.72 | on UD SQ-STAF |
| `sv` | Swedish | 871 | 114 | 0.91 | on UD SV-Talbanken, alternative: [lemmy](https://github.com/sorenlind/lemmy) |
| `sw` | Swahili | 4,869 | 4 |  | experimental |
| `tl` | Tagalog | 71 | 18 | 0.84 | on UD TL-TRG |
| `tr` | Turkish | 1,236 | 40 | 0.91 | on UD TR-KeNet |
| `uk` | Ukrainian | 502 | 35 | 0.90 | on UD UK-IU, alternative: [pymorphy2](https://github.com/kmike/pymorphy2/) |


Languages marked as low-coverage may be better served by
language-specific libraries, which are referenced where an open-source
Python alternative exists; Simplemma still provides limited functionality.
*Experimental* means the language is untested, or that its data or
lemmatization may have issues.

The scores measure how accurately tokens are mapped to their lemma on
[Universal Dependencies](https://universaldependencies.org/) treebanks,
over single word tokens (including some contractions but not merged
prepositions). Each figure is the accuracy on that language's
best-performing general-purpose treebank; parallel, spoken, learner,
historical and other narrow-domain treebanks are excluded. Two
annotation-driven exceptions: the Dutch figure excludes underscore-joined
compound lemmas (e.g. `klooster_orde`), an Alpino convention that
single-token output cannot match — ≈0.88 without that exclusion; Hebrew and
Arabic proclitics fuse onto their host word in real text but are scored as
pre-split sub-tokens by the protocol above, so on whole, unsegmented input
those accuracies are ≈0.77 and ≈0.74. See the `training/` folder for more.

The benchmark only incidentally captures what this library is most useful
for, the lemmatization of less frequent words. In some languages a fixed
set of words such as pronouns can be mapped by hand to improve results.


<!-- include:languages:end -->
## Speed

The following orders of magnitude are provided for reference only and
were measured on an old laptop to establish a lower bound:

-   Tokenization: > 1 million tokens/sec
-   Sentence splitting: > 100 MB of text per second
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
