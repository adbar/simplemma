"""Tests for rule-based behavior of the `simplemma` package."""

import logging
import pytest

from simplemma.rules import apply_rules, apply_de, apply_en, apply_fi

logging.basicConfig(level=logging.DEBUG)


def test_apply_de():
    """Test German rules."""
    # doesn't exist
    assert apply_de("Whatawordicantbelieveit") is None
    # nouns
    assert apply_de("Abonnenten") == "Abonnent"
    assert apply_de("Pfifferlinge") == "Pfifferling"
    assert apply_de("Pfifferlingen") == "Pfifferling"
    assert apply_de("Heiterkeiten") == "Heiterkeit"
    assert apply_de("Bahnreisenden") == "Bahnreisender"
    assert apply_de("Bürgertums") == "Bürgertum"
    assert apply_de("Achterls") == "Achterl"
    assert apply_de("Inspekteurinnen") == "Inspekteurin"
    assert apply_de("Zwiebelschneider") == "Zwiebelschneider"
    # assert apply_de("Zwiebelschneidern") == "Zwiebelschneider"
    assert apply_de("Facetten") == "Facette"
    assert apply_de("Kazakhstans") == "Kazakhstan"
    assert apply_de("Hämatome") == "Hämatom"
    assert apply_de("Hämatomen") == "Hämatom"
    assert apply_de("Hämatoms") == "Hämatom"
    assert apply_de("Ökonomen") == "Ökonom"
    # assert apply_de("Theologien") == "Theologie"
    # assert apply_de("Zeitschriftenmarken", greedy=True) == "Zeitschriftenmarke"
    # assert apply_de("Gesundheitsfreaks", greedy=True) == "Gesundheitsfreak"
    # adjectives
    assert apply_de("großartiges") == "großartig"
    assert apply_de("achtsame") == "achtsam"
    assert apply_de("aufgemachtes") == "aufgemacht"
    assert apply_de("schnellster") == "schnell"
    assert apply_de("geächteten") == "geächtet"
    assert apply_de("aufgeblasenes") == "aufgeblasen"
    assert apply_de("geschleunigst") == "geschleunig"
    assert apply_de("zweitrangigster") == "zweitrangig"
    assert apply_de("zwielichtigen", greedy=True) == "zwielichtig"
    assert apply_de("freakige", greedy=True) == "freakig"
    # Gendersprache normalization
    assert apply_de("ZuschauerInnen") == "Zuschauer:innen"
    assert apply_de("Zuschauer*innen") == "Zuschauer:innen"
    assert apply_de("Zuschauer_innen") == "Zuschauer:innen"


def test_apply_en():
    """Test English rules."""
    # doesn't exist
    assert apply_en("Whatawordicantbelieveit") is None
    # nouns
    assert apply_en("delicacies") == "delicacy"
    assert apply_en("nurseries") == "nursery"
    assert apply_en("realities") == "reality"
    assert apply_en("kingdoms") == "kingdom"
    assert apply_en("mistresses") == "mistress"
    assert apply_en("realisms") == "realism"
    assert apply_en("naturists") == "naturist"
    assert apply_en("atonements") == "atonement"
    assert apply_en("nonces") == "nonce"
    assert apply_en("hardships") == "hardship"
    assert apply_en("atonements") == "atonement"
    assert apply_en("nations") == "nation"
    # adjectives / verb forms
    assert apply_en("vindicated") == "vindicate"
    assert apply_en("fastened") == "fasten"
    assert apply_en("dignified") == "dignify"
    assert apply_en("realized") == "realize"
    # assert apply_en('realised') == 'realise'


def test_apply_fi():
    """Test Finnish rules."""
    # doesn't exist
    assert apply_fi("Whatawordicantbelieveit") is None
    # nouns
    assert apply_fi("kansalaiseksi") == "kansalainen"
    assert apply_fi("huokoisten") == "huokoinen"
    assert apply_fi("kasvatteja") == "kasvatti"


def test_apply_rules():
    """Test rules on all available languages."""
    assert apply_rules("Pfifferlinge", "de") == "Pfifferling"
    assert apply_rules("Pfifferlinge", "en") is None
    assert apply_rules("Pfifferlinge", "fi") is None
    assert apply_rules("atonements", "de") is None
    assert apply_rules("atonements", "en") == "atonement"
    assert apply_rules("atonements", "fi") is None
    assert apply_rules("kansalaiseksi", "de") is None
    assert apply_rules("kansalaiseksi", "en") is None
    assert apply_rules("kansalaiseksi", "fi") == "kansalainen"
