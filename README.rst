# Simplemma: a simple multilingual lemmatizer for Python

.. image:: https://img.shields.io/pypi/v/simplemma.svg
    :target: https://pypi.python.org/pypi/simplemma
    :alt: Python package

.. image:: https://img.shields.io/pypi/l/simplemma.svg
    :target: https://pypi.python.org/pypi/simplemma
    :alt: License

.. image:: https://img.shields.io/pypi/pyversions/simplemma.svg
    :target: https://pypi.python.org/pypi/simplemma
    :alt: Python versions

.. image:: https://img.shields.io/codecov/c/github/adbar/simplemma.svg
    :target: https://codecov.io/gh/adbar/simplemma
    :alt: Code Coverage

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Code style: black

.. image:: https://img.shields.io/badge/DOI-10.5281%2Fzenodo.4673264-brightgreen
   :target: https://doi.org/10.5281/zenodo.4673264
   :alt: Reference DOI: 10.5281/zenodo.4673264

## Purpose

`Lemmatization <https://en.wikipedia.org/wiki/Lemmatisation>`_ is the process of grouping together the inflected forms of a word so they can be analysed as a single item, identified by the word's lemma, or dictionary form. Unlike stemming, lemmatization outputs word units that are still valid linguistic forms.

In modern natural language processing (NLP), this task is often indirectly tackled by more complex systems encompassing a whole processing pipeline. However, it appears that there is no straightforward way to address lemmatization in Python although this task can be crucial in fields such as information retrieval and NLP.

*Simplemma* provides a simple and multilingual approach to look for base forms or lemmata. It may not be as powerful as full-fledged solutions but it is generic, easy to install and straightforward to use. In particular, it does not need morphosyntactic information and can process a raw series of tokens or even a text with its built-in tokenizer. By design it should be reasonably fast and work in a large majority of cases, without being perfect.

With its comparatively small footprint it is especially useful when speed and simplicity matter, in low-resource contexts, for educational purposes, or as a baseline system for lemmatization and morphological analysis.

Currently, 48 languages are partly or fully supported (see table below).


## Installation

The current library is written in pure Python with no dependencies:

`pip install simplemma`

- `pip3` where applicable
- `pip install -U simplemma` for updates


## Usage


### Dictionary Factory

Simplemma uses dictionaries to lemmatize words. Such dictionaries are provided with the libraries and must be loaded to memory before they can be used.

The `DictionaryFactory` uses a LRU cache for dictionaries. The user can configure the size of that cache when instantiating the class using the `cache_max_size` option (defaults to 65536 bytes).

Once instantiated, the `get_dictionaries` method provides a dictionary of languages and their associated dictionaries


```python
    >>> from simplemma import DictionaryFactory
    >>> dictionaryFactory = DictionaryFactory(cache_max_size = 65536)
    >>> dictionaries = dictionaryFactory.get_dictionaries(('en', 'de'))
    >>> englishDictionary = dictionaries['en']
```



### Tokenizer

A simple `Tokenizer`class to tokenize strings is included for convenience:

```python
    >>> from simplemma import Tokenizer
    >>> tokenizer = Tokenizer()
    >>> tokenizer.tokenize('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')
    ['Lorem', 'ipsum', 'dolor', 'sit', 'amet', ',', 'consectetur', 'adipiscing', 'elit', ',', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua', '.']
    # use iterator instead
    >>> tokenizer.tokenize('Lorem ipsum dolor sit amet', iterate=True)
```

### Lemmatizer

The `Lemmatizer` class is uses dictionaries provided by a `DictionaryFactory` to lemmatize words/tokens.
It uses the `Tokenizer` to tokenize text and lemmatize all of its tokens.

#### Instantiation

`Lemmatizer^ accepts several arguments:
* `dictionaryFactory` can be used to control caching of the dictionaries in memory
* `lemmatized_tokens_cache_max_size` defines the LRU cache size for calculated lemmas (defaults to 1048576 bytes)
* `levenshtein_distance_cache_max_size` defines the LRU cache size for calculated levenshtein distances (defaults to 1048576 bytes)

```python
	# Create dictionary factory
    >>> from simplemma import DictionaryFactory
    >>> dictionaryFactory = DictionaryFactory()
    # Create lemmatizer
    >>> from simplemma import Lemmatizer
    >>> lemmatizer = Lemmatizer(dictionaryFactory, lemmatized_tokens_cache_max_size = 1048576, levenshtein_distance_cache_max_size = 1048576)
```

#### Word-by-word lemmatization

`Lemmatizer` is used by selecting a language of interest and then applying the data on a list of words.

```python
    >>> from simplemma import Lemmatizer
    >>> lemmatizer = Lemmatizer()
    # get a word
    >>> myword = 'masks'
    # decide which language to use and apply it on a word form
    >>> lemmatizer.lemmatize_token(myword, lang='en')
    'mask'
    # grab a list of tokens
    >>> mytokens = ['Hier', 'sind', 'Vaccines']
    >>> for token in mytokens:
    >>>     lemmatizer.lemmatize_token(token, lang='de')
    'hier'
    'sein'
    'Vaccines'
    # list comprehensions can be faster
    >>> [lemmatizer.lemmatize_token(t, lang='de') for t in mytokens]
    ['hier', 'sein', 'Vaccines']
```

Chaining several languages can improve coverage, they are used in sequence:

```python
    >>> from simplemma import Lemmatizer
    >>> lemmatizer = Lemmatizer()
    >>> lemmatizer.lemmatize_token('Vaccines', lang=('de', 'en'))
    'vaccine'
    >>> lemmatizer.lemmatize_token('spaghettis', lang='it')
    'spaghettis'
    >>> lemmatizer.lemmatize_token('spaghettis', lang=('it', 'fr'))
    'spaghetti'
    >>> lemmatizer.lemmatize_token('spaghetti', lang=('it', 'fr'))
    'spaghetto'
```

There are cases in which a greedier decomposition and lemmatization algorithm is better. It is deactivated by default:

```python
    # same example as before, comes to this result in one step
    >>> lemmatizer.lemmatize_token('spaghettis', lang=('it', 'fr'), greedy=True)
    'spaghetto'
    # a German case
    >>> lemmatizer.lemmatize_token('angekündigten', lang='de')
    'ankündigen' # infinitive verb
    >>> lemmatizer.lemmatize_token('angekündigten', lang='de', greedy=False)
    'angekündigt' # past participle
```

`Lemmatizer` also can tell if a given token exists in any of the dictionaries for the given languages:

```python
    # same example as before, comes to this result in one step
    >>> lemmatizer.is_token_known('spaghetti', lang='it')
    True
```

#### Text lemmatization

The functions `lemmatize_text()` and `lemmatize_text_iterator()` chain tokenization and lemmatization. They can take `greedy` (affecting lemmatization) and `silent` (affecting errors and logging) as arguments:

```python
    >>> from simplemma import Lemmatizer
    >>> lemmatizer = Lemmatizer()
    >>> lemmatizer.lemmatize_text('Sou o intervalo entre o que desejo ser e os outros me fizeram.', lang='pt')
    # caveat: desejo is also a noun, should be desejar here
    ['ser', 'o', 'intervalo', 'entre', 'o', 'que', 'desejo', 'ser', 'e', 'o', 'outro', 'me', 'fazer', '.']
    # same principle, returns an iterator and not a list
    >>> lemmatizer.lemmatize_text_iterator('Sou o intervalo entre o que desejo ser e os outros me fizeram.', lang='pt')
```

#### Caveats

```python
    # don't expect too much though
    # this diminutive form isn't in the model data
    >>> lemmatizer.lemmatize('spaghettini', lang='it')
    'spaghettini' # should read 'spaghettino'
    # the algorithm cannot choose between valid alternatives yet
    >>> lemmatizer.lemmatize('son', lang='es')
    'son' # valid common name, but what about the verb form?
```

As the focus lies on overall coverage, some short frequent words (typically: pronouns and conjunctions) may need post-processing, this generally concerns a few dozens of tokens per language.

The current absence of morphosyntactic information is both an advantage in terms of simplicity and an impassable frontier regarding lemmatization accuracy, e.g. disambiguation between past participles and adjectives derived from verbs in Germanic and Romance languages. In most cases, `simplemma` often does not change such input words.

The greedy algorithm seldom produces invalid forms. It is designed to work best in the low-frequency range, notably for compound words and neologisms. Aggressive decomposition is only useful as a general approach in the case of morphologically-rich languages, where it can also act as a linguistically motivated stemmer.

Bug reports over the `issues page <https://github.com/adbar/simplemma/issues>`_ are welcome.


### Language detector

Language detection works by providing a text and tuple `lang` consisting of a series of languages of interest. Scores between 0 and 1 are returned.

The `detect_languages()` function returns a list of language codes along with scores and adds "unk" for unknown or out-of-vocabulary words. The latter can also be calculated by using the function `detect_coverage_of_languages()` which returns a ratio.

```python
    # import necessary functions
    >>> from simplemma.laguagedetector import LanguageDetector
    >>> languageDetector = LanguageDetector()
    # language detection
    >>> languageDetector.detect_languages('"Moderní studie narazily na několik tajemství." Extracted from Wikipedia.', lang=("cs", "sk"))
    [('cs', 0.625), ('unk', 0.375), ('sk', 0.125)]
    # proportion of known words
    >>> languageDetector.detect_coverage_of_languages("opera post physica posita (τὰ μετὰ τὰ φυσικά)", lang="la")
    0.5
```

## Supported languages

The following languages are available using their `ISO 639-1 code <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_:


======= ==================== =========== ===== ========================================================================
Available languages (2022-09-05)
-----------------------------------------------------------------------------------------------------------------------
Code    Language             Forms (10³) Acc.  Comments
======= ==================== =========== ===== ========================================================================
``bg``  Bulgarian            213
``ca``  Catalan              579
``cs``  Czech                187         0.88  on UD CS-PDT
``cy``  Welsh                360
``da``  Danish               554         0.92  on UD DA-DDT, alternative: `lemmy <https://github.com/sorenlind/lemmy>`_
``de``  German               682         0.95  on UD DE-GSD, see also `German-NLP list <https://github.com/adbar/German-NLP#Lemmatization>`_
``el``  Greek                183         0.88  on UD EL-GDT
``en``  English              136         0.94  on UD EN-GUM, alternative: `LemmInflect <https://github.com/bjascob/LemmInflect>`_
``enm`` Middle English       38
``es``  Spanish              720         0.94  on UD ES-GSD
``et``  Estonian             133               low coverage
``fa``  Persian              10                experimental
``fi``  Finnish              2,106             evaluation and alternatives: see `this benchmark <https://github.com/aajanki/finnish-pos-accuracy>`_
``fr``  French               217         0.94  on UD FR-GSD
``ga``  Irish                383
``gd``  Gaelic               48
``gl``  Galician             384
``gv``  Manx                 62
``hbs`` Serbo-Croatian       838               Croatian and Serbian lists to be added later
``hi``  Hindi                58                experimental
``hu``  Hungarian            458
``hy``  Armenian             323
``id``  Indonesian           17          0.91  on UD ID-CSUI
``is``  Icelandic            175
``it``  Italian              333         0.93  on UD IT-ISDT
``ka``  Georgian             65
``la``  Latin                850
``lb``  Luxembourgish        305
``lt``  Lithuanian           247
``lv``  Latvian              168
``mk``  Macedonian           57
``ms``  Malay                14
``nb``  Norwegian (Bokmål)   617
``nl``  Dutch                254         0.91  on UD-NL-Alpino
``nn``  Norwegian (Nynorsk)
``pl``  Polish               3,733       0.91  on UD-PL-PDB
``pt``  Portuguese           933         0.92  on UD-PT-GSD
``ro``  Romanian             311
``ru``  Russian              607               alternative: `pymorphy2 <https://github.com/kmike/pymorphy2/>`_
``se``  Northern Sámi        113               experimental
``sk``  Slovak               846         0.92  on UD SK-SNK
``sl``  Slovene              136
``sq``  Albanian             35
``sv``  Swedish              658               alternative: `lemmy <https://github.com/sorenlind/lemmy>`_
``sw``  Swahili              10                experimental
``tl``  Tagalog              33                experimental
``tr``  Turkish              1,333       0.88  on UD-TR-Boun
``uk``  Ukrainian            190               alternative: `pymorphy2 <https://github.com/kmike/pymorphy2/>`_
======= ==================== =========== ===== ========================================================================


*Low coverage* mentions means one would probably be better off with a language-specific library, but *simplemma* will work to a limited extent. Open-source alternatives for Python are referenced if possible.

*Experimental* mentions indicate that the language remains untested or that there could be issues with the underlying data or lemmatization process.

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions), they describe to what extent simplemma can accurately map tokens to their lemma form. They can be reproduced by concatenating all available UD files and by using the script `udscore.py` in the `tests/` folder.

This library is particularly relevant as regards the lemmatization of less frequent words. Its performance in this case is only incidentally captured by the benchmark above. In some languages, a fixed number of words such as pronouns can be further mapped by hand to enhance performance.


## Performance

Orders of magnitude given for reference only, measured on an old laptop to give a lower bound:

- Tokenization: > 1 million tokens/sec
- Lemmatization: > 250,000 words/sec

Installing the most recent Python version can improve speed.


### Optional pre-compilation with `mypyc <https://github.com/mypyc/mypyc>`_

1. `pip3 install mypy`
2. clone or download the source code from the repository
3. `python3 setup.py --use-mypyc bdist_wheel`
4. `pip3 install dist/*.whl` (where `*` is the compiled wheel)


## Roadmap

-  [-] Add further lemmatization lists
-  [ ] Grammatical categories as option
-  [ ] Function as a meta-package?
-  [ ] Integrate optional, more complex models?


## Credits and licenses


Software under MIT license, for the linguistic information databases see ``licenses`` folder.

The surface lookups (non-greedy mode) use lemmatization lists derived from various sources, ordered by relative importance:

- `Lemmatization lists <https://github.com/michmech/lemmatization-lists>`_ by Michal Měchura (Open Database License)
- Wiktionary entries packaged by the `Kaikki project <https://kaikki.org/>`_
- `FreeLing project <https://github.com/TALP-UPC/FreeLing>`_
- `spaCy lookups data <https://github.com/explosion/spacy-lookups-data>`_
- `Unimorph Project <https://unimorph.github.io/>`_
- `Wikinflection corpus <https://github.com/lenakmeth/Wikinflection-Corpus>`_ by Eleni Metheniti (CC BY 4.0 License)


## Contributions

Feel free to contribute, notably by `filing issues <https://github.com/adbar/simplemma/issues/>`_ for feedback, bug reports, or links to further lemmatization lists, rules and tests.

You can also contribute to this `lemmatization list repository <https://github.com/michmech/lemmatization-lists>`_.


## Other solutions

See lists: `German-NLP <https://github.com/adbar/German-NLP>`_ and `other awesome-NLP lists <https://github.com/adbar/German-NLP#More-lists>`_.

For a more complex and universal approach in Python see `universal-lemmatizer <https://github.com/jmnybl/universal-lemmatizer/>`_.


## References

.. image:: https://img.shields.io/badge/DOI-10.5281%2Fzenodo.4673264-brightgreen
   :target: https://doi.org/10.5281/zenodo.4673264
   :alt: Reference DOI: 10.5281/zenodo.4673264

Barbaresi A. (*year*). Simplemma: a simple multilingual lemmatizer for Python [Computer software] (Version *version number*). Berlin, Germany: Berlin-Brandenburg Academy of Sciences. Available from https://github.com/adbar/simplemma DOI: 10.5281/zenodo.4673264

This work draws from lexical analysis algorithms used in:

- Barbaresi, A., & Hein, K. (2017). `Data-driven identification of German phrasal compounds <https://hal.archives-ouvertes.fr/hal-01575651/document>`_. In International Conference on Text, Speech, and Dialogue Springer, pp. 192-200.
- Barbaresi, A. (2016). `An unsupervised morphological criterion for discriminating similar languages <https://aclanthology.org/W16-4827/>`_. In 3rd Workshop on NLP for Similar Languages, Varieties and Dialects (VarDial 2016), Association for Computational Linguistics, pp. 212-220.
- Barbaresi, A. (2016). `Bootstrapped OCR error detection for a less-resourced language variant <https://hal.archives-ouvertes.fr/hal-01371689/document>`_. In 13th Conference on Natural Language Processing (KONVENS 2016), pp. 21-26.
