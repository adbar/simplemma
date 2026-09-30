"""Per-language spot-checks of the default rules. None means the rule must not fire."""

from collections.abc import Mapping

import pytest

from simplemma import Lemmatizer
from simplemma.strategies import DefaultStrategy, DictionaryFactory, RulesStrategy

_RULES = RulesStrategy()

RULE_CASES = [
    ("de", "Whatawordicantbelieveit", None),
    ("de", "Pfifferling", "Pfifferling"),
    ("de", "Pfifferlinge", "Pfifferling"),
    ("de", "Pfifferlingen", "Pfifferling"),
    ("de", "Heiterkeiten", "Heiterkeit"),
    ("de", "Bürgertums", "Bürgertum"),
    ("de", "Achterls", "Achterl"),
    # only -erinnen feminine agent plurals are handled
    ("de", "Lehrerinnen", "Lehrerin"),
    ("de", "Inspekteurinnen", None),
    ("de", "Gerinnen", None),  # stoplisted
    ("de", "Kazakhstans", "Kazakhstan"),
    ("de", "Ökonomen", "Ökonom"),
    ("de", "Chauffeusen", "Chauffeuse"),
    ("de", "Luftikussen", "Luftikus"),
    ("de", "Trunkenbolde", "Trunkenbold"),
    ("de", "Theologien", "Theologie"),
    ("de", "großartiges", "großartig"),
    ("de", "isotropen", "isotrop"),
    ("de", "angebrachtes", "angebracht"),
    # Gendersprache normalization
    ("de", "ZuschauerInnen", "Zuschauer:innen"),
    ("de", "Zuschauer*innen", "Zuschauer:innen"),
    ("de", "Zuschauer_innen", "Zuschauer:innen"),
    ("de", "Zuschauer-innen", "Zuschauer:innen"),
    ("en", "Whatawordicantbelieveit", None),
    ("en", "delicacies", "delicacy"),
    ("en", "kingdoms", "kingdom"),
    ("en", "realisms", "realism"),
    ("en", "naturists", "naturist"),
    ("en", "atonements", "atonement"),
    ("en", "nonces", "nonce"),
    ("en", "nations", "nation"),
    ("en", "realized", "realize"),
    ("en", "preserves", "preserve"),
    # these suffix rules fell below the precision bar
    ("en", "hardships", None),
    ("en", "nurseries", None),
    ("en", "realities", None),
    ("en", "mistresses", None),
    ("en", "matrices", None),
    ("fi", "aakkoselliseen", "aakkosellinen"),
    ("fi", "aakkoselliseksi", "aakkosellinen"),
    ("fi", "aakkosellisella", "aakkosellinen"),
    ("fi", "kirjoituksen", "kirjoitus"),
    ("fi", "ystävyyden", "ystävyys"),
    ("fi", "kirjallisuuden", "kirjallisuus"),
    ("fi", "kalastuksen", "kalastus"),
    ("fi", "kissa", None),
    ("fi", "Liikenaisen", None),
    ("nl", "achterpagina's", "achterpagina"),
    ("nl", "achterpagina’s", "achterpagina"),
    ("nl", "achterpaginaʼs", "achterpagina"),
    ("nl", "mogelijkheden", "mogelijkheid"),
    ("nl", "boerderijen", "boerderij"),
    ("nl", "hond", None),
    ("nl", "kastelen", None),
    # -ieven collides with -ieve adjective plurals (executieven)
    ("nl", "brieven", None),
    ("ru", "уверенностью", "уверенность"),
    ("ru", "хозяйством", "хозяйство"),
    ("ru", "безгра́мотностью", "безгра́мотность"),
    ("ru", "своё", "свое"),
    ("ru", "кот", None),
    ("ru", "Хозяйством", None),
    ("lv", "risinājumu", "risinājums"),
    ("lv", "iespējamības", "iespējamība"),
    ("lv", "Rīga", None),
    ("lv", "sijas", None),  # min_len=6
    # definite adjectives are not handled
    ("lv", "labākajiem", None),
    ("lv", "baltajiem", None),
    ("eo", "domojn", "domo"),
    ("eo", "belajn", "bela"),
    ("eo", "kuras", "kuri"),
    ("eo", "manĝu", "manĝi"),
    ("eo", "kurantojn", "kuranto"),
    ("eo", "hejmen", "hejme"),
    ("et", "tavalised", "tavaline"),
    ("et", "peamisteks", "peamine"),
    ("et", "kunstnikud", "kunstnik"),
    ("et", "keelkondade", "keelkond"),
    ("et", "Läänemere", None),
    ("ms", "bukunya", "buku"),
    ("ms", "rumahku", "rumah"),
    ("ms", "baku", None),
    ("ka", "ღვინოთა", "ღვინო"),
    ("ka", "ტურისტმა", "ტურისტი"),
    # -ისას: the case cells cannot reach the citation form
    ("ka", "მოძრაობისას", None),
    # stem-final -ლთა is not a case ending here, so no *კალი
    ("ka", "კალთა", None),
    ("nn", "akslingane", "aksling"),
    ("nn", "kaptein", None),
    ("uk", "близького", "близький"),
    ("uk", "авторського", "авторський"),
    ("uk", "гірничо-добувних", "гірничо-добувний"),
    # дехто/ніхто/абихто decline like -кий adjectives but lemmatise to a pronoun
    ("uk", "декого", None),
    ("cs", "argumentuju", "argumentovat"),
    ("cs", "domovského", "domovský"),
    ("cs", "vědecko-pedagogičtí", "vědecko-pedagogický"),
    ("la", "abalienabant", "abalieno"),
    ("la", "Roma", None),
    # the stem floor forbids stripping to a bare "o"
    ("la", "abimus", None),
    # 1-char stems are never stripped
    ("la", "antium", None),
    ("sv", "ackordssättningarna", "ackordssättning"),
    ("sv", "lanterna", None),
    ("pt", "hegemônicos", "hegemônico"),
    ("pt", "superdegustadores", "superdegustador"),
    ("pt", "tenetehara-guajajara", None),
    ("es", "aplicaciones", "aplicación"),
    ("es", "mientras", None),
    ("is", "fagurfræðilegu", "fagurfræðilegur"),
    ("is", "vonandi", None),
    ("sl", "ekonomskega", "ekonomski"),
    ("sl", "totalno", None),
    ("sk", "robotníkoch", "robotník"),
    ("sk", "slovenského", "slovenský"),
    ("sk", "naozaj", None),
    ("ro", "profesorului", "profesor"),
    ("ro", "explica", None),
]


@pytest.mark.parametrize("lang, form, expected", RULE_CASES)
def test_default_rules(lang: str, form: str, expected: str | None) -> None:
    assert _RULES.get_lemma(form, lang) == expected


def test_apply_ru_ye_reachable_through_pipeline() -> None:
    """The ё->е rule fires through DefaultStrategy when the dictionary misses."""

    class EmptyDictionaryFactory(DictionaryFactory):
        def get_dictionary(self, lang: str) -> Mapping[str, str]:
            return {}

    lemmatizer = Lemmatizer(
        lemmatization_strategy=DefaultStrategy(
            dictionary_factory=EmptyDictionaryFactory()
        )
    )
    assert lemmatizer.lemmatize("своё", lang="ru") == "свое"
