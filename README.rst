=====================================================
Simplemma: a simple mutilingual lemmatizer for Python
=====================================================


.. image:: https://img.shields.io/pypi/v/simplemma.svg
    :target: https://pypi.python.org/pypi/simplemma
    :alt: Python package

.. image:: https://img.shields.io/pypi/pyversions/trafilatura.svg
    :target: https://pypi.python.org/pypi/trafilatura
    :alt: Python versions

.. image:: https://img.shields.io/travis/adbar/simplemma.svg
    :target: https://travis-ci.org/adbar/simplemma
    :alt: Travis build status


`Lemmatization <https://en.wikipedia.org/wiki/Lemmatisation>`_ is the process of grouping together the inflected forms of a word so they can be analysed as a single item, identified by the word's lemma, or dictionary form. Unlike stemming, lemmatization outputs word units that are still valid linguistic forms.

In modern natural language processing (NLP), this task is often indirectly tackled by more complex systems encompassing a whole processing pipeline. However, it appears that there is no straightforward way to address lemmatization in Python although this task is useful in information retrieval and natural language processing.

*Simplemma* provides a simple and multilingual approach (currently 22 languages, see list below) to look for base forms or lemmata. It may not be as powerful as full-fledged solutions but it is generic, easy to install and straightforward to use. By design it should be reasonably fast and work in a large majority of cases, without being perfect. With its comparatively small footprint it is especially useful when speed and simplicity matter, for educational purposes or as a baseline system for lemmatization and morphological analysis.


Installation
------------

The current library is written in pure Python with no dependencies:

``pip install simplemma``


Usage
-----

Simplemma is used by selecting a language of interest and then applying the data on a list of words.

.. code-block:: python

    >>> import simplemma
    # decide which language data to load
    >>> langdata = simplemma.load_data('de')
    # apply it on a word form
    >>> simplemma.lemmatize(myword, langdata)
    # grab a list of tokens
    >>> mytokens = ['Hier', 'sind', 'Tokens']
    >>> for token in mytokens:
    >>>     simplemma.lemmatize(token, langdata)
    'hier'
    'sein'
    'tokens'
    # list comprehensions can be faster
    >>> [simplemma.lemmatize(t, langdata) for t in mytokens]
    ['hier', 'sein', 'tokens']


Chaining several languages can improve coverage:


.. code-block:: python

    >>> langdata = simplemma.load_data('de', 'en')
    >>> simplemma.lemmatize('Tokens', langdata)
    'token'
    >>> langdata = simplemma.load_data('en')
    >>> simplemma.lemmatize('spaghetti', langdata)
    'spaghetti'
    >>> langdata = simplemma.load_data('en', 'it')
    >>> simplemma.lemmatize('spaghetti', langdata)
    'spaghetto'


There are cases for which a greedier algorithm is better. It is activated by default:

.. code-block:: python

    >>> langdata = simplemma.load_data('de')
    >>> simplemma.lemmatize('angekündigten', langdata)
    'ankündigen' # infinitive verb
    >>> simplemma.lemmatize('angekündigten', langdata, greedy=False)
    'angekündigt' # past participle


Caveats:

.. code-block:: python

    # don't expect too much though
    >>> langdata = simplemma.load_data('it')
    # this diminutive form isn't in the model data
    >>> simplemma.lemmatize('spaghettini', langdata)
    'spaghettini' # should read 'spaghettino'


Supported languages
-------------------


The following languages are available using their `ISO 639-1 code <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_:

- ``bg``: Bulgarian *(low coverage)*
- ``ca``: Catalan
- ``cs``: Czech *(low coverage)*
- ``cy``: Welsh
- ``de``: German
- ``en``: English *(alternative: *`LemmInflect <https://github.com/bjascob/LemmInflect>`_*)*
- ``es``: Spanish
- ``fa``: Persian *(low coverage)*
- ``fr``: French
- ``ga``: Irish
- ``gd``. Gaelic
- ``gl``: Galician
- ``gv``: Manx
- ``hu``: Hungarian *(low coverage)*
- ``it``: Italian
- ``pt``: Portuguese
- ``ro``: Romanian
- ``ru``: Russian *(alternative: *`pymorphy2 <https://github.com/kmike/pymorphy2/>`_*)*
- ``sk``: Slovak
- ``sl``: Slovenian *(low coverage)*
- ``sv``: Swedish *(alternative: *`lemmy <https://github.com/sorenlind/lemmy>`_*)*
- ``uk``: Ukranian *(alternative: *`pymorphy2 <https://github.com/kmike/pymorphy2/>`_*)*


*Low coverage* mentions means you'd probably be better off with a language-specific library, but *simplemma* will work to a limited extent. Open-source alternatives for Python are referenced if available.


* Free software: MIT license
* Documentation: https://github.com/adbar/simplemma


Roadmap
-------

-  [ ] Function as a meta-package?
-  [ ] Integrate optional, more complex models?


Credits
-------

The current version basically acts as a wrapper for `lemmatization lists <https://github.com/michmech/lemmatization-lists>`_ by Michal Měchura (Open Database License). This rule-based approach based on flexion and lemmatizations dictionaries is to this day an approach used in popular libraries such as `spacy <https://spacy.io/usage/adding-languages#lemmatizer>`_.

This package was created with `Cookiecutter <https://github.com/audreyr/cookiecutter>`_ and the `audreyr/cookiecutter-pypackage <https://github.com/audreyr/cookiecutter-pypackage>`_ project template.


Contributions
-------------

Feel free to contribute, notably by `filing issues <https://github.com/adbar/simplemma/issues/>`_ for feedback, bug reports, or links to further lemmatization lists, rules and tests.

You can also contribute to this `lemmatization list repository <https://github.com/michmech/lemmatization-lists>`_.


Other solutions
---------------

See lists: `German-NLP <https://github.com/adbar/German-NLP>`_ and `other awesome-NLP lists <https://github.com/adbar/German-NLP#More-lists>`_.

For a more complex but universal approach in Python see `universal-lemmatizer <https://github.com/jmnybl/universal-lemmatizer/>`_.

