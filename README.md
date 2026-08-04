# Simplemma: fast multilingual lemmatization for Python

[![Python package](https://img.shields.io/pypi/v/simplemma.svg)](https://pypi.python.org/pypi/simplemma)
[![Downloads](https://img.shields.io/pypi/dm/simplemma.svg)](https://pypistats.org/packages/simplemma)
[![Python versions](https://img.shields.io/pypi/pyversions/simplemma.svg)](https://pypi.python.org/pypi/simplemma)
[![Code Coverage](https://img.shields.io/codecov/c/github/adbar/simplemma.svg)](https://codecov.io/gh/adbar/simplemma)
[![Reference DOI: 10.5281/zenodo.4673264](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.4673264-brightgreen)](https://doi.org/10.5281/zenodo.4673264)

Fast, dependency-free lemmatization for 54 languages.
Pure Python, no models to download, works offline.

- **A 19 MB install** with no per-language downloads: 9 of the 54 languages have
  no Stanza lemmatizer and 34 no spaCy pipeline
- **~1.9M tokens/s** (German) and **~3.4M** (English), milliseconds to first lemma
- **Tunable RAM footprint**: ~175 MB, ~50 MB with `low_memory=True`, or ~30 MB per
  language with tries
- **0.91 to 0.97 accuracy** for 34 languages, German at 0.97 and English at
  0.96, and 0.85 to 0.90 for morphologically richer ones such as Hungarian,
  Latin and Ancient Greek: a few points behind trained neural pipelines,
  hundreds of times faster
- Useful utilities included: script-aware tokenizer, rule-based sentence
  splitter, dictionary-based language detection


## Purpose

<!-- include:pitch:start -->
[Lemmatization](https://en.wikipedia.org/wiki/Lemmatisation) groups the
inflected forms of a word so they can be analysed as a single item,
identified by the word's lemma, or dictionary form. Unlike stemming, the
output is always a valid linguistic form.

*Simplemma* provides a simple and multilingual approach to looking for
base forms. It needs no morphosyntactic information and processes a raw
series of tokens, or a text through its built-in tokenizer. It is not as
powerful as full-fledged solutions, but it is generic, easy to install
and fast, and its small footprint suits contexts where speed and
simplicity matter: low-resource settings, teaching, or a baseline for
lemmatization and morphological analysis.

Currently, 54 languages are partly or fully supported (see the list below).
<!-- include:pitch:end -->


## Installation

<!-- include:quickstart:start -->
The current library is written in pure Python with no dependencies:
`pip install simplemma`

- `pip install -U simplemma` for updates
- `pip install git+https://github.com/adbar/simplemma` for the cutting-edge version
- `pip install simplemma[marisa-trie]` for the lowest memory usage. For a
  dependency-free alternative, pass `low_memory=True` (see
  [Memory usage](https://adbar.github.io/simplemma/memory-usage/))

Python 3.10 or later is required: the last version supporting 3.8 and 3.9
is `simplemma==1.1.2`, and `simplemma==1.0.0` for 3.6 and 3.7.


## Usage

<!-- include:quickstart:end -->

### Quick start

<!-- include:usage:start -->
Pick a language and apply it to a single word, to a list of tokens, or to a
whole text through the built-in tokenizer:

``` python
>>> import simplemma

>>> simplemma.lemmatize('masks', lang='en')
'mask'

>>> mytokens = ['Hier', 'sind', 'Vaccines']
>>> [simplemma.lemmatize(t, lang='de') for t in mytokens]
['hier', 'sein', 'Vaccines']

>>> simplemma.is_known('spaghetti', lang='it')
True

>>> simplemma.simple_tokenizer('Hier sind Vaccines.')
['Hier', 'sind', 'Vaccines', '.']

>>> simplemma.text_lemmatizer('Hier sind Vaccines.', lang=('de', 'en'))
['hier', 'sein', 'vaccine', '.']
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
```


### Greedier decomposition

For certain languages a greedier decomposition is activated by default
as it can be beneficial, mostly due to a certain capacity to address
affixes in an unsupervised way. It can be triggered manually by setting
the `greedy` parameter to `True`, which adds an iteration of the search
algorithm and may come closer to stemming than to lemmatization.

``` python
>>> simplemma.lemmatize('ausgezeichneten', lang='de', greedy=False)
'ausgezeichnet' # 1 step: reduction to past participle
>>> simplemma.lemmatize('ausgezeichneten', lang='de', greedy=True)
'auszeichnen' # 2 steps: further reduction to infinitive verb
```


### Tokenization

A simple tokenization function is provided for convenience:

``` python
>>> from simplemma import simple_tokenizer
>>> simple_tokenizer('Lorem ipsum dolor sit amet, consectetur elit.')
['Lorem', 'ipsum', 'dolor', 'sit', 'amet', ',', 'consectetur', 'elit', '.']
# for an iterator instead of a list, use the RegexTokenizer directly
>>> from simplemma import RegexTokenizer
>>> RegexTokenizer().split_text('Lorem ipsum dolor sit amet')
<generator object ...>
```

The tokenizer is script-aware: in-word joiners stay inside their word
(`l'homme`, `בית־ספר`), as do the combining marks of Hebrew, Arabic,
Devanagari and Malayalam. Punctuation becomes its own token, but a run of
the same character stays whole (`...`, `--`), and numbers keep their
internal separators (`3,50`, `4:1`, `3/5`). A currency sign priced against a
number is a token of its own on either side, even where the text glues it
(`€3.50` and `50€` both split, following UD gold). A sign attached to a word
stays part of it (`R$`, `US$`). Characters outside the word and punctuation
sets, such as emoji and arrows, are not emitted as tokens.

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

Both functions know where sentences start, and lower a sentence-initial word
before looking it up, since its capital is positional rather than lexical.
Mid-sentence capitals are left alone, so the same word can lemmatize
differently depending on its position:

``` python
>>> text_lemmatizer('Laufen ist gesund.', lang='de')
['laufen', 'sein', 'gesund', '.']
>>> text_lemmatizer('Beim Laufen ist es gesund.', lang='de')
['beim', 'Laufen', 'sein', 'es', 'gesund', '.']
```

For Danish, English and German the lowering is skipped when the capitalized
form looks like a proper noun, and for a few languages ALL-CAPS acronyms are
kept verbatim. See the [`casing`
module](https://adbar.github.io/simplemma/reference/casing/) for details.


### Sentence splitting

`split_sentences()` segments raw text into sentences, using rules plus
per-language abbreviation data where it measurably pays (currently `cs`,
`de`, `en`, `fr`, `nl`, `pl`, `pt`). Other codes use the generic rules,
which stay close in quality. `lang='el'` additionally treats `;` as a
question mark, and a blank line always starts a new sentence. On Universal
Dependencies data the splitter matches or beats NLTK's punkt on 6 of 7
evaluated languages, with no added dependency.

``` python
>>> from simplemma import split_sentences
>>> split_sentences('Das Tor fiel in der 95. Minute. Das Spiel war aus.', lang='de')
['Das Tor fiel in der 95. Minute.', 'Das Spiel war aus.']
```

The sentences are slices of the input with surrounding whitespace removed:
nothing is normalized or rewritten. `lang` also accepts a tuple, like the
other entry points, and pre-tokenized or OCR-style text whose punctuation
is spaced out (`Le prix est bas .`) still splits correctly.

On the held-out PUD corpora (the same 1000 professionally translated
sentences per language), sentence-boundary F1 is 0.98 to 0.998. Register
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
'ser' # 3rd-person plural of 'ser', but 'son' is also a noun (a Cuban music genre)
```

Working without morphosyntactic information keeps things simple but sets a
hard ceiling on accuracy, for instance when disambiguating past participles
from verb-derived adjectives. Such words are usually left unchanged. Since
the focus lies on overall coverage, some short frequent words (typically
pronouns and conjunctions) may need post-processing, generally a few dozen
tokens per language.

The greedy algorithm seldom produces invalid forms and works best in the
low-frequency range, notably for compound words and neologisms. Aggressive
decomposition is only useful for morphologically-rich languages, where it
can act as a linguistically motivated stemmer.


### Language detection

Language detection takes a text and a tuple `lang` of languages of
interest. `langdetect()` returns each language code with its score, plus
"unk" for the proportion of unknown tokens. `in_target_language()` returns
the single ratio of tokens belonging to the target language(s). Scores are
proportions between 0 and 1, computed independently per language, so a
token recognized in several counts towards each and they need not sum to 1.

``` python
# import necessary functions
>>> from simplemma import in_target_language, langdetect
# language detection
>>> langdetect('"Exoplaneta, též extrasolární planeta, je planeta obíhající kolem jiné hvězdy než kolem Slunce."', lang=("cs", "sk"))
[('cs', 1.0), ('sk', 0.25), ('unk', 0.0)]
# proportion of known words
>>> in_target_language("opera post physica posita (τὰ μετὰ τὰ φυσικά)", lang="la")
0.6666666666666666
```

The `greedy` argument triggers use of the greedier decomposition algorithm
described above, thus extending word coverage and recall of detection at
the potential cost of a lesser accuracy.


<!-- include:usage:end -->
### Advanced usage via classes and lower memory usage

Instantiating the classes instead of calling the functions gives more
control: a custom `LemmatizationStrategy`, a `DictionaryFactory` with its own
cache size, or one of the low-memory backends selected by `low_memory=True`.
See [Classes and strategies](https://adbar.github.io/simplemma/classes-and-strategies/)
for the classes and [Memory usage](https://adbar.github.io/simplemma/memory-usage/)
for the `low_memory` flag and a comparison of the three dictionary backends.

## Supported languages
<!-- include:languages:start -->

The following languages are available, identified by their [BCP 47
language tag](https://en.wikipedia.org/wiki/IETF_language_tag), which
typically corresponds to the [ISO 639-1 code](
https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes).
If no such code exists, a [ISO 639-3
code](https://en.wikipedia.org/wiki/List_of_ISO_639-3_codes) is
used instead.

Available languages (2026-08-04):

The *Forms* column counts the inflected word forms stored in the
dictionary, while *Lemmata* counts the distinct base forms they map to
(both in thousands). A large gap between the two reflects rich
morphology rather than a data error.


| Code | Language | Forms (10³) | Lemm. (10³) | Acc. | Comments |
| ---- | -------- | ----------- | ------------| ---- | -------- |
| `ar` | Arabic | 298 | 49 | 0.91 | on UD AR-PADT; real-world (unsegmented) input scores ≈0.85 |
| `ast` | Asturian | 154 | 36 |  |  |
| `bg` | Bulgarian | 226 | 26 | 0.89 | on UD BG-BTB |
| `ca` | Catalan | 641 | 64 | 0.95 | on UD CA-AnCora |
| `cs` | Czech | 363 | 47 | 0.95 | on UD CS-FicTree |
| `cy` | Welsh | 402 | 21 | 0.94 | on UD CY-CCG |
| `da` | Danish | 788 | 117 | 0.95 | on UD DA-DDT, alternative: [lemmy](https://github.com/sorenlind/lemmy) |
| `de` | German | 1,116 | 334 | 0.97 | on UD DE-GSD, see also [German-NLP list](https://github.com/adbar/German-NLP#Lemmatization) |
| `el` | Greek | 250 | 28 | 0.93 | on UD EL-GDT |
| `en` | English | 182 | 78 | 0.96 | on UD EN-LinES, alternative: [LemmInflect](https://github.com/bjascob/LemmInflect) |
| `enm` | Middle English | 43 | 6 |  |  |
| `eo` | Esperanto | 191 | 18 | 0.95 | on UD EO-PraGo (test-only treebank, no train split) |
| `es` | Spanish | 824 | 88 | 0.93 | on UD ES-AnCora |
| `et` | Estonian | 2,690 | 95 | 0.91 | on UD ET-EWT, low coverage |
| `fa` | Persian | 47 | 14 | 0.95 | on UD FA-Seraji |
| `fi` | Finnish | 3,547 | 125 | 0.91 | on UD FI-TDT, see [this benchmark](https://github.com/aajanki/finnish-pos-accuracy) |
| `fr` | French | 250 | 37 | 0.96 | on UD FR-Sequoia |
| `ga` | Irish | 444 | 48 | 0.92 | on UD GA-IDT |
| `gd` | Gaelic | 73 | 16 | 0.89 | on UD GD-ARCOSG |
| `gl` | Galician | 426 | 43 | 0.92 | on UD GL-CTG |
| `grc` | Ancient Greek | 852 | 22 | 0.86 | on UD GRC-PROIEL (best available; no general-register grc treebank exists), alternative: [odyCy](https://github.com/centre-for-humanities-computing/odyCy) |
| `gv` | Manx | 77 | 14 | 0.92 | on UD GV-Cadhan |
| `hbs` | Serbo-Croatian | 610 | 49 | 0.90 | on UD HR-SET + SR-SET (token-weighted); Croatian and Serbian lists to be added later |
| `he` | Hebrew | 105 | 10 | 0.93 | on UD HE-HTB; real-world (unsegmented) input scores ≈0.82 |
| `hi` | Hindi | 86 | 19 | 0.95 | on UD HI-HDTB |
| `hu` | Hungarian | 1,763 | 45 | 0.88 | on UD HU-Szeged |
| `hy` | Armenian | 467 | 17 | 0.91 | on UD HY-BSUT |
| `id` | Indonesian | 22 | 4 | 0.93 | on UD ID-CSUI |
| `is` | Icelandic | 210 | 18 | 0.81 | on UD IS-GC |
| `it` | Italian | 358 | 28 | 0.95 | on UD IT-ISDT |
| `ka` | Georgian | 448 | 16 | 0.85 | on UD KA-GLC |
| `la` | Latin | 1,289 | 70 | 0.89 | on UD LA-PROIEL, alternative: [LatinCy](https://spacy.io/universe/project/latincy) |
| `lb` | Luxembourgish | 306 | 79 |  | only a <1k-token UD treebank available |
| `lt` | Lithuanian | 365 | 28 | 0.86 | on UD LT-ALKSNIS |
| `lv` | Latvian | 178 | 15 | 0.83 | on UD LV-LVTB |
| `mk` | Macedonian | 546 | 41 | 0.92 | on UD MK-MTB (test-only treebank, no train split) |
| `ml` | Malayalam | 746 | 64 | 0.69 | on UD ML-UFAL (small test-only treebank, no train split), experimental |
| `ms` | Malay | 18 | 4 |  |  |
| `nb` | Norwegian (Bokmål) | 641 | 140 | 0.84 | on UD NO-Bokmaal |
| `nl` | Dutch | 370 | 125 | 0.96 | on UD NL-Alpino, excl. underscore-joined compound lemmas |
| `nn` | Norwegian (Nynorsk) | 138 | 36 | 0.83 | on UD NO-Nynorsk |
| `pl` | Polish | 3,670 | 264 | 0.96 | on UD PL-LFG |
| `pt` | Portuguese | 927 | 95 | 0.94 | on UD PT-GSD |
| `ro` | Romanian | 345 | 37 | 0.94 | on UD RO-RRT |
| `ru` | Russian | 1,362 | 131 | 0.93 | on UD RU-SynTagRus, alternative: [pymorphy2](https://github.com/kmike/pymorphy2/) |
| `se` | Northern Sámi | 115 | 7 | 0.97 | on UD SME-Giella |
| `sk` | Slovak | 908 | 73 | 0.92 | on UD SK-SNK |
| `sl` | Slovene | 157 | 31 | 0.95 | on UD SL-SSJ |
| `sq` | Albanian | 96 | 10 | 0.71 | on UD SQ-STAF |
| `sv` | Swedish | 964 | 129 | 0.94 | on UD SV-Talbanken, alternative: [lemmy](https://github.com/sorenlind/lemmy) |
| `sw` | Swahili | 4,869 | 4 |  | experimental |
| `tl` | Tagalog | 78 | 25 | 0.84 | on UD TL-TRG (test-only treebank, no train split) |
| `tr` | Turkish | 1,236 | 40 | 0.92 | on UD TR-KeNet |
| `uk` | Ukrainian | 599 | 45 | 0.92 | on UD UK-IU, alternative: [pymorphy2](https://github.com/kmike/pymorphy2/) |


Languages marked as low-coverage may be better served by
language-specific libraries, which are referenced where an open-source
Python alternative exists. Simplemma still provides limited functionality.
*Experimental* means the language is untested, or that its data or
lemmatization may have issues.

The scores measure how accurately tokens are mapped to their lemma on
[Universal Dependencies](https://universaldependencies.org/) treebanks, over
single word tokens (including some contractions but not merged prepositions).
Each figure is the accuracy on the held-out dev+test splits of each language's
best-performing general-purpose treebank; train splits are excluded from
scoring as they are mined for the correction lists and gate every candidate.
The `training/` folder documents the protocol, the annotation-driven
exceptions (Dutch compound lemmas, Hebrew and Arabic proclitics,
Finnish/Estonian/Hungarian compound-boundary markers) and how to reproduce
the figures.

The benchmark only incidentally captures what this library is most useful
for, the lemmatization of less frequent words.


<!-- include:languages:end -->
## Speed

Measured on real text from Universal Dependencies treebanks. Figures vary
with hardware, language and how repetitive the text is:

-   Lemmatization: 1.9M tokens/sec (German), 3.4M (English), tokenization included
-   Tokenization alone: > 1 million tokens/sec
-   Sentence splitting: > 100 MB of text per second


## Roadmap

- [ ] Return all candidate lemmas for ambiguous words (#94, #132)
- [ ] Optional compound splitting (#141)
- [ ] More and better source data (#1, #3)


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
