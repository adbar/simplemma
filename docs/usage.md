---
title: "Usage: lemmatize, tokenize and split text in Python"
description: "Worked examples for Simplemma: lemmatizing words and texts, chaining languages, greedy decomposition, tokenization, sentence splitting and language detection."
---

# Usage

Worked examples for every entry point, from a single word to a full text.

{%
   include-markdown "../README.md"
   start="<!-- include:usage:start -->"
   end="<!-- include:usage:end -->"
   heading-offset=-1
%}


## Tokenization

A simple tokenization function is provided for convenience:

``` python
>>> from simplemma import simple_tokenizer
>>> simple_tokenizer('Lorem ipsum dolor sit amet, consectetur elit.')
['Lorem', 'ipsum', 'dolor', 'sit', 'amet', ',', 'consectetur', 'elit', '.']
# for an iterator instead of a list, use the RegexTokenizer directly
>>> from simplemma import RegexTokenizer
>>> RegexTokenizer().split_text('Lorem ipsum dolor sit amet')
<generator object ...>
```

The tokenizer is script-aware. In-word joiners and combining marks stay
inside their word (`l'homme`, `בית־ספר`), punctuation becomes its own token,
and numbers and currency amounts keep a sensible shape (`3,50`, `€3.50`).

Measured against Universal Dependencies gold, token-level F1 is 0.97 to
0.998 for most languages (median 0.99), lower for French, Catalan and
Italian (0.93 to 0.96), where UD splits elided articles (`l'homme` →
`l'` + `homme`) and simplemma keeps them whole.

The functions `text_lemmatizer()` and `lemma_iterator()` chain
tokenization and lemmatization. They accept the same `greedy` argument
as `lemmatize()`:

``` python
>>> from simplemma import text_lemmatizer
>>> sentence = 'Sou o intervalo entre o que desejo ser e os outros me fizeram.'
>>> text_lemmatizer(sentence, lang='pt')
# caveat: desejo is also a noun, should be desejar here
['ser', 'o', 'intervalo', 'entre', 'o', 'que', 'desejo', 'ser', 'e', 'o', 'outro', 'me', 'fazer', '.']
# same principle, returns a generator and not a list
>>> from simplemma import lemma_iterator
>>> lemma_iterator(sentence, lang='pt')
```

Both functions know where sentences start, and lower a sentence-initial word
before looking it up, since its capital is positional rather than lexical.
Mid-sentence capitals are left alone, so the same word can lemmatize
differently depending on its position:

``` python
>>> text_lemmatizer('Laufen ist gesund.', lang='de')
['laufen', 'sein', 'gesund', '.']
>>> text_lemmatizer('Beim Laufen ist es gesund.', lang='de')
['beim', 'Laufen', 'sein', 'es', 'gesund', '.']
```

For Danish, English and German the lowering is skipped when the capitalized
form looks like a proper noun, and for a few languages ALL-CAPS acronyms are
kept verbatim. See the [`casing`
module](reference/casing.md) for details.


## Sentence splitting

`split_sentences()` segments raw text into sentences, using rules plus
per-language abbreviation data where it measurably pays (currently `cs`,
`de`, `en`, `fr`, `nl`, `pl`, `pt`). Other codes use the generic rules,
which stay close in quality. `lang='el'` additionally treats `;` as a
question mark, and a blank line always starts a new sentence. On Universal
Dependencies data the splitter matches or beats NLTK's punkt on 6 of 7
evaluated languages, with no added dependency.

``` python
>>> from simplemma import split_sentences
>>> split_sentences('Das Tor fiel in der 95. Minute. Das Spiel war aus.', lang='de')
['Das Tor fiel in der 95. Minute.', 'Das Spiel war aus.']
```

The sentences are stripped slices of the input, and `lang` also accepts a
tuple, like the other entry points.

On the held-out PUD corpora, sentence-boundary F1 is 0.98 to 0.998. Text
without reliable terminal punctuation, such as social media, is much harder.


## Caveats

``` python
# don't expect too much though
# this diminutive form isn't in the model data
>>> simplemma.lemmatize('spaghettini', lang='it')
'spaghettini' # should read 'spaghettino'
# the algorithm cannot choose between valid alternatives yet
>>> simplemma.lemmatize('son', lang='es')
'ser' # 3rd-person plural of 'ser', but 'son' is also a noun (a Cuban music genre)
```

Working without morphosyntactic information keeps things simple but sets a
hard ceiling on accuracy, for instance when disambiguating past participles
from verb-derived adjectives. Such words are usually left unchanged. Since
the focus lies on overall coverage, some short frequent words (typically
pronouns and conjunctions) may need post-processing, generally a few dozen
tokens per language.

The greedy algorithm seldom produces invalid forms and works best in the
low-frequency range, notably for compound words and neologisms. Aggressive
decomposition is only useful for morphologically-rich languages, where it
can act as a linguistically motivated stemmer.


## Language detection

Language detection takes a text and a tuple `lang` of languages of
interest. `langdetect()` returns each language code with its score, plus
"unk" for the proportion of unknown tokens. `in_target_language()` returns
the single ratio of tokens belonging to the target language(s). Scores are
proportions between 0 and 1, computed independently per language, so a
token recognized in several counts towards each and they need not sum to 1.

``` python
# import necessary functions
>>> from simplemma import in_target_language, langdetect
# language detection
>>> langdetect('"Exoplaneta, též extrasolární planeta, je planeta obíhající kolem jiné hvězdy než kolem Slunce."', lang=("cs", "sk"))
[('cs', 1.0), ('sk', 0.25), ('unk', 0.0)]
# proportion of known words
>>> in_target_language("opera post physica posita (τὰ μετὰ τὰ φυσικά)", lang="la")
0.6666666666666666
```

The `greedy` argument triggers use of the greedier decomposition algorithm
described above, thus extending word coverage and recall of detection at
the potential cost of a lesser accuracy.


To build your own lemmatizer out of these pieces, see
[Classes and strategies](classes-and-strategies.md). To run them with a
smaller memory footprint, see [Memory usage](memory-usage.md).
