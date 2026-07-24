=======
History
=======

2.0.0
-----

- All dictionaries rebuilt from fresh sources, adding Wikidata lexemes and
  reviewed closed-class overrides: accuracy improves markedly for more than
  20 languages (e.g. Welsh 0.59 → 0.91, Armenian 0.63 → 0.88,
  Swedish 0.79 → 0.91, Russian 0.86 → 0.89)
- Breaking: new front-coded dictionary format shrinks the shipped data from
  67 MB to 17 MB; pre-2.0 pickled ``.plzma`` files are no longer read
- More accurate default rules covering more languages: near-100% precision
  enforced against the dictionaries, new rule sets (e.g. Georgian,
  Icelandic) (#175)
- More targeted affix handling, validated per language on UD treebanks: new
  clitic-decomposition and apostrophe strategies, simplified greedy affix
  search, updated prefix handling (#176)
- Improved tokenization (apostrophes, hyphens) and new sentence-initial
  casing handling in ``get_lemmas_in_text``, with a new ``casing`` module
  (#177)
- Lower memory footprint: all strategies share one process-wide default
  dictionary factory, so the dictionaries are cached once per process
- New ``low_memory`` flag on ``lemmatize``, ``text_lemmatizer``,
  ``lemma_iterator``, ``is_known``, ``langdetect``, ``in_target_language``
  and ``DefaultStrategy`` to opt into the new zero-dependency
  ``StreamDictionaryFactory``
- New ``StreamDictionaryFactory``: a stdlib-only low-memory backend that reads
  the shipped dictionaries directly instead of loading them into a dict
- Rebuilt training pipeline: layered dictionary builds (word-list base +
  Wikidata fill + reviewed overrides) gated by cross-treebank evaluation


1.2.0
-----

- Add support for Esperanto @axel584 (#167)
- Update setup and docs, modernize code (#168, #169)
- Security: fix arbitrary file write during tarfile extraction in training (#165)
- Maintenance: fix file opening in ``training/download-eval-data.py`` (#164)
- Breaking: rename the ``trie_directory_factory`` module to
  ``trie_dictionary_factory``


1.1.2
-----

- Fix cyclic import by @juanjoDiaz (#148)
- Fix language detector proportion_in_each_language results by @juanjoDiaz (#150)
- Init: use explicit re-exports (#151)
- Fix data written by dictionary pickler by @Dunedan (#156)
- Add demo rules for Latvian and Estonian (#154, #157)
- Remove deprecated langdetect submodule (#160)
- Test: remove dummy pickled data (#161)
- Language data: upgrade pickle to v5 (#162)


1.1.1
-----

- Fix `ModuleNotFoundError` and test optional dependencies (#142)
- Simplify code and add missing type annotations (#144)


1.1.0
-----

- Add a memory-efficient dictionary factory backed by MARISA-tries by @Dunedan in #133
- Drop support for Python 3.6 & 3.7 by @Dunedan in #134
- Update setup files (#138)


1.0.0
-----

Extensive refactoring by @juanjoDiaz:
- Series of modular classes
- Different lemmatization strategies available
- Customization of dictionary loading and handling (`DictionaryFactory`)
- `LanguageDetector` class with extended options
- See readme and [detailed documentation](https://adbar.github.io/simplemma/)

Breaking changes:
- The `extensive` argument is now `greedy`
- The `langdetect` submodule is now `language_detector`
`from simplemma.langdetect import ...` → `from simplemma.language_detector import ...`

Fixes and improvements:
- `is_known()` function now restored to its state in v0.9.0 (full dictionary)
- More languages and better rules (with @juanjoDiaz)
- Use binary strings in dictionaries to save memory
- Dictionary sort before compression by @1over137

Documentation:
- Classes and general doc pages by @juanjoDiaz 
- Section on classes in the readme by @osma


0.9.1
-----

* smaller language data footprint with smallest possible impact on performance, using a combination of rules, upper limit on word length, and better data cleaning (#31)
* unsupervised approach to affixes activated by default for some languages
* reviewed rules for English and German (less greedy)
* added rules for Dutch, Finnish, Polish and Russian
* improved Russian and Ukrainian language data (#3)
* improved tokenizer


0.9.0
-----

* smaller data files (especially for fi, la, pl, pt, sk & tr, #19)
* added support for Asturian (``ast``, #20)
* bug fixes (#18, #26)


0.8.2
-----

* languages added: Albanian, Hindi, Icelandic, Malay, Middle English, Northern Sámi, Nynorsk, Serbo-Croatian, Swahili, Tagalog
* fix for slow language detection introduced in 0.7.0


0.8.1
-----

* better rules for English and German
* inconsistencies fixed for cy, de, en, ga, sv (#16)
* docs: added language detection and citation info


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
