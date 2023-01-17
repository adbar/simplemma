"""Tests for rule-based behavior of the `simplemma` package."""

import logging
import pytest

from simplemma.rules import apply_rules, apply_de, apply_en, apply_fi, apply_nl

logging.basicConfig(level=logging.DEBUG)


def test_apply_de():
    """Test German rules."""
    # doesn't exist
    assert apply_de("Whatawordicantbelieveit") is None
    # nouns
    # assert apply_de("Besorgnis", greedy=True) == "Besorgnis"
    # assert apply_de("Besorgnisse", greedy=True) == "Besorgnis"
    # assert apply_de("Abonnenten", greedy=True) == "Abonnent"
    assert apply_de("Pfifferlinge", greedy=True) == "Pfifferling"
    assert apply_de("Pfifferlingen", greedy=True) == "Pfifferling"
    assert apply_de("Heiterkeiten", greedy=True) == "Heiterkeit"
    assert apply_de("Bahnreisenden", greedy=True) == "Bahnreisende"
    assert apply_de("Bürgertums", greedy=True) == "Bürgertum"
    assert apply_de("Achterls", greedy=True) == "Achterl"
    # assert apply_de("Inspekteurinnen", greedy=True) == "Inspekteurin"
    # assert apply_de("Zwiebelschneider", greedy=True) == "Zwiebelschneider"
    assert apply_de("Zwiebelschneiders", greedy=True) == "Zwiebelschneider"
    # assert apply_de("Schneidern", greedy=True) == "Schneider"
    # assert apply_de("Bedenkens", greedy=True) == "Bedenken"
    # assert apply_de("Facetten", greedy=True) == "Facette"
    assert apply_de("Kazakhstans", greedy=True) == "Kazakhstan"
    # assert apply_de("Hämatome", greedy=True) == "Hämatom"
    # assert apply_de("Hämatomen", greedy=True) == "Hämatom"
    # assert apply_de("Hämatoms", greedy=True) == "Hämatom"
    assert apply_de("Ökonomen", greedy=True) == "Ökonom"
    assert apply_de("Chauffeusen", greedy=True) == "Chauffeuse"
    # assert apply_de("Bibliotheken", greedy=True) == "Bibliothek"
    assert apply_de("Kazakhstans", greedy=True) == "Kazakhstan"
    # assert apply_de("Gymnasiasten", greedy=True) == "Gymnasiast"
    # assert apply_de("Dezernates", greedy=True) == "Dezernat"
    assert apply_de("Luftikussen", greedy=True) == "Luftikus"
    assert apply_de("Trunkenbolde", greedy=True) == "Trunkenbold"
    assert apply_de("Theologien", greedy=True) == "Theologie"
    # assert apply_de("Geschädigten", greedy=True) == "Geschädigte"
    # assert apply_de("Zeitschriftenmarken", greedy=True) == "Zeitschriftenmarke"
    # assert apply_de("Gesundheitsfreaks", greedy=True) == "Gesundheitsfreak"
    # adjectives
    assert apply_de("großartiges", greedy=True) == "großartig"
    assert apply_de("achtsame", greedy=True) == "achtsam"
    # assert apply_de("aufgemachtes", greedy=True) == "aufgemacht"
    # assert apply_de("schnellster", greedy=True) == "schnell"
    # assert apply_de("geächteten", greedy=True) == "geächtet"
    # assert apply_de("aufgeblasenes", greedy=True) == "aufgeblasen"
    # assert apply_de("viszerale", greedy=True) == "viszeral"
    # assert apply_de("kurioses", greedy=True) == "kurios"
    # assert apply_de("adipösen", greedy=True) == "adipös"
    assert apply_de("isotropen", greedy=True) == "isotrop"
    # assert apply_de("kulanten", greedy=True) == "kulant"
    # assert apply_de("konvexes", greedy=True) == "konvex"
    # assert apply_de("myope", greedy=True) == "myop"
    # assert apply_de("geschleunigst", greedy=True) == "geschleunig"
    # assert apply_de("zweitrangigster", greedy=True) == "zweitrangig"
    assert apply_de("kompetenteste", greedy=True) == "kompetent"
    # assert apply_de("leiwandste", greedy=True) == "leiwand"
    # assert apply_de("gescheitesten", greedy=True) == "gescheit"
    # assert apply_de("luzidesten", greedy=True) == "luzide"  # luzid?
    # assert apply_de("frigides", greedy=True) == "frigide"
    # assert apply_de("frigideren", greedy=True) == "frigide"
    # assert apply_de("kruden", greedy=True) == "krude"
    # assert apply_de("krudesten", greedy=True) == "krude"
    # assert apply_de("zwielichtigen", greedy=True) == "zwielichtig"
    # assert apply_de("freakige", greedy=True) == "freakig"
    # assert apply_de("plausibles", greedy=True) == "plausibel"
    # assert apply_de("propres", greedy=True) == "proper"
    assert apply_de("perlende", greedy=True) == "perlend"
    assert apply_de("wuchernder", greedy=True) == "wuchernd"
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
    # assert apply_en("nerves") == "nerve"
    # assert apply_en("dwarves") == "dwarf"
    # assert apply_en("matrices") == "matrix"
    # adjectives / verb forms
    # assert apply_en("vindicated") == "vindicate"
    # assert apply_en("fastened") == "fasten"
    # assert apply_en("dignified") == "dignify"
    # assert apply_en("realized") == "realize"
    # assert apply_en("complies") == "comply"
    # assert apply_en("pinches") == "pinch"
    # assert apply_en("dignified") == "dignify"
    # assert apply_en('realised') == 'realise'


def test_apply_nl():
    """Test Dutch rules."""
    assert apply_nl("achterpagina's") == "achterpagina"
    assert apply_nl("mogelijkheden") == "mogelijkheid"
    assert apply_nl("boerderijen") == "boerderij"
    assert apply_nl("brieven") == "brief"


def test_apply_fi():
    """Test Finnish rules."""
    # common -inen cases
    assert apply_fi("liikenaisen") == "liikenainen"
    assert apply_fi("liikenaiset") == "liikenainen"
    assert apply_fi("liikenaisia") == "liikenainen"
    assert apply_fi("liikenaisissa") == "liikenainen"
    assert apply_fi("liikenaisista") == "liikenainen"
    assert apply_fi("liikenaiseksi") == "liikenainen"
    assert apply_fi("liikenaiseen") == "liikenainen"
    assert apply_fi("liikenaisella") == "liikenainen"
    assert apply_fi("liikenaiselle") == "liikenainen"
    assert apply_fi("liikenaiselta") == "liikenainen"
    assert apply_fi("liikenaiseni") == "liikenainen"
    assert apply_fi("liikenaisensa") == "liikenainen"
    assert apply_fi("liikenaisesta") == "liikenainen"
    assert apply_fi("liikenaisien") == "liikenainen"
    assert apply_fi("liikenaisiksi") == "liikenainen"
    assert apply_fi("liikenaisilla") == "liikenainen"
    assert apply_fi("liikenaisilta") == "liikenainen"
    assert apply_fi("liikenaisille") == "liikenainen"
    assert apply_fi("liikenaisina") == "liikenainen"
    assert apply_fi("liikenaisineen") == "liikenainen"
    assert apply_fi("liikenaisitta") == "liikenainen"
    assert apply_fi("liikenaisemme") == "liikenainen"
    assert apply_fi("liikenaisenne") == "liikenainen"
    assert apply_fi("liikenaisille") == "liikenainen"
    assert apply_fi("liikenaiselta") == "liikenainen"
    assert apply_fi("liikenaisetta") == "liikenainen"
    # other cases
    assert apply_fi("zzzzztteja") == "zzzzztti"


def test_apply_rules():
    """Test rules on all available languages."""
    assert apply_rules("Pfifferlinge", "de", greedy=True) == "Pfifferling"
    assert apply_rules("Pfifferlinge", "en", greedy=True) is None
    assert apply_rules("atonements", "de") is None
    assert apply_rules("atonements", "en") == "atonement"
    assert apply_rules("brieven", "nl") == "brief"
    assert apply_rules("liikenaisessa", "fi") == "liikenainen"
    assert apply_rules("pracowaliście", "pl") == "pracować"
    assert apply_rules("безгра́мотностью", "ru") == "безгра́мотность"
