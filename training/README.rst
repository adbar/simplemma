Instructions to run the evaluation
----------------------------------

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions). They can be reproduced by the following steps:

1. Install the evaluation dependencies, Python >= 3.8 required (``pip install -r training/requirements.txt``)
2. Update ``DATA_URL`` in ``training/download-eval-data.py`` to point to the latest treebanks archive from `Universal Dependencies <https://universaldependencies.org/#download>` (or the version that you which to use).
3. Run ``python3 training/download-eval-data.py`` which will
  1. Download the archive
  2. Extract relevant data (language and if applicable specific treebank, see notes in the results table)
  3. Concatenate the train, dev and test data into a single file (e.g. ``cat de_gsd*.conllu > de-gsd-all.conllu``)
  4. Store the files at the expected location (``training/data/UD/``)
4. Run the script, e.g. from the home directory ``python3 training/evaluate_simplema.py``
5. Results are stored at ``training/data/results/results_summary.csv``. Also, errors are written in a CSV file for each dataset under the ``data/results``folder. 

