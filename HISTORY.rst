=======
History
=======


0.8.0
-----

* code fully type checked, optional pre-compilation with ``mypyc``
* fixes: logging error (#11), input type (#12)
* code style: `black <https://github.com/psf/black>`_


0.7.0
-----

* **breaking change**: language data pre-loading now occurs internally, language codes are now directly provided in ``lemmatize()`` call, e.g. ``simplemma.lemmatize("test", lang="en")``
* faster lemmatization, result cache
* sentence-aware ``text_lemmatizer()``
* optional iterators for tokenization and lemmatization


0.6.0
-----

* improved language models
* improved tokenizer
* maintenance and code efficiency
* added basic language detection (undocumented)


0.5.0
-----

* faster, more efficient code
* dropped support for Python 3.5


0.4.0
-----

* new languages: Armenian, Greek, Macedonian, Norwegian (Bokmål), and Polish
* language data reviewed for: Dutch, Finnish, German, Hungarian, Latin, Russian, and Swedish
* Urdu removed of language list due to issues with the data
* add support for Python 3.10 and drop support for Python 3.4
* improved decomposition and tokenization algorithms


0.3.0
-----

* improved models and disambiguation
* improved tokenization
* extended rules for German


0.2.2
-----

* Work on decomposition rules
* Reviewed language data
* Cleaner code


0.2.1
-----

* Better decomposition into subwords by greedy algorithm
* First benchmarks and data-based corrections: German, French, English, Spanish


0.2.0
-----

* Languages added: Danish, Dutch, Finnish, Georgian, Indonesian, Latin, Latvian, Lithuanian, Luxembourgish, Turkish, Urdu
* Improved word pair coverage
* Tokenization functions added
* Limit greediness and range of potential candidates


0.1.0
-----

* First release on PyPI
