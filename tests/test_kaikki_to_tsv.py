import json

import pytest

from training import dictionary_pickler
from training.kaikki_to_tsv import extract_pairs, main


def _readme_example_pairs(item):
    """Faithful transcription of training/README.rst's extraction example.

    Used as a differential oracle against `extract_pairs` on well-formed
    input, to confirm the two share the same core mapping logic.
    """
    pairs = []
    i = 0
    if "senses" in item:
        for s in item["senses"]:
            if "form_of" in s and item["word"]:
                i += 1
                pairs.append((s["form_of"][0]["word"], item["word"]))
            elif "alt_of" in s and item["word"]:
                i += 1
                pairs.append((s["alt_of"][0]["word"], item["word"]))
    if i == 0 and "forms" in item:
        for f in item["forms"]:
            if f["form"]:
                pairs.append((item["word"], f["form"]))
    return pairs


@pytest.mark.parametrize(
    "entry",
    [
        {"word": "Hunde", "senses": [{"form_of": [{"word": "Hund"}]}]},
        {"word": "colour", "senses": [{"alt_of": [{"word": "color"}]}]},
        {"word": "Hund", "forms": [{"form": "Hunde"}, {"form": "Hundes"}]},
        {
            "word": "run",
            "senses": [{"glosses": ["to move fast"]}, {"form_of": [{"word": "run"}]}],
        },
        {
            "word": "flavor",
            "senses": [
                {"form_of": [{"word": "flavour"}], "alt_of": [{"word": "flavour2"}]}
            ],
        },
        {
            "word": "cat",
            "senses": [{"glosses": ["a feline"]}],
            "forms": [{"form": "cats"}],
        },
        {"word": "lonely"},
        {"word": "empty_senses", "senses": [], "forms": [{"form": "x"}]},
    ],
)
def test_matches_readme_example_on_happy_path(entry):
    """extract_pairs must agree with the README's example on well-formed input.

    The two are known to diverge on malformed entries (extract_pairs is
    crash-safe via `.get()`, the README example is not) and on meta-tagged
    forms (extract_pairs filters `table-tags` noise, the README example
    does not) — both intentional improvements, out of scope here.
    """
    assert list(extract_pairs(entry)) == _readme_example_pairs(entry)


def test_extract_pairs_form_of():
    entry = {"word": "Hunde", "senses": [{"form_of": [{"word": "Hund"}]}]}
    assert list(extract_pairs(entry)) == [("Hund", "Hunde")]


def test_extract_pairs_alt_of():
    entry = {"word": "colour", "senses": [{"alt_of": [{"word": "color"}]}]}
    assert list(extract_pairs(entry)) == [("color", "colour")]


def test_extract_pairs_forms_fallback():
    entry = {"word": "Hund", "forms": [{"form": "Hunde"}, {"form": "Hundes"}]}
    assert list(extract_pairs(entry)) == [("Hund", "Hunde"), ("Hund", "Hundes")]


def test_extract_pairs_top_level_form_of():
    """form_of/alt_of can also appear directly on the entry, not just nested
    in a sense (kaikki.org's WordData schema declares both places)."""
    entry = {"word": "Hunde", "form_of": [{"word": "Hund"}]}
    assert list(extract_pairs(entry)) == [("Hund", "Hunde")]


def test_extract_pairs_top_level_alt_of():
    entry = {"word": "colour", "alt_of": [{"word": "color"}]}
    assert list(extract_pairs(entry)) == [("color", "colour")]


def test_extract_pairs_top_level_relation_suppresses_forms_fallback():
    entry = {
        "word": "Hunde",
        "form_of": [{"word": "Hund"}],
        "forms": [{"form": "Hundchen"}],  # would be wrong if used as fallback
    }
    assert list(extract_pairs(entry)) == [("Hund", "Hunde")]


def test_extract_pairs_prefers_senses_over_forms():
    entry = {
        "word": "Hunde",
        "senses": [{"form_of": [{"word": "Hund"}]}],
        "forms": [{"form": "Hundchen"}],  # ignored: senses already matched
    }
    assert list(extract_pairs(entry)) == [("Hund", "Hunde")]


def test_extract_pairs_skips_meta_tagged_forms():
    """table-tags and inflection-template rows are table/template headers,
    not real word forms — confirmed on a real kaikki.org Romanian entry."""
    entry = {
        "word": "Hund",
        "forms": [
            {"form": "no-table-tags", "tags": ["table-tags"]},
            {"form": "de-noun-n-e", "tags": ["inflection-template"]},
            {"form": "Hunde"},
        ],
    }
    assert list(extract_pairs(entry)) == [("Hund", "Hunde")]


def test_extract_pairs_skips_placeholder_form():
    """A literal "-" marks a form that doesn't exist for this word (e.g. an
    adjective with no definite form) — must be dropped regardless of tags,
    unlike "error-unrecognized-form" itself which mostly flags real forms."""
    entry = {
        "word": "gratis",
        "forms": [
            {"form": "-", "tags": ["definite", "error-unrecognized-form"]},
            {"form": "gratis", "tags": ["error-unrecognized-form"]},
        ],
    }
    assert list(extract_pairs(entry)) == [("gratis", "gratis")]


def test_extract_pairs_strips_stress_marks_from_forms():
    """Bulgarian/Russian/Ukrainian mark stress with combining accents in
    inflection tables (never in the page title) — confirmed on a real
    kaikki.org Bulgarian entry ('указ' -> 'у́кази', combining U+0301)."""
    entry = {"word": "указ", "forms": [{"form": "у́кази"}]}
    assert list(extract_pairs(entry)) == [("указ", "укази")]


def test_extract_pairs_strips_stress_marks_from_relations():
    entry = {"word": "у́кази", "form_of": [{"word": "у́каз"}]}
    assert list(extract_pairs(entry)) == [("указ", "укази")]


def test_extract_pairs_skips_romanization_forms():
    """A 'romanization' row transliterates the headword into Latin script
    instead of giving a real inflected form — confirmed on a real
    kaikki.org Bulgarian entry ('указ' -> 'úkaz', tagged only 'romanization')."""
    entry = {
        "word": "указ",
        "forms": [
            {"form": "úkaz", "tags": ["romanization"]},
            {"form": "у́кази", "tags": ["indefinite", "plural"]},
        ],
    }
    assert list(extract_pairs(entry)) == [("указ", "укази")]


def test_extract_pairs_skips_transliteration_forms():
    entry = {
        "word": "x",
        "forms": [{"form": "y", "tags": ["transliteration"]}, {"form": "z"}],
    }
    assert list(extract_pairs(entry)) == [("x", "z")]


def test_extract_pairs_skips_class_forms():
    """A 'class' row is a verb-conjugation-class label, not a word form —
    confirmed on a real kaikki.org German entry ('sehen' -> '5 strong')."""
    entry = {
        "word": "sehen",
        "forms": [
            {"form": "5 strong", "tags": ["class"]},
            {"form": "sieht", "tags": ["present"]},
        ],
    }
    assert list(extract_pairs(entry)) == [("sehen", "sieht")]


def test_extract_pairs_skips_pronoun_cross_reference():
    """German's personal-pronoun overview template lists every pronoun as
    a cross-referenced cell on each pronoun's own page — confirmed on a
    real kaikki.org German entry ('er' listing 'ich' as tagged 'pronoun').
    Only the cross-reference is dropped; the entry's own identity survives."""
    entry = {
        "word": "er",
        "forms": [
            {"form": "ich", "tags": ["pronoun", "first-person"]},
            {"form": "er", "tags": ["pronoun", "third-person", "masculine"]},
        ],
    }
    assert list(extract_pairs(entry)) == [("er", "er")]


def test_extract_pairs_skips_possessive_cross_reference():
    """Same pathology for the possessive-determiner overview template —
    confirmed on a real kaikki.org German entry ('sein' listing 'mein')."""
    entry = {
        "word": "sein",
        "forms": [
            {"form": "mein", "tags": ["possessive", "first-person"]},
            {"form": "sein", "tags": ["possessive", "third-person"]},
        ],
    }
    assert list(extract_pairs(entry)) == [("sein", "sein")]


def test_extract_pairs_skips_auxiliary_cross_reference():
    """An 'auxiliary' row names the verb ('sein'/'haben') used to build the
    perfect tense, not an inflected form — confirmed on a real kaikki.org
    German entry ('ausgehen' -> 'sein'). A verb using itself as its own
    auxiliary ('sein' -> 'sein') is a real self-mapping and must survive."""
    entry = {"word": "ausgehen", "forms": [{"form": "sein", "tags": ["auxiliary"]}]}
    assert list(extract_pairs(entry)) == []

    entry = {"word": "sein", "forms": [{"form": "sein", "tags": ["auxiliary"]}]}
    assert list(extract_pairs(entry)) == [("sein", "sein")]


def test_extract_pairs_handles_missing_data():
    assert list(extract_pairs({})) == []
    assert list(extract_pairs({"word": "x", "senses": [{}]})) == []
    assert list(extract_pairs({"word": "x", "senses": [{"form_of": []}]})) == []
    assert list(extract_pairs({"word": "x", "forms": [{}]})) == []
    assert list(extract_pairs({"word": "x", "form_of": []})) == []


def test_main_writes_tsv(tmp_path):
    input_path = tmp_path / "kaikki.json"
    entries = [
        {"word": "Hunde", "senses": [{"form_of": [{"word": "Hund"}]}]},
        {"word": "Hund", "forms": [{"form": "Hundes"}]},
    ]
    input_path.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8"
    )
    output_path = tmp_path / "de.txt"

    main(input_path, output_path)

    assert output_path.read_text(encoding="utf-8") == "Hund\tHunde\nHund\tHundes\n"


def test_main_preserves_unicode(tmp_path):
    input_path = tmp_path / "kaikki.json"
    entry = {"word": "Bäckerei", "forms": [{"form": "Bäckereien"}]}
    input_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    output_path = tmp_path / "de.txt"

    main(input_path, output_path)

    assert output_path.read_text(encoding="utf-8") == "Bäckerei\tBäckereien\n"


def test_output_is_valid_pickler_input(tmp_path):
    """The produced TSV must be directly consumable by dictionary_pickler."""
    input_path = tmp_path / "kaikki.json"
    entries = [
        {"word": "Hunde", "senses": [{"form_of": [{"word": "Hund"}]}]},
        {"word": "Katzen", "senses": [{"form_of": [{"word": "Katze"}]}]},
    ]
    input_path.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8"
    )
    list_path = tmp_path / "de.txt"
    main(input_path, list_path)

    result = dictionary_pickler._read_dict(str(list_path), "de", silent=True)
    assert result[b"Hunde"] == b"Hund"
    assert result[b"Katzen"] == b"Katze"
