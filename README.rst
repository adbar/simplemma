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


Purpose
-------

`Lemmatization <https://en.wikipedia.org/wiki/Lemmatisation>`_ is the process of grouping together the inflected forms of a word so they can be analysed as a single item, identified by the word's lemma, or dictionary form. Unlike stemming, lemmatization outputs word units that are still valid linguistic forms.

In modern natural language processing (NLP), this task is often indirectly tackled by more complex systems encompassing a whole processing pipeline. However, it appears that there is no straightforward way to address lemmatization in Python although this task is useful in information retrieval and natural language processing.

*Simplemma* provides a simple and multilingual approach to look for base forms or lemmata. It may not be as powerful as full-fledged solutions but it is generic, easy to install and straightforward to use. In particular, it doesn't need morphosyntactic information and can process a raw series of tokens or even a text with its built-in (simple) tokenizer. By design it should be reasonably fast and work in a large majority of cases, without being perfect.

With its comparatively small footprint it is especially useful when speed and simplicity matter, for educational purposes or as a baseline system for lemmatization and morphological analysis.

Currently, 38 languages are partly or fully supported (see table below).


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
    # decide which language data to load
    >>> langdata = simplemma.load_data('en')
    # apply it on a word form
    >>> simplemma.lemmatize(myword, langdata)
    'mask'
    # grab a list of tokens
    >>> mytokens = ['Hier', 'sind', 'Vaccines']
    >>> langdata = simplemma.load_data('de')
    >>> for token in mytokens:
    >>>     simplemma.lemmatize(token, langdata)
    'hier'
    'sein'
    'Vaccines'
    # list comprehensions can be faster
    >>> [simplemma.lemmatize(t, langdata) for t in mytokens]
    ['hier', 'sein', 'Vaccines']


Chaining several languages can improve coverage:


.. code-block:: python

    >>> langdata = simplemma.load_data('de', 'en')
    >>> simplemma.lemmatize('Vaccines', langdata)
    'vaccine'
    >>> langdata = simplemma.load_data('it')
    >>> simplemma.lemmatize('spaghettis', langdata)
    'spaghettis'
    >>> langdata = simplemma.load_data('it', 'fr')
    >>> simplemma.lemmatize('spaghettis', langdata)
    'spaghetti'
    >>> simplemma.lemmatize('spaghetti', langdata)
    'spaghetto'


There are cases in which a greedier decomposition and lemmatization algorithm is better. It is deactivated by default:

.. code-block:: python

    # same example as before, comes to this result in one step
    >>> simplemma.lemmatize('spaghettis', mydata, greedy=True)
    'spaghetto'
    # a German case
    >>> langdata = simplemma.load_data('de')
    >>> simplemma.lemmatize('angekündigten', langdata)
    'ankündigen' # infinitive verb
    >>> simplemma.lemmatize('angekündigten', langdata, greedy=False)
    'angekündigt' # past participle


Tokenization
~~~~~~~~~~~~

A simple tokenization function is included for convenience:

.. code-block:: python

    >>> from simplemma import simple_tokenizer
    >>> simple_tokenizer('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')
    ['Lorem', 'ipsum', 'dolor', 'sit', 'amet', ',', 'consectetur', 'adipiscing', 'elit', ',', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua', '.']


The function ``text_lemmatizer()`` chains tokenization and lemmatization. It can take ``greedy`` (affecting lemmatization) and ``silent`` (affecting errors and logging) as arguments:

.. code-block:: python

    >>> from simplemma import text_lemmatizer
    >>> langdata = simplemma.load_data('pt')
    >>> text_lemmatizer('Sou o intervalo entre o que desejo ser e os outros me fizeram.', langdata)
    # caveat: desejo is also a noun, should be desejar here
    ['ser', 'o', 'intervalo', 'entre', 'o', 'que', 'desejo', 'ser', 'e', 'o', 'outro', 'me', 'fazer', '.']


Caveats
~~~~~~~

.. code-block:: python

    # don't expect too much though
    >>> langdata = simplemma.load_data('it')
    # this diminutive form isn't in the model data
    >>> simplemma.lemmatize('spaghettini', langdata)
    'spaghettini' # should read 'spaghettino'
    # the algorithm cannot choose between valid alternatives yet
    >>> langdata = simplemma.load_data('es')
    >>> simplemma.lemmatize('son', langdata)
    'son' # valid common name, but what about the verb form?


As the focus lies on overall coverage, some short frequent words (typically: pronouns) can need post-processing, this generally concerns 10-20 tokens per language.

Additionally, the current absence of morphosyntactic information is both an advantage in terms of simplicity and an impassable frontier with respect to lemmatization accuracy, e.g. to disambiguate between past participles and adjectives derived from verbs in Germanic and Romance languages. In most cases, ``simplemma`` often doesn't change the input then.

The greedy algorithm rarely produces forms that are not valid. It is designed to work best in the low-frequency range, notably for compound words and neologisms. Aggressive decomposition is only useful as a general approach in the case of morphologically-rich languages. It can also act as a linguistically motivated stemmer.

Bug reports over the `issues page <https://github.com/adbar/simplemma/issues>`_ are welcome.


Supported languages
-------------------

The following languages are available using their `ISO 639-1 code <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_:


====== ================== ========== ===== =========================================================================
Available languages (2021-10-19)
--------------------------------------------------------------------------------------------------------------------
Code   Language           Word pairs Acc.  Comments
====== ================== ========== ===== =========================================================================
``bg`` Bulgarian          73,847           low coverage
``ca`` Catalan            579,507
``cs`` Czech              34,674           low coverage
``cy`` Welsh              360,412
``da`` Danish             554,238          alternative: `lemmy <https://github.com/sorenlind/lemmy>`_
``de`` German             683,207    0.95  on UD DE-GSD, see also `German-NLP list <https://github.com/adbar/German-NLP#Lemmatization>`_
``el`` Greek              76,388           low coverage
``en`` English            136,162    0.94  on UD EN-GUM, alternative: `LemmInflect <https://github.com/bjascob/LemmInflect>`_
``es`` Spanish            720,623    0.94  on UD ES-GSD
``et`` Estonian           133,104          low coverage
``fa`` Persian            10,967           low coverage
``fi`` Finnish            2,106,359        alternatives: `voikko <https://voikko.puimula.org/python.html>`_ or `NLP list <https://blogs.helsinki.fi/language-technology/hi-nlp/morphology/>`_
``fr`` French             217,213    0.94  on UD FR-GSD
``ga`` Irish              383,448
``gd`` Gaelic             48,661
``gl`` Galician           384,183
``gv`` Manx               62,765
``hu`` Hungarian          458,847
``hy`` Armenian           323,820
``id`` Indonesian         17,419     0.91  on UD ID-CSUI
``it`` Italian            333,680    0.92  on UD IT-ISDT
``ka`` Georgian           65,936
``la`` Latin              850,283
``lb`` Luxembourgish      305,367
``lt`` Lithuanian         247,337
``lv`` Latvian            57,153
``mk`` Macedonian         57,063
``nb`` Norwegian (Bokmål) 617,940
``nl`` Dutch              254,073    0.91  on UD-NL-Alpino
``pl`` Polish             3,723,580
``pt`` Portuguese         933,730    0.92  on UD-PT-GSD
``ro`` Romanian           311,411
``ru`` Russian            607,416          alternative: `pymorphy2 <https://github.com/kmike/pymorphy2/>`_
``sk`` Slovak             846,453    0.87  on UD SK-SNK
``sl`` Slovenian          97,050           low coverage
``sv`` Swedish            658,606          alternative: `lemmy <https://github.com/sorenlind/lemmy>`_
``tr`` Turkish            1,333,137  0.88  on UD-TR-Boun
``uk`` Ukrainian          190,472          alternative: `pymorphy2 <https://github.com/kmike/pymorphy2/>`_
====== ================== ========== ===== =========================================================================


*Low coverage* mentions means you'd probably be better off with a language-specific library, but *simplemma* will work to a limited extent. Open-source alternatives for Python are referenced if possible.

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions), they describe to what extent simplemma can accurately map tokens to their lemma form. They can be reproduced using the script ``udscore.py`` in the ``tests/`` folder.


Roadmap
-------

-  [-] Add further lemmatization lists
-  [ ] Grammatical categories as option
-  [ ] Function as a meta-package?
-  [ ] Integrate optional, more complex models?


Credits
-------

Software under MIT license, for the linguistic information databases see ``licenses`` folder.

The surface lookups (non-greedy mode) use lemmatization lists taken from various sources:

- `Lemmatization lists <https://github.com/michmech/lemmatization-lists>`_ by Michal Měchura (Open Database License)
- `FreeLing project <https://github.com/TALP-UPC/FreeLing>`_
- `spaCy lookups data <https://github.com/explosion/spacy-lookups-data/tree/master/spacy_lookups_data/data>`_
- Wiktionary entries parsed by the `Kaikki project <https://kaikki.org/>`_
- `Wikinflection corpus <https://github.com/lenakmeth/Wikinflection-Corpus>`_ by Eleni Metheniti (CC BY 4.0 License)
- `Unimorph Project <http://unimorph.ethz.ch/languages>`_

This rule-based approach based on flexion and lemmatizations dictionaries is to this day an approach used in popular libraries such as `spacy <https://spacy.io/usage/adding-languages#lemmatizer>`_.


Contributions
-------------

Feel free to contribute, notably by `filing issues <https://github.com/adbar/simplemma/issues/>`_ for feedback, bug reports, or links to further lemmatization lists, rules and tests.

You can also contribute to this `lemmatization list repository <https://github.com/michmech/lemmatization-lists>`_.


Other solutions
---------------

See lists: `German-NLP <https://github.com/adbar/German-NLP>`_ and `other awesome-NLP lists <https://github.com/adbar/German-NLP#More-lists>`_.

For a more complex and universal approach in Python see `universal-lemmatizer <https://github.com/jmnybl/universal-lemmatizer/>`_.


References
----------

.. image:: https://zenodo.org/badge/330707034.svg
   :target: https://zenodo.org/badge/latestdoi/330707034

Barbaresi A. (2021). Simplemma: a simple multilingual lemmatizer for Python. Zenodo. http://doi.org/10.5281/zenodo.4673264

This work draws from lexical analysis algorithms used in:

- Barbaresi, A., & Hein, K. (2017). `Data-driven identification of German phrasal compounds <https://hal.archives-ouvertes.fr/hal-01575651/document>`_. In International Conference on Text, Speech, and Dialogue Springer, pp. 192-200.
- Barbaresi, A. (2016). `Bootstrapped OCR error detection for a less-resourced language variant <https://hal.archives-ouvertes.fr/hal-01371689/document>`_. In 13th Conference on Natural Language Processing (KONVENS 2016), pp. 21-26.

