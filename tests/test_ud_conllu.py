from conllu import parse

from training.ud_conllu import (
    canon_lemma,
    dataset_to_lang,
    iter_word_tokens_in_sentences,
)

# 3.1 is an empty node with a real lemma and 1-2 an MWT span, both skipped
CONLLU = (
    "1-2\tdunno\t_\t_\t_\t_\t_\t_\t_\t_\n"
    "1\tDo\tdo\tAUX\t_\t_\t0\troot\t_\t_\n"
    "2\tnot\tnot\tPART\t_\t_\t1\tadvmod\t_\t_\n"
    "3\tknow\tknow\tVERB\t_\t_\t1\txcomp\t_\t_\n"
    "3.1\tknow\tknow\tVERB\t_\t_\t_\t_\t_\t_\n"
    "4\tit\tit\tPRON\t_\t_\t3\tobj\t_\t_\n\n"
)


def test_iter_word_tokens_skips_mwt_and_empty_nodes():
    forms = [f for f, _ in iter_word_tokens_in_sentences(parse(CONLLU), "en")]
    assert forms == ["do", "not", "know", "it"]


def test_iter_word_tokens_lowercases_sentence_initial_only():
    forms = dict(
        (t["id"], f) for f, t in iter_word_tokens_in_sentences(parse(CONLLU), "en")
    )
    assert forms[1] == "do"
    assert forms[3] == "know"


def test_iter_word_tokens_canonicalizes_lemma_for_lang():
    """The gold lemma, not the form, is canonicalized for lang in place."""
    conllu = "1\tكتاب\tكِتَاب\tNOUN\t_\t_\t0\troot\t_\t_\n\n"
    ((form, token),) = list(iter_word_tokens_in_sentences(parse(conllu), "ar"))
    assert token["lemma"] == "كتاب"  # vocalization stripped
    assert form == "كتاب"
    # no-op without a canon table
    ((_, token2),) = list(iter_word_tokens_in_sentences(parse(conllu), "en"))
    assert token2["lemma"] == "كِتَاب"


# he treebanks mark the elided side of a split morpheme with an edge underscore
MWT_ARTIFACT_CONLLU = (
    "1-2\tשיכולת\t_\t_\t_\t_\t_\t_\t_\t_\n"
    "1\tש\tש_\tSCONJ\t_\t_\t2\tmark\t_\t_\n"
    "2\tיכולת\t_יכולת\tNOUN\t_\t_\t0\troot\t_\t_\n\n"
)


def test_iter_word_tokens_strips_mwt_artifact_from_form_and_lemma():
    results = list(iter_word_tokens_in_sentences(parse(MWT_ARTIFACT_CONLLU), "he"))
    forms = [f for f, _ in results]
    lemmas = [t["lemma"] for _, t in results]
    assert forms == ["ש", "יכולת"]
    assert lemmas == ["ש", "יכולת"]


def test_iter_word_tokens_mutates_token_form_in_place():
    """Readers of token["form"] see the stripped value too."""
    _, token = next(iter_word_tokens_in_sentences(parse(MWT_ARTIFACT_CONLLU), "he"))
    assert token["form"] == "ש"


def test_iter_word_tokens_null_marker_unaffected_by_strip():
    """The CoNLL-U null value '_' is not an artifact and stays untouched."""
    forms = [f for f, _ in iter_word_tokens_in_sentences(parse(CONLLU), "en")]
    assert forms == ["do", "not", "know", "it"]


def test_iter_word_tokens_underscore_run_form_survives():
    """An underscore-run PUNCT token must not strip to an empty form."""
    conllu = "1\t____\t____\tPUNCT\t_\t_\t0\tpunct\t_\t_\n\n"
    (form, token), *_ = iter_word_tokens_in_sentences(parse(conllu), "et")
    assert form == "____" and token["lemma"] == "____"


def test_canon_lemma_strips_compound_separators():
    assert canon_lemma("yli#opisto", "yliopisto", "fi") == "yliopisto"
    assert canon_lemma("sisse_tulek", "sissetulek", "et") == "sissetulek"
    assert canon_lemma("el+mond", "elmond", "hu") == "elmond"
    assert canon_lemma("klooster_orde", "kloosterorde", "nl") == "klooster_orde"


def test_canon_lemma_folds_apostrophes_like_the_runtime():
    assert canon_lemma("Chomksy’ye", "Chomksy’ye", "tr") == "Chomksy'ye"


def test_canon_lemma_keeps_marker_present_in_the_form():
    """A marker in the surface form is token content, not annotation."""
    assert canon_lemma("#luonto", "#luonto", "fi") == "#luonto"
    assert canon_lemma("MAX_FILE_SIZE", "MAX_FILE_SIZE", "et") == "MAX_FILE_SIZE"
    assert canon_lemma("16+3", "16+3", "hu") == "16+3"
    # MWT artifacts strip first, so they cannot defeat the gate
    assert canon_lemma("20_000_", "_20_000", "et") == "20_000"


def test_canon_lemma_keeps_marker_per_occurrence_on_inflected_forms():
    """Edge markers the inflected form carries stay, internal compound markers go."""
    assert canon_lemma("#Oscar", "#oscarit", "fi") == "#Oscar"
    assert canon_lemma("#luonto#kuva", "#luontokuvan", "fi") == "#luontokuva"
    # no marker in the form at all: the lemma's markers are annotation
    assert canon_lemma("#yli#opisto", "yliopistot", "fi") == "yliopisto"


def test_canon_lemma_trailing_edge_marker_follows_the_form():
    """A trailing marker survives only when the form also ends with it."""
    assert canon_lemma("Oscar#", "oscarit#", "fi") == "Oscar#"
    assert canon_lemma("Oscar#", "oscarit", "fi") == "Oscar"
    assert canon_lemma("yli#opisto#", "yliopistot", "fi") == "yliopisto"


def test_canon_lemma_never_strips_a_lemma_to_nothing():
    """An all-marker lemma is kept rather than stripped to an empty string."""
    assert canon_lemma("###", "hashtags", "fi") == "###"
    assert canon_lemma("+++", "plusses", "hu") == "+++"


def test_dataset_to_lang_overrides_and_default():
    assert dataset_to_lang("no_nynorsk") == "nn"
    assert dataset_to_lang("sme_giella") == "se"
    assert dataset_to_lang("hr_set") == "hbs"
    assert dataset_to_lang("sr_set") == "hbs"
    assert dataset_to_lang("ro_rrt") == "ro"
    assert dataset_to_lang("en") == "en"
