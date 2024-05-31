"""The setup script."""

import re

from pathlib import Path
from setuptools import setup, find_packages


def get_version(package):
    "Return package version as listed in `__version__` in `init.py`"
    initfile = Path(package, "__init__.py").read_text()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", initfile)[1]


readme = Path("README.md").read_text()
# with open('HISTORY.rst') as history_file:
#    history = history_file.read()

requirements = []

setup_requirements = []

test_requirements = ["pytest>=3", "pytest-cov"]


setup(
    author="Adrien Barbaresi",
    author_email="barbaresi@bbaw.de",
    python_requires=">=3.6",
    classifiers=[  # https://pypi.org/classifiers/
        "Development Status :: 4 - Beta",
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
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
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
    long_description_content_type="text/markdown",
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
    package_data={"simplemma": ["strategies/dictionaries/data/*.plzma"]},
    packages=find_packages(include=["simplemma", "simplemma.*"]),
    project_urls={
        "Source": "https://github.com/adbar/simplemma",
        "Docs": "https://adbar.github.io/simplemma/",
        # "Blog": "https://adrien.barbaresi.eu/blog/",  # tag/simplemma
    },
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/adbar/simplemma",
    version=get_version("simplemma"),
    zip_safe=False,
)
