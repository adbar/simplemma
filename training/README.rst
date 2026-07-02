Running the evaluation
----------------------

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions). They can be reproduced by the following steps:

1. Install the evaluation dependencies, Python >= 3.10 required (``pip install ".[dev]"``)
2. Update ``DATA_URL`` in ``training/download_eval_data.py`` to point to the latest treebanks archive from `Universal Dependencies <https://universaldependencies.org/#download>`_ (or the version that you which to use).
3. Run ``python3 training/download_eval_data.py`` which will
  1. Download the archive
  2. Extract relevant data (language and if applicable specific treebank, see notes in the results table)
  3. Concatenate the train, dev and test data into a single file (e.g. ``cat de_gsd*.conllu > de-gsd-all.conllu``)
  4. Store the files at the expected location (``training/data/UD/``)
4. Run the script, e.g. from the home directory ``python3 training/evaluate_simplemma.py``
5. Results are stored at ``training/data/results/results_summary.csv``. Also, errors are written in a CSV file for each dataset under the ``data/results``folder. 



Building lemmatization dictionaries
-----------------------------------

For a list of potential sources see `issue 1 <https://github.com/adbar/simplemma/issues/1>`_.


Input data
^^^^^^^^^^

- Tab-separated columns, first lemma, then word form, e.g. ``pelican TAB pelicans``.
- Redundant and noisy cases are mostly filtered out by the input script but it is best to check the data as smaller errors in available lists or machine-generated data are common.
- The data should be tested on an authoritative source like the Universal Dependencies (see above).


Adding languages
^^^^^^^^^^^^^^^^

- The Simplemma approach currently works best on languages written from left to right, results will be impacted otherwise (e.g. Urdu).
- The target language has to be prone to lemmatization by allowing for the reduction of at least two word forms to a single dictionary entry (e.g. Korean does not fit the current scope).
- The new language (two- or three-letter ISO code) needs a word list at ``training/lists/<code>.txt`` (tab-separated, see "Input data" above) and has to be added to the dictionary data using the ``dictionary_pickler`` script, it should then be available in ``SUPPORTED_LANGUAGES``.


Building the pickled dictionaries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``training/dictionary_pickler.py`` reads a language's word list and writes the compressed, pickled dictionary the runtime loads. Two things to know before running it:

- Without ``--in-place``, output goes to ``training/output/`` (gitignored) rather than the real package data, so a run never clobbers a shipped dictionary by accident. Pass ``--in-place`` to write into the installed package and actually update what ships.
- Its ``__main__`` CLI (``python3 training/dictionary_pickler.py --in-place``) only *rebuilds* languages already in ``SUPPORTED_LANGUAGES``, since that set is derived from the ``.plzma`` files already on disk. To add a genuinely *new* language, call ``_pickle_dict`` directly instead, e.g.:

.. code-block:: python

    from training.dictionary_pickler import _pickle_dict
    _pickle_dict("xx", in_place=True)


Example using ``kaikki.org``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since a source has to comprise enough words without sacrificing quality, the `kaikki.org <https://kaikki.org>`_ project is currently a good place to start. It leverages information from the Wiktionary project and is rather extensive. Its main drawbacks are lack of coverage for less-resourced languages and errors during processing of entries as the Wiktionary form tables are not all alike.


1. Find the link to all word senses for a given language, e.g. "Download JSON data for all word senses in the Lithuanian dictionary" leading to ``https://kaikki.org/dictionary/Lithuanian/kaikki.org-dictionary-Lithuanian.json``.
2. Convert the JSON dump to a tab-separated word list with ``training/kaikki_to_tsv.py``:

.. code-block:: shell

    python3 training/kaikki_to_tsv.py kaikki.org-dictionary-Lithuanian.json training/lists/lt.txt

This prefers explicit inflection relations (``form_of``/``alt_of``) and falls back to an entry's own ``forms`` table, while dropping known-noisy rows (structural placeholders, romanization/transliteration entries, stress marks, cross-reference tables that list unrelated words rather than inflections).

3. Don't deduplicate the output: ``dictionary_pickler.py`` counts repeated ``lemma\tword`` lines as evidence and uses that count to resolve conflicting lemmas for the same word form, so duplicates should be left as-is.
4. Check the output by exploring the data by hand to spot inconsistencies; ``dictionary_pickler.py`` itself filters out lines that are too short or otherwise malformed once you run it.
