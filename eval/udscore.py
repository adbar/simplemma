import csv
import time

from collections import Counter
from os import path

from conllu import parse_incr  # type: ignore
from simplemma import Lemmatizer
from simplemma.strategies.dictionaries import DefaultDictionaryFactory
from simplemma.strategies.default import DefaultStrategy


data_files = [
    ("bg", "tests/UD/bg-btb-all.conllu"),
    ("cs", "tests/UD/cs-pdt-all.conllu"),  # longer to process
    ("da", "tests/UD/da-ddt-all.conllu"),
    ("de", "tests/UD/de-gsd-all.conllu"),
    ("el", "tests/UD/el-gdt-all.conllu"),
    ("en", "tests/UD/en-gum-all.conllu"),
    ("es", "tests/UD/es-gsd-all.conllu"),
    ("et", "tests/UD/et-edt-all.conllu"),
    ("fi", "tests/UD/fi-tdt-all.conllu"),
    ("fr", "tests/UD/fr-gsd-all.conllu"),
    ("ga", "tests/UD/ga-idt-all.conllu"),
    ("hi", "tests/UD/hi-hdtb-all.conllu"),
    ("hu", "tests/UD/hu-szeged-all.conllu"),
    ("hy", "tests/UD/hy-armtdp-all.conllu"),
    ("id", "tests/UD/id-csui-all.conllu"),
    ("it", "tests/UD/it-isdt-all.conllu"),
    ("la", "tests/UD/la-proiel-all.conllu"),
    ("lt", "tests/UD/lt-alksnis-all.conllu"),
    ("lv", "tests/UD/lv-lvtb-all.conllu"),
    ("nb", "tests/UD/nb-bokmaal-all.conllu"),
    ("nl", "tests/UD/nl-alpino-all.conllu"),
    ("pl", "tests/UD/pl-pdb-all.conllu"),
    ("pt", "tests/UD/pt-gsd-all.conllu"),
    ("ru", "tests/UD/ru-gsd-all.conllu"),
    ("sk", "tests/UD/sk-snk-all.conllu"),
    ("tr", "tests/UD/tr-boun-all.conllu"),
]

# doesn't work: right-to-left?
# data_files = [
#              ('he', 'tests/UD/he-htb-all.conllu'),
#              ('ur', 'tests/UD/ur-udtb-all.conllu'),
# ]

# data_files = [
#             ('de', 'tests/UD/de-gsd-all.conllu'),
#]


for filedata in data_files:
    total, focus_total, _greedy, nongreedy, zero, focus_zero, focus, focus_nongreedy = (
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    errors, flag = [], False
    language, filename = filedata[0], filedata[1]

    start = time.time()
    _dictionary_factory = DefaultDictionaryFactory()
    strategies = DefaultStrategy(greedy=False)
    lemmatizer = Lemmatizer(
        lemmatization_strategy=DefaultStrategy(
            greedy=False, dictionary_factory=_dictionary_factory
        ),
    )
    greedy_lemmatizer = Lemmatizer(
        lemmatization_strategy=DefaultStrategy(
            greedy=True, dictionary_factory=_dictionary_factory
        ),
    )
    print("==", filedata, "==")
    with open(filename, "r", encoding="utf-8") as data_file:
        for tokenlist in parse_incr(data_file):
            for token in tokenlist:
                error_flag = False
                if token["lemma"] == "_":  # or token['upos'] in ('PUNCT', 'SYM')
                    # flag = True
                    continue

                initial = bool(token["id"] == 1)
                token_form = token["form"].lower() if initial else token["form"]

                candidate = lemmatizer.lemmatize(token_form, lang=language)
                greedy_candidate = greedy_lemmatizer.lemmatize(token_form, lang=language)

                if token["upos"] in ("ADJ", "NOUN"):
                    focus_total += 1
                    if token["form"] == token["lemma"]:
                        focus_zero += 1
                    if greedy_candidate == token["lemma"]:
                        focus += 1
                    if candidate == token["lemma"]:
                        focus_nongreedy += 1
                total += 1
                if token["form"] == token["lemma"]:
                    zero += 1
                if greedy_candidate == token["lemma"]:
                    _greedy += 1
                else:
                    error_flag = True
                if candidate == token["lemma"]:
                    nongreedy += 1
                else:
                    error_flag = True
                if error_flag:
                    errors.append(
                        (token["form"], token["lemma"], candidate, greedy_candidate)
                    )
    with open(
        f'{path.basename(filename).replace("conllu","csv")}', "w", encoding="utf-8"
    ) as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(("form", "lemma", "candidate", "greedy_candidate"))
        writer.writerows(errors)

    print("exec time:\t %.3f" % (time.time() - start))
    print("token count:\t", total)
    print("greedy:\t\t %.3f" % (_greedy / total))
    print("non-greedy:\t %.3f" % (nongreedy / total))
    print("baseline:\t %.3f" % (zero / total))
    print("ADJ+NOUN greedy:\t\t %.3f" % (focus / focus_total))
    print("ADJ+NOUN non-greedy:\t\t %.3f" % (focus_nongreedy / focus_total))
    print("ADJ+NOUN baseline:\t\t %.3f" % (focus_zero / focus_total))
    mycounter = Counter(errors)
    print(mycounter.most_common(20))
