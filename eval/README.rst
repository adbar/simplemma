Instructions to run the evaluation
----------------------------------

The scores are calculated on `Universal Dependencies <https://universaldependencies.org/>`_ treebanks on single word tokens (including some contractions but not merged prepositions). They can be reproduced by concatenating all available UD files and by using the script ``udscore.py``.

1. Download the main archive containing the `Universal Dependencies <https://universaldependencies.org/#download>`_ treebanks
2. Extract relevant data (language and if applicable specific treebank, see notes in the results table)
3. Concatenate the train, dev and test data into a single file (e.g. ``cat de_gsd*.conllu > de-gsd-all.conllu``)
4. Store the files at the expected location (``tests/UD/``) and/or edit the corresponding paths in ``udscore.py``
5. Install the evaluation dependencies (``pip install -r eval-requirements.txt``)
6. Run the script, e.g. from the home directory ``python3 eval/udscore.py``
7. Results are displayed in the terminal and errors are written in a CSV file

