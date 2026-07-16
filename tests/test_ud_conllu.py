from conllu import parse

from training.ud_conllu import dataset_to_lang, iter_word_tokens_in_sentences

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
    forms = [f for f, _ in iter_word_tokens_in_sentences(parse(CONLLU))]
    # "dunno" (MWT span) and the 3.1 empty node are both excluded
    assert forms == ["do", "not", "know", "it"]


def test_iter_word_tokens_lowercases_sentence_initial_only():
    forms = dict((t["id"], f) for f, t in iter_word_tokens_in_sentences(parse(CONLLU)))
    assert forms[1] == "do"  # id==1 lowered ("Do" -> "do")
    assert forms[3] == "know"  # non-initial kept as-is


def test_dataset_to_lang_overrides_and_default():
    assert dataset_to_lang("no_nynorsk") == "nn"  # override
    assert dataset_to_lang("sme_giella") == "se"  # override
    assert dataset_to_lang("ro_rrt") == "ro"  # prefix default
    assert dataset_to_lang("en") == "en"  # no separator
