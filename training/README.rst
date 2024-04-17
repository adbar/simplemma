Running the evaluation
----------------------

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions). They can be reproduced by the following steps:

1. Install the evaluation dependencies, Python >= 3.8 required (``pip install -r training/requirements.txt``)
2. Update ``DATA_URL`` in ``training/download-eval-data.py`` to point to the latest treebanks archive from `Universal Dependencies <https://universaldependencies.org/#download>` (or the version that you which to use).
3. Run ``python3 training/download-eval-data.py`` which will
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

- The input data has to be in tab-separated columns, first lemma, then word form, e.g. ``pelican TAB pelicans``.
- Redundant and noisy cases are mostly filtered out by input script but it is best if the data are controlled by hand as errors in lists or machine-generated data are common.
- The data should be reviewed and tested on an authoritative source like the universal dependencies (see above).


Adding languages
^^^^^^^^^^^^^^^^

- The Simplemma approach currently works best on languages written from left-to-right, results will not be as good on other languages (e.g. Urdu).
- The target language has to be prone to lemmatization by allowing for the reduction of at least two word forms to a single dictionary entry (e.g. Korean is not quite adapted in the current state of Simplemma).
- The new language (two- or three-letter ISO code) has to be added to the dictionary data (using the dictionary_pickler script), it should then be available in `SUPPORTED_LANGUAGES`.


Example using ``kaikki.org``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since a source has to comprise enough words without sacrificing quality, the `kaikki.org <https://kaikki.org>`_ project is currently a good place to start. It leverages information from the Wiktionary project and is rather extensive. Its main drawbacks are lack of coverage for less-resourced languages and errors during processing of entries as the Wiktionary form tables are not all alike.


1. Find the link to all word senses for a given langauge, e.g. "Download JSON data for all word senses in the Lithuanian dictionary" leading to `https://kaikki.org/dictionary/Lithuanian/kaikki.org-dictionary-Lithuanian.json`.
2. Convert the JSON file to the required tabular data by extracting word forms related to a dictionary entry.
3. Deduplicate the entries.
4. Control the output by skipping lines which are too short or contain unexpected characters, converting lines if they are not in the right character set, exploring the data by hand to spot inconsistencies.


Here is an example of how the data can be extracted, the attributes may not be the same for all languages in Kaikki, hence the two different ways, ``senses`` and ``forms`` mostly corresponding to tables in the source.


.. code-block:: python

    with open('de-wikt.txt', 'w') as outfh, open('kaikki.org-dictionary-German.json') as infh:
        for line in infh:
            item = json.loads(line)
            i = 0
            # use senses
            if 'senses' in item:
                for s in item['senses']:
                    if 'form_of' in s and item['word']:
                        i += 1
                        lemma = s['form_of'][0]['word']
                        outfh.write(lemma + '\t' + item['word'] + '\n')
                    elif 'alt_of' in s and item['word']:
                        i += 1
                        lemma = s['alt_of'][0]['word']
                        outfh.write(lemma + '\t' + item['word'] + '\n')
            # use forms
            if i == 0 and 'forms' in item:
                for f in item['forms']:
                    if f['form']:
                        lemma = item['word']
                        outfh.write(lemma + '\t' + f['form'] + '\n')
