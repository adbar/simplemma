

from collections import Counter

from conllu import parse_incr
from simplemma import load_data, lemmatize


data_files = [
              ('de', 'tests/UD/de-gsd-all.conllu'),
              ('en', 'tests/UD/en-gum-all.conllu'),
              ('es', 'tests/UD/es-gsd-all.conllu'),
              ('fi', 'tests/UD/fi-tdt-all.conllu'),
              ('fr', 'tests/UD/fr-gsd-all.conllu'),
              ('sk', 'tests/UD/sk-snk-all.conllu'),
             ]


for filedata in data_files:
    total, greedy, nongreedy, zero = 0, 0, 0, 0
    errors, flag = [], False
    langdata = load_data(filedata[0])
    data_file = open(filedata[1], 'r', encoding='utf-8')
    print('==', filedata, '==')
    for tokenlist in parse_incr(data_file):
        for token in tokenlist:
            if token['lemma'] == '_':
            #    flag = True
                continue
            greedy_candidate = lemmatize(token['form'], langdata, greedy=True)
            candidate = lemmatize(token['form'], langdata, greedy=False)
            total += 1
            if token['form'] == token['lemma']:
                zero += 1
            if greedy_candidate == token['lemma']:
                greedy += 1
            else:
                errors.append((token['form'], token['lemma'], candidate))
            if candidate == token['lemma']:
                nongreedy += 1
    print('greedy:\t\t %.3f' % (greedy/total))
    print('non-greedy:\t %.3f' % (nongreedy/total))
    print('baseline:\t %.3f' % (zero/total))
    mycounter = Counter(errors)
    print(mycounter.most_common(20))

