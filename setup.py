#!/usr/bin/env python

"""The setup script."""

import re

from pathlib import Path
from setuptools import setup, find_packages


def get_version(package):
    "Return package version as listed in `__version__` in `init.py`"
    # version = Path(package, '__init__.py').read_text() # Python >= 3.5
    with open(str(Path(package, '__init__.py')), 'r', encoding='utf-8') as filehandle:
        initfile = filehandle.read()
    return re.search('__version__ = [\'"]([^\'"]+)[\'"]', initfile).group(1)


readme = Path('README.rst').read_text()
#with open('HISTORY.rst') as history_file:
#    history = history_file.read()

requirements = []

setup_requirements = []

test_requirements = ['pytest>=3', 'pytest-cov']

setup(
    author="Adrien Barbaresi",
    author_email='barbaresi@bbaw.de',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: Bulgarian',
        'Natural Language :: Catalan',
        'Natural Language :: Czech',
        'Natural Language :: Danish',
        'Natural Language :: Dutch',
        'Natural Language :: English',
        'Natural Language :: Finnish',
        'Natural Language :: French',
        'Natural Language :: Galician',
        'Natural Language :: German',
        'Natural Language :: Greek',
        'Natural Language :: Hungarian',
        'Natural Language :: Indonesian',
        'Natural Language :: Irish',
        'Natural Language :: Italian',
        'Natural Language :: Latin',
        'Natural Language :: Latvian',
        'Natural Language :: Lithuanian',
        'Natural Language :: Macedonian',
        'Natural Language :: Norwegian',
        'Natural Language :: Polish',
        'Natural Language :: Portuguese',
        'Natural Language :: Romanian',
        'Natural Language :: Russian',
        'Natural Language :: Slovak',
        'Natural Language :: Slovenian',
        'Natural Language :: Spanish',
        'Natural Language :: Swedish',
        'Natural Language :: Turkish',
        'Natural Language :: Ukrainian',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Text Processing :: Linguistic',
    ],
    description="A simple multilingual lemmatizer for Python.",
    install_requires=requirements,
    license="MIT license",
    long_description=readme, # + '\n\n' + history,
    include_package_data=True,
    keywords=['nlp', 'lemmatization', 'lemmatisation', 'lemmatiser', 'tokenization', 'tokenizer'],
    name='simplemma',
    package_data={'simplemma': ['data/*.plzma']},
    packages=find_packages(include=['simplemma', 'simplemma.*']),
    project_urls={
        "Source": "https://github.com/adbar/",
        "Blog": "https://adrien.barbaresi.eu/blog/", # tag/simplemma
    },
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/adbar/simplemma',
    version=get_version('simplemma'),
    zip_safe=False,
)
