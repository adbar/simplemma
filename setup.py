#!/usr/bin/env python

"""The setup script."""

import re
import sys

from pathlib import Path
from setuptools import setup, find_packages


def get_version(package):
    "Return package version as listed in `__version__` in `init.py`"
    initfile = Path(package, "__init__.py").read_text()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", initfile)[1]


readme = Path("README.rst").read_text()
# with open('HISTORY.rst') as history_file:
#    history = history_file.read()

requirements = []

setup_requirements = []

test_requirements = ["pytest>=3", "pytest-cov"]

# add argument to compile with mypyc
if len(sys.argv) > 1 and sys.argv[1] == "--use-mypyc":
    sys.argv.pop(1)
    from mypyc.build import mypycify

    ext_modules = mypycify(
        [
            "simplemma/__init__.py",
            "simplemma/langdetect.py",
            "simplemma/rules.py",
            "simplemma/simplemma.py",
            "simplemma/tokenizer.py",
        ],
        opt_level="3",
        multi_file=True,
    )
else:
    ext_modules = []

setup(
    author="Adrien Barbaresi",
    author_email="barbaresi@bbaw.de",
    python_requires=">=3.6",
    classifiers=[  # https://pypi.org/classifiers/
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: Bulgarian",
        "Natural Language :: Catalan",
        "Natural Language :: Croatian",
        "Natural Language :: Czech",
        "Natural Language :: Danish",
        "Natural Language :: Dutch",
        "Natural Language :: English",
        "Natural Language :: Finnish",
        "Natural Language :: French",
        "Natural Language :: Galician",
        "Natural Language :: German",
        "Natural Language :: Greek",
        "Natural Language :: Hindi",
        "Natural Language :: Hungarian",
        "Natural Language :: Icelandic",
        "Natural Language :: Indonesian",
        "Natural Language :: Irish",
        "Natural Language :: Italian",
        "Natural Language :: Latin",
        "Natural Language :: Latvian",
        "Natural Language :: Lithuanian",
        "Natural Language :: Macedonian",
        "Natural Language :: Malay",
        "Natural Language :: Norwegian",
        "Natural Language :: Polish",
        "Natural Language :: Portuguese",
        "Natural Language :: Romanian",
        "Natural Language :: Russian",
        "Natural Language :: Slovak",
        "Natural Language :: Slovenian",
        "Natural Language :: Spanish",
        "Natural Language :: Swedish",
        "Natural Language :: Thai",
        "Natural Language :: Turkish",
        "Natural Language :: Ukrainian",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Internationalization",
        "Topic :: Software Development :: Localization",
        "Topic :: Text Processing :: Linguistic",
        "Typing :: Typed",
    ],
    description="A simple multilingual lemmatizer for Python.",
    install_requires=requirements,
    license="MIT license",
    long_description=readme,  # + '\n\n' + history,
    include_package_data=True,
    keywords=[
        "nlp",
        "lemmatization",
        "lemmatisation",
        "lemmatiser",
        "tokenization",
        "tokenizer",
    ],
    name="simplemma",
    package_data={"simplemma": ["data/*.plzma"]},
    packages=find_packages(include=["simplemma", "simplemma.*"]),
    project_urls={
        "Source": "https://github.com/adbar/",
        "Blog": "https://adrien.barbaresi.eu/blog/",  # tag/simplemma
    },
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/adbar/simplemma",
    version=get_version("simplemma"),
    zip_safe=False,
    # optional mypyc
    ext_modules=ext_modules,
)
