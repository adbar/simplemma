"""Simple rules for unknown tokens."""

import re



def apply_rules(token, langcode):
    candidate = None
    if langcode == 'de':
        candidate = apply_de(token)
    return candidate



def apply_de(token):
    if len(token) > 8:
        # plural noun forms
        if token[0].isupper():
            if re.search('(erei|erie|heit|ik|keit|schaft|tät|tion|ung)en$', token): # ur
                return token[:-2]
            if re.search('(and|ant|ent|ist|or)en$', token):
                return token[:-2]
            if re.search('(eur|ich|ier|ling|ör)e$', token): # ig
                return token[:-1]
            # genitive – too rare?
            #if re.search('(aner|chen|eur|ier|iker|ikum|iment|iner|iter|ium|land|lein|ler|ling|ner|tum)s$', token):  # er
            #    return token[:-1]
        else:
            # adjectives # en, ig
            if re.search('(arm|bar|ell|erig|ern|fach|frei|haft|isch|iv|lich|los|mäßig|reich|sam|sch|voll)(e|em|en|es|er)$', token):
                return re.sub(r'(e|em|en|es|er)$', '', token)
    return None
