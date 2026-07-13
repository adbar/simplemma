Running the evaluation
----------------------

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions). They can be reproduced by the following steps:

1. Install the evaluation dependencies, Python >= 3.10 required (``pip install ".[dev]"``)
2. Run ``python3 -m training.download_eval_data``, which resolves the pinned
   UD release (``UD_HANDLE`` in the script) via the LINDAT/CLARIAH-CZ REST
   API, downloads and checksums the treebanks archive, and for every
   supported language:
  1. Concatenates the train, dev and test data into a single file (e.g. ``da_ddt.conllu``) at the expected location (``training/data/UD/``)
  2. ALSO copies the individual train/dev/test files unmerged to ``training/data/UD/splits/`` (for per-split evaluation that needs the dev/test boundary preserved)
   To move to a newer UD release, update ``UD_VERSION``/``UD_HANDLE`` at the
   top of the script (find the new release's handle at
   `Universal Dependencies <https://universaldependencies.org/#download>`_,
   "released through LINDAT/CLARIAH-CZ") and delete ``training/data/UD/``
   before re-running. Re-check the evaluation afterwards, since annotation
   conventions can change between releases.
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
2. In-dict build + gate: ``python -m training.rulebuilder <lang>`` mines
   candidates and runs the recipe below end to end, printing the final
   precision/coverage report; the per-cell precision gate is enforced in CI
   by ``tests/strategies/defaultrules/test_precision.py``.
3. Real-text impact: re-run ``python3 training/evaluate_simplemma.py`` and
   compare ``results_summary.csv`` against the pre-change run — the shipped
   dictionaries underrepresent the OOV forms the fallbacks actually meet, so
   an in-dict-only check is not sufficient.

``defaultrules/`` policy: a rule's output must BE the lemma (2026-07,
lemma-first). ``rulebuilder.mine``/``score_cells``/``evaluate`` and the CI
precision harness all score with ``rulebuilder.output_is_lemma`` — exact
match against the dictionary lemma; "the output is at least a real word" no
longer counts. Combining accents are folded only for
``_ACCENT_FOLD_LANGS`` (uk stress acute, la macron, sl tonal marks — each
0% of UD lemmas but present in the dictionary, i.e. pedagogical marks real
text drops); every other language is scored exact, so a standard
orthographic letter (fi ä/ö, cs/sk long-vowel acute, es/pt lexical acute)
that the rule gets wrong is no longer masked as a hit. Languages built under the old
predicate are being rebuilt one by one; until then they sit in the harness's
``_LEGACY_REAL_WORD_LANGS`` set. Rules are meant to add a little coverage
cheaply, not to be mined exhaustively.

The build recipe is four steps, each a plain function over the previous
step's output — run them together via ``python -m training.rulebuilder
<lang>``, or drive them by hand for the judgment calls in between:

1. ``mine(lang)`` — candidate ``(suffix, target)`` cells, each individually
   at or above the precision/support bar.
2. ``trim_by_mass(cells, 0.70)`` — keep the highest-firing cells covering
   70% of firing mass, drop the low-value tail. Do this BEFORE refining:
   trimming first means the batch drop-bad-cells loop runs on a small
   ruleset instead of the full mined set, which is both faster and yields
   fewer groups for the same coverage.
3. ``refine(cells, dictionary)`` — build rules, drop any cell that is either
   imprecise or (once combined with every other cell) under-supported, and
   repeat until stable. The under-support drop matters: a cell mine()
   validated in isolation can be starved below the support floor once a more
   general cell intercepts most of its tokens, and an under-supported cell's
   precision is not a reliable signal — leaving it in place is how a rule
   with a handful of firings, all wrong, has shipped before.
4. ``subsume(rules, dictionary)`` — drop alternatives that are provably
   redundant (an earlier group already intercepts them, or a later, more
   general group produces the identical output), verified by construction:
   removing alternative ``a`` can only change first-match for tokens ending
   in ``a``, so checking exactly those tokens is a complete proof of
   output-equivalence, not a sample.

A rebuilt or retuned language ships only after the in-dict per-cell
precision gate (enforced in CI by
``tests/strategies/defaultrules/test_precision.py``): every cell must clear
the precision bar against the shipped dictionary, and no two rules may
overlap. The in-dict proxy has a known blind spot — a cell can clear the bar
yet do worse on real text when the dictionary's composition doesn't match
usage (regular declensions dominate the dictionary; a few irregular,
high-frequency collisions dominate real text). The worst case was hyphenated
compounds: a suffix rule only touches a token's tail, so on a compound it
half-fixes it or collides with a UD boundary marker it can't reproduce. They
are now handled by ``HyphenRemovalStrategy`` earlier in the pipeline and
skipped in rules via ``generic.apply_rules(..., hyphen=True)``.

Keep a language's stoplist small and FINITE — if a rule cell needs more
than roughly a dozen exceptions, or the comment would have to say "more will
likely need adding", drop that rule cell instead of growing the list
(``rulebuilder.complexity_report()`` is the at-a-glance budget check: groups
/ alternatives / stoplist size per language). One measured exception (the
hybrid rule, 2026-07): when dropping a colliding cell would cost ~100 or more
correct tokens on the UD treebank, keep the cell and enumerate its exceptions
past the dozen mark instead (each checked against the dictionary and the
majority UD gold — a form the rule gets right for most of its real
occurrences must NOT be stoplisted). A language whose morphology needs an
unreasonable amount of whitelisting to tame is a WONTFIX, not a "do it later".

Every data-driven language's `apply_*` function is a one-line call into
`generic.apply_rules(token, DEFAULT_RULES, min_len=..., caps=..., hyphen=...,
excluded=...)` — the length floor, capitalized-token skip, hyphen skip, and
stoplist are keyword-only guard parameters on the shared dispatcher, not
hand-copied per module. Defaults are neutral (no guard applied), so a
bespoke caller like lv (which picks between two rule tables based on
capitalization) is unaffected. de/en/nl stay fully bespoke; ru keeps its
one-line ё-normalization fast path ahead of the guarded call.


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


The dictionary data pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Beyond the raw ``kaikki_to_tsv`` extraction above, the dictionaries are
prepared and validated with a few small standalone CLIs (their git-ignored
inputs live under ``training/data/``):

- ``clean_wordlist.py <in.tsv> <out.tsv>`` — language-independent character
  hygiene between extraction and pickling: NFC-normalize, canonicalize curly
  quotes, strip invisible characters, reject mojibake and control/unassigned
  codepoints. Keeps duplicate lines (the pickler treats line count as
  evidence) and exits nonzero if the reject rate exceeds ``--max-reject-pct``
  (a data-drift alarm).
- ``wikidata_lexemes.py <lang> <dump> <out.tsv>`` — extract extra
  ``(lemma, form)`` pairs from a Wikidata lexeme dump as an OOV *fill* layered
  onto (never overriding) the shipped dictionary; ``--prune`` drops pairs the
  shipped dict + rules/affix chain already reproduces.
- ``build_override.py <lang> <train.conllu> <out.tsv>`` — mine a closed-class
  override lexicon (pronouns, determiners, adpositions, …) from a UD train
  split, the one place Wiktionary is systematically thin.
- ``eval_gate.py <lang> <baseline.tsv> <candidate.tsv>`` — release gate:
  refuse a candidate that regresses token- OR type-level accuracy on any UD
  test treebank for the language (cross-treebank is automatic).

``ud_conllu.py`` holds the shared UD conventions (the dataset-name → language
map and the gold-token iteration rule) these tools read with. Finally,
``dictionary_pickler.py --frontcode`` writes the smaller front-coded
byte-stream format instead of a pickle; simplemma reads both, so existing
``.plzma`` files keep working.
