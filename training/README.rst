Running the evaluation
----------------------

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions). They can be reproduced by the following steps:

1. Install the evaluation dependencies, Python >= 3.10 required (``pip install ".[dev]"``)
2. Run ``python3 -m training.download_eval_data``, which resolves the pinned
   UD release (``UD_HANDLE`` in the script) via the LINDAT/CLARIAH-CZ REST
   API, downloads and checksums the treebanks archive, and for every
   supported language:
  1. Concatenates the train, dev and test data into a single file (e.g. ``da_ddt.conllu``) at the expected location (``training/data/UD/``)
  2. ALSO copies the individual train/dev/test files unmerged to ``training/data/UD/splits/`` (used by the ``training.ud_eval``/``ud_end_to_end``/``diff_audit`` toolkit below, which needs the dev/test split boundary preserved)
   To move to a newer UD release, update ``UD_VERSION``/``UD_HANDLE`` at the
   top of the script (find the new release's handle at
   `Universal Dependencies <https://universaldependencies.org/#download>`_,
   "released through LINDAT/CLARIAH-CZ") and delete ``training/data/UD/``
   before re-running -- then rerun ``training.ud_eval reliability`` across
   the evaluation treebanks, since annotation conventions can change
   between releases.
3. Run the script, e.g. from the home directory ``python3 training/evaluate_simplemma.py``
4. Results are stored at ``training/data/results/results_summary.csv``. Also, errors are written in a CSV file for each dataset under the ``data/results``folder.


Evaluating a candidate change (rules, affix config, new language)
-----------------------------------------------------------------

Any change to the OOV fallbacks (``strategies/defaultrules/``,
``strategies/affix_decomposition.py``) or a new candidate language should be
validated against real text, not only against the shipped dictionaries — the
dictionaries underrepresent exactly what the fallbacks meet in production
(function words, productive derivation, proper nouns). The toolkit:

1. ``python -m training.download_eval_data`` — fetch the pinned UD release
   (same one used above; run once, the data is git-ignored and reused
   across sessions).
2. ``python -m training.ud_eval reliability <lang:prefix>`` — annotation-quality
   profile of the treebank FIRST; known convention quirks (e.g. proper-noun
   lowercasing, compound-plural laziness) can fake or hide a regression.
3. In-dict prefilter: ``python -m training.rulebuilder <lang>`` for rules
   candidates (the per-cell precision gate is enforced by
   ``tests/strategies/defaultrules/test_precision.py``).
4. ``python -m training.ud_end_to_end <lang> <prefix> <config> [...]`` — accuracy
   plus a tune (dev) / confirm (test) sign-test verdict for a runtime-patched
   affix-config candidate.
5. ``python -m training.diff_audit --config <cfg> <lang> <prefix>`` or
   ``--worktree <path> [langs]`` (for defaultrules/ changes, against another
   checkout) — inspect the worsened tokens before trusting ANY positive
   delta: a harm class concentrated in one POS or lexical pattern is a red
   flag even when the net counts look fine.
6. ``python -m training.diff_audit --consistency <lang> <prefix>`` — the
   stoplist-candidate finder: flags words the rules change despite the
   treebank showing them as ALWAYS identity-gold (n>=2). Distinguishes a
   genuine collision from annotation noise (a sometimes-reduced word isn't
   a stoplist candidate).

``defaultrules/`` policy: rules are meant to add a little coverage
cheaply, not to be mined exhaustively. Trim to ~70-80% of firing mass
(``rulebuilder.trim_by_mass``), not 100%, before merging
(``rulebuilder.merge_stem_classes``); keep a language's stoplist small and
FINITE — if a rule cell needs more than roughly a dozen exceptions, or the
comment would have to say "more will likely need adding", drop that rule
cell instead of growing the list (``rulebuilder.complexity_report()`` is
the at-a-glance budget check: groups / alternatives / stoplist size per
language). A language whose morphology needs an unreasonable amount of
whitelisting to tame is a WONTFIX, not a "do it later".


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
