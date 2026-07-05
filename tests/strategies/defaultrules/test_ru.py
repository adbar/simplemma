from collections.abc import Mapping

from simplemma import Lemmatizer
from simplemma.strategies import DefaultStrategy, DictionaryFactory, RulesStrategy


def test_apply_ru() -> None:
    """Test Russian rules."""
    rules_strategy = RulesStrategy()
    assert rules_strategy.get_lemma("уверенностью", "ru") == "уверенность"
    assert rules_strategy.get_lemma("хозяйством", "ru") == "хозяйство"
    assert rules_strategy.get_lemma("своё", "ru") == "свое"
    assert rules_strategy.get_lemma("кот", "ru") is None
    assert rules_strategy.get_lemma("Хозяйством", "ru") is None


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
