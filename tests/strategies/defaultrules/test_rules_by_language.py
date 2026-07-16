"""Per-language spot-checks of the default rules via ``RulesStrategy``.

One parametrized case list, ``(lang, form, expected)`` where ``expected`` is the
lemma the rules must produce or ``None`` when they deliberately don't fire.
Consolidated from the former per-language ``test_<lang>.py`` files; the comments
record why a given ``None`` case is dropped. Aggregate/per-cell precision is
enforced separately in ``test_precision.py``.
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
    # --- Polish ---
    ("pl", "wolnościach", "wolność"),
    ("pl", "malowałbym", "malować"),
    ("pl", "czytalibyśmy", "czytać"),
    ("pl", "robilibyście", "robić"),
    ("pl", "zmyłybyśmy", "zmyć"),
    ("pl", "kotów", None),
    ("pl", "Wolnościach", None),
    # --- Russian ---
    ("ru", "уверенностью", "уверенность"),
    ("ru", "хозяйством", "хозяйство"),
    ("ru", "своё", "свое"),
    ("ru", "кот", None),
    ("ru", "Хозяйством", None),
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
