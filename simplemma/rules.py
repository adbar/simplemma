"""Simple rules for unknown tokens."""

import re



ADJ_DE = re.compile(r'^(.+?)(arm|artig|bar|ell|en|end|erig|ern|fach|frei|haft|isch|iv|lich|los|mäßig|reich|sam|sch|voll)(?:e|em|en|es|er)$')  # ig


def apply_rules(token, langcode):
    candidate = None
    if langcode == 'de':
        candidate = apply_de(token)
    elif langcode == 'en':
        candidate = apply_de(token)
    return candidate



def apply_de(token):
    if len(token) > 8 and re.search(r'(e|em|en|es|er)$', token):
        # plural noun forms
        if token[0].isupper():
            if re.search('(and|ant|ent|erei|erie|heit|ik|ist|keit|or|schaft|tät|tion|ung|ur)en$', token):
                return token[:-2]
            if re.search('(eur|ich|ier|ling|ör)e$', token): # ig
                return token[:-1]
            # genitive – too rare?
            #if re.search('(aner|chen|eur|ier|iker|ikum|iment|iner|iter|ium|land|lein|ler|ling|ner|tum)s$', token):  # er
            #    return token[:-1]
        else:
            # adjectives
            if ADJ_DE.match(token):
                return ADJ_DE.sub(r'\1\2', token)
    # inclusive speech
    if token.endswith('nnen'):
        return re.sub(r'Innen|\*innen|\*Innen|-innen', ':innen', token)
    return None


def apply_en(token):
    # nouns
    if token.endswith('s'):
        if token.endswith('ies') and len(token) > 7:
            if token.endswith('cies'):
                return token[:-4] + 'cy'
            if token.endswith('ries'):
                return token[:-4] + 'ry'
            if token.endswith('ties'):
                return token[:-4] + 'ty'
        if token.endswith('doms'):
            return token[:-4] + 'dom'
        if token.endswith('esses'):
            return token[:-5] + 'ess'
        if token.endswith('isms'):
            return token[:-4] + 'ism'
        if token.endswith('ists'):
            return token[:-4] + 'ist'
        if token.endswith('ments'):
            return token[:-5] + 'ment'
        if token.endswith('nces'):
            return token[:-4] + 'nce'
        if token.endswith('ships'):
            return token[:-5] + 'ship'
        if token.endswith('tions'):
            return token[:-5] + 'tion'
    # verbs
    if token.endswith('ed'):
        if token.endswith('ated'):
            return token[:-4] + 'ate'
        if token.endswith('ened'):
            return token[:-4] + 'en'
        if token.endswith('fied'):
            return token[:-4] + 'fy'
        if token.endswith('ized'):
            return token[:-4] + 'ize'
    return None
