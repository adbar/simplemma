Training and evaluation
=======================

Every tool here is a standalone script under ``training/``. Input data (UD
treebanks, Kaikki and Wikidata dumps, word lists) is git-ignored under
``training/data/`` and ``training/lists/``. The only committed data are the
reviewed override lexicons in ``training/overrides/``.

Setup, once:

.. code-block:: shell

    pip install ".[dev]"                        # Python >= 3.10
    python3 -m training.download_eval_data      # pinned UD release, md5-checked

The download copies each supported language's train/dev/test files to
``training/data/UD/splits/``. To move to a newer UD release, follow the
script's docstring, delete ``training/data/UD/`` and re-run. Then re-check
the evaluation, since annotation conventions change between releases.


Evaluation
----------

Scores are token accuracy on `Universal Dependencies
<https://universaldependencies.org/>`_ treebanks, single word tokens only.
Each figure in the main README is the accuracy on the language's best
general-purpose treebank. Parallel, spoken, learner and historical treebanks
are excluded.

Three exceptions due to treebank annotation:

- Dutch excludes underscore-joined compound lemmas (``klooster_orde``),
  which single-token output cannot match. With them it is about 0.91.
- Hebrew and Arabic proclitics are scored as pre-split sub-tokens. On
  unsegmented input the accuracies are about 0.82 and 0.85.
- Finnish, Estonian and Hungarian compound markers (``yli#opisto``,
  ``sisse_tulek``, ``el+mond``) are stripped before scoring, see
  ``_GOLD_COMPOUND_SEPARATORS`` in ``ud_conllu.py``.

``python3 training/evaluate_simplemma.py`` scores the ``dev`` and ``test``
splits and writes ``training/data/results/results_summary.csv`` plus one
error CSV per dataset.

Each split has one role. **train** is used to mine overrides and sentence
starters and to gate changes. It is never scored. **dev** and **test** are
scored and never used for any decision. Train shows whether a change helps
or hurts, but overstates by how much (up to 2x), so never report from it
or rank candidates with it. A language without a train split is gated on
dev, else test, with a WARNING. ``sw`` has no UD data at all.

``eval_gate.gate()`` (library, no CLI) rejects a candidate dictionary that
lowers token or type accuracy on any of the language's treebanks. It runs
the full ``Lemmatizer``, same protocol as ``evaluate_simplemma``. Shared UD
conventions live in ``ud_conllu.py``.


Dictionaries
------------

``dictionary_builder.py`` writes the front-coded ``.plzma`` files the runtime
loads (encoder ``frontcode_encode.py``, decoder
``simplemma/strategies/dictionaries/frontcode.py``). Keys are NFC-normalized
at build time. Per-language normalization and junk filters live in
``build_lang_config.py``.

Two layers: the reviewed override lexicon ``training/overrides/<code>.tsv``
always wins over the base. The base is the installed dictionary for a
rebuild, or a word list for an ingest.

.. code-block:: shell

    python3 -m training.dictionary_builder <code>            # -> training/output/
    python3 -m training.dictionary_builder <code> --in-place # overwrite shipped data
    python3 -m training.dictionary_builder --check           # idempotence check

Without ``--in-place`` nothing shipped is touched. A rebuild decodes the
shipped file and re-applies overrides and cleanup, so it reproduces the file
byte for byte when nothing changed. ``--check`` verifies that for every
language (about 15 minutes for all). Run it after any pipeline or data
change: a difference means the change silently rewrites shipped data.

Ingesting new data, for a new or a shipped language:

.. code-block:: shell

    python3 -m training.wordlist_ingest <code> [--gate] [--in-place]

It reads ``training/lists/<code>.txt``, tab-separated ``lemma TAB form``
lines. Duplicate lines count as votes when a form has conflicting lemmas, so
do not deduplicate. For a shipped language the installed mapping wins every
shared key: new data can only add keys, existing mappings change only via a
reviewed override. ``--gate`` refuses to write on a UD regression.

A new language needs an ISO code, a left-to-right script, and morphology
where several forms reduce to one entry (Korean does not fit, Urdu suffers).
After ``--in-place`` it appears in ``SUPPORTED_LANGUAGES``. Potential sources:
`issue 1 <https://github.com/adbar/simplemma/issues/1>`_.


Word lists from Kaikki
^^^^^^^^^^^^^^^^^^^^^^

`kaikki.org <https://kaikki.org>`_ exposes Wiktionary as JSONL and is the
usual starting point. It is thin on less-resourced languages and noisy.

1. Download "all word senses" for the language, e.g.
   ``https://kaikki.org/dictionary/Lithuanian/kaikki.org-dictionary-Lithuanian.jsonl``.
2. ``python3 training/kaikki_to_tsv.py <dump.jsonl> training/lists/lt.txt``.
   The converter prefers explicit ``form_of``/``alt_of`` relations, falls back
   to the entry's ``forms`` table, drops known-noisy rows, and emits an
   identity pair for uninflected headwords.
3. Skim the output by hand. Small errors are common in every source.


Word lists from Wikidata
^^^^^^^^^^^^^^^^^^^^^^^^

``wikidata_lexemes.py`` extracts pairs from the Wikidata lexeme dump
(``dumps.wikimedia.org/wikidatawiki/entities/latest-lexemes.json.gz``, about
600 MB). Append the result to a Kaikki list for coverage, or use it as the
base list when Wiktionary is thin (``ml`` Malayalam).

1. Add the language's QID to ``LANGUAGE_QIDS`` in ``wikidata_lexemes.py``.
2. ``python3 -m training.wikidata_lexemes ml <dump> training/lists/ml.txt``
3. ``python3 -m training.wordlist_ingest ml --in-place``


Override lexicons
^^^^^^^^^^^^^^^^^

``python3 -m training.build_override <code> [--in-place]`` mines an override
lexicon from all of the language's UD train splits. A form qualifies with
3 occurrences and 90% agreement (closed class) or 5 and 95% (open class),
and is rejected if any single treebank with 3 or more occurrences prefers
another lemma. Output goes to ``training/output/`` unless ``--in-place``
rewrites ``training/overrides/<code>.tsv``. Shipping still requires a
rebuild.

The committed files are the reviewed source of truth: derived from UD data
plus review, never from the current dictionary. Rows the pipeline already
reproduces are kept, so a re-mine after a UD bump merges cleanly. The miner
is not gated: an override is the majority lemma of its form, so train
accuracy can only rise.

``--in-place`` is deliberately lossy: multi-word forms are dropped and
``grc``/``he``/``ar`` entries are rewritten into the canonical key space.
Prefer the default run and diff it by hand.


Suffix rules
------------

Rules in ``simplemma/strategies/defaultrules/`` handle words missing from
the dictionary. A rule's output must *be* the lemma. Rules add a little
coverage cheaply and are not mined exhaustively.

Each data-driven language's ``DEFAULT_RULES`` is a ``generic.SuffixRules``
table, ``{target: "suffix suffix ..."}``. The longest matching suffix wins, so
order does not matter. Leading dots are required stem characters
(``"..ante"``), ``min_stem=`` sets a minimum stem length for the whole table,
``stops=`` lists suffixes on which the rules abstain. Guards are keywords of
the same table, all off by default: ``min_len=``, ``caps=`` (skip
capitalized), ``hyphen=`` (skip hyphenated, ``HyphenRemovalStrategy``
handles them earlier), ``excluded=`` (stoplist). lv picks between two tables
by capitalization, de is hand-written, ru normalizes ё ahead of its table.

``python3 -m training.rulebuilder <code>`` runs four functions and prints
the precision/coverage report. Run them by hand for the judgment calls in
between:

1. ``mine(lang)``: candidate ``(suffix, target)`` pairs, each above the
   precision and support bar.
2. ``trim_by_mass(cells, 0.70)``: keep the pairs that account for 70% of
   rule applications. Trim before refining: faster, and fewer rules for the
   same coverage.
3. ``refine(cells, dictionary)``: build rules, drop pairs that are imprecise
   or lose support once combined, repeat until stable.
4. ``subsume(rules, dictionary)``: drop alternatives another rule already
   produces identically, verified on exactly the affected tokens.

Scoring is exact match against the dictionary lemma
(``rulebuilder.output_is_lemma``). Combining accents are ignored only for
``_ACCENT_FOLD_LANGS`` (sl). ``eo`` alone keeps the old "output is a real
word" predicate. The CI test
``tests/strategies/defaultrules/test_precision.py`` enforces the per-rule
precision bar and the no-overlap rule on every shipped table.

The in-dictionary check has a blind spot: dictionaries are dominated by
regular declensions, real text by a few irregular high-frequency words. So
always re-run ``evaluate_simplemma.py`` and diff ``results_summary.csv``
against the previous run.

Keep stoplists small. A rule needing more than about a dozen exceptions is
dropped, unless dropping it costs about 100 or more correct UD tokens. Then
list the exceptions, checking each against the dictionary and the majority
UD gold. A language that needs unreasonable whitelisting is a WONTFIX.

``affixbuilder.py`` measures affix-decomposition settings.
``prefixbuilder.py`` generates prefix candidates only, never evidence.


Sentence starters
-----------------

``simplemma/sentences.py`` holds two per-language tables: ``_ABBREVS``
(suppress a boundary after ``.``) and ``_STARTERS`` (re-open a suppressed
one).

``python3 -m training.sentencebuilder <code>`` mines starters on train and
prints a paste-able literal only if they beat the shipped list on dev,
otherwise it says ``keep the shipped list``. ``--check`` scores the shipped
list alone. Run it before and after any splitter change.

Abbreviations are not mined: held out they gain at most +0.0025 F1, against
up to +0.09 for starters, and a mined list runs to thousands of entries.
