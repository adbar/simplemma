from conllu import parse

from training.ud_conllu import (
    canon_lemma,
    dataset_to_lang,
    iter_word_tokens_in_sentences,
)

# id 3.1 = an empty node (enhanced deps) carrying a REAL lemma; id 1-2 = an MWT
# span (lemma "_"). Only the four real word tokens must be yielded.
CONLLU = (
    "1-2\tdunno\t_\t_\t_\t_\t_\t_\t_\t_\n"
    "1\tDo\tdo\tAUX\t_\t_\t0\troot\t_\t_\n"
    "2\tnot\tnot\tPART\t_\t_\t1\tadvmod\t_\t_\n"
    "3\tknow\tknow\tVERB\t_\t_\t1\txcomp\t_\t_\n"
    "3.1\tknow\tknow\tVERB\t_\t_\t_\t_\t_\t_\n"  # empty node, real lemma
    "4\tit\tit\tPRON\t_\t_\t3\tobj\t_\t_\n\n"
)


def test_iter_word_tokens_skips_mwt_and_empty_nodes():
    forms = [f for f, _ in iter_word_tokens_in_sentences(parse(CONLLU), "en")]
    # "dunno" (MWT span) and the 3.1 empty node are both excluded
    assert forms == ["do", "not", "know", "it"]


def test_iter_word_tokens_lowercases_sentence_initial_only():
    forms = dict(
        (t["id"], f) for f, t in iter_word_tokens_in_sentences(parse(CONLLU), "en")
    )
    assert forms[1] == "do"  # id==1 lowered ("Do" -> "do")
    assert forms[3] == "know"  # non-initial kept as-is


def test_iter_word_tokens_canonicalizes_lemma_for_lang():
    """The gold LEMMA (not the form) is canonicalized for `lang` in place, so
    every reader (eval harnesses + build_override) compares/mines in the
    shipped dict's key space. Here: ar vocalized gold -> unvocalized."""
    conllu = "1\tكتاب\tكِتَاب\tNOUN\t_\t_\t0\troot\t_\t_\n\n"
    ((form, token),) = list(iter_word_tokens_in_sentences(parse(conllu), "ar"))
    assert token["lemma"] == "كتاب"  # vocalization stripped
    assert form == "كتاب"  # form left as-is (already unvocalized real text)
    # no-op for a language without a canon table
    ((_, token2),) = list(iter_word_tokens_in_sentences(parse(conllu), "en"))
    assert token2["lemma"] == "كِتَاب"


# Constructed fixture, but the artifact pattern is real: he_htb marks the
# elided side of a split bound morpheme with a leading/trailing underscore
# on form and/or lemma (e.g. real he_htb rows: form='יכולת_' lemma='יכולת').
MWT_ARTIFACT_CONLLU = (
    "1-2\tשיכולת\t_\t_\t_\t_\t_\t_\t_\t_\n"
    "1\tש\tש_\tSCONJ\t_\t_\t2\tmark\t_\t_\n"
    "2\tיכולת\t_יכולת\tNOUN\t_\t_\t0\troot\t_\t_\n\n"
)


def test_iter_word_tokens_strips_mwt_artifact_from_form_and_lemma():
    results = list(iter_word_tokens_in_sentences(parse(MWT_ARTIFACT_CONLLU), "he"))
    forms = [f for f, _ in results]
    lemmas = [t["lemma"] for _, t in results]
    assert forms == ["ש", "יכולת"]  # the MWT span itself is skipped, not yielded
    assert lemmas == ["ש", "יכולת"]  # artifact stripped from both sides


def test_iter_word_tokens_mutates_token_form_in_place():
    """Direct readers of token["form"] (not just the yielded tuple) must see
    the stripped value too -- evaluate_simplemma's baseline check relies on this."""
    _, token = next(iter_word_tokens_in_sentences(parse(MWT_ARTIFACT_CONLLU), "he"))
    assert token["form"] == "ש"


def test_iter_word_tokens_null_marker_unaffected_by_strip():
    """The CoNLL-U null value '_' itself (not an artifact-wrapped real value)
    must not be touched -- this is what the lemma=='_' skip check depends on."""
    forms = [f for f, _ in iter_word_tokens_in_sentences(parse(CONLLU), "en")]
    assert forms == ["do", "not", "know", "it"]  # unchanged: no artifact present


def test_iter_word_tokens_underscore_run_form_survives():
    """A real underscore-run PUNCT token (et_ewt '________') must not strip
    to an empty form -- an empty string crashes the Lemmatizer input check."""
    conllu = "1\t____\t____\tPUNCT\t_\t_\t0\tpunct\t_\t_\n\n"
    (form, token), *_ = iter_word_tokens_in_sentences(parse(conllu), "et")
    assert form == "____" and token["lemma"] == "____"


def test_canon_lemma_strips_compound_separators():
    assert canon_lemma("yli#opisto", "yliopisto", "fi") == "yliopisto"
    assert canon_lemma("sisse_tulek", "sissetulek", "et") == "sissetulek"
    assert canon_lemma("el+mond", "elmond", "hu") == "elmond"
    # nl untouched
    assert canon_lemma("klooster_orde", "kloosterorde", "nl") == "klooster_orde"


def test_canon_lemma_keeps_marker_present_in_the_form():
    """A marker in the surface form is token content, not annotation
    (real UD rows: fi '#luonto', et 'MAX_FILE_SIZE', hu '16+3')."""
    assert canon_lemma("#luonto", "#luonto", "fi") == "#luonto"
    assert canon_lemma("MAX_FILE_SIZE", "MAX_FILE_SIZE", "et") == "MAX_FILE_SIZE"
    assert canon_lemma("16+3", "16+3", "hu") == "16+3"
    # the gate compares MWT-stripped, so a he-style artifact can't defeat it
    assert canon_lemma("20_000_", "_20_000", "et") == "20_000"


def test_canon_lemma_keeps_marker_per_occurrence_on_inflected_forms():
    """Per-occurrence, not whole-string equality: an inflected form keeps the
    edge marker it carries ('#oscarit' / '#Oscar' -- equality testing
    corrupted 45 fi/et gold rows), internal compound markers still go."""
    assert canon_lemma("#Oscar", "#oscarit", "fi") == "#Oscar"
    assert canon_lemma("#luonto#kuva", "#luontokuvan", "fi") == "#luontokuva"
    # no marker in the form at all: the lemma's markers are annotation
    assert canon_lemma("#yli#opisto", "yliopistot", "fi") == "yliopisto"


def test_canon_lemma_trailing_edge_marker_follows_the_form():
    """A trailing marker run survives only when the form also ends with the
    marker; otherwise it strips with the internal ones (mirror of the
    '#oscarit' leading-edge rule)."""
    assert canon_lemma("Oscar#", "oscarit#", "fi") == "Oscar#"
    assert canon_lemma("Oscar#", "oscarit", "fi") == "Oscar"
    assert canon_lemma("yli#opisto#", "yliopistot", "fi") == "yliopisto"


def test_canon_lemma_never_strips_a_lemma_to_nothing():
    """An all-marker lemma whose form differs would strip to '' and score every
    prediction wrong. Unreachable in UD 2.18, guarded anyway."""
    assert canon_lemma("###", "hashtags", "fi") == "###"
    assert canon_lemma("+++", "plusses", "hu") == "+++"


def test_dataset_to_lang_overrides_and_default():
    assert dataset_to_lang("no_nynorsk") == "nn"  # override
    assert dataset_to_lang("sme_giella") == "se"  # override
    assert dataset_to_lang("hr_set") == "hbs"  # override (both BCS sets)
    assert dataset_to_lang("sr_set") == "hbs"  # override
    assert dataset_to_lang("ro_rrt") == "ro"  # prefix default
    assert dataset_to_lang("en") == "en"  # no separator
