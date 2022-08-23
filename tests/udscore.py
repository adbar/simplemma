import time

from collections import Counter

from conllu import parse_incr
from simplemma import lemmatize


data_files = [
    ("bg", "tests/UD/bg-btb-all.conllu"),
    #              ('cs', 'tests/UD/cs-pdt-all.conllu'),
    ("da", "tests/UD/da-ddt-all.conllu"),
    ("de", "tests/UD/de-gsd-all.conllu"),
    ("el", "tests/UD/el-gdt-all.conllu"),
    ("en", "tests/UD/en-gum-all.conllu"),
    ("es", "tests/UD/es-gsd-all.conllu"),
    ("et", "tests/UD/et-edt-all.conllu"),
    ("fi", "tests/UD/fi-tdt-all.conllu"),
    ("fr", "tests/UD/fr-gsd-all.conllu"),
    ("ga", "tests/UD/ga-idt-all.conllu"),
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
#              ('hi', 'tests/UD/hi-hdtb-all.conllu'),
#              ('ur', 'tests/UD/ur-udtb-all.conllu'),
# ]

# data_files = [
#              ('de', 'tests/UD/de-gsd-all.conllu'),
# ]


for filedata in data_files:
    total, nonprototal, greedy, nongreedy, zero, zerononpro, nonpro, nongreedynonpro = (
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
    language = filedata[0]
    data_file = open(filedata[1], "r", encoding="utf-8")
    start = time.time()
    print("==", filedata, "==")
    for tokenlist in parse_incr(data_file):
        for token in tokenlist:
            if token["lemma"] == "_":  #  or token['upos'] in ('PUNCT', 'SYM')
                #    flag = True
                continue

            initial = token["id"] == 1
            greedy_candidate = lemmatize(
                token["form"], lang=language, greedy=True, initial=initial
            )
            candidate = lemmatize(
                token["form"], lang=language, greedy=False, initial=initial
            )

            if token["upos"] in ("ADJ", "NOUN"):
                nonprototal += 1
                if token["form"] == token["lemma"]:
                    zerononpro += 1
                if greedy_candidate == token["lemma"]:
                    nonpro += 1
                if candidate == token["lemma"]:
                    nongreedynonpro += 1
                    # if len(token['lemma']) < 3:
                    #    print(token['form'], token['lemma'], greedy_candidate)
                # else:
                #    errors.append((token['form'], token['lemma'], candidate))
            total += 1
            if token["form"] == token["lemma"]:
                zero += 1
            if greedy_candidate == token["lemma"]:
                greedy += 1
            if candidate == token["lemma"]:
                nongreedy += 1
            else:
                errors.append((token["form"], token["lemma"], candidate))
    print("exec time:\t %.3f" % (time.time() - start))
    print("greedy:\t\t %.3f" % (greedy / total))
    print("non-greedy:\t %.3f" % (nongreedy / total))
    print("baseline:\t %.3f" % (zero / total))
    print("-PRO greedy:\t\t %.3f" % (nonpro / nonprototal))
    print("-PRO non-greedy:\t %.3f" % (nongreedynonpro / nonprototal))
    print("-PRO baseline:\t\t %.3f" % (zerononpro / nonprototal))
    mycounter = Counter(errors)
    print(mycounter.most_common(20))
