=========================================
Simplemma: a simple lemmatizer for Python
=========================================


.. image:: https://img.shields.io/pypi/v/simplemma.svg
        :target: https://pypi.python.org/pypi/simplemma

.. image:: https://img.shields.io/travis/adbar/simplemma.svg
        :target: https://travis-ci.org/adbar/simplemma


Simple and multilingual (22, see below).

Pure-Python with no dependencies:

``pip install simplemma``


Usage:

.. code-block:: python

    >>> import simplemma
    # decide which language data to load
    >>> langdata = simplemma.load_data('de')
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
    # don't expect too much though
    >>> simplemma.lemmatize('spaghettini', langdata)
    'spaghettini' # the diminutive form should read 'spaghettino'



The following languages are available using their `ISO 639-1 code <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_:

- ``bg``: Bulgarian *(low coverage)*
- ``ca``: Catalan
- ``cs``: Czech *(low coverage)*
- ``cy``: Welsh
- ``de``: German
- ``en``: English *(low coverage)*
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
- ``ru``: Russian *(low coverage)*
- ``sk``: Slovak
- ``sl``: Slovenian *(low coverage)*
- ``sv``: Swedish
- ``uk``: Ukranian *(low coverage)*



* Free software: MIT license
* Documentation: https://github.com/adbar/simplemma


Features
--------

* TODO

Credits
-------

Based on the `lemmatization lists <https://github.com/michmech/lemmatization-lists>`_ by Michal Měchura (Open Database License).

This package was created with `Cookiecutter <https://github.com/audreyr/cookiecutter>`_ and the `audreyr/cookiecutter-pypackage <https://github.com/audreyr/cookiecutter-pypackage>`_ project template.

