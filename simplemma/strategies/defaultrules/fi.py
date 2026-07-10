import re

from .generic import apply_rules

# Finnish nominal/verbal suffix classes, mined lemma-first (99.72% in-dict).
# Only harmony-determinate cells survive (a suffix's own vowels fix -taa vs
# -tää); TU/VA-participle oblique cells were dropped (UD wants the verb
# infinitive, not the bare participle). min_len=10: shorter tokens are
# dominated by hyphen-elliptic/compound collisions.
DEFAULT_RULES = {
    re.compile(
        r"(?:misineen|miseksi|miselle|misiksi|misille|misemme|misenne|misella|miselta|misessa|misesta|misetta|misilla|misilta|misissa|misista|misitta|misensa|misillä|misiltä|misissä|misistä|misittä|miseen|misiin|misten|miseni|misesi|misien|misena|misina|misinä|misen|miset|misin|misia|misiä)$"
    ): r"minen",
    re.compile(
        r"(?:uksineen|uksiksi|uksilla|uksille|uksilta|uksitta|uksemme|uksina|uksien|uksia|uksin|ukset)$"
    ): r"us",
    re.compile(
        r"(?:yksineen|yksistä|yksiksi|yksille|yksillä|yksiltä|yksittä|ykseksi|ykselle|yksemme|yksenne|yksensä|yksinä|yksien|ykseen|ykseni|yksesi|yksena|yksin|yksiä|ysten|yksen|ykset)$"
    ): r"ys",
    re.compile(
        r"(?:tuisimme|tuisitte|tuisivat|tukaamme|tunemme|duttiin|tuisit|tuivat|tukoon|tukoot|duimme|duitte|dutaan|tunen|tuisi|tukaa|tunee|tunet|dumme|dutte|duttu|duit|tui)$"
    ): r"tua",
    re.compile(
        r"(?:takaamme|taakseen|tanemme|tanette|tanevat|takoot|tanen|tanut|takaa|tanee|tanet|taen)$"
    ): r"taa",
    re.compile(
        r"(?:uuksissa|uuksista|uudeksi|uudelle|uudella|uudelta|uudesta|uudessa|uudetta|uutemme|uutenne|uutensa|uuksiin|uuteen|uutena|uuteni|uutesi|uuden|uudet)$"
    ): r"uus",
    re.compile(
        r"(?:täkäämme|tääkseen|tänemme|tänette|tänevät|tämällä|tämässä|tämästä|tämättä|täkööt|tämään|täkoot|täkää|tänee|tänen|tänet|tänyt|täen|tämä)$"
    ): r"tää",
    re.compile(
        r"(?:laiseksi|laisella|laiselle|laiselta|laisessa|laisesta|laisetta|laisiksi|laisilla|laisille|laisilta|laisissa|laisista|laisitta|laisensa|laisenne|laiseen|laisena|laisten|laisina|laiseni|laisesi|laisien|laisen|laiset|laisia)$"
    ): r"lainen",
    re.compile(r"(?:llisiksi|llisille|llisiin|llisien)$"): r"llinen",
    re.compile(
        r"(?:tukseksi|tukselle|tuksella|tukselta|tuksessa|tuksesta|tuksetta|tuksissa|tuksista|tuksenne|tuksensa|tuksena|tuksiin|tukseni|tuksesi|tusten)$"
    ): r"tus",
    re.compile(
        r"(?:ijoineen|ijoiksi|ijoilla|ijoille|ijoilta|ijoissa|ijoista|ijoitta|ijoihin|ijoiden|ijoina|ijoita|ijain|ijasi|ijoin|ijat)$"
    ): r"ija",
    re.compile(
        r"(?:auksista|auksissa|aukseksi|aukselle|auksella|aukselta|auksessa|auksesta|auksetta|auksenne|auksensa|auksiin|aukseen|auksena|aukseni|auksesi|auksen|austen)$"
    ): r"aus",
    re.compile(
        r"(?:ttomissa|ttomitta|ttomiksi|ttomilla|ttomille|ttomilta|ttomista|ttomamme|ttomanne|ttomansa|ttomiin|ttomien|ttomina|ttomani|ttomasi|ttomine|tonten|ttomat|ttomia)$"
    ): r"ton",
    re.compile(r"(?:llakseen|ltaneen|lkaamme|llevat|llessa)$"): r"lla",
    re.compile(
        r"(?:oikaamme|oitaneen|oitakoon|oitaessa|oinemme|oinette|oinevat|oitaman|oidessa|oitava|oitiin|oikoon|oikoot|oinee|oinet)$"
    ): r"oida",
    re.compile(
        r"(?:tyisimme|tyisitte|tyisivät|tykäämme|tyäkseen|tynemme|tynette|tynevät|tyisit|tyivät|tyköön|tykööt|tyessä|tykoon|tykoot|tyen)$"
    ): r"tyä",
    re.compile(
        r"(?:yyksissä|yydeksi|yydelle|yydessä|yydellä|yydeltä|yydestä|yydettä|yytemme|yytenne|yytensä|yyksiin|yyteen|yytenä|yyteni|yytesi|yyden|yydet)$"
    ): r"yys",
    re.compile(
        r"(?:inneilla|inneilta|inneissa|inneista|inneitta|inniksi|innille|innilla|innilta|innissa|innista|innitta|innein|inteja|innin|innit)$"
    ): r"inti",
    re.compile(
        r"(?:ttamalla|ttamassa|ttamasta|ttamatta|ttamaan|ttivat|ttama)$"
    ): r"ttaa",
    re.compile(
        r"(?:ilisivat|iltakoon|ilemalla|ilemassa|ilemasta|ilematta|iltaessa|ilemaan|iltaman|ilivat|iltava|ileman)$"
    ): r"illa",
    re.compile(r"(?:attaneen|annemme|atessa|ataan)$"): r"ata",
    re.compile(
        r"(?:tajiksi|tajilla|tajille|tajilta|tajissa|tajista|tajitta|tajien|tajiin|tajina|tajia|tajin)$"
    ): r"taja",
    re.compile(r"(?:teltaman|telkaa)$"): r"tella",
    re.compile(
        r"(?:stamalla|stamassa|stamasta|stamatta|stetaan|stamaan|statte|stivat|stama)$"
    ): r"staa",
    re.compile(
        r"(?:ltäisiin|lläkseen|ltäneen|lkäämme|llevät|llessä|lköön|lkööt)$"
    ): r"llä",
    re.compile(
        r"(?:iiteiksi|iiteille|iitiksi|iitille|iitilla|iitilta|iitissa|iitista|iititta|iitein)$"
    ): r"iitti",
    re.compile(r"(?:utettava|utettiin|utetaan|utatte|utitte)$"): r"uttaa",
    re.compile(r"(?:iineihin|iineiksi|iineille|iineina|iinein|iineja)$"): r"iini",
    re.compile(r"(?:ismeihin|ismeiksi|ismeille|ismeina|ismein|ismeja)$"): r"ismi",
    re.compile(r"(?:idakseen|idaan)$"): r"ida",
    re.compile(r"(?:tyksissä|tyksiin)$"): r"tys",
    re.compile(r"(?:ytettiin|ytettävä|ytetään)$"): r"yttää",
    re.compile(
        r"(?:liseksi|liselle|lisemme|lisenne|lisella|liselta|lisessa|lisesta|lisetta|lisilta|lisilla|lisissa|lisista|lisitta|lisensa|liseen|listen|liseni|lisesi|lisena|lisina|lisen|liset|lisia)$"
    ): r"linen",
    re.compile(
        r"(?:oiseksi|oisella|oiselle|oiselta|oisessa|oisesta|oisetta|oisemme|oisenne|oisensa|oiseen|oisena|oisten|oiseni|oisesi|oisen|oiset)$"
    ): r"oinen",
    re.compile(r"(?:ajineen|ajaan|ajana|ajain|ajasi|ajaa)$"): r"aja",
    re.compile(r"(?:takseen|tkaamme|nnevat)$"): r"ta",
    re.compile(
        r"(?:uiseksi|uisella|uiselle|uiselta|uisessa|uisesta|uisetta|uisemme|uisenne|uisensa|uiseen|uisena|uisten|uiseni|uisesi|uisen|uiset)$"
    ): r"uinen",
    re.compile(
        r"(?:lyineen|lyihin|lyiden|lyinä|lynne|lynsä|lyitä|lyni|lysi|lyyn|lyjä|lynä|lyä)$"
    ): r"ly",
    re.compile(r"(?:uakseen|unette|unevat)$"): r"ua",
    re.compile(
        r"(?:taiseen|taisena|taisien|taiseni|taisesi|taisina|taisen|taiset|taisia)$"
    ): r"tainen",
    re.compile(r"(?:eisemme|eisenne|eiseen|eiseni|eisesi|eisen|eiset)$"): r"einen",
    re.compile(r"(?:kkeiden|kkeiksi|kkeemme|kkeenne|kkeeni|kkeesi|kkeet)$"): r"ke",
    re.compile(
        r"(?:maiseen|maisena|maisina|maiseni|maisesi|maisien|maisen)$"
    ): r"mainen",
    re.compile(r"(?:kaisien|kaiseni|kaisesi|kaisia)$"): r"kainen",
    re.compile(r"(?:täkseen|tessä|tänä)$"): r"tä",
    re.compile(r"(?:stuksen)$"): r"stus",
    re.compile(r"(?:utuessa)$"): r"utua",
    re.compile(r"(?:utuksen)$"): r"utus",
    re.compile(r"(?:ituksen)$"): r"itus",
    re.compile(r"(?:isellä|iseltä|isessä|isestä|isettä|isensä|isine|isenä)$"): r"inen",
    re.compile(r"(?:ttimme|ttinne|ttinsa|ttinsä|ttini|ttisi|tteja|ttejä)$"): r"tti",
    re.compile(
        r"(?:tiolla|tiolle|tiolta|tiossa|tiosta|tiotta|tiona|tiota|tioni|tion)$"
    ): r"tio",
    re.compile(
        r"(?:eluksi|elulla|elulle|elulta|elussa|elutta|elujen|elumme|elunne|elunsa|eluna|eluin|eluun|eluja|eluni|elusi|elut)$"
    ): r"elu",
    re.compile(r"(?:kkanne|kkansa)$"): r"kka",
    re.compile(r"(?:ksellä|kseltä|ksessä|ksestä|ksettä|ksenä)$"): r"s",
    re.compile(r"(?:kkimme|kkinne|kkinsa|kkinsä|kkini|kkisi|kkejä)$"): r"kki",
    re.compile(r"(?:ntamme|ntanne|ntansa|ntasi|ntani)$"): r"nta",
    re.compile(
        r"(?:iluksi|ilulla|ilulle|ilulta|ilussa|ilutta|ilumme|ilunne|ilunsa|ilujen|iluni|ilusi|iluja)$"
    ): r"ilu",
    re.compile(r"(?:stomme|stonne|stonsa|stoni|stosi|stot)$"): r"sto",
    re.compile(r"(?:ntimme|ntinne|ntinsa|ntini|ntisi)$"): r"nti",
    re.compile(r"(?:kkoon)$"): r"kko",
    re.compile(r"(?:ttomme|ttonne|ttonsa|ttona|ttoni|ttosi|ttoa)$"): r"tto",
    # avaan/avana/avasi/avaa (-> ava) dropped: participle obliques want the
    # verb infinitive on UD (huomautettavaa -> huomauttaa)
    re.compile(r"(?:smimme|sminne|sminsa|smini|smisi|smit)$"): r"smi",
    re.compile(r"(?:stinne|stinsa|stini|stisi|steja)$"): r"sti",
    re.compile(r"(?:ikanne|ikojen|ikoja)$"): r"ika",
    re.compile(r"(?:ppimme|ppinne|ppini|ppisi|ppeja)$"): r"ppi",
    re.compile(r"(?:ininsa|inini|inisi|init)$"): r"ini",
    re.compile(r"(?:alamme|alanne|alansa|alani)$"): r"ala",
    re.compile(r"(?:ttivät)$"): r"ttää",
    re.compile(r"(?:jamme|janne|jansa|jani)$"): r"ja",
    re.compile(r"(?:ioksi|iomme|ionne|ionsa|ioon|iosi|iot)$"): r"io",
    re.compile(r"(?:kamme|kasi|kani)$"): r"ka",
    re.compile(
        r"(?:jäksi|jälle|jällä|jältä|jässä|jästä|jämme|jänsä|jänä|jäni|jää|jän)$"
    ): r"jä",
    re.compile(r"(?:iamme|iansa|ianne|iani|iasi)$"): r"ia",
    re.compile(r"(?:komme|konne|konsa|kosi)$"): r"ko",
    # vansa/vani dropped (same participle gap: joutuvansa -> joutua); vamme kept
    re.compile(r"(?:vamme)$"): r"va",
    re.compile(r"(?:töön)$"): r"tö",
    # tujen/tuna dropped (puhdistettuna -> puhdistaa); tunsa/tuni/tusi kept
    re.compile(r"(?:tunsa|tuni|tusi)$"): r"tu",
    re.compile(r"(?:yöhön|yöllä|yöltä|yössä|yöstä|yöttä)$"): r"yö",
    re.compile(r"(?:pujen|pumme|punne|punsa|puni|pusi)$"): r"pu",
    re.compile(r"(?:giaan|giana|giain|giaa|gian|giat)$"): r"gia",
    re.compile(r"(?:hamme|hansa|hani|hasi)$"): r"ha",
    re.compile(r"(?:romme|ronne|ronsa|roon|rosi)$"): r"ro",
    re.compile(r"(?:oksen|okset)$"): r"os",
    re.compile(r"(?:venne|vemme|veni)$"): r"vi",
    re.compile(r"(?:iikan|iikat)$"): r"iikka",
    re.compile(r"(?:oreja|orit)$"): r"ori",
    re.compile(r"(?:tettä)$"): r"te",
    re.compile(r"(?:ellyt)$"): r"ellä",
    re.compile(r"(?:risin)$"): r"rinen",
    re.compile(r"(?:ömme|önsä|önne|ösi|önä|öni|ötä|öä)$"): r"ö",
    re.compile(r"(?:toon)$"): r"to",
    # yjen/vänä/vää dropped (same participle gap: käärittyjen -> kääriä)
    re.compile(r"(?:loon)$"): r"lo",
    re.compile(r"(?:suun)$"): r"su",
    re.compile(r"(?:ikot)$"): r"ikko",
    re.compile(r"(?:rjat)$"): r"rja",
    re.compile(r"(?:mää)$"): r"mä",
}

# idempotence chains, identity lemmas, and OOV invariants
_EXCLUDED = frozenset(
    {
        "heidänlaisiansa",
        "hänenlaisiansa",
        "korkkijällessä",
        "meidänlaisiamme",
        "minunlaisiani",
        "sinunlaisiasi",
        "teidänlaisianne",
        "naimisissa",
        "lukuunottamatta",
        "illumination",
        "keskuudessa",
        "vastatusten",
    }
)


def apply_fi(token: str) -> str | None:
    "Apply pre-defined rules for Finnish."
    # hyphen-elliptic compound lemmas are unreachable by suffix rules
    return apply_rules(
        token, DEFAULT_RULES, min_len=10, caps=True, hyphen=True, excluded=_EXCLUDED
    )
