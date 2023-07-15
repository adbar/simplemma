# Introduction

## Purpose

[Lemmatization](https://en.wikipedia.org/wiki/Lemmatisation) is the process of grouping together the inflected forms of a word so they can be analysed as a single item, identified by the word's lemma, or dictionary form. Unlike stemming, lemmatization outputs word units that are still valid linguistic forms.

In modern natural language processing (NLP), this task is often indirectly tackled by more complex systems encompassing a whole processing pipeline. However, it appears that there is no straightforward way to address lemmatization in Python although this task can be crucial in fields such as information retrieval and NLP.

**Simplemma** provides a simple and multilingual approach to look for base forms or lemmata. It may not be as powerful as full-fledged solutions but it is generic, easy to install and straightforward to use. In particular, it does not need morphosyntactic information and can process a raw series of tokens or even a text with its built-in tokenizer. By design it should be reasonably fast and work in a large majority of cases, without being perfect.

With its comparatively small footprint it is especially useful when speed and simplicity matter, in low-resource contexts, for educational purposes, or as a baseline system for lemmatization and morphological analysis.

Currently, 48 languages are partly or fully supported (see table below).


## Installation

The current library is written in pure Python with no dependencies:

`pip install simplemma`

- `pip3` where applicable
- `pip install -U simplemma` for updates


## Usage


### Word-by-word


Simplemma is used by selecting a language of interest and then applying the data on a list of words.

```python
    >>> import simplemma
    # get a word
    myword = 'masks'
    # decide which language to use and apply it on a word form
    >>> simplemma.lemmatize(myword, lang='en')
    'mask'
    # grab a list of tokens
    >>> mytokens = ['Hier', 'sind', 'Vaccines']
    >>> for token in mytokens:
    >>>     simplemma.lemmatize(token, lang='de')
    'hier'
    'sein'
    'Vaccines'
    # list comprehensions can be faster
    >>> [simplemma.lemmatize(t, lang='de') for t in mytokens]
    ['hier', 'sein', 'Vaccines']
```
