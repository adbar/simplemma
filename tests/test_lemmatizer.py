"""Tests for `simplemma` package."""

import unicodedata
from collections.abc import Iterator, Mapping

import pytest

from simplemma import Lemmatizer, is_known, lemma_iterator, lemmatize, text_lemmatizer
from simplemma.strategies import (
    DefaultStrategy,
    DictionaryFactory,
    LemmatizationStrategy,
    RaiseErrorFallbackStrategy,
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
    """Test function to verify readme examples."""
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
    # greediness
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
    # chaining
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
    # error
    assert Lemmatizer().lemmatize("スパゲッティ", lang="pt") == lemmatize(
        "スパゲッティ", lang="pt"
    )
    assert lemmatize("スパゲッティ", lang="pt") == "スパゲッティ"

    with pytest.raises(ValueError):
        Lemmatizer(
            fallback_lemmatization_strategy=RaiseErrorFallbackStrategy()
        ).lemmatize("スパゲッティ", lang="pt")


def test_nn_fill_full_pipeline() -> None:
    """The WD fill added standalone "ane" (a real nn verb), which makes
    AffixDecompositionStrategy alone mis-split "underleverandørane" (see
    test_strategies.py's affix_decomposition cases) -- but dictionary_lookup
    runs first in the full pipeline and hits the fill-added whole-word entry,
    so the user-facing lemmatize() result is unaffected."""
    assert lemmatize("underleverandørane", lang="nn") == "underleverandør"


def test_hbs_closed_class_override() -> None:
    """The mined hbs override fixes two shipped-dict defects: a Latin
    closed-class word must not lemmatize to its Cyrillic spelling (was
    na->на), and a high-frequency homograph must resolve to its real lemma
    (je is 3sg of biti, not the pronoun ju)."""
    assert lemmatize("na", lang="hbs") == "na"  # was "на" (cross-script bug)
    assert lemmatize("je", lang="hbs") == "biti"  # was "ju" (homograph clash)
    # pitch-fold alias: the dict's marked key Afganìstān gains a plain twin
    assert lemmatize("Afganistan", lang="hbs") == "Afganistan"
    # script-consistency: a Latin key's Cyrillic value is transliterated
    assert lemmatize("Milorad", lang="hbs") == "Milorad"  # was "Милорад"
    # ś/ź (Montenegrin letters) survive the pitch fold's keep= guard
    assert lemmatize("dośetka", lang="hbs") == "dośetka"
    assert lemmatize("źenica", lang="hbs") == "źenica"
    assert lemmatize("doseci", lang="hbs") == "doseci"  # no longer -> dosetka


def test_stress_mark_fold_aliases() -> None:
    """Same BUILD_NORMALIZATION mechanism, four more languages: a dictionary-
    only stress/pitch/length-marked key (Wiktionary headword convention,
    never typed in real text) gains a plain-spelled alias twin. bg/uk
    examples are Cyrillic-scripted (Latin-scripted marked keys are academic
    romanization noise, dropped by _drop_junk_keys instead -- see
    test_foreign_script_key_drop below)."""
    assert lemmatize("Авакуме", lang="bg") == "Авакум"  # was unreachable
    assert lemmatize("Єзуча", lang="uk") == "Єзуч"
    assert lemmatize("Abadauskai", lang="lt") == "Abadauskas"
    assert lemmatize("Afganistanom", lang="sl") == "Afganistan"
    assert lemmatize("Abobrigae", lang="la") == "Abobriga"


def test_foreign_script_key_drop() -> None:
    """Wiktionary academic-transliteration/IPA rows that leaked in as if
    they were real word forms are unreachable (identity fallback), not
    resolved to the wrong-script lemma: ar IPA transcriptions, grc Beta-code
    romanization, bg/uk BGN/PCGN-style transliteration, hi Perso-Arabic
    (Urdu-script) leaks. ms is asymmetric: a Jawi query correctly resolves
    to its Rumi citation lemma (kept), but a Rumi query must never resolve
    to a Jawi lemma (dropped)."""
    assert lemmatize("rádost", lang="bg") == "rádost"  # was "радост"
    assert lemmatize("zanos", lang="uk") == "zanos"  # was "занос"
    assert lemmatize("hubrisin", lang="grc") == "hubrisin"  # was "ὑβρίς"
    assert lemmatize("uð.ðu.ki.ruː", lang="ar") == "uð.ðu.ki.ruː"  # was "اذكروا"
    assert lemmatize("سفید", lang="hi") == "سفید"  # was "सफ़ेद"
    assert lemmatize("جون", lang="ms") == "Jun"  # Jawi->Rumi: still correct
    assert lemmatize("pintu", lang="ms") == "pintu"  # Rumi->Jawi: was "ڤينتو"


def test_armenian_intonation_marks() -> None:
    """Marked token looked up first, then the mark-stripped form."""
    assert lemmatize("Մի՞թե", lang="hy") == "միթե"  # strip fallback, cased match
    assert lemmatize("կարո՞ղ", lang="hy") == "կարող"  # strip fallback, exact match
    assert lemmatize("Կարո՞ղ", lang="hy") == "կարող"
    assert lemmatize("ազատի՛", lang="hy") == "ազատել"  # marked key wins
    assert lemmatize("ազատի", lang="hy") == "ազատ"
    assert lemmatize("՞", lang="hy") == "՞"  # all-marks token: safe recursion


def test_apostrophe_variants() -> None:
    """All three apostrophe glyphs fold to the same lemma, including the
    modifier-letter U+02BC common in Ukrainian text (dict keys use U+0027)."""
    assert lemmatize("здоров'я", lang="uk") == "здоров'я"  # straight
    assert lemmatize("здоров’я", lang="uk") == "здоров'я"  # curly U+2019
    assert lemmatize("здоровʼя", lang="uk") == "здоров'я"  # modifier U+02BC


def test_exceptions() -> None:
    """Test if certain code parts correspond to the intended logic."""
    # missing languages or faulty language codes
    with pytest.raises(TypeError):
        Lemmatizer().lemmatize("test", lang=["test"])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        lemmatize("test", lang=["test"])  # type: ignore[arg-type]

    # searches
    with pytest.raises(TypeError):
        assert Lemmatizer().lemmatize(None, lang="en") is None  # type: ignore
    with pytest.raises(TypeError):
        assert lemmatize(None, lang="en") is None  # type: ignore
    with pytest.raises(ValueError):
        assert lemmatize("", lang="en") is None
    with pytest.raises(ValueError):
        assert Lemmatizer().lemmatize("", lang="en") is None


# (lang, word, greedy, expected) -- subword/compound handling through the
# full pipeline; the API-parity contract (class vs module-level function)
# is covered once in test_class_and_function_api_agree, not per case.
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
    ("de", "Lichtbild-Ausweis", True, "Lichtbildausweis"),
    ("de", "Kapuzenpullis", True, "Kapuzenpulli"),
    ("de", "Pharmagrößen", True, "Pharmagröße"),
    ("de", "Funktionärsebene", True, "Funktionärsebene"),
    ("de", "strafbewehrte", True, "strafbewehrt"),
    ("de", "fälschungssicheren", True, "fälschungssicher"),
    ("de", "Spargelstangen", True, "Spargelstange"),
    ("de", "Bandmitgliedern", True, "Bandmitglied"),
    ("de", "lemmatisiertes", False, "lemmatisiert"),
    ("de", "zerlemmatisiertes", False, "zerlemmatisiert"),
    ("ru", "фиксированные", False, "фиксированный"),
    ("ru", "зафиксированные", False, "зафиксированный"),
]


@pytest.mark.parametrize("lang, word, greedy, expected", _SUBWORD_CASES)
def test_subwords(lang: str, word: str, greedy: bool, expected: str) -> None:
    """Recognition and conversion of subword units."""
    assert lemmatize(word, lang=lang, greedy=greedy) == expected


def test_class_and_function_api_agree() -> None:
    """Lemmatizer-class and module-level APIs are the same code path; the
    contract is asserted once here instead of on every _SUBWORD_CASES row."""
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
    # unicode numerals also count as numeric: the short-circuit returns the
    # token verbatim instead of lowercasing it (which would yield "ⅻ")
    assert "Ⅻ".isnumeric()
    assert lemmatize("Ⅻ", lang="en") == "Ⅻ"
    # near-misses are NOT numeric: the strategy falls through to a normal
    # lookup (returning None here) rather than short-circuiting on the token
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


# (lang, greedy, text, expected lemmas) -- full-text lemmatization through
# the tokenizer + pipeline; API parity (get_lemmas_in_text / lemma_iterator /
# text_lemmatizer) is covered once in test_text_api_parity, not per case.
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
    """The three text-level APIs are the same code path; asserted once here
    instead of on every _TEXT_CASES row."""
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


# (lang, text, expected first lemma): sentence-initial casing policy per
# language. Gated languages (da/de/en) keep probable proper nouns; all-caps
# initials are lowered (and may be recovered by lookup); non-gated languages
# lower unconditionally as before.
_INITIAL_CASING_CASES = [
    ("en", "Iran is large.", "Iran"),  # proper noun kept
    ("en", "The cat sleeps.", "the"),  # common word lowered
    ("de", "BERLIN meldet Erfolg.", "Berlin"),  # all-caps recovered
    ("de", "Schöne Tage kommen.", "schön"),  # adjective lowered
    ("de", "Häuser stehen dort.", "Haus"),  # noun kept
    ("da", "MED venlig hilsen.", "med"),  # da: all-caps still lowered
    ("es", "Pepa baila.", "pepa"),  # non-gated lang: unchanged
    ("de", "DENIC verwaltet die Domains.", "DENIC"),  # initial acronym kept
    ("de", "MIT dem Auto fahren.", "mit"),  # dateline homograph defers to D' gate
]


@pytest.mark.parametrize("lang, text, first", _INITIAL_CASING_CASES)
def test_sentence_initial_casing(lang: str, text: str, first: str) -> None:
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False))
    assert next(lem.get_lemmas_in_text(text, lang)) == first


# (lang, text, kept, dropped): tokens that must / must not survive verbatim.
_ACRONYM_CASES = [
    ("de", "Die Firma heißt MIT und ist bekannt.", ["MIT"], []),  # kept mid-sentence
    ("uk", "Колишній Радянський Союз, або СССР, розпався.", ["СССР"], []),
    ("lv", "Viņš dzīvo ASV jau daudzus gadus.", ["ASV"], []),
    ("lt", "Šiaurės Amerikoje esanti JAV yra didelė valstybė.", ["JAV"], []),
    # es/pt/ca: acronym kept instead of collapsing to a verb homograph
    ("es", "El PSOE negocia el IVA con la UE.", ["IVA"], []),
    ("pt", "O IBGE informou que os EUA assinaram.", ["IBGE"], []),
    ("ca", "La FEDER i la USA financen el projecte.", ["USA"], []),
    ("de", "Das steht in Kapitel XII.", ["XII"], []),  # Roman numeral, not an acronym
    # 2-char Roman-numeral lookalikes stay keepable as acronyms
    ("es", "El disco CD es popular hoy.", ["CD"], []),
    # MM now lowercases: v2.0 fill adds 'mm' as a known de word; DC has no such homograph
    ("de", "MM und DC sind hier bekannt.", ["DC"], ["MM"]),
    ("uk", "Це СБУ.", ["СБУ"], []),  # lone acronym isn't "shouting" (leave-one-out)
    # an opening quote shifts neither the initial slot nor the flush
    ("de", "„MIT dem Auto fahren.“", ["mit"], ["MIT"]),
    # hy: the Armenian full stop isolates the shouted heading from sentence 2
    (
        "hy",
        "ՎՏԱՆԳ ԱՅՍՏԵՂ։ Կառավարությունը հրապարակեց, որ ՀՀ ստորագրեց փաստաթուղթը։",
        ["ՀՀ"],
        ["ԱՅՍՏԵՂ"],
    ),
    # punctuation runs ('!!!', '...') end the sentence: the shouted headline
    # stays isolated from the next sentence
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
    # non-allowlisted language: acronym still lowered as before
    ("fr", "Ils ont vu un OVNI hier soir.", ["ovni"], ["OVNI"]),
]


@pytest.mark.parametrize("lang, text, kept, dropped", _ACRONYM_CASES)
def test_allcaps_acronym_keeping(
    lang: str, text: str, kept: list[str], dropped: list[str]
) -> None:
    """ALL-CAPS tokens are kept verbatim as likely acronyms in the allowlisted
    languages, unless the sentence is shouted or the token is a Roman numeral."""
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False))
    out = list(lem.get_lemmas_in_text(text, lang))
    for token in kept:
        assert token in out, (token, out)
    for token in dropped:
        assert token not in out, (token, out)


def test_shouted_sentence_defers_to_gate() -> None:
    """A fully shouted sentence turns acronym-keep off; the initial D' gate
    still lowers the first word."""
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False))
    out = list(lem.get_lemmas_in_text("WARNUNG VOR DEM HUNDE", "de"))
    assert out == ["Warnung", "vor", "der", "HUNDE"]


def test_casing_heuristics_off_without_membership() -> None:
    """Both casing heuristics need a dictionary-membership check; a strategy
    without one falls back to unconditional initial-lowering."""

    class _LowerStrategy(LemmatizationStrategy):
        def get_lemma(self, token: str, lang: str) -> str | None:
            return token.lower()

    custom = Lemmatizer(lemmatization_strategy=_LowerStrategy())
    # en gate off: initial proper noun lowered
    assert next(custom.get_lemmas_in_text("Iran is large.", "en")) == "iran"
    # de acronym-keep off: all-caps token lowered as before
    out = list(custom.get_lemmas_in_text("Die Firma heißt MIT und.", "de"))
    assert "mit" in out and "MIT" not in out


def test_lang_tuple_casing_follows_first_language() -> None:
    """Documented semantics: the first language owns the casing policy."""
    lem = Lemmatizer(lemmatization_strategy=DefaultStrategy())
    text = "Ils ont vu un OVNI hier soir."
    assert "OVNI" in list(lem.get_lemmas_in_text(text, ("de", "fr")))
    assert "ovni" in list(lem.get_lemmas_in_text(text, ("fr", "de")))


def test_gate_probes_nfc_normalized() -> None:
    """The casing gate must find NFD tokenizer output in the NFC dictionaries
    (unit-level coverage lives in test_casing.py)."""

    class _NFDTokenizer:
        def split_text(self, text: str) -> Iterator[str]:
            return (unicodedata.normalize("NFD", t) for t in text.split(" "))

    lem = Lemmatizer(
        tokenizer=_NFDTokenizer(), lemmatization_strategy=DefaultStrategy()
    )
    # the NFD initial token is still found in the dict and lowered
    assert list(lem.get_lemmas_in_text("Schöne Tage kommen .", "de"))[0] == "schön"


def test_nfc_normalization() -> None:
    """Decomposed (NFD) input must lemmatize like its composed (NFC) form."""
    nfd = unicodedata.normalize("NFD", "Häuser")
    assert lemmatize(nfd, lang="de") == lemmatize("Häuser", lang="de") == "Haus"
    assert is_known(nfd, lang="de") == is_known("Häuser", lang="de") is True
    # output is always NFC, even when the input was decomposed
    out = lemmatize(unicodedata.normalize("NFD", "café"), lang="fr")
    assert out == unicodedata.normalize("NFC", out)


def test_long_token_does_not_hang() -> None:
    """A pathologically long token must return quickly, not trigger O(n²) decomposition."""
    assert lemmatize("a" * 50000, lang="fi") == "a" * 50000  # was minutes, now instant
    assert lemmatize("a" * 101, lang="fi") == "a" * 101
    assert lemmatize("masks", lang="en") == "mask"


def test_he_acronyms_survive_tokenization() -> None:
    assert text_lemmatizer('שילם ש"ח היום.', lang="he")[1] == 'ש"ח'
