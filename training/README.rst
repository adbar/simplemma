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

- Hebrew and Arabic proclitics are scored as pre-split sub-tokens, as the
  treebanks come segmented. Accuracy is lower on unsegmented input.
- Gold annotation markers are stripped before scoring, see ``_GOLD_MARKERS``
  and ``_GOLD_SUFFIXES`` in ``ud_conllu.py``. These are compound markers in
  Dutch, Estonian, Finnish, Hungarian and Latin (``klooster_orde``,
  ``sisse_tulek``, ``yli#opisto``, ``el+mond``), Norwegian ``$`` on
  punctuation, the Arabic PUD dagger alif and the Bulgarian optional
  reflexive (``смея-(се)``).
- Korean gold lemmas are morpheme sequences (``주관+하+고``) or bare stems.
  ``ko_gold_lemma`` in ``ud_conllu.py`` cuts them before the first particle,
  ending or copula morpheme and adds 다 to predicate stems. LittlePrince keeps
  the first morpheme only (소화될 -> 소화) and scores about 0.79.

``python3 training/evaluate_simplemma.py`` scores the ``dev`` and ``test``
splits and writes ``training/data/results/results_summary.csv`` plus one
error CSV per dataset.

Each split has one role. **train** is used to mine overrides and sentence
starters and to gate changes. It is never scored. **dev** and **test** are
scored and gate nothing, except sentence-starter adoption on dev (see
``sentencebuilder`` below) and the Korean clitic tail pruning (see the
``rulebuilder`` section). Train shows whether a change helps
or hurts, but overstates by how much (up to 2x), so never report from it
or rank candidates with it. A language without a train split is gated on
dev, else test, with a WARNING. ``sw`` has no UD data at all.

``eval_gate.gate()`` (library, no CLI) rejects a candidate dictionary that
lowers token or type accuracy on any of the language's treebanks. It runs
the full ``Lemmatizer``, same protocol as ``evaluate_simplemma``. It scores
on every treebank whatever its license, since no data from scoring ships.
The same holds for the sentence-starter dev check. Shared UD conventions
live in ``ud_conllu.py``.


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

A re-ingest can gain overall and still break frequent forms. The ru, hbs and
pl overrides therefore carry pin rows, which keep the previous lemma of each
form whose new mapping breaks at least 3 more train tokens than it fixes
(licensed treebanks only).

A new language needs an ISO code, a left-to-right script, and morphology
where several forms reduce to one entry (Urdu suffers).
After ``--in-place`` it appears in ``SUPPORTED_LANGUAGES``. Potential sources:
`issue 1 <https://github.com/adbar/simplemma/issues/1>`_.

Building from scratch
^^^^^^^^^^^^^^^^^^^^^

The shipped dictionaries cannot be rebuilt from public data alone. Their base
merges word lists from earlier releases that are no longer published, and
kaikki.org keeps no past dumps. A rebuild is reproducible only because it
starts from the shipped file.

To build a shipped language from a word list alone, move its ``.plzma`` out of
``simplemma/strategies/dictionaries/data/`` and run ``wordlist_ingest``. The
overrides still apply. Expect a weaker dictionary. On UD dev and test, a build
from the current Kaikki dump alone scored below the shipped one for 36 of 41
languages (measured 2026-11). For 32 of them the loss is 1.8 to 21 points,
e.g. fr -11.6, it -13.7, tr -20.7. Most of it comes from frequent function
words. A form that is also a headword with its own inflections maps to itself
(fr ``est`` the noun, not ``être``). The overrides were mined against the
shipped dictionary, so they do not cover these cases. With the file moved,
``--gate`` has no baseline. Keep the moved file and score both versions with
``evaluate_simplemma.py`` before shipping the new one.


Word lists from Kaikki
^^^^^^^^^^^^^^^^^^^^^^

`kaikki.org <https://kaikki.org>`_ exposes Wiktionary as JSONL and is the
usual starting point. It is thin on less-resourced languages and noisy.

1. Download "all word senses" for the language, e.g.
   ``https://kaikki.org/dictionary/Lithuanian/kaikki.org-dictionary-Lithuanian.jsonl``.
2. ``python3 training/kaikki_to_tsv.py <dump.jsonl> training/lists/lt.txt``.
   The converter prefers explicit ``form_of``/``alt_of`` relations, falls back
   to the entry's ``forms`` table, drops known-noisy rows, and emits an
   identity pair for uninflected headwords. A dropped romanization or
   transliteration does not block that identity. Korean verb and adjective
   forms in 다 also yield their stem (했다 -> 했), so the clitic cells can
   strip an ending down to a key (``_STEM_KEY_ENDINGS``). Korean
   inflected-form entries without a ``form_of`` link are skipped, since they
   would map to themselves (``_FORM_TEMPLATES``).
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

``python3 -m training.build_override <code> [--exclude TREEBANK ...] [--in-place]``
mines an override lexicon from the language's UD train splits, minus the
excluded treebanks.

Only CC BY, CC BY-SA, CC0 and public-domain treebanks
are mined, plus CC BY-NC-SA for grc and la (``allowed_license``). Licenses
come from each treebank's README, recorded at download in
``training/data/UD/licenses.tsv``. A treebank without one is skipped with a
warning. ``licenses/UD_Treebanks.txt`` lists the treebanks per language.
Regenerate it after a UD bump. It lists the allowed train splits that yield
tokens with a usable form and lemma. This leaves out ar_nyuad, en_esl and
en_gumreddit (forms replaced by ``_``) and en_eslspok (no lemmas).

A form
qualifies with 3 occurrences (closed class) or 5 (open class) and 60%
agreement on its majority lemma. The lemma must beat the current output by
2 tokens, and lose tokens in no treebank with 3 or more occurrences. Proper
nouns, adpositions, participles, underscore-joined lemmas and case-only
changes are skipped as treebank conventions. Letterless
lemmas are skipped as junk. A lowercase form with a cased lemma is skipped
as a sentence-initial artifact. Existing rows that UD contradicts are
logged, not changed. Output goes to ``training/output/`` unless
``--in-place`` rewrites ``training/overrides/<code>.tsv``. Shipping still
requires a rebuild.

The committed files are the reviewed source of truth. Their lemmas come from
UD data plus review. The current output only decides which forms need a row.
Rows the pipeline already reproduces are kept, so a re-mine after a UD bump
merges cleanly.

New rows can change the output of other forms, for instance a capitalized
form that falls back to a new lowercase row. After the rebuild, mine again
until nothing is added. Candidates rejected in review come back on every
run. Removing a row needs a rebuild from the committed
``.plzma``: a rebuild starts from the shipped file, so the key would stay.

Only re-mine languages whose treebanks agree: rows mined from the other
treebanks must improve each held-out one. As of 2026-10, this holds for
``cs``, ``es``, ``et``, ``is``, ``it``, ``nl``, ``pl``, ``ru``, ``sl``,
``sv`` and ``uk``, for ``fr`` with ``--exclude fr_alts`` (Middle French) and
for ``ko`` with ``--exclude ko_ksl`` (learner treebank).
It fails for ``de``, ``fi``, ``la``, ``lt``, ``pt`` and ``ro``.

``--in-place`` is deliberately lossy: multi-word forms are dropped, curly
apostrophes are folded, and ``grc``/``he``/``ar`` entries are rewritten into
the canonical key space. Prefer the default run and diff it by hand.


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
capitalized), ``excluded=`` (stoplist). lv picks between two tables
by capitalization, de is hand-written, ru normalizes ё ahead of its table.

``python3 -m training.rulebuilder <code>`` runs four functions, then
``evaluate`` prints the precision/coverage report. Run them by hand for the
judgment calls in between:

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

Korean is the exception. Its particle strip cell (target ``""``) cannot be
scored in the dictionary, which holds no noun+particle forms. A tail is kept
if at least 20 GSD+Kaist train tokens left unresolved by the dictionary,
clitic, prefix and hyphen strategies end in it, and at least 85% of them have
the form minus the tail as gold. Candidates are the Kaikki particles, the
forms of 이다 and pairs of them (에서는, 이라고도). The 하다/되다 tails are
the endings found in at least half of the X하다/X되다 tables. A Korean clitic
tail is kept only if removing it loses UD train tokens, confirmed per
treebank on dev and test. If train is unaffected, dev and test decide. The
screens are not part of the repository.

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

``python3 -m training.sentencebuilder <code>`` mines starters on train,
under the same license filter as the override lexicons. It prints a
paste-able literal only if they beat the shipped list on dev. Otherwise it
says ``keep the shipped list``. Dev treebanks with pre-tokenized text
(such as de_hdt, pt_cintil) are not scored on. ``--check`` scores the shipped
list alone. Run it before and after any splitter change.

Abbreviations are not mined: held out they gain at most +0.0025 F1, against
up to +0.09 for starters, and a mined list runs to thousands of entries.
