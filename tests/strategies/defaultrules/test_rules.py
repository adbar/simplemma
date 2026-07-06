from simplemma.strategies import RulesStrategy


def test_DEFAULT_RULES() -> None:
    """Test rules on all available languages."""
    rules_strategy = RulesStrategy()

    assert rules_strategy.get_lemma("Pfifferlinge", "de") == "Pfifferling"
    assert rules_strategy.get_lemma("atonements", "de") is None

    assert rules_strategy.get_lemma("atonements", "en") == "atonement"
    assert rules_strategy.get_lemma("Pfifferlinge", "en") is None

    assert rules_strategy.get_lemma("mogelijkheden", "nl") == "mogelijkheid"

    assert rules_strategy.get_lemma("kirjoituksen", "fi") == "kirjoitus"

    assert rules_strategy.get_lemma("pracowaliście", "pl") == "pracować"

    assert rules_strategy.get_lemma("безгра́мотностью", "ru") == "безгра́мотность"

    assert rules_strategy.get_lemma("Rīga", "lv") is None
    assert rules_strategy.get_lemma("labākajiem", "lv") == "labākais"
    assert rules_strategy.get_lemma("baltajiem", "lv") == "baltais"

    assert rules_strategy.get_lemma("domojn", "eo") == "domo"
    assert rules_strategy.get_lemma("belajn", "eo") == "bela"
    assert rules_strategy.get_lemma("kuras", "eo") == "kuri"
    assert rules_strategy.get_lemma("manĝu", "eo") == "manĝi"
    assert rules_strategy.get_lemma("kurantojn", "eo") == "kuranto"
    assert rules_strategy.get_lemma("hejmen", "eo") == "hejme"

    assert rules_strategy.get_lemma("Läänemere", "et") is None
    assert rules_strategy.get_lemma("tavalised", "et") == "tavaline"
    assert rules_strategy.get_lemma("peamisteks", "et") == "peamine"
    # -dus dropped: -dustena etc. collide with -dune adjectives (kodune)
    assert rules_strategy.get_lemma("kunstnikud", "et") == "kunstnik"
    assert rules_strategy.get_lemma("keelkondade", "et") == "keelkond"

    assert rules_strategy.get_lemma("bukunya", "ms") == "buku"
    assert rules_strategy.get_lemma("rumahku", "ms") == "rumah"
    assert rules_strategy.get_lemma("baku", "ms") is None

    assert rules_strategy.get_lemma("ღვინოთა", "ka") == "ღვინო"
    assert rules_strategy.get_lemma("ტურისტმა", "ka") == "ტურისტი"
    # -ისას abstains: the case cells cannot reach the citation form
    assert rules_strategy.get_lemma("მოძრაობისას", "ka") is None

    assert rules_strategy.get_lemma("luesteger", "lb") == "luesteg"
    assert rules_strategy.get_lemma("bequemer", "lb") is None

    assert rules_strategy.get_lemma("akslingane", "nn") == "aksling"
    assert rules_strategy.get_lemma("kaptein", "nn") is None

    assert rules_strategy.get_lemma("авторката", "mk") == "авторка"
    assert rules_strategy.get_lemma("автостоперката", "mk") == "автостоперка"

    assert rules_strategy.get_lemma("близького", "uk") == "близький"
    assert rules_strategy.get_lemma("авторського", "uk") == "авторський"
    # дехто/ніхто/абихто decline like -кий adjectives but lemmatise to a pronoun
    assert rules_strategy.get_lemma("декого", "uk") is None

    assert rules_strategy.get_lemma("argumentuju", "cs") == "argumentovat"
    assert rules_strategy.get_lemma("domovského", "cs") == "domovský"

    assert rules_strategy.get_lemma("abalienabant", "la") == "abalieno"
    assert rules_strategy.get_lemma("Roma", "la") is None

    assert rules_strategy.get_lemma("ackordssättningarna", "sv") == "ackordssättning"
    assert rules_strategy.get_lemma("lanterna", "sv") is None

    assert rules_strategy.get_lemma("hegemônicos", "pt") == "hegemônico"
    assert rules_strategy.get_lemma("superdegustadores", "pt") == "superdegustador"
    assert rules_strategy.get_lemma("tenetehara-guajajara", "pt") is None

    # gl_ctg gold keeps this castellanized technical term as its own lemma
    assert rules_strategy.get_lemma("crustáceos", "gl") is None
    assert rules_strategy.get_lemma("párkinson", "gl") is None

    assert rules_strategy.get_lemma("declaracions", "ca") == "declaració"
    assert rules_strategy.get_lemma("mitjançant", "ca") is None

    assert rules_strategy.get_lemma("aplicaciones", "es") == "aplicación"
    assert rules_strategy.get_lemma("mientras", "es") is None

    assert rules_strategy.get_lemma("fagurfræðilegu", "is") == "fagurfræðilegur"
    assert rules_strategy.get_lemma("vonandi", "is") is None

    assert rules_strategy.get_lemma("ekonomskega", "sl") == "ekonomski"
    assert rules_strategy.get_lemma("totalno", "sl") is None

    assert rules_strategy.get_lemma("robotníkoch", "sk") == "robotník"
    assert rules_strategy.get_lemma("slovenského", "sk") == "slovenský"
    assert rules_strategy.get_lemma("naozaj", "sk") is None

    assert rules_strategy.get_lemma("profesorului", "ro") == "profesor"
    assert rules_strategy.get_lemma("explica", "ro") is None
