import json

import pytest

from training import wordlist_ingest
from training.kaikki_to_tsv import extract_pairs, main


def _readme_example_pairs(item):
    """Reference implementation of the naive extraction, used as a happy-path oracle."""
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
    if not pairs and item.get("word"):
        pairs.append((item["word"], item["word"]))
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
def test_matches_reference_extraction_on_happy_path(entry):
    assert list(extract_pairs(entry)) == _readme_example_pairs(entry)


def test_extract_pairs_top_level_form_of():
    """form_of/alt_of can also appear directly on the entry, not nested in a sense."""
    entry = {"word": "Hunde", "form_of": [{"word": "Hund"}]}
    assert list(extract_pairs(entry)) == [("Hund", "Hunde")]


def test_extract_pairs_top_level_alt_of():
    entry = {"word": "colour", "alt_of": [{"word": "color"}]}
    assert list(extract_pairs(entry)) == [("color", "colour")]


def test_extract_pairs_top_level_relation_suppresses_forms_fallback():
    entry = {
        "word": "Hunde",
        "form_of": [{"word": "Hund"}],
        "forms": [{"form": "Hundchen"}],
    }
    assert list(extract_pairs(entry)) == [("Hund", "Hunde")]


def test_extract_pairs_prefers_senses_over_forms():
    entry = {
        "word": "Hunde",
        "senses": [{"form_of": [{"word": "Hund"}]}],
        "forms": [{"form": "Hundchen"}],
    }
    assert list(extract_pairs(entry)) == [("Hund", "Hunde")]


def test_extract_pairs_skips_meta_tagged_forms():
    """table-tags/inflection-template rows are template headers, not word forms."""
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
    """A literal "-" marks a nonexistent form and must be dropped regardless of tags."""
    entry = {
        "word": "gratis",
        "forms": [
            {"form": "-", "tags": ["definite", "some-other-tag"]},
            {"form": "gratis"},
        ],
    }
    assert list(extract_pairs(entry)) == [("gratis", "gratis")]


def test_extract_pairs_skips_error_unrecognized_form_for_tagalog():
    """On Tagalog pages 'error-unrecognized-form' marks unparsed template cells."""
    entry = {
        "lang_code": "tl",
        "word": "akuin",
        "forms": [
            {"form": "ako", "tags": ["error-unrecognized-form"]},
            {"form": "-in", "tags": ["error-unrecognized-form"]},
            {"form": "actor", "tags": ["error-unrecognized-form"]},
            {"form": "inako", "tags": ["completive"]},
        ],
    }
    assert list(extract_pairs(entry)) == [("akuin", "inako")]


def test_extract_pairs_keeps_error_unrecognized_form_for_other_langs():
    """Elsewhere the tag also marks real inflections, like Welsh mutations."""
    entry = {
        "lang_code": "cy",
        "word": "brown",
        "forms": [{"form": "mrown", "tags": ["error-unrecognized-form"]}],
    }
    assert list(extract_pairs(entry)) == [("brown", "mrown")]


def test_extract_pairs_skips_baybayin_forms():
    """A 'Baybayin' row is a script-variant display of the headword, not a form."""
    entry = {
        "word": "akuin",
        "forms": [
            {"form": "ᜀᜃᜓᜁᜈ᜔", "tags": ["Baybayin"]},
            {"form": "inako", "tags": ["completive"]},
        ],
    }
    assert list(extract_pairs(entry)) == [("akuin", "inako")]


def test_extract_pairs_strips_stress_marks_from_forms():
    """Combining stress accents in Cyrillic inflection tables are stripped."""
    entry = {"word": "указ", "forms": [{"form": "у́кази"}]}
    assert list(extract_pairs(entry)) == [("указ", "укази")]


def test_extract_pairs_strips_stress_marks_from_relations():
    entry = {"word": "у́кази", "form_of": [{"word": "у́каз"}]}
    assert list(extract_pairs(entry)) == [("указ", "укази")]


def test_extract_pairs_folds_grc_length_marks_keeping_accents():
    """grc: vowel-length marks are dropped, accents and breathings survive."""
    entry = {
        "lang_code": "grc",
        "word": "σκύλος",
        "forms": [{"form": "σκῠλους"}],  # breve (U+1FE0) length mark on υ
    }
    assert list(extract_pairs(entry)) == [("σκύλος", "σκυλους")]


def test_extract_pairs_does_not_fold_length_marks_for_other_langs():
    """Latvian macron is orthographic, so length folding must not touch it."""
    entry = {"lang_code": "lv", "word": "garš", "forms": [{"form": "garā"}]}
    assert list(extract_pairs(entry)) == [("garš", "garā")]


def test_extract_pairs_keeps_polytonic_greek_accents_from_nfd_input():
    """NFD polytonic Greek keeps its accents: the stress strip targets Cyrillic only."""
    import unicodedata

    word = unicodedata.normalize("NFD", "ἄνθρωπος")
    form = unicodedata.normalize("NFD", "ἀνθρώπους")
    entry = {"word": word, "forms": [{"form": form}]}
    assert list(extract_pairs(entry)) == [("ἄνθρωπος", "ἀνθρώπους")]


def test_extract_pairs_skips_romanization_forms():
    """A 'romanization' row transliterates the headword, it's not an inflected form."""
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
    """A 'class' row is a verb-conjugation-class label, not a word form."""
    entry = {
        "word": "sehen",
        "forms": [
            {"form": "5 strong", "tags": ["class"]},
            {"form": "sieht", "tags": ["present"]},
        ],
    }
    assert list(extract_pairs(entry)) == [("sehen", "sieht")]


def test_extract_pairs_skips_pronoun_cross_reference():
    """A cross-referenced 'pronoun' row is dropped, the identity pair survives."""
    entry = {
        "word": "er",
        "forms": [
            {"form": "ich", "tags": ["pronoun", "first-person"]},
            {"form": "er", "tags": ["pronoun", "third-person", "masculine"]},
        ],
    }
    assert list(extract_pairs(entry)) == [("er", "er")]


def test_extract_pairs_skips_possessive_cross_reference():
    """Same pathology as the pronoun template, for 'possessive' rows."""
    entry = {
        "word": "sein",
        "forms": [
            {"form": "mein", "tags": ["possessive", "first-person"]},
            {"form": "sein", "tags": ["possessive", "third-person"]},
        ],
    }
    assert list(extract_pairs(entry)) == [("sein", "sein")]


def test_extract_pairs_skips_auxiliary_cross_reference():
    """An 'auxiliary' row names a helper verb, so the entry falls back to identity."""
    entry = {"word": "ausgehen", "forms": [{"form": "sein", "tags": ["auxiliary"]}]}
    assert list(extract_pairs(entry)) == [("ausgehen", "ausgehen")]

    entry = {"word": "sein", "forms": [{"form": "sein", "tags": ["auxiliary"]}]}
    assert list(extract_pairs(entry)) == [("sein", "sein")]


def test_extract_pairs_emits_all_form_of_targets():
    """A multi-target form_of must not silently discard candidates after the first."""
    entry = {
        "word": "colour",
        "senses": [{"form_of": [{"word": "color"}, {"word": "colour2"}]}],
    }
    assert list(extract_pairs(entry)) == [("color", "colour"), ("colour2", "colour")]


def test_extract_pairs_emits_all_alt_of_targets():
    entry = {"word": "x", "alt_of": [{"word": "a"}, {"word": "b"}, {"word": "c"}]}
    assert list(extract_pairs(entry)) == [("a", "x"), ("b", "x"), ("c", "x")]


def test_extract_pairs_skips_targets_missing_word_but_keeps_others():
    entry = {"word": "x", "form_of": [{}, {"word": "y"}]}
    assert list(extract_pairs(entry)) == [("y", "x")]


def test_extract_pairs_dedups_repeated_pair_across_senses():
    """Senses repeating a pair are one attestation, so one entry yields one line."""
    entry = {
        "word": "Hunde",
        "senses": [
            {"form_of": [{"word": "Hund"}]},
            {"form_of": [{"word": "Hund"}]},
        ],
    }
    assert list(extract_pairs(entry)) == [("Hund", "Hunde")]


def test_extract_pairs_dedup_preserves_first_seen_order():
    entry = {
        "word": "x",
        "senses": [
            {"form_of": [{"word": "b"}]},
            {"form_of": [{"word": "a"}]},
            {"form_of": [{"word": "b"}]},
        ],
    }
    assert list(extract_pairs(entry)) == [("b", "x"), ("a", "x")]


def test_extract_pairs_dedup_does_not_affect_forms_fallback_duplicates():
    """Repeated forms in the forms fallback still dedup."""
    entry = {"word": "x", "forms": [{"form": "y"}, {"form": "y"}]}
    assert list(extract_pairs(entry)) == [("x", "y")]


def test_extract_pairs_handles_missing_data():
    assert list(extract_pairs({})) == []
    assert list(extract_pairs({"word": "x", "senses": [{}]})) == [("x", "x")]
    assert list(extract_pairs({"word": "x", "senses": [{"form_of": []}]})) == [
        ("x", "x")
    ]
    assert list(extract_pairs({"word": "x", "forms": [{}]})) == [("x", "x")]
    assert list(extract_pairs({"word": "x", "form_of": []})) == [("x", "x")]


def test_extract_pairs_identity_for_uninflected_headword():
    """A headword with no forms and no relations is its own identity pair."""
    assert list(extract_pairs({"word": "μέν"})) == [("μέν", "μέν")]


def test_extract_pairs_no_identity_after_junk_form_drop():
    """An entry with only dropped junk forms must not fall back to identity."""
    entry = {"word": "plants", "forms": [{"form": "plánts", "tags": ["romanization"]}]}
    assert list(extract_pairs(entry)) == []
    entry = {"word": "x", "forms": [{"form": "y", "tags": ["table-tags"]}]}
    assert list(extract_pairs(entry)) == []


def test_extract_pairs_expands_optional_letter_group():
    """A single optional group like grc 'ἦ(ν)' expands to both spellings."""
    entry = {"word": "εἰμί", "forms": [{"form": "ἦ(ν)"}]}
    assert list(extract_pairs(entry)) == [("εἰμί", "ἦ"), ("εἰμί", "ἦν")]

    entry = {"word": "hoten", "forms": [{"form": "(y)hote"}]}
    assert list(extract_pairs(entry)) == [("hoten", "hote"), ("hoten", "yhote")]

    entry = {"word": "x", "forms": [{"form": "a(b/c)"}, {"form": "a(b)c(d)"}]}
    assert list(extract_pairs(entry)) == [("x", "a(b/c)"), ("x", "a(b)c(d)")]


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


def test_output_is_valid_builder_input(tmp_path):
    """The produced TSV must be directly consumable by wordlist_ingest."""
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

    result = wordlist_ingest.read_wordlist(list_path, "de")
    assert result["Hunde"] == "Hund"
    assert result["Katzen"] == "Katze"
