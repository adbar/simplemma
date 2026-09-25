from .generic import SuffixRules

# idempotence chains, identity lemmas, and OOV invariants
_EXCLUDED = frozenset(
    (
        "heidänlaisiansa hänenlaisiansa korkkijällessä meidänlaisiamme "
        "minunlaisiani sinunlaisiasi teidänlaisianne naimisissa lukuunottamatta "
        "illumination keskuudessa vastatusten".split()
    )
)

# Finnish nominal/verbal suffix classes, mined lemma-first (99.72% in-dict).
# Only harmony-determinate cells survive (a suffix's own vowels fix -taa vs
# -tää); TU/VA-participle oblique cells were dropped (UD wants the verb
# infinitive, not the bare participle). min_len=10: shorter tokens are
# dominated by hyphen-elliptic/compound collisions.
# hyphen-elliptic compound lemmas are unreachable by suffix rules
DEFAULT_RULES = SuffixRules(
    {
        "minen": (
            "misineen miseksi miselle misiksi misille misemme misenne misella"
            " miselta misessa misesta misetta misilla misilta misissa misista"
            " misitta misensa misillä misiltä misissä misistä misittä miseen misiin"
            " misten miseni misesi misien misena misina misinä misen miset misin"
            " misia misiä"
        ),
        "us": (
            "uksineen uksiksi uksilla uksille uksilta uksitta uksemme uksina uksien"
            " uksia uksin ukset"
        ),
        "ys": (
            "yksineen yksistä yksiksi yksille yksillä yksiltä yksittä ykseksi"
            " ykselle yksemme yksenne yksensä yksinä yksien ykseen ykseni yksesi"
            " yksena yksin yksiä ysten yksen ykset"
        ),
        "tua": (
            "tuisimme tuisitte tuisivat tukaamme tunemme duttiin tuisit tuivat"
            " tukoon tukoot duimme duitte dutaan tunen tuisi tukaa tunee tunet dumme"
            " dutte duttu duit tui"
        ),
        "taa": (
            "takaamme taakseen tanemme tanette tanevat takoot tanen tanut takaa"
            " tanee tanet taen"
        ),
        "uus": (
            "uuksissa uuksista uudeksi uudelle uudella uudelta uudesta uudessa"
            " uudetta uutemme uutenne uutensa uuksiin uuteen uutena uuteni uutesi"
            " uuden uudet"
        ),
        "tää": (
            "täkäämme tääkseen tänemme tänette tänevät tämällä tämässä tämästä"
            " tämättä täkööt tämään täkoot täkää tänee tänen tänet tänyt täen tämä"
        ),
        "lainen": (
            "laiseksi laisella laiselle laiselta laisessa laisesta laisetta"
            " laisiksi laisilla laisille laisilta laisissa laisista laisitta"
            " laisensa laisenne laiseen laisena laisten laisina laiseni laisesi"
            " laisien laisen laiset laisia"
        ),
        "llinen": "llisiksi llisille llisiin llisien",
        "tus": (
            "tukseksi tukselle tuksella tukselta tuksessa tuksesta tuksetta"
            " tuksissa tuksista tuksenne tuksensa tuksena tuksiin tukseni tuksesi"
            " tusten"
        ),
        "ija": (
            "ijoineen ijoiksi ijoilla ijoille ijoilta ijoissa ijoista ijoitta"
            " ijoihin ijoiden ijoina ijoita ijain ijasi ijoin ijat"
        ),
        "aus": (
            "auksista auksissa aukseksi aukselle auksella aukselta auksessa"
            " auksesta auksetta auksenne auksensa auksiin aukseen auksena aukseni"
            " auksesi auksen austen"
        ),
        "ton": (
            "ttomissa ttomitta ttomiksi ttomilla ttomille ttomilta ttomista"
            " ttomamme ttomanne ttomansa ttomiin ttomien ttomina ttomani ttomasi"
            " ttomine tonten ttomat ttomia"
        ),
        "lla": "llakseen ltaneen lkaamme llevat llessa",
        "oida": (
            "oikaamme oitaneen oitakoon oitaessa oinemme oinette oinevat oitaman"
            " oidessa oitava oitiin oikoon oikoot oinee oinet"
        ),
        "tyä": (
            "tyisimme tyisitte tyisivät tykäämme tyäkseen tynemme tynette tynevät"
            " tyisit tyivät tyköön tykööt tyessä tykoon tykoot tyen"
        ),
        "yys": (
            "yyksissä yydeksi yydelle yydessä yydellä yydeltä yydestä yydettä"
            " yytemme yytenne yytensä yyksiin yyteen yytenä yyteni yytesi yyden"
            " yydet"
        ),
        "inti": (
            "inneilla inneilta inneissa inneista inneitta inniksi innille innilla"
            " innilta innissa innista innitta innein inteja innin innit"
        ),
        "ttaa": "ttamalla ttamassa ttamasta ttamatta ttamaan ttivat ttama",
        "illa": (
            "ilisivat iltakoon ilemalla ilemassa ilemasta ilematta iltaessa ilemaan"
            " iltaman ilivat iltava ileman"
        ),
        "ata": "attaneen annemme atessa ataan",
        "taja": (
            "tajiksi tajilla tajille tajilta tajissa tajista tajitta tajien tajiin"
            " tajina tajia tajin"
        ),
        "tella": "teltaman telkaa",
        "staa": "stamalla stamassa stamasta stamatta stetaan stamaan statte stivat stama",
        "llä": "ltäisiin lläkseen ltäneen lkäämme llevät llessä lköön lkööt",
        "iitti": (
            "iiteiksi iiteille iitiksi iitille iitilla iitilta iitissa iitista"
            " iititta iitein"
        ),
        "uttaa": "utettava utettiin utetaan utatte utitte",
        "iini": "iineihin iineiksi iineille iineina iinein iineja",
        "ismi": "ismeihin ismeiksi ismeille ismeina ismein ismeja",
        "ida": "idakseen idaan",
        "tys": "tyksissä tyksiin",
        "yttää": "ytettiin ytettävä ytetään",
        "linen": (
            "liseksi liselle lisemme lisenne lisella liselta lisessa lisesta"
            " lisetta lisilta lisilla lisissa lisista lisitta lisensa liseen listen"
            " liseni lisesi lisena lisina lisen liset lisia"
        ),
        "oinen": (
            "oiseksi oisella oiselle oiselta oisessa oisesta oisetta oisemme"
            " oisenne oisensa oiseen oisena oisten oiseni oisesi oisen oiset"
        ),
        "aja": "ajineen ajaan ajana ajain ajasi ajaa",
        "ta": "takseen tkaamme nnevat",
        "uinen": (
            "uiseksi uisella uiselle uiselta uisessa uisesta uisetta uisemme"
            " uisenne uisensa uiseen uisena uisten uiseni uisesi uisen uiset"
        ),
        "ly": "lyineen lyihin lyiden lyinä lynne lynsä lyitä lyni lysi lyyn lyjä lynä lyä",
        "ua": "uakseen unette unevat",
        "tainen": "taiseen taisena taisien taiseni taisesi taisina taisen taiset taisia",
        "einen": "eisemme eisenne eiseen eiseni eisesi eisen eiset",
        "ke": "kkeiden kkeiksi kkeemme kkeenne kkeeni kkeesi kkeet",
        "mainen": "maiseen maisena maisina maiseni maisesi maisien maisen",
        "kainen": "kaisien kaiseni kaisesi kaisia",
        "tä": "täkseen tessä tänä",
        "stus": "stuksen",
        "utua": "utuessa",
        "utus": "utuksen",
        "itus": "ituksen",
        "inen": "isellä iseltä isessä isestä isettä isensä isine isenä",
        "tti": "ttimme ttinne ttinsa ttinsä ttini ttisi tteja ttejä",
        "tio": "tiolla tiolle tiolta tiossa tiosta tiotta tiona tiota tioni tion",
        "elu": (
            "eluksi elulla elulle elulta elussa elutta elujen elumme elunne elunsa"
            " eluna eluin eluun eluja eluni elusi elut"
        ),
        "kka": "kkanne kkansa",
        "s": "ksellä kseltä ksessä ksestä ksettä ksenä",
        "kki": "kkimme kkinne kkinsa kkinsä kkini kkisi kkejä",
        "nta": "ntamme ntanne ntansa ntasi ntani",
        "ilu": (
            "iluksi ilulla ilulle ilulta ilussa ilutta ilumme ilunne ilunsa ilujen"
            " iluni ilusi iluja"
        ),
        "sto": "stomme stonne stonsa stoni stosi stot",
        "nti": "ntimme ntinne ntinsa ntini ntisi",
        "kko": "kkoon",
        "tto": "ttomme ttonne ttonsa ttona ttoni ttosi ttoa",
        # avaan/avana/avasi/avaa (-> ava) dropped: participle obliques want the
        # verb infinitive on UD (huomautettavaa -> huomauttaa)
        "smi": "smimme sminne sminsa smini smisi smit",
        "sti": "stinne stinsa stini stisi steja",
        "ika": "ikanne ikojen ikoja",
        "ppi": "ppimme ppinne ppini ppisi ppeja",
        "ini": "ininsa inini inisi init",
        "ala": "alamme alanne alansa alani",
        "ttää": "ttivät",
        "ja": "jamme janne jansa jani",
        "io": "ioksi iomme ionne ionsa ioon iosi iot",
        "ka": "kamme kasi kani",
        "jä": "jäksi jälle jällä jältä jässä jästä jämme jänsä jänä jäni jää jän",
        "ia": "iamme iansa ianne iani iasi",
        "ko": "komme konne konsa kosi",
        # vansa/vani dropped (same participle gap: joutuvansa -> joutua); vamme kept
        "va": "vamme",
        "tö": "töön",
        # tujen/tuna dropped (puhdistettuna -> puhdistaa); tunsa/tuni/tusi kept
        "tu": "tunsa tuni tusi",
        "yö": "yöhön yöllä yöltä yössä yöstä yöttä",
        "pu": "pujen pumme punne punsa puni pusi",
        "gia": "giaan giana giain giaa gian giat",
        "ha": "hamme hansa hani hasi",
        "ro": "romme ronne ronsa roon rosi",
        "os": "oksen okset",
        "vi": "venne vemme veni",
        "iikka": "iikan iikat",
        "ori": "oreja orit",
        "te": "tettä",
        "ellä": "ellyt",
        "rinen": "risin",
        "ö": "ömme önsä önne ösi önä öni ötä öä",
        "to": "toon",
        # yjen/vänä/vää dropped (same participle gap: käärittyjen -> kääriä)
        "lo": "loon",
        "su": "suun",
        "ikko": "ikot",
        "rja": "rjat",
        "mä": "mää",
    },
    min_len=10,
    caps=True,
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_fi = DEFAULT_RULES.apply
