Running the evaluation
----------------------

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions). They can be reproduced by the following steps:

1. Install the evaluation dependencies, Python >= 3.10 required (``pip install ".[dev]"``)
2. Run ``python3 -m training.download_eval_data``, which resolves the pinned
   UD release (``UD_HANDLE`` in the script) via the LINDAT/CLARIAH-CZ REST
   API, downloads and checksums the treebanks archive, and copies every
   supported language's train/dev/test files to ``training/data/UD/splits/``
   -- the one on-disk representation all evaluators read, kept split so that
   every tool has to name the split it wants (see step 3).
   To move to a newer UD release, update ``UD_VERSION``/``UD_HANDLE`` at the
   top of the script (find the new release's handle at
   `Universal Dependencies <https://universaldependencies.org/#download>`_,
   "released through LINDAT/CLARIAH-CZ") and delete ``training/data/UD/``
   before re-running. Re-check the evaluation afterwards, since annotation
   conventions can change between releases.
3. Run the script, e.g. from the home directory ``python3 training/evaluate_simplemma.py``.
   Scoring uses each dataset's held-out ``dev``+``test`` splits. The splits
   have strictly separate jobs and nothing may blur them:

   - **train** — the only in-sample split, and it does two jobs: it is mined
     for the reviewed override lexicons (``training/build_override.py``) and
     the sentence-starter lists (``training/sentencebuilder.py``), AND it is
     what ``eval_gate`` calibrates against. Every shipping decision is made
     here. Never scored.
   - **dev** + **test** — both reported. Neither is consulted by any
     shipping decision, which is the only reason the numbers mean anything.

   Gating on train rather than dev is measured, not assumed. Sweeping every
   override layer: 40 languages gated on train, zero FAILs, and of the 38 that
   also have a dev split 37 give the identical verdict. The one disagreement is
   ``lt`` (train PASS, dev FAIL), and it runs in train's favour — the failing
   ``lt_hse-ud-dev`` is 1,086 tokens losing 0.64pp (~7 tokens) while the same
   treebank gains on train (+1.62pp) and on test (+0.19pp), so a dev gate would
   have thrown away lt's entire 207-entry layer over small-sample noise.

   Train does overstate the size of the gain, by a mean 1.22× (min 1.00×, max
   2.02× across the 27 languages measurable off a fresh base). The gate needs
   only the *sign* of the delta, which train gets right — but train must never
   be used to report, or to rank candidates against each other by size of gain.

   A language with no train split is gated on dev, else test; ``eval_gate``
   logs a WARNING naming it, and its published figure is then selected rather
   than held out. ``sw`` has no UD data at all, so it is neither gated nor
   scored.
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


Regenerating the sentence-starter data
--------------------------------------

``simplemma/sentences.py`` holds two per-language tables: ``_ABBREVS`` (an
abbreviation before a ``.`` suppresses the boundary) and ``_STARTERS`` (a
known opener re-opens a suppressed one).

``python -m training.sentencebuilder <lang>`` mines starter candidates on the
``*-ud-train`` splits and prints a paste-able literal only if they beat the
shipped list on the ``*-ud-dev`` splits (adopting on that comparison is
model selection, so it must not read test); otherwise it says ``keep
the shipped list`` (fr, nl and pl today). ``--check`` scores the shipped list
alone — run it before and after any splitter change, because each entry's
verdict depends on the rules around it.

Abbreviations are not mined: held out they gain at most +0.0025 F1 (nothing at
all for en), against up to +0.09 for starters. A mined list runs to thousands of entries because it
memorizes UD's sentence-initial vocabulary, so weigh one against the text you
actually expect before pasting it in.


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
- The new language (two- or three-letter ISO code) needs a word list at ``training/lists/<code>.txt`` (tab-separated, see "Input data" above) and is ingested via a direct ``_build_dictionary("<code>", listpath="lists", in_place=True)`` call (NOT the ``dictionary_builder`` CLI, which only rebuilds already-shipped languages — see "Building the dictionaries" below); it should then be available in ``SUPPORTED_LANGUAGES``.


Building the dictionaries
^^^^^^^^^^^^^^^^^^^^^^^^^^^

``training/dictionary_builder.py`` reads a language's word list and writes the compressed, front-coded ``.plzma`` dictionary the runtime loads (see ``frontcode.py``, which replaced the pickled format in 2.0.0). Two things to know before running it:

- Without ``--in-place``, output goes to ``training/output/`` (gitignored) rather than the real package data, so a run never clobbers a shipped dictionary by accident. Pass ``--in-place`` to write into the installed package and actually update what ships.
- The base of a routine rebuild is the installed dictionary itself — the shipped ``.plzma`` is the pinned artifact, decoded and recomposed through the layers and stages, so a rebuild is idempotent when nothing changed. There is no way to accidentally rebuild a curated language from a thin word list.
- Passing a word-list directory (``listpath``, direct ``_build_dictionary`` call) *ingests* new data instead: the resolved list becomes the base, and for an already-shipped language the installed mappings win every shared key (policy B) — a re-extraction can only *add* keys; an existing mapping changes only via a reviewed override.
- Its ``__main__`` CLI (``python3 -m training.dictionary_builder --in-place``) only *rebuilds* languages already in ``SUPPORTED_LANGUAGES``, since that set is derived from the ``.plzma`` files already on disk. To add a genuinely *new* language (or ingest a fresh extraction), call ``_build_dictionary`` directly instead, e.g.:

.. code-block:: python

    from training.dictionary_builder import _build_dictionary
    _build_dictionary("xx", listpath="lists", in_place=True)


Example using ``kaikki.org``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since a source has to comprise enough words without sacrificing quality, the `kaikki.org <https://kaikki.org>`_ project is currently a good place to start. It leverages information from the Wiktionary project and is rather extensive. Its main drawbacks are lack of coverage for less-resourced languages and errors during processing of entries as the Wiktionary form tables are not all alike.


1. Find the link to all word senses for a given language, e.g. "Download JSON data for all word senses in the Lithuanian dictionary" leading to ``https://kaikki.org/dictionary/Lithuanian/kaikki.org-dictionary-Lithuanian.jsonl``.
2. Convert the JSONL dump to a tab-separated word list with ``training/kaikki_to_tsv.py``:

.. code-block:: shell

    python3 training/kaikki_to_tsv.py kaikki.org-dictionary-Lithuanian.jsonl training/lists/lt.txt

This prefers explicit inflection relations (``form_of``/``alt_of``) and falls back to an entry's own ``forms`` table, while dropping known-noisy rows (structural placeholders, romanization/transliteration entries, stress marks, cross-reference tables that list unrelated words rather than inflections). A single parenthesized optional letter group (Ancient Greek movable nu ``ἦ(ν)``) expands to both spellings, and an entry left with no pairs yields its own identity pair, so uninflected headwords (grc ``μέν``) still enter the dictionary.

3. Don't deduplicate the output: ``dictionary_builder.py`` counts repeated ``lemma\tword`` lines as evidence and uses that count to resolve conflicting lemmas for the same word form, so duplicates should be left as-is.
4. Check the output by exploring the data by hand to spot inconsistencies; ``dictionary_builder.py`` itself filters out lines that are too short or otherwise malformed once you run it.


Example using Wikidata as the PRIMARY source
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``wikidata_lexemes.py`` is normally an *OOV-fill* source layered onto an
already-shipped dictionary (see "The dictionary data pipeline" below). For a
language Wiktionary covers poorly but Wikidata covers well (``ml`` Malayalam
is the first: ~11k Kaikki words vs 67k WD lexemes / 754k forms), it doubles
as the *base* word list instead — same extractor, different destination:

1. Add the language's Wikidata QID to ``LANGUAGE_QIDS`` in
   ``wikidata_lexemes.py``.
2. Extract straight into ``training/lists/<code>.txt`` (NOT
   ``training/fill/``) — the output format (``lemma\tform``) is identical
   either way:

.. code-block:: shell

    python3 -m training.wikidata_lexemes ml training/data/wikidata/latest-lexemes.json.gz training/lists/ml.txt

3. Build from the list (no shipped dict exists yet, so nothing layers on
   top): ``_build_dictionary("ml", listpath="lists", in_place=True)``.
4. ``training/lists/<code>.txt`` is git-ignored like every other list file,
   so it must be regenerated from the dump to rebuild the dictionary later —
   there is no committed copy of the extracted word list, only the shipped
   ``.plzma``.

The Wikidata lexeme dump itself
(``dumps.wikimedia.org/wikidatawiki/entities/latest-lexemes.json.gz``, ~600MB
compressed) is git-ignored too; download it once and reuse it across
sessions, the same way the UD treebank archive is handled above.


The dictionary data pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Beyond the raw ``kaikki_to_tsv`` extraction above, the dictionaries are
prepared and validated with a few small standalone CLIs (their git-ignored
inputs live under ``training/data/``):

- ``clean_wordlist.py <in.tsv> <out.tsv>`` — language-independent character
  hygiene between extraction and building: NFC-normalize, canonicalize curly
  quotes, strip invisible characters, reject mojibake and control/unassigned
  codepoints. Keeps duplicate lines (dictionary_builder treats line count as
  evidence) and exits nonzero if the reject rate exceeds ``--max-reject-pct``
  (a data-drift alarm).
- ``wikidata_lexemes.py <lang> <dump> <out.tsv>`` — extract extra
  ``(lemma, form)`` pairs from a Wikidata lexeme dump as an OOV *fill* layered
  onto (never overriding) the shipped dictionary; ``--prune`` drops pairs the
  shipped dict + rules/affix chain already reproduces. Can also serve as the
  PRIMARY base word list for a language Wiktionary covers poorly (write to
  ``training/lists/<code>.txt`` instead of ``training/fill/``) — see "Example
  using Wikidata as the PRIMARY source" above.
- ``build_override.py <lang> [--in-place]`` — mine an override lexicon from
  ALL of the language's UD train splits (closed-class at ≥3/90%, open-class at
  ≥5/95%, plus a per-treebank majority veto against convention splits), and
  gate the merged candidate with ``eval_gate`` on every train treebank.
  Output goes to ``training/output/`` unless ``--in-place`` updates the
  reviewed file on a passing gate; shipping still requires a dictionary
  rebuild. Deterministic given a pinned UD version (``download_eval_data.py``
  fixes UD 2.18, md5-verified).

  The committed ``training/overrides/<code>.tsv`` files are **reviewed
  source-of-truth**: a pure function of the UD data plus review, never of the
  current dictionary. Entries the pipeline already reproduces are kept — they
  are harmless (the override layer wins with the same mapping) — and only
  counted in the run's log, so a re-mine after a UD bump merges cleanly.

  ``--in-place`` rewrites that reviewed file through the same loader the build
  uses, which is *lossy by policy*: a multi-word form is dropped (unreachable —
  the tokenizer never yields it as one token) and a ``grc``/``he``/``ar`` entry
  is rewritten into the canonical key space. Every committed row survives the
  round trip today, but a hand-added spaced entry would be lost permanently.
  Prefer the default ``training/output/`` run and diff it by hand.

  Historical note: the 2.0.0-era files were delta-trimmed against their
  then-current bases (5,096 rows dropped, verified byte-identical at the
  time; git history holds the fuller sets) and 17 of the 47 files never were.
  File length therefore reflects mining era, not curation quality.
- ``verify_idempotence.py [lang ...]`` — byte-idempotence lint: every shipped
  dictionary must recompose byte-identically from its own data (zero expected
  drift; any difference means a pipeline change silently rewrites shipped
  data). Run it by hand after pipeline or data changes (~15 min for all
  languages, seconds per language).
- ``eval_gate.py <lang> <baseline.tsv> <candidate.tsv>`` — release gate:
  refuse a candidate that regresses token- OR type-level accuracy on any UD
  treebank for the language (cross-treebank is automatic), each at its
  most-held-out split — train, the only split that is not published, falling
  back per TREEBANK to dev, then test, with a WARNING. Per-treebank
  resolution keeps test-only parallel treebanks (``fi_pud``, ``ru_pud``, …)
  in the gate next to their train-having siblings.

``ud_conllu.py`` holds the shared UD conventions (the dataset-name → language
map and the gold-token iteration rule) these tools read with.

``dictionary_builder.py`` composes the layers itself when building a
dictionary: a reviewed ``training/overrides/<code>.tsv`` always wins, the base
wordlist comes next, and an optional ``training/fill/<code>.tsv`` (git-ignored,
``wikidata_lexemes.py`` output) only fills gaps, never overriding. Keys are
NFC-normalized at build time, matching runtime lookups. Output is the
front-coded byte-stream format (see ``frontcode.py``), which replaced the
pickled ``.plzma`` format in 2.0.0.
