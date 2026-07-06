import re

from .generic import apply_rules

# Finnish nominal/verbal suffix classes (-nen/-Us/-minen/-ja family nouns,
# -taa/-tää/-ata/-oida/... verb conjugations). Lemma-first build (mine ->
# trim(0.70) -> refine -> subsume): 102 groups, 21.22% coverage, 99.72%
# in-dict. min_len=10 (not the usual 6): shorter tokens are dominated by
# hyphen-elliptic/compound collisions, see the hyphen-guard rationale below.
DEFAULT_RULES = {
    re.compile(
        r"(?:misineen|miseksi|miselle|misiksi|misille|misemme|misenne|misella"
        r"|miselta|misessa|misesta|misetta|misilla|misilta|misissa|misista"
        r"|misitta|misensa|misillä|misiltä|misissä|misistä|misittä|miseen"
        r"|misiin|misten|miseni|misesi|misien|misena|misina|misinä|misen"
        r"|miset|misin|misia|misiä)$"
    ): r"minen",
    re.compile(
        r"(?:uksineen|uksiksi|uksilla|uksille|uksilta|uksitta|uksemme"
        r"|uksina|uksien|uksia|uksin|ukset)$"
    ): r"us",
    re.compile(
        r"(?:yksineen|yksistä|yksiksi|yksille|yksillä|yksiltä|yksittä"
        r"|ykseksi|ykselle|yksemme|yksenne|yksensä|yksinä|yksien|ykseen"
        r"|ykseni|yksesi|yksena|yksin|yksiä|ysten|yksen|ykset)$"
    ): r"ys",
    re.compile(
        r"(?:tuisimme|tuisitte|tuisivat|tukaamme|tunemme|duttiin|tuisit"
        r"|tuivat|tukoon|tukoot|duimme|duitte|dutaan|tunen|tuisi|tukaa"
        r"|tunee|tunet|dumme|dutte|duttu|duit|tui)$"
    ): r"tua",
    re.compile(
        r"(?:takaamme|taakseen|tanemme|tanette|tanevat|dettiin|takoot"
        r"|tanen|tanut|takaa|tanee|tanet|dettu|taen)$"
    ): r"taa",
    re.compile(
        r"(?:uuksissa|uuksista|uudeksi|uudelle|uudella|uudelta|uudesta"
        r"|uudessa|uudetta|uutemme|uutenne|uutensa|uuksiin|uuteen|uutena"
        r"|uuteni|uutesi|uuden|uudet)$"
    ): r"uus",
    re.compile(
        r"(?:täkäämme|tääkseen|tänemme|tänette|tänevät|tämällä|tämässä"
        r"|tämästä|tämättä|täisit|täkööt|tämään|täkoot|täkää|tänee|tänen"
        r"|tänet|tänyt|tänut|täen|tämä)$"
    ): r"tää",
    re.compile(
        r"(?:laiseksi|laisella|laiselle|laiselta|laisessa|laisesta"
        r"|laisetta|laisiksi|laisilla|laisille|laisilta|laisissa|laisista"
        r"|laisitta|laisensa|laisenne|laiseen|laisena|laisten|laisina"
        r"|laiseni|laisesi|laisien|laisen|laiset|laisia)$"
    ): r"lainen",
    re.compile(r"(?:llisiksi|llisille|llisiin|llisien)$"): r"llinen",
    re.compile(
        r"(?:tukseksi|tukselle|tuksella|tukselta|tuksessa|tuksesta"
        r"|tuksetta|tuksissa|tuksista|tuksenne|tuksensa|tuksena|tuksiin"
        r"|tukseni|tuksesi|tusten)$"
    ): r"tus",
    re.compile(
        r"(?:ijoineen|ijoiksi|ijoilla|ijoille|ijoilta|ijoissa|ijoista"
        r"|ijoitta|ijoihin|ijoiden|ijaksi|ijalla|ijalle|ijalta|ijassa"
        r"|ijasta|ijatta|ijoina|ijoita|ijaan|ijana|ijain|ijasi|ijoin"
        r"|ijat)$"
    ): r"ija",
    re.compile(
        r"(?:auksista|auksissa|aukseksi|aukselle|auksella|aukselta"
        r"|auksessa|auksesta|auksetta|auksenne|auksensa|auksiin|aukseen"
        r"|auksena|aukseni|auksesi|auksen|austen)$"
    ): r"aus",
    re.compile(
        r"(?:ttomaksi|ttomalla|ttomalle|ttomalta|ttomassa|ttomasta"
        r"|ttomatta|ttomissa|ttomitta|ttomiksi|ttomilla|ttomille|ttomilta"
        r"|ttomista|ttomamme|ttomanne|ttomansa|ttomaan|ttomana|ttomiin"
        r"|ttomien|ttomina|ttomani|ttomasi|ttomine|ttoman|tonten|ttomat"
        r"|ttomia|tonta)$"
    ): r"ton",
    re.compile(
        r"(?:llakseen|ltaneen|lkaamme|llette|llevat|llessa|lkoot|llen"
        r"|llet|llee)$"
    ): r"lla",
    re.compile(
        r"(?:oikaamme|oitaneen|oitakoon|oitaessa|oinemme|oinette|oinevat"
        r"|oitaman|oidessa|oitava|oitiin|oikoon|oikoot|oinee|oinet)$"
    ): r"oida",
    re.compile(
        r"(?:tyisimme|tyisitte|tyisivät|tykäämme|tyäkseen|tynemme|tynette"
        r"|tynevät|tyisit|tyivät|tyköön|tykööt|tyessä|tykoon|tykoot|tynen"
        r"|tyisi|tykää|tynee|tynet|tyen)$"
    ): r"tyä",
    re.compile(
        r"(?:yyksissä|yydeksi|yydelle|yydessä|yydellä|yydeltä|yydestä"
        r"|yydettä|yytemme|yytenne|yytensä|yyksiin|yyteen|yytenä|yyteni"
        r"|yytesi|yyden|yydet)$"
    ): r"yys",
    re.compile(
        r"(?:inneilla|inneilta|inneissa|inneista|inneitta|inniksi"
        r"|innille|innilla|innilta|innissa|innista|innitta|innein"
        r"|inteja|innin|innit)$"
    ): r"inti",
    re.compile(
        r"(?:ttamalla|ttamassa|ttamasta|ttamatta|ttamaan|ttivat|ttama)$"
    ): r"ttaa",
    re.compile(
        r"(?:ilisimme|ilisitte|ilisivat|iltakoon|ilemalla|ilemassa"
        r"|ilemasta|ilematta|iltaessa|ilemaan|iltaman|ilette|ilisit"
        r"|ilitte|iltiin|ilkoon|ilivat|iltava|ileman)$"
    ): r"illa",
    re.compile(r"(?:attaneen|annemme|atessa|ataan)$"): r"ata",
    re.compile(
        r"(?:tajiksi|tajilla|tajille|tajilta|tajissa|tajista|tajitta"
        r"|tajien|tajiin|tajina|tajia|tajin)$"
    ): r"taja",
    re.compile(
        r"(?:teltaman|ttelemme|ttelette|ttelisin|ttelisit|ttelitte"
        r"|teltiin|telkaa|ttelin|ttelit|ttelee|ttelen|ttelet)$"
    ): r"tella",
    re.compile(
        r"(?:stettiin|stamalla|stamassa|stamasta|stamatta|stetaan"
        r"|stamaan|stitte|statte|stivat|stama)$"
    ): r"staa",
    re.compile(
        r"(?:ltäisiin|lläkseen|ltäneen|lkäämme|llevät|llessä|lköön"
        r"|lkööt)$"
    ): r"llä",
    re.compile(
        r"(?:iiteiksi|iiteille|iitiksi|iitille|iitilla|iitilta|iitissa"
        r"|iitista|iititta|iitein)$"
    ): r"iitti",
    re.compile(r"(?:utettava|utettiin|utetaan|utatte|utitte)$"): r"uttaa",
    re.compile(r"(?:iineihin|iineiksi|iineille|iineina|iinein|iineja)$"): r"iini",
    re.compile(r"(?:ismeihin|ismeiksi|ismeille|ismeina|ismein|ismeja)$"): r"ismi",
    re.compile(r"(?:idakseen|idaan)$"): r"ida",
    re.compile(r"(?:tyksissä|tyksiin)$"): r"tys",
    re.compile(r"(?:ytettiin|ytettävä|ytetään)$"): r"yttää",
    re.compile(r"(?:itettiin|ititte)$"): r"ittää",
    re.compile(
        r"(?:liseksi|liselle|lisemme|lisenne|lisella|liselta|lisessa"
        r"|lisesta|lisetta|lisilta|lisilla|lisissa|lisista|lisitta"
        r"|lisensa|liseen|listen|liseni|lisesi|lisena|lisina|lisen"
        r"|liset|lisia)$"
    ): r"linen",
    re.compile(
        r"(?:oiseksi|oisella|oiselle|oiselta|oisessa|oisesta|oisetta"
        r"|oisemme|oisenne|oisensa|oiseen|oisena|oisten|oiseni|oisesi"
        r"|oisen|oiset)$"
    ): r"oinen",
    re.compile(r"(?:ajineen|ajaan|ajana|ajain|ajasi|ajaa)$"): r"aja",
    re.compile(r"(?:takseen|tkaamme|nnette|nnevat|tkoot)$"): r"ta",
    re.compile(
        r"(?:uiseksi|uisella|uiselle|uiselta|uisessa|uisesta|uisetta"
        r"|uisemme|uisenne|uisensa|uiseen|uisena|uisten|uiseni|uisesi"
        r"|uisen|uiset)$"
    ): r"uinen",
    re.compile(
        r"(?:lyineen|lyihin|lyiden|lyinä|lynne|lynsä|lyitä|lyni|lysi"
        r"|lyyn|lyjä|lynä|lyä)$"
    ): r"ly",
    re.compile(r"(?:uakseen|unette|unevat)$"): r"ua",
    re.compile(
        r"(?:taiseen|taisena|taisien|taiseni|taisesi|taisina|taisen"
        r"|taiset|taisia)$"
    ): r"tainen",
    re.compile(r"(?:eisemme|eisenne|eiseen|eiseni|eisesi|eisen|eiset)$"): r"einen",
    re.compile(r"(?:kkeiden|kkeiksi|kkeemme|kkeenne|kkeeni|kkeesi|kkeet)$"): r"ke",
    re.compile(
        r"(?:maiseen|maisena|maisina|maiseni|maisesi|maisien|maisen)$"
    ): r"mainen",
    re.compile(r"(?:ellemme|elkoon)$"): r"ella",
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
        r"(?:eluksi|elulla|elulle|elulta|elussa|elutta|elujen|elumme"
        r"|elunne|elunsa|eluna|eluin|eluun|eluja|eluni|elusi|elut)$"
    ): r"elu",
    re.compile(r"(?:kkanne|kkansa|kkana)$"): r"kka",
    re.compile(r"(?:ksellä|kseltä|ksessä|ksestä|ksettä|ksenä)$"): r"s",
    re.compile(r"(?:kkimme|kkinne|kkinsa|kkinsä|kkini|kkisi|kkejä)$"): r"kki",
    re.compile(r"(?:ntamme|ntanne|ntansa|ntana|ntasi|ntani)$"): r"nta",
    re.compile(
        r"(?:iluksi|ilulla|ilulle|ilulta|ilussa|ilutta|ilumme|ilunne"
        r"|ilunsa|ilujen|iluni|ilusi|iluja)$"
    ): r"ilu",
    re.compile(r"(?:stomme|stonne|stonsa|stoni|stosi|stot)$"): r"sto",
    re.compile(r"(?:ntimme|ntinne|ntinsa|ntini|ntisi)$"): r"nti",
    re.compile(r"(?:kkoon)$"): r"kko",
    re.compile(r"(?:ttomme|ttonne|ttonsa|ttona|ttoni|ttosi|ttoa)$"): r"tto",
    re.compile(r"(?:avaan|avana|avasi|avaa)$"): r"ava",
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
        r"(?:jäksi|jälle|jällä|jältä|jässä|jästä|jämme|jänsä|jänä|jäni"
        r"|jää|jän)$"
    ): r"jä",
    re.compile(r"(?:iamme|iansa|ianne|iani|iasi)$"): r"ia",
    re.compile(r"(?:komme|konne|konsa|kosi)$"): r"ko",
    re.compile(r"(?:vansa|vamme|vani|vine)$"): r"va",
    re.compile(r"(?:töön)$"): r"tö",
    re.compile(r"(?:tujen|tunsa|tuna|tuni|tusi)$"): r"tu",
    re.compile(r"(?:yöhön|yöllä|yöltä|yössä|yöstä|yöttä)$"): r"yö",
    re.compile(r"(?:pujen|pumme|punne|punsa|puni|pusi)$"): r"pu",
    re.compile(r"(?:giaan|giana|giain|giaa|gian|giat)$"): r"gia",
    re.compile(r"(?:hamme|hansa|hani|hasi|haa)$"): r"ha",
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
    re.compile(r"(?:yjen)$"): r"y",
    re.compile(r"(?:vänä|vää)$"): r"vä",
    re.compile(r"(?:loon)$"): r"lo",
    re.compile(r"(?:suun)$"): r"su",
    re.compile(r"(?:ikot)$"): r"ikko",
    re.compile(r"(?:rjat)$"): r"rja",
    re.compile(r"(?:mää)$"): r"mä",
}

# "-laisia"-class possessives reduce to a non-word the "lainen" cell
# re-fires on (idempotence), plus one "-jälsi" noun; naimisissa/keskuudessa
# are identity lemmas in the dictionary itself; the rest are OOV invariants.
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
        "vähitellen",
        "vastatusten",
    }
)


def apply_fi(token: str) -> str | None:
    "Apply pre-defined rules for Finnish."
    # hyphen-elliptic compounds and '#'-marked UD compound lemmas are
    # unreachable by suffix rules (0/47 on real text despite 98.9% in-dict).
    return apply_rules(
        token, DEFAULT_RULES, min_len=10, caps=True, hyphen=True, excluded=_EXCLUDED
    )
