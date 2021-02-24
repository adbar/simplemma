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

.. image:: https://img.shields.io/travis/adbar/simplemma.svg
    :target: https://travis-ci.org/adbar/simplemma
    :alt: Travis build status


`Lemmatization <https://en.wikipedia.org/wiki/Lemmatisation>`_ is the process of grouping together the inflected forms of a word so they can be analysed as a single item, identified by the word's lemma, or dictionary form. Unlike stemming, lemmatization outputs word units that are still valid linguistic forms.

In modern natural language processing (NLP), this task is often indirectly tackled by more complex systems encompassing a whole processing pipeline. However, it appears that there is no straightforward way to address lemmatization in Python although this task is useful in information retrieval and natural language processing.

*Simplemma* provides a simple and multilingual approach to look for base forms or lemmata. It may not be as powerful as full-fledged solutions but it is generic, easy to install and straightforward to use. By design it should be reasonably fast and work in a large majority of cases, without being perfect. Currently, 35 languages are partly or fully supported, see table below.

With its comparatively small footprint it is especially useful when speed and simplicity matter, for educational purposes or as a baseline system for lemmatization and morphological analysis.


Installation
------------

The current library is written in pure Python with no dependencies:

``pip install simplemma`` (or ``pip3`` where applicable)


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

A simple tokenization is included for convenience:

.. code-block:: python

    >>> from simplemma import simple_tokenizer
    >>> simple_tokenizer('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')
    ['Lorem', 'ipsum', 'dolor', 'sit', 'amet', ',', 'consectetur', 'adipiscing', 'elit', ',', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua', '.']


The function ``text_lemmatizer()`` chains tokenization and lemmatization. It can take *greedy* and *silent* as arguments:

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

The greedy algorithm rarely produces forms that are not valid. Still, it is mainly useful on long words and neologisms, not for general approaches.

Bug reports over the `issues page <https://github.com/adbar/simplemma/issues>`_ are welcome.


Supported languages
-------------------

The following languages are available using their `ISO 639-1 code <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_:


====== ============= ========== ========= =========================================================================
Available languages (2021-02-02)
-------------------------------------------------------------------------------------------------------------------
Code   Language      Word pairs Scores    Comments
====== ============= ========== ========= =========================================================================
``bg`` Bulgarian     69,680               low coverage
``ca`` Catalan       583,969
``cs`` Czech         35,021               low coverage
``cy`` Welsh         349,638
``da`` Danish        555,559              alternative: `lemmy <https://github.com/sorenlind/lemmy>`_
``de`` German        623,249    0.95      on UD DE-GSD. See also `German-NLP list <https://github.com/adbar/German-NLP#Lemmatization>`_
``en`` English       136,226    0.94      on UD EN-GUM. Alternative: `LemmInflect <https://github.com/bjascob/LemmInflect>`_
``es`` Spanish       666,016    0.93      on UD ES-GSD.
``et`` Estonian      112,501              low coverage
``fa`` Persian       9,333                low coverage
``fi`` Finnish       2,096,328            alternatives: `voikko <https://voikko.puimula.org/python.html>`_ or `NLP list <https://blogs.helsinki.fi/language-technology/hi-nlp/morphology/>`_
``fr`` French        217,091    0.93      on UD FR-GSD.
``ga`` Irish         366,086
``gd`` Gaelic        49,080
``gl`` Galician      386,714
``gv`` Manx          63,667
``hu`` Hungarian     446,650
``id`` Indonesian    36,461
``it`` Italian       333,682
``ka`` Georgian      65,938
``la`` Latin         96,409               low coverage
``lb`` Luxembourgish 305,398
``lt`` Lithuanian    247,418
``lv`` Latvian       57,154
``nl`` Dutch         228,123    0.91      on UD-NL-Alpino.
``pt`` Portuguese    933,730    0.92      on UD-PT-GSD.
``ro`` Romanian      313,181
``ru`` Russian       608,770              alternative: `pymorphy2 <https://github.com/kmike/pymorphy2/>`_
``sk`` Slovak        847,383    0.87      on UD SK-SNK.
``sl`` Slovene       97,460               low coverage
``sv`` Swedish       663,984              alternative: `lemmy <https://github.com/sorenlind/lemmy>`_
``tr`` Turkish       1,333,970  0.88      on UD-TR-Boun.
``uk`` Ukranian      190,725              alternative: `pymorphy2 <https://github.com/kmike/pymorphy2/>`_
``ur`` Urdu          28,848
====== ============= ========== ========= =========================================================================


*Low coverage* mentions means you'd probably be better off with a language-specific library, but *simplemma* will work to a limited extent. Open-source alternatives for Python are referenced if available.

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions), they describe to what extent simplemma can accurately map tokens to their lemma form.

* Software under MIT license, for the linguistic information databases see ``licenses`` folder
* Documentation: https://github.com/adbar/simplemma


Roadmap
-------

-  [-] Add further lemmatization lists
-  [ ] Grammatical categories as option
-  [ ] Function as a meta-package?
-  [ ] Integrate optional, more complex models?


Credits
-------

The current version basically acts as a wrapper for lemmatization lists:

- `Lemmatization lists <https://github.com/michmech/lemmatization-lists>`_ by Michal Měchura (Open Database License)
- `Wikinflection corpus <https://github.com/lenakmeth/Wikinflection-Corpus>`_ by Eleni Metheniti (CC BY 4.0 License)
- `Unimorph Project <http://unimorph.ethz.ch/languages>`_
- `FreeLing project <https://github.com/TALP-UPC/FreeLing>`_
- `spaCy lookups data <https://github.com/explosion/spacy-lookups-data/tree/master/spacy_lookups_data/data>`_


This rule-based approach based on flexion and lemmatizations dictionaries is to this day an approach used in popular libraries such as `spacy <https://spacy.io/usage/adding-languages#lemmatizer>`_.


Contributions
-------------

Feel free to contribute, notably by `filing issues <https://github.com/adbar/simplemma/issues/>`_ for feedback, bug reports, or links to further lemmatization lists, rules and tests.

You can also contribute to this `lemmatization list repository <https://github.com/michmech/lemmatization-lists>`_.


Other solutions
---------------

See lists: `German-NLP <https://github.com/adbar/German-NLP>`_ and `other awesome-NLP lists <https://github.com/adbar/German-NLP#More-lists>`_.

For a more complex but universal approach in Python see `universal-lemmatizer <https://github.com/jmnybl/universal-lemmatizer/>`_.

