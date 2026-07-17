"""Per-language spot-checks of the default rules via ``RulesStrategy``.

``(lang, form, expected)`` cases; ``expected`` is None when the rule
deliberately doesn't fire. Aggregate/per-cell precision is checked in
``test_precision.py``.
"""

from collections.abc import Mapping

import pytest

from simplemma import Lemmatizer
from simplemma.strategies import DefaultStrategy, DictionaryFactory, RulesStrategy

_RULES = RulesStrategy()

# (lang, form, expected-lemma-or-None)
RULE_CASES = [
    # --- German ---
    ("de", "Whatawordicantbelieveit", None),  # doesn't exist
    ("de", "Pfifferling", "Pfifferling"),
    ("de", "Pfifferlinge", "Pfifferling"),
    ("de", "Pfifferlingen", "Pfifferling"),
    ("de", "Heiterkeiten", "Heiterkeit"),
    ("de", "Bürgertums", "Bürgertum"),
    ("de", "Achterls", "Achterl"),
    # feminine agent plural: only -erinnen is handled (see de.py)
    ("de", "Lehrerinnen", "Lehrerin"),
    ("de", "Inspekteurinnen", None),
    ("de", "Gerinnen", None),  # -erinnen stop
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
    # --- English ---
    ("en", "Whatawordicantbelieveit", None),  # doesn't exist
    ("en", "delicacies", "delicacy"),
    ("en", "kingdoms", "kingdom"),
    ("en", "realisms", "realism"),
    ("en", "naturists", "naturist"),
    ("en", "atonements", "atonement"),
    ("en", "nonces", "nonce"),
    ("en", "hardships", "hardship"),
    ("en", "nations", "nation"),
    ("en", "realized", "realize"),
    ("en", "preserves", "preserve"),
    # dropped (below the 99% bar): ries/ties (-erie/-tie), esses (finesse), trices
    ("en", "nurseries", None),
    ("en", "realities", None),
    ("en", "mistresses", None),
    ("en", "matrices", None),
    # --- Finnish ---
    # -inen possessive cells
    ("fi", "aakkoselliseen", "aakkosellinen"),
    ("fi", "aakkoselliseksi", "aakkosellinen"),
    ("fi", "aakkosellisella", "aakkosellinen"),
    # -us / -ys nouns
    ("fi", "kirjoituksen", "kirjoitus"),
    ("fi", "ystävyyden", "ystävyys"),
    # -uus abstract nouns
    ("fi", "kirjallisuuden", "kirjallisuus"),
    ("fi", "kalastuksen", "kalastus"),
    ("fi", "kissa", None),
    ("fi", "Liikenaisen", None),
    # --- Dutch ---
    ("nl", "achterpagina's", "achterpagina"),
    ("nl", "mogelijkheden", "mogelijkheid"),
    ("nl", "boerderijen", "boerderij"),
    ("nl", "hond", None),
    ("nl", "kastelen", None),
    # -ieven dropped: collides with -ieve adjective plurals (executieven)
    ("nl", "brieven", None),
    # --- Russian ---
    ("ru", "уверенностью", "уверенность"),
    ("ru", "хозяйством", "хозяйство"),
    ("ru", "безгра́мотностью", "безгра́мотность"),
    ("ru", "своё", "свое"),
    ("ru", "кот", None),
    ("ru", "Хозяйством", None),
    # --- Latvian ---
    ("lv", "risinājumu", "risinājums"),
    ("lv", "iespējamības", "iespējamība"),
    ("lv", "Rīga", None),
    # definite-adjective declension dropped, see lv.py
    ("lv", "labākajiem", None),
    ("lv", "baltajiem", None),
    # --- Esperanto ---
    ("eo", "domojn", "domo"),
    ("eo", "belajn", "bela"),
    ("eo", "kuras", "kuri"),
    ("eo", "manĝu", "manĝi"),
    ("eo", "kurantojn", "kuranto"),
    ("eo", "hejmen", "hejme"),
    # --- Estonian ---
    ("et", "tavalised", "tavaline"),
    ("et", "peamisteks", "peamine"),
    ("et", "kunstnikud", "kunstnik"),
    ("et", "keelkondade", "keelkond"),
    ("et", "Läänemere", None),
    # --- Malay ---
    ("ms", "bukunya", "buku"),
    ("ms", "rumahku", "rumah"),
    ("ms", "baku", None),
    # --- Georgian ---
    ("ka", "ღვინოთა", "ღვინო"),
    ("ka", "ტურისტმა", "ტურისტი"),
    # -ისას abstains: the case cells cannot reach the citation form
    ("ka", "მოძრაობისას", None),
    # stem-final -ლთა nouns (not a case ending) stoplisted, not -> *კალი
    ("ka", "კალთა", None),
    # --- Norwegian Nynorsk ---
    ("nn", "akslingane", "aksling"),
    ("nn", "kaptein", None),
    # --- Ukrainian ---
    ("uk", "близького", "близький"),
    ("uk", "авторського", "авторський"),
    # дехто/ніхто/абихто decline like -кий adjectives but lemmatise to a pronoun
    ("uk", "декого", None),
    # --- Czech ---
    ("cs", "argumentuju", "argumentovat"),
    ("cs", "domovského", "domovský"),
    # --- Latin ---
    ("la", "abalienabant", "abalieno"),
    ("la", "Roma", None),
    # (?<=..) stem floor: whole-word match must not strip to a bare "o"
    ("la", "abimus", None),
    # floor on all groups: 1-char-stem matches must not strip to bare targets
    ("la", "antium", None),
    # --- Swedish ---
    ("sv", "ackordssättningarna", "ackordssättning"),
    ("sv", "lanterna", None),
    # --- Portuguese ---
    ("pt", "hegemônicos", "hegemônico"),
    ("pt", "superdegustadores", "superdegustador"),
    ("pt", "tenetehara-guajajara", None),
    # --- Spanish ---
    ("es", "aplicaciones", "aplicación"),
    ("es", "mientras", None),
    # --- Icelandic ---
    ("is", "fagurfræðilegu", "fagurfræðilegur"),
    ("is", "vonandi", None),
    # --- Slovenian ---
    ("sl", "ekonomskega", "ekonomski"),
    ("sl", "totalno", None),
    # --- Slovak ---
    ("sk", "robotníkoch", "robotník"),
    ("sk", "slovenského", "slovenský"),
    ("sk", "naozaj", None),
    # --- Romanian ---
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
