# Supported languages

The following languages are available using their [ISO 639-1 code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes):

## Available languages (2022-09-05)

Code    | Language             | Forms (10³) |Acc.  | Comments
------- | -------------------- | ----------- |----- | ------------------------------------------------------------------------
``bg``  | Bulgarian            | 213         |      |
``ca``  | Catalan              | 579         |      |
``cs``  | Czech                | 187         |0.88  | on UD CS-PDT
``cy``  | Welsh                | 360         || 
``da``  | Danish               | 554         |0.92  | on UD DA-DDT, alternative: [lemmy](https://github.com/sorenlind/lemmy)
``de``  | German               | 682         |0.95  | on UD DE-GSD, see also [German-NLP list](https://github.com/adbar/German-NLP#Lemmatization)
``el``  | Greek                | 183         |0.88  | on UD EL-GDT
``en``  | English              | 136         |0.94  | on UD EN-GUM, alternative: [LemmInflect](https://github.com/bjascob/LemmInflect)
``enm`` | Middle English       | 38          |      |
``es``  | Spanish              | 720         |0.94  | on UD ES-GSD
``et``  | Estonian             | 133         |      | low coverage
``fa``  | Persian              | 10          |      | experimental
``fi``  | Finnish              | 2,106       |      | evaluation and alternatives: see [this benchmark](https://github.com/aajanki/finnish-pos-accuracy)
``fr``  | French               | 217         |0.94  | on UD FR-GSD
``ga``  | Irish                | 383         |      |
``gd``  | Gaelic               | 48          |      |
``gl``  | Galician             | 384         |      |
``gv``  | Manx                 | 62          |      |
``hbs`` | Serbo-Croatian       | 838         |      | Croatian and Serbian lists to be added later
``hi``  | Hindi                | 58          |      | experimental
``hu``  | Hungarian            | 458         |      |
``hy``  | Armenian             | 323         |      |
``id``  | Indonesian           | 17          |0.91  | on UD ID-CSUI
``is``  | Icelandic            | 175         |      |
``it``  | Italian              | 333         |0.93  | on UD IT-ISDT
``ka``  | Georgian             | 65          |      |
``la``  | Latin                | 850         |      |
``lb``  | Luxembourgish        | 305         |      |
``lt``  | Lithuanian           | 247         |      |
``lv``  | Latvian              | 168         |      |
``mk``  | Macedonian           | 57          |      |
``ms``  | Malay                | 14          |      |
``nb``  | Norwegian (Bokmål)   | 617         |      |
``nl``  | Dutch                | 254         |0.91  | on UD-NL-Alpino
``nn``  | Norwegian (Nynorsk)| || 
``pl``  | Polish               | 3,733       |0.91  | on UD-PL-PDB
``pt``  | Portuguese           | 933         |0.92  | on UD-PT-GSD
``ro``  | Romanian             | 311         |      |
``ru``  | Russian              | 607         |      | alternative: [pymorphy2](https://github.com/kmike/pymorphy2/)
``se``  | Northern Sámi        | 113         |      | experimental
``sk``  | Slovak               | 846         |0.92  | on UD SK-SNK
``sl``  | Slovene              | 136         |      |
``sq``  | Albanian             | 35          |      |
``sv``  | Swedish              | 658         |      | alternative: [lemmy](https://github.com/sorenlind/lemmy)
``sw``  | Swahili              | 10          |      | experimental
``tl``  | Tagalog              | 33          |      | experimental
``tr``  | Turkish              | 1,333       |0.88  | on UD-TR-Boun
``uk``  | Ukrainian            | 190         |      | alternative: [pymorphy2](https://github.com/kmike/pymorphy2)



**Low coverage** mentions means one would probably be better off with a language-specific library, but *simplemma* will work to a limited extent. Open-source alternatives for Python are referenced if possible.

**Experimental** mentions indicate that the language remains untested or that there could be issues with the underlying data or lemmatization process.

The scores are calculated on [Universal Dependencies](https://universaldependencies.org) treebanks on single word tokens (including some contractions but not merged prepositions), they describe to what extent simplemma can accurately map tokens to their lemma form. They can be reproduced by concatenating all available UD files and by using the script `udscore.py` in the `training/` folder.

This library is particularly relevant as regards the lemmatization of less frequent words. Its performance in this case is only incidentally captured by the benchmark above. In some languages, a fixed number of words such as pronouns can be further mapped by hand to enhance performance.
