"""Tests for `simplemma` package."""

import unicodedata
from collections.abc import Iterator, Mapping

import pytest

from simplemma import Lemmatizer, is_known, lemma_iterator, lemmatize, text_lemmatizer
from simplemma.strategies import (
    DefaultStrategy,
    DictionaryFactory,
    LemmatizationStrategy,
)


def test_custom_dictionary_factory() -> None:
    class CustomDictionaryFactory(DictionaryFactory):
        def get_dictionary(
            self,
            lang: str,
        ) -> Mapping[str, str]:
            return {"testing": "the test works!!"}

    assert (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(
                dictionary_factory=CustomDictionaryFactory()
            )
        ).lemmatize("testing", lang="en")
        == "the test works!!"
    )


def test_readme() -> None:
    myword = "masks"
    assert (
        Lemmatizer().lemmatize(myword, lang="en")
        == lemmatize(myword, lang="en")
        == "mask"
    )
    mytokens = ["Hier", "sind", "Vaccines", "."]
    assert [lemmatize(t, lang="de") for t in mytokens] == [
        "hier",
        "sein",
        "Vaccines",
        ".",
    ]
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False)).lemmatize(
            "ausgezeichneten", lang="de"
        )
        == lemmatize("ausgezeichneten", lang="de", greedy=False)
        == "ausgezeichnet"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "ausgezeichneten", lang="de"
        )
        == lemmatize("ausgezeichneten", lang="de", greedy=True)
        == "auszeichnen"
    )
    assert [lemmatize(t, lang=("de", "en")) for t in mytokens] == [
        "hier",
        "sein",
        "vaccine",
        ".",
    ]
    assert (
        Lemmatizer().lemmatize("spaghettis", lang="it")
        == lemmatize("spaghettis", lang="it")
        == "spaghettis"
    )
    assert (
        Lemmatizer().lemmatize("spaghettini", lang="it")
        == lemmatize("spaghettini", lang="it")
        == "spaghettini"
    )
    assert (
        Lemmatizer().lemmatize("spaghettis", lang=("it", "fr"))
        == lemmatize("spaghettis", lang=("it", "fr"))
        == "spaghetti"
    )
    assert (
        Lemmatizer().lemmatize("spaghetti", lang=("it", "fr"))
        == lemmatize("spaghetti", lang=("it", "fr"))
        == "spaghetto"
    )
    assert (
        Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True)).lemmatize(
            "spaghettis", lang=("it", "fr")
        )
        == lemmatize("spaghettis", lang=("it", "fr"), greedy=True)
        == "spaghetti"
    )
    assert text_lemmatizer(
        "Sou o intervalo entre o que desejo ser e os outros me fizeram.", lang="pt"
    ) == [
        "ser",
        "o",
        "intervalo",
        "entre",
        "o",
        "que",
        "desejo",
        "ser",
        "e",
        "o",
        "outro",
        "me",
        "fazer",
        ".",
    ]
    assert Lemmatizer().lemmatize("スパゲッティ", lang="pt") == lemmatize(
        "スパゲッティ", lang="pt"
    )
    assert lemmatize("スパゲッティ", lang="pt") == "スパゲッティ"

    def _raise_fallback(token: str, lang: str) -> str:
        raise ValueError(f"Token not found: {token}")

    with pytest.raises(ValueError):
        Lemmatizer(fallback=_raise_fallback).lemmatize("スパゲッティ", lang="pt")


def test_nn_fill_full_pipeline() -> None:
    """A whole-word fill entry resolves this compound in the full pipeline."""
    assert lemmatize("underleverandørane", lang="nn") == "underleverandør"


def test_hbs_closed_class_override() -> None:
    """hbs: no Cyrillic values for Latin words, je -> biti, marked keys gain aliases."""
    assert lemmatize("na", lang="hbs") == "na"
    assert lemmatize("je", lang="hbs") == "biti"
    # plain alias of the marked key Afganìstān
    assert lemmatize("Afganistan", lang="hbs") == "Afganistan"
    assert lemmatize("Milorad", lang="hbs") == "Milorad"
    assert lemmatize("dośetka", lang="hbs") == "dośetka"
    assert lemmatize("źenica", lang="hbs") == "źenica"
    assert lemmatize("doseci", lang="hbs") == "doseci"  # not dosetka


def test_stress_mark_fold_aliases() -> None:
    """A stress-marked dictionary key gains a plain alias in bg, uk, lt, sl, la."""
    assert lemmatize("Авакуме", lang="bg") == "Авакум"
    assert lemmatize("Єзуча", lang="uk") == "Єзуч"
    assert lemmatize("Abadauskai", lang="lt") == "Abadauskas"
    assert lemmatize("Afganistanom", lang="sl") == "Afganistan"
    assert lemmatize("Abobrigae", lang="la") == "Abobriga"


def test_foreign_script_key_drop() -> None:
    """Transliteration and IPA rows stay unreachable, but ms Jawi still maps to Rumi."""
    assert lemmatize("rádost", lang="bg") == "rádost"
    assert lemmatize("zanos", lang="uk") == "zanos"
    assert lemmatize("hubrisin", lang="grc") == "hubrisin"
    assert lemmatize("uð.ðu.ki.ruː", lang="ar") == "uð.ðu.ki.ruː"
    assert lemmatize("سفید", lang="hi") == "سفید"
    assert lemmatize("جون", lang="ms") == "Jun"
    assert lemmatize("pintu", lang="ms") == "pintu"


def test_armenian_intonation_marks() -> None:
    """Marked token looked up first, then the mark-stripped form."""
    assert lemmatize("Մի՞թե", lang="hy") == "միթե"  # strip fallback, cased match
    assert lemmatize("կարո՞ղ", lang="hy") == "կարող"  # strip fallback, exact match
    assert lemmatize("Կարո՞ղ", lang="hy") == "կարող"
    assert lemmatize("ազատի՛", lang="hy") == "ազատել"  # marked key wins
    assert lemmatize("ազատի", lang="hy") == "ազատ"
    assert lemmatize("՞", lang="hy") == "՞"  # all-marks token: safe recursion


def test_apostrophe_variants() -> None:
    """All apostrophe glyphs fold to the U+0027 dictionary keys."""
    assert lemmatize("здоров'я", lang="uk") == "здоров'я"
    assert lemmatize("здоров’я", lang="uk") == "здоров'я"  # curly U+2019
    assert lemmatize("здоровʼя", lang="uk") == "здоров'я"  # modifier U+02BC
    # unknown tokens keep their glyph, direct strategy calls fold too
    assert lemmatize("xyz’abc", lang="fr") == "xyz’abc"
    assert text_lemmatizer("xyz’abc aujourd’hui", lang="fr") == [
        "xyz’abc",
        "aujourd'hui",
    ]
    assert DefaultStrategy().get_lemma("aujourd’hui", "fr") == "aujourd'hui"
    assert DefaultStrategy().is_dictionary_member("aujourd’hui", "fr")


def test_exceptions() -> None:
    with pytest.raises(TypeError):
        Lemmatizer().lemmatize("test", lang=["test"])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        lemmatize("test", lang=["test"])  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        assert Lemmatizer().lemmatize(None, lang="en") is None  # type: ignore
    with pytest.raises(TypeError):
        assert lemmatize(None, lang="en") is None  # type: ignore
    with pytest.raises(ValueError):
        assert lemmatize("", lang="en") is None
    with pytest.raises(ValueError):
        assert Lemmatizer().lemmatize("", lang="en") is None


_SUBWORD_CASES = [
    ("de", "OBI", True, "OBI"),
    ("de", "mRNA-Impfstoffe", False, "mRNA-Impfstoff"),
    ("de", "mRNA-impfstoffe", True, "mRNA-Impfstoff"),
    ("de", "Impftermine", False, "Impftermine"),
    ("de", "Impftermine", True, "Impftermin"),
    ("de", "Impfbeginn", False, "Impfbeginn"),
    ("de", "Impfbeginn", True, "Impfbeginn"),
    ("de", "Hoffnungsmaschinen", False, "Hoffnungsmaschinen"),
    ("de", "Hoffnungsmaschinen", True, "Hoffnungsmaschine"),
    ("de", "börsennotierter", True, "börsennotiert"),
    ("de", "journalistischer", True, "journalistisch"),
    ("de", "Delegiertenstimmen", True, "Delegiertenstimme"),
    ("de", "Koalitionskreisen", True, "Koalitionskreis"),
    ("de", "Infektionsfälle", True, "Infektionsfall"),
    ("de", "Corona-Einsatzstabes", True, "Corona-Einsatzstab"),
    ("de", "Clearinghäusern", True, "Clearinghaus"),
    ("de", "Mittelstreckenjets", True, "Mittelstreckenjet"),
    ("de", "Länderministerien", True, "Länderministerium"),
    ("de", "Gesundheitsschutzkontrollen", True, "Gesundheitsschutzkontrolle"),
    ("de", "Nachkriegsjuristen", True, "Nachkriegsjurist"),
    ("de", "insulinproduzierende", True, "insulinproduzierend"),
    ("de", "Urlaubsreisenden", True, "Urlaubsreisende"),
    ("de", "Grünenvorsitzende", True, "Grünenvorsitzende"),
    ("de", "Qualifikationsrunde", True, "Qualifikationsrunde"),
    ("de", "krisensichere", True, "krisensicher"),
    ("de", "ironischerweise", True, "ironischerweise"),
    ("de", "Landespressedienstes", True, "Landespressedienst"),
    ("de", "Lehrerverbänden", True, "Lehrerverband"),
    ("de", "Terminvergaberunden", True, "Terminvergaberunde"),
    ("de", "Gen-Sequenzierungen", True, "Gen-Sequenzierung"),
    ("de", "wiederverwendbaren", True, "wiederverwendbar"),
    ("de", "Spitzenposten", True, "Spitzenposten"),
    ("de", "I-Pace", True, "I-Pace"),
    ("de", "PCR-Bestätigungstests", True, "PCR-Bestätigungstest"),
    ("de", "obamaartigere", True, "obamaartig"),
    ("de", "durchgestyltes", True, "durchstylen"),
    ("de", "durchgeknallte", True, "durchgeknallt"),
    ("de", "herunterfährt", True, "herunterfahren"),
    ("de", "Atomdeals", True, "Atomdeal"),
    ("de", "Anspruchsberechtigten", True, "Anspruchsberechtigte"),
    ("de", "Bürgerschaftsabgeordneter", True, "Bürgerschaftsabgeordnete"),
    ("de", "Lichtbild-Ausweis", True, "Lichtbild-Ausweis"),
    ("de", "Kapuzenpullis", True, "Kapuzenpulli"),
    ("de", "Pharmagrößen", True, "Pharmagröße"),
    ("de", "Funktionärsebene", True, "Funktionärsebene"),
    ("de", "strafbewehrte", True, "strafbewehrt"),
    ("de", "fälschungssicheren", True, "fälschungssicher"),
    ("de", "Spargelstangen", True, "Spargelstange"),
    ("de", "Bandmitgliedern", True, "Bandmitglied"),
    ("de", "lemmatisiertes", False, "lemmatisiert"),
    ("ru", "фиксированные", False, "фиксированный"),
    ("ru", "зафиксированные", False, "зафиксированный"),
    ("fr", "l'après-midi", False, "après-midi"),
    ("it", "l'italo-americano", False, "italo-americano"),
    ("es", "transmitiéndoselo", False, "transmitir"),
    ("gl", "remitiráselles", False, "remitir"),
    ("it", "diecimila", False, "diecimila"),
]


@pytest.mark.parametrize("lang, word, greedy, expected", _SUBWORD_CASES)
def test_subwords(lang: str, word: str, greedy: bool, expected: str) -> None:
    assert lemmatize(word, lang=lang, greedy=greedy) == expected


def test_class_and_function_api_agree() -> None:
    """Class and module APIs share a code path, so parity is checked once here."""
    for lang, word, greedy, _ in (
        _SUBWORD_CASES[0],
        _SUBWORD_CASES[1],
        _SUBWORD_CASES[-1],
    ):
        assert Lemmatizer(
            lemmatization_strategy=DefaultStrategy(greedy=greedy)
        ).lemmatize(word, lang=lang) == lemmatize(word, lang=lang, greedy=greedy)


def test_numeric_tokens() -> None:
    """Numeric tokens are returned unchanged regardless of language."""
    assert (
        Lemmatizer().lemmatize("2024", lang="en")
        == lemmatize("2024", lang="en")
        == "2024"
    )
    assert lemmatize("123", lang=("de", "en")) == "123"
    # Unicode numerals return verbatim, lowercasing would give ⅻ
    assert "Ⅻ".isnumeric()
    assert lemmatize("Ⅻ", lang="en") == "Ⅻ"
    # 12.5 is not numeric, so it falls through to a lookup
    assert DefaultStrategy().get_lemma("2024", "en") == "2024"
    assert DefaultStrategy().get_lemma("12.5", "en") is None


def test_is_known() -> None:
    with pytest.raises(TypeError):
        assert is_known(None, lang="en") is None  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        assert is_known("", lang="en") is None

    assert is_known("FanCY", lang="en")
    assert not is_known("Fancy-String", lang="en")

    assert is_known("espejos", lang=("es", "de"))
    assert is_known("espejos", lang=("de", "es"))
    assert is_known("aujourd’hui", lang="fr")  # curly apostrophe folds at lookup


_TEXT_CASES = [
    (
        "fr",
        False,
        "Nous déciderons une fois arrivées. Voilà.",
        ["nous", "décider", "un", "fois", "arrivée", ".", "voilà", "."],
    ),
    (
        "es",
        False,
        "Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas.",
        [
            "pepa",
            "e",
            "Iván",
            "ser",
            "uno",
            "pareja",
            "sentimental",
            ",",
            "ambos",
            "dedicar",
            "al",
            "doblaje",
            "de",
            "película",
            ".",
        ],
    ),
    (
        "es",
        True,
        "Pepa e Iván son una pareja sentimental, ambos dedicados al doblaje de películas.",
        [
            "pepa",
            "e",
            "Iván",
            "ser",
            "uno",
            "pareja",
            "sentimental",
            ",",
            "ambos",
            "dedicar",
            "al",
            "doblaje",
            "de",
            "película",
            ".",
        ],
    ),
    (
        "eo",
        False,
        "Mi vidas la pomon.",
        ["mi", "vidi", "la", "pomo", "."],
    ),
]


@pytest.mark.parametrize("lang, greedy, text, expected", _TEXT_CASES)
def test_get_lemmas_in_text(
    lang: str, greedy: bool, text: str, expected: list[str]
) -> None:
    assert text_lemmatizer(text, lang=lang, greedy=greedy) == expected


def test_text_api_parity() -> None:
    """The three text APIs share a code path, so parity is checked once here."""
    lang, greedy, text, expected = _TEXT_CASES[0]
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=greedy))
    assert (
        list(lem.get_lemmas_in_text(text, lang=lang))
        == list(lemma_iterator(text, lang=lang, greedy=greedy))
        == text_lemmatizer(text, lang=lang, greedy=greedy)
        == expected
    )


def test_text_lemmatizer_apostrophe_boundaries() -> None:
    """Apostrophe-joined tokens reach the clitic/boundary strategies."""
    assert text_lemmatizer("L'homme n'est qu'un roseau.", lang="fr") == [
        "homme",
        "être",
        "un",
        "roseau",
        ".",
    ]
    assert text_lemmatizer("Ankara Türkiye’nin başkentidir.", lang="tr") == [
        "ankara",
        "Türkiye",
        "başkent",
        ".",
    ]
    assert "здоров'я" in text_lemmatizer("Це для здоров’я людини.", lang="uk")
    assert "do" in text_lemmatizer("They don't sing.", lang="en")


# Gated languages (da, de, en) keep probable proper nouns.
_INITIAL_CASING_CASES = [
    ("en", "Iran is large.", "Iran"),
    ("en", "The cat sleeps.", "the"),
    ("de", "BERLIN meldet Erfolg.", "Berlin"),  # all-caps recovered
    ("de", "Schöne Tage kommen.", "schön"),
    ("de", "Häuser stehen dort.", "Haus"),
    ("da", "MED venlig hilsen.", "med"),  # da: all-caps still lowered
    ("es", "Pepa baila.", "pepa"),  # non-gated lang: unchanged
    ("de", "DENIC verwaltet die Domains.", "DENIC"),
    ("de", "MIT dem Auto fahren.", "mit"),  # dateline homograph defers to D' gate
]


@pytest.mark.parametrize("lang, text, first", _INITIAL_CASING_CASES)
def test_sentence_initial_casing(lang: str, text: str, first: str) -> None:
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False))
    assert next(lem.get_lemmas_in_text(text, lang)) == first


_ACRONYM_CASES = [
    ("de", "Die Firma heißt MIT und ist bekannt.", ["MIT"], []),
    ("uk", "Колишній Радянський Союз, або СССР, розпався.", ["СССР"], []),
    ("lv", "Viņš dzīvo ASV jau daudzus gadus.", ["ASV"], []),
    ("lt", "Šiaurės Amerikoje esanti JAV yra didelė valstybė.", ["JAV"], []),
    # acronym, not the verb homograph
    ("es", "El PSOE negocia el IVA con la UE.", ["IVA"], []),
    ("pt", "O IBGE informou que os EUA assinaram.", ["IBGE"], []),
    ("ca", "La FEDER i la USA financen el projecte.", ["USA"], []),
    ("de", "Das steht in Kapitel XII.", ["XII"], []),  # Roman numeral, not an acronym
    # 2-char Roman-numeral lookalikes stay keepable
    ("es", "El disco CD es popular hoy.", ["CD"], []),
    # MM lowercases because 'mm' is a known de word
    ("de", "MM und DC sind hier bekannt.", ["DC"], ["MM"]),
    ("uk", "Це СБУ.", ["СБУ"], []),  # a lone acronym is not shouting
    # an opening quote shifts neither the initial slot nor the flush
    ("de", "„MIT dem Auto fahren.“", ["mit"], ["MIT"]),
    # the Armenian full stop isolates the shouted heading
    (
        "hy",
        "ՎՏԱՆԳ ԱՅՍՏԵՂ։ Կառավարությունը հրապարակեց, որ ՀՀ ստորագրեց փաստաթուղթը։",
        ["ՀՀ"],
        ["ԱՅՍՏԵՂ"],
    ),
    # '!!!' and '...' end the sentence, isolating the shouted headline
    (
        "uk",
        "УВАГА НЕБЕЗПЕКА!!! Це звичайне речення про природу.",
        ["небезпека"],
        ["НЕБЕЗПЕКА"],
    ),
    (
        "uk",
        "УВАГА НЕБЕЗПЕКА... Це речення про природу.",
        ["небезпека"],
        ["НЕБЕЗПЕКА"],
    ),
    # non-allowlisted language: acronym lowered
    ("fr", "Ils ont vu un OVNI hier soir.", ["ovni"], ["OVNI"]),
]


@pytest.mark.parametrize("lang, text, kept, dropped", _ACRONYM_CASES)
def test_allcaps_acronym_keeping(
    lang: str, text: str, kept: list[str], dropped: list[str]
) -> None:
    """Allowlisted languages keep ALL-CAPS acronyms unless the sentence is shouted."""
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False))
    out = list(lem.get_lemmas_in_text(text, lang))
    for token in kept:
        assert token in out, (token, out)
    for token in dropped:
        assert token not in out, (token, out)


def test_shouted_sentence_defers_to_gate() -> None:
    """A shouted sentence disables acronym-keep, the initial gate still applies."""
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False))
    out = list(lem.get_lemmas_in_text("WARNUNG VOR DEM HUNDE", "de"))
    assert out == ["Warnung", "vor", "der", "HUNDE"]


def test_casing_heuristics_off_without_membership() -> None:
    """Without a membership check, the sentence initial is always lowered."""

    class _LowerStrategy(LemmatizationStrategy):
        def get_lemma(self, token: str, lang: str) -> str | None:
            return token.lower()

    custom = Lemmatizer(lemmatization_strategy=_LowerStrategy())
    # en gate off: proper noun lowered
    assert next(custom.get_lemmas_in_text("Iran is large.", "en")) == "iran"
    # de acronym-keep off: all-caps lowered
    out = list(custom.get_lemmas_in_text("Die Firma heißt MIT und.", "de"))
    assert "mit" in out and "MIT" not in out


def test_lang_tuple_casing_follows_first_language() -> None:
    """The first language owns the casing policy."""
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy())
    text = "Ils ont vu un OVNI hier soir."
    assert "OVNI" in list(lem.get_lemmas_in_text(text, ("de", "fr")))
    assert "ovni" in list(lem.get_lemmas_in_text(text, ("fr", "de")))


def test_gate_probes_nfc_normalized() -> None:
    """The casing gate finds NFD tokens in the NFC dictionaries."""

    class _NFDTokenizer:
        def split_text(self, text: str) -> Iterator[str]:
            return (unicodedata.normalize("NFD", t) for t in text.split(" "))

    lem = Lemmatizer(
        tokenizer=_NFDTokenizer(), lemmatization_strategy=DefaultStrategy()
    )
    assert list(lem.get_lemmas_in_text("Schöne Tage kommen .", "de"))[0] == "schön"


def test_nfc_normalization() -> None:
    """Decomposed (NFD) input must lemmatize like its composed (NFC) form."""
    nfd = unicodedata.normalize("NFD", "Häuser")
    assert lemmatize(nfd, lang="de") == lemmatize("Häuser", lang="de") == "Haus"
    assert is_known(nfd, lang="de") == is_known("Häuser", lang="de") is True
    out = lemmatize(unicodedata.normalize("NFD", "café"), lang="fr")
    assert out == unicodedata.normalize("NFC", out)


def test_long_token_does_not_hang() -> None:
    """A pathologically long token must return quickly, not trigger O(n²) decomposition."""
    assert lemmatize("a" * 50000, lang="fi") == "a" * 50000
    assert lemmatize("a" * 101, lang="fi") == "a" * 101
    assert lemmatize("masks", lang="en") == "mask"


def test_he_acronyms_survive_tokenization() -> None:
    assert text_lemmatizer('שילם ש"ח היום.', lang="he")[1] == 'ש"ח'
