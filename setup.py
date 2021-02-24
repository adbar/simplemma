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


with open('README.rst') as readme_file:
    readme = readme_file.read()

#with open('HISTORY.rst') as history_file:
#    history = history_file.read()

requirements = []

setup_requirements = []

test_requirements = ['pytest>=3', 'pytest-cov', 'tox']

setup(
    author="Adrien Barbaresi",
    author_email='barbaresi@bbaw.de',
    python_requires='>=3.4',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        #'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Text Processing :: Linguistic',
    ],
    description="A simple multilingual lemmatizer for Python.",
    install_requires=requirements,
    license="MIT license",
    long_description=readme, # + '\n\n' + history,
    include_package_data=True,
    keywords=['nlp', 'lemmatization', 'lemmatisation', 'lemmatiser'],
    name='simplemma',
    package_data={'simplemma': ['data/*.plzma']},
    packages=find_packages(include=['simplemma', 'simplemma.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/adbar/simplemma',
    version=get_version('simplemma'),
    zip_safe=False,
)
