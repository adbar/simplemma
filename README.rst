======================================================
Simplemma: a simple multilingual lemmatizer for Python
======================================================


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


Purpose
-------

`Lemmatization <https://en.wikipedia.org/wiki/Lemmatisation>`_ is the process of grouping together the inflected forms of a word so they can be analysed as a single item, identified by the word's lemma, or dictionary form. Unlike stemming, lemmatization outputs word units that are still valid linguistic forms.

In modern natural language processing (NLP), this task is often indirectly tackled by more complex systems encompassing a whole processing pipeline. However, it appears that there is no straightforward way to address lemmatization in Python although this task can be crucial in fields such as information retrieval and NLP.

*Simplemma* provides a simple and multilingual approach to look for base forms or lemmata. It may not be as powerful as full-fledged solutions but it is generic, easy to install and straightforward to use. In particular, it does not need morphosyntactic information and can process a raw series of tokens or even a text with its built-in tokenizer. By design it should be reasonably fast and work in a large majority of cases, without being perfect.

With its comparatively small footprint it is especially useful when speed and simplicity matter, in low-resource contexts, for educational purposes, or as a baseline system for lemmatization and morphological analysis.

Currently, 49 languages are partly or fully supported (see table below).


Installation
------------

The current library is written in pure Python with no dependencies:

``pip install simplemma``

- ``pip3`` where applicable
- ``pip install -U simplemma`` for updates


Usage
-----

Word-by-word
~~~~~~~~~~~~

Simplemma is used by selecting a language of interest and then applying the data on a list of words.

.. code-block:: python

    >>> import simplemma
    # get a word
    myword = 'masks'
    # decide which language to use and apply it on a word form
    >>> simplemma.lemmatize(myword, lang='en')
    'mask'
    # grab a list of tokens
    >>> mytokens = ['Hier', 'sind', 'Vaccines']
    >>> for token in mytokens:
    >>>     simplemma.lemmatize(token, lang='de')
    'hier'
    'sein'
    'Vaccines'
    # list comprehensions can be faster
    >>> [simplemma.lemmatize(t, lang='de') for t in mytokens]
    ['hier', 'sein', 'Vaccines']


Chaining languages
~~~~~~~~~~~~~~~~~~

Chaining several languages can improve coverage, they are used in sequence:


.. code-block:: python

    >>> from simplemma import lemmatize
    >>> lemmatize('Vaccines', lang=('de', 'en'))
    'vaccine'
    >>> lemmatize('spaghettis', lang='it')
    'spaghettis'
    >>> lemmatize('spaghettis', lang=('it', 'fr'))
    'spaghetti'
    >>> lemmatize('spaghetti', lang=('it', 'fr'))
    'spaghetto'


Greedier decomposition
~~~~~~~~~~~~~~~~~~~~~~

For certain languages a greedier decomposition is activated by default as it can be beneficial, mostly due to a certain capacity to address affixes in an unsupervised way. This can be triggered manually by setting the ``greedy`` parameter to ``True``.

This option also triggers a stronger reduction through a further iteration of the search algorithm, e.g. "angekündigten" → "angekündigt" (standard) → "ankündigen" (greedy). In some cases it may be closer to stemming than to lemmatization.


.. code-block:: python

    # same example as before, comes to this result in one step
    >>> simplemma.lemmatize('spaghettis', lang=('it', 'fr'), greedy=True)
    'spaghetto'
    # German case described above
    >>> simplemma.lemmatize('angekündigten', lang='de', greedy=True)
    'ankündigen' # 2 steps: reduction to infinitive verb
    >>> simplemma.lemmatize('angekündigten', lang='de', greedy=False)
    'angekündigt' # 1 step: reduction to past participle


is_known()
~~~~~~~~~~

The additional function ``is_known()`` checks if a given word is present in the language data:

.. code-block:: python

    >>> from simplemma import is_known
    >>> is_known('spaghetti', lang='it')
    True


Tokenization
~~~~~~~~~~~~

A simple tokenization function is included for convenience:

.. code-block:: python

    >>> from simplemma import simple_tokenizer
    >>> simple_tokenizer('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')
    ['Lorem', 'ipsum', 'dolor', 'sit', 'amet', ',', 'consectetur', 'adipiscing', 'elit', ',', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua', '.']
    # use iterator instead
    >>> simple_tokenizer('Lorem ipsum dolor sit amet', iterate=True)


The functions ``text_lemmatizer()`` and ``lemma_iterator()`` chain tokenization and lemmatization. They can take ``greedy`` (affecting lemmatization) and ``silent`` (affecting errors and logging) as arguments:

.. code-block:: python

    >>> from simplemma import text_lemmatizer
    >>> sentence = 'Sou o intervalo entre o que desejo ser e os outros me fizeram.'
    >>> text_lemmatizer(sentence, lang='pt')
    # caveat: desejo is also a noun, should be desejar here
    ['ser', 'o', 'intervalo', 'entre', 'o', 'que', 'desejo', 'ser', 'e', 'o', 'outro', 'me', 'fazer', '.']
    # same principle, returns a generator and not a list
    >>> from simplemma import lemma_iterator
    >>> lemma_iterator(sentence, lang='pt')


Caveats
~~~~~~~

.. code-block:: python

    # don't expect too much though
    # this diminutive form isn't in the model data
    >>> simplemma.lemmatize('spaghettini', lang='it')
    'spaghettini' # should read 'spaghettino'
    # the algorithm cannot choose between valid alternatives yet
    >>> simplemma.lemmatize('son', lang='es')
    'son' # valid common name, but what about the verb form?


As the focus lies on overall coverage, some short frequent words (typically: pronouns and conjunctions) may need post-processing, this generally concerns a few dozens of tokens per language.

The current absence of morphosyntactic information is both an advantage in terms of simplicity and an impassable frontier regarding lemmatization accuracy, e.g. disambiguation between past participles and adjectives derived from verbs in Germanic and Romance languages. In most cases, ``simplemma`` often does not change such input words.

The greedy algorithm seldom produces invalid forms. It is designed to work best in the low-frequency range, notably for compound words and neologisms. Aggressive decomposition is only useful as a general approach in the case of morphologically-rich languages, where it can also act as a linguistically motivated stemmer.

Bug reports over the `issues page <https://github.com/adbar/simplemma/issues>`_ are welcome.


Language detection
~~~~~~~~~~~~~~~~~~

Language detection works by providing a text and tuple ``lang`` consisting of a series of languages of interest. Scores between 0 and 1 are returned.

The ``lang_detector()`` function returns a list of language codes along with scores and adds "unk" at the end for unknown or out-of-vocabulary words. The latter can also be calculated by using the function ``in_target_language()`` which returns a ratio.

.. code-block:: python

    # import necessary functions
    >>> from simplemma import in_target_language, lang_detector
    # language detection
    >>> lang_detector('"Exoplaneta, též extrasolární planeta, je planeta obíhající kolem jiné hvězdy než kolem Slunce."', lang=("cs", "sk"))
    [("cs", 0.75), ("sk", 0.125), ("unk", 0.25)]
    # proportion of known words
    >>> in_target_language("opera post physica posita (τὰ μετὰ τὰ φυσικά)", lang="la")
    0.5


The ``greedy`` argument (``extensive`` in past software versions) triggers use of the greedier decomposition algorithm described above, thus extending word coverage and recall of detection at the potential cost of a lesser accuracy.


Supported languages
-------------------

The following languages are available using their `BCP 47 language tag <https://en.wikipedia.org/wiki/IETF_language_tag>`_, which is usually the `ISO 639-1 code <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_ but if no such code exists, a `ISO 639-3 code <https://en.wikipedia.org/wiki/List_of_ISO_639-3_codes>`_ is used instead:


======= ==================== =========== ===== ========================================================================
Available languages (2022-01-20)
-----------------------------------------------------------------------------------------------------------------------
Code    Language             Forms (10³) Acc.  Comments
======= ==================== =========== ===== ========================================================================
``ast`` Asturian             124
``bg``  Bulgarian            204
``ca``  Catalan              579
``cs``  Czech                187         0.89  on UD CS-PDT
``cy``  Welsh                360
``da``  Danish               554         0.92  on UD DA-DDT, alternative: `lemmy <https://github.com/sorenlind/lemmy>`_
``de``  German               675         0.95  on UD DE-GSD, see also `German-NLP list <https://github.com/adbar/German-NLP#Lemmatization>`_
``el``  Greek                181         0.88  on UD EL-GDT
``en``  English              131         0.94  on UD EN-GUM, alternative: `LemmInflect <https://github.com/bjascob/LemmInflect>`_
``enm`` Middle English       38
``es``  Spanish              665         0.95  on UD ES-GSD
``et``  Estonian             119               low coverage
``fa``  Persian              12                experimental
``fi``  Finnish              3,199             see `this benchmark <https://github.com/aajanki/finnish-pos-accuracy>`_
``fr``  French               217         0.94  on UD FR-GSD
``ga``  Irish                372
``gd``  Gaelic               48
``gl``  Galician             384
``gv``  Manx                 62
``hbs`` Serbo-Croatian       656               Croatian and Serbian lists to be added later
``hi``  Hindi                58                experimental
``hu``  Hungarian            458
``hy``  Armenian             246
``id``  Indonesian           17          0.91  on UD ID-CSUI
``is``  Icelandic            174
``it``  Italian              333         0.93  on UD IT-ISDT
``ka``  Georgian             65
``la``  Latin                843
``lb``  Luxembourgish        305
``lt``  Lithuanian           247
``lv``  Latvian              164
``mk``  Macedonian           56
``ms``  Malay                14
``nb``  Norwegian (Bokmål)   617
``nl``  Dutch                250         0.92  on UD-NL-Alpino
``nn``  Norwegian (Nynorsk)  56
``pl``  Polish               3,211       0.91  on UD-PL-PDB
``pt``  Portuguese           924         0.92  on UD-PT-GSD
``ro``  Romanian             311
``ru``  Russian              595               alternative: `pymorphy2 <https://github.com/kmike/pymorphy2/>`_
``se``  Northern Sámi        113
``sk``  Slovak               818         0.92  on UD SK-SNK
``sl``  Slovene              136
``sq``  Albanian             35
``sv``  Swedish              658               alternative: `lemmy <https://github.com/sorenlind/lemmy>`_
``sw``  Swahili              10                experimental
``tl``  Tagalog              32                experimental
``tr``  Turkish              1,232       0.89  on UD-TR-Boun
``uk``  Ukrainian            370               alternative: `pymorphy2 <https://github.com/kmike/pymorphy2/>`_
======= ==================== =========== ===== ========================================================================


*Low coverage* mentions means one would probably be better off with a language-specific library, but *simplemma* will work to a limited extent. Open-source alternatives for Python are referenced if possible.

*Experimental* mentions indicate that the language remains untested or that there could be issues with the underlying data or lemmatization process.

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions), they describe to what extent simplemma can accurately map tokens to their lemma form. They can be reproduced by concatenating all available UD files and by using the script ``udscore.py`` in the ``eval/`` folder of the code repository.

This library is particularly relevant as regards the lemmatization of less frequent words. Its performance in this case is only incidentally captured by the benchmark above. In some languages, a fixed number of words such as pronouns can be further mapped by hand to enhance performance.


Speed
-----

Orders of magnitude given for reference only, measured on an old laptop to give a lower bound:

- Tokenization: > 1 million tokens/sec
- Lemmatization: > 250,000 words/sec

Using the most recent Python version (i.e. with ``pyenv``) can make the package run faster.


Roadmap
-------

-  [-] Add further lemmatization lists
-  [ ] Grammatical categories as option
-  [ ] Function as a meta-package?
-  [ ] Integrate optional, more complex models?


Credits and licenses
--------------------

Software under MIT license, for the linguistic information databases see ``licenses`` folder.

The surface lookups (non-greedy mode) use lemmatization lists derived from various sources, ordered by relative importance:

- `Lemmatization lists <https://github.com/michmech/lemmatization-lists>`_ by Michal Měchura (Open Database License)
- Wiktionary entries packaged by the `Kaikki project <https://kaikki.org/>`_
- `FreeLing project <https://github.com/TALP-UPC/FreeLing>`_
- `spaCy lookups data <https://github.com/explosion/spacy-lookups-data>`_
- `Unimorph Project <https://unimorph.github.io/>`_
- `Wikinflection corpus <https://github.com/lenakmeth/Wikinflection-Corpus>`_ by Eleni Metheniti (CC BY 4.0 License)


Contributions
-------------

See this `list of contributors <https://github.com/adbar/simplemma/graphs/contributors>`_ to the repository.

Feel free to contribute, notably by `filing issues <https://github.com/adbar/simplemma/issues/>`_ for feedback, bug reports, or links to further lemmatization lists, rules and tests.

Contributions by pull requests ought to follow the following conventions: code style with `black <https://github.com/psf/black>`_, type hinting with `mypy <https://github.com/python/mypy>`_, included tests with `pytest <https://pytest.org>`_.


Other solutions
---------------

See lists: `German-NLP <https://github.com/adbar/German-NLP>`_ and `other awesome-NLP lists <https://github.com/adbar/German-NLP#More-lists>`_.

For a more complex and universal approach in Python see `universal-lemmatizer <https://github.com/jmnybl/universal-lemmatizer/>`_.


References
----------

To cite this software:

.. image:: https://img.shields.io/badge/DOI-10.5281%2Fzenodo.4673264-brightgreen
   :target: https://doi.org/10.5281/zenodo.4673264
   :alt: Reference DOI: 10.5281/zenodo.4673264

Barbaresi A. (*year*). Simplemma: a simple multilingual lemmatizer for Python [Computer software] (Version *version number*). Berlin, Germany: Berlin-Brandenburg Academy of Sciences. Available from https://github.com/adbar/simplemma DOI: 10.5281/zenodo.4673264

This work draws from lexical analysis algorithms used in:

- Barbaresi, A., & Hein, K. (2017). `Data-driven identification of German phrasal compounds <https://hal.archives-ouvertes.fr/hal-01575651/document>`_. In International Conference on Text, Speech, and Dialogue Springer, pp. 192-200.
- Barbaresi, A. (2016). `An unsupervised morphological criterion for discriminating similar languages <https://aclanthology.org/W16-4827/>`_. In 3rd Workshop on NLP for Similar Languages, Varieties and Dialects (VarDial 2016), Association for Computational Linguistics, pp. 212-220.
- Barbaresi, A. (2016). `Bootstrapped OCR error detection for a less-resourced language variant <https://hal.archives-ouvertes.fr/hal-01371689/document>`_. In 13th Conference on Natural Language Processing (KONVENS 2016), pp. 21-26.

