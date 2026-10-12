"""Static reference data used to bootstrap the platform.

Everything here is idempotent seed content that can safely be re-run.
"""

# --------------------------------------------------------------------------- #
# 47 Counties of Kenya
# --------------------------------------------------------------------------- #
COUNTIES = [
    ("001", "Mombasa", "Coast"),
    ("002", "Kwale", "Coast"),
    ("003", "Kilifi", "Coast"),
    ("004", "Tana River", "Coast"),
    ("005", "Lamu", "Coast"),
    ("006", "Taita Taveta", "Coast"),
    ("007", "Garissa", "North Eastern"),
    ("008", "Wajir", "North Eastern"),
    ("009", "Mandera", "North Eastern"),
    ("010", "Marsabit", "Eastern"),
    ("011", "Isiolo", "Eastern"),
    ("012", "Meru", "Eastern"),
    ("013", "Tharaka-Nithi", "Eastern"),
    ("014", "Embu", "Eastern"),
    ("015", "Kitui", "Eastern"),
    ("016", "Machakos", "Eastern"),
    ("017", "Makueni", "Eastern"),
    ("018", "Nyandarua", "Central"),
    ("019", "Nyeri", "Central"),
    ("020", "Kirinyaga", "Central"),
    ("021", "Murang'a", "Central"),
    ("022", "Kiambu", "Central"),
    ("023", "Turkana", "Rift Valley"),
    ("024", "West Pokot", "Rift Valley"),
    ("025", "Samburu", "Rift Valley"),
    ("026", "Trans Nzoia", "Rift Valley"),
    ("027", "Uasin Gishu", "Rift Valley"),
    ("028", "Elgeyo-Marakwet", "Rift Valley"),
    ("029", "Nandi", "Rift Valley"),
    ("030", "Baringo", "Rift Valley"),
    ("031", "Laikipia", "Rift Valley"),
    ("032", "Nakuru", "Rift Valley"),
    ("033", "Narok", "Rift Valley"),
    ("034", "Kajiado", "Rift Valley"),
    ("035", "Kericho", "Rift Valley"),
    ("036", "Bomet", "Rift Valley"),
    ("037", "Kakamega", "Western"),
    ("038", "Vihiga", "Western"),
    ("039", "Bungoma", "Western"),
    ("040", "Busia", "Western"),
    ("041", "Siaya", "Nyanza"),
    ("042", "Kisumu", "Nyanza"),
    ("043", "Homa Bay", "Nyanza"),
    ("044", "Migori", "Nyanza"),
    ("045", "Kisii", "Nyanza"),
    ("046", "Nyamira", "Nyanza"),
    ("047", "Nairobi", "Nairobi"),
]


# --------------------------------------------------------------------------- #
# Languages and dialects.
# Each entry: (language, native_name, iso, [dialects], [county names])
# --------------------------------------------------------------------------- #
LANGUAGES = [
    ("Kiswahili", "Kiswahili", "swa",
     ["Mswahili", "Kiunguja", "Kimvita", "Kiamu", "Sheng", "Kipemba"],
     ["Mombasa", "Kwale", "Kilifi", "Lamu", "Tana River", "Nairobi"]),
    ("Kikuyu", "Gĩkũyũ", "kik",
     ["Standard Kikuyu", "Ndia", "Gichugu", "Mathira", "Kabete"],
     ["Kiambu", "Murang'a", "Nyeri", "Kirinyaga", "Nyandarua"]),
    ("Kimeru", "Kĩmĩrũ", "mer",
     ["Standard Kimeru", "Imenti", "Tigania", "Igembe", "Muiname"],
     ["Meru", "Tharaka-Nithi", "Isiolo"]),
    ("Kiembu", "Kĩembu", "ebu", ["Mbeere"], ["Embu"]),
    ("Kitharaka", "Kĩtharaka", "thk", ["Tharaka", "Chuka"], ["Tharaka-Nithi"]),
    ("Kikamba", "Kĩkamba", "kam",
     ["Standard Kikamba", "Kitui", "Machakos", "Makueni", "Mbooni"],
     ["Machakos", "Kitui", "Makueni"]),
    ("Ekegusii", "Ekegusii", "guz",
     ["Standard Ekegusii", "Maate", "Etango", "Kisii"],
     ["Kisii", "Nyamira"]),
    ("Dholuo", "Dholuo", "luo",
     ["Standard Dholuo", "Trans-Yala", "Ugenya", "Alego", "Kano"],
     ["Kisumu", "Siaya", "Homa Bay", "Migori"]),
    ("Luhya", "Oluluhya", "luy",
     ["Bukusu", "Wanga", "Maragoli", "Idakho", "Isukha", "Samia", "Tachoni", "Nyala"],
     ["Kakamega", "Vihiga", "Bungoma", "Busia", "Trans Nzoia"]),
    ("Kalenjin", "Kalenjin", "kln",
     ["Kipsigis", "Nandi", "Tugen", "Keiyo", "Marakwet", "Sabaot", "Pokot", "Ogiek"],
     ["Uasin Gishu", "Nandi", "Kericho", "Bomet", "Baringo", "Elgeyo-Marakwet",
      "West Pokot", "Trans Nzoia", "Narok"]),
    ("Maasai", "Maa", "mas",
     ["Standard Maasai", "Purko", "Keekonyokie", "Kisonko", "Loitokitok"],
     ["Kajiado", "Narok"]),
    ("Samburu", "Samburu", "saq", ["Standard Samburu"], ["Samburu"]),
    ("Somali", "Soomaali", "som",
     ["Standard Somali", "Rahanweyn", "Benaadir"],
     ["Garissa", "Wajir", "Mandera"]),
    ("Borana", "Borana", "gax",
     ["Standard Borana", "Gabbra", "Sakuye"], ["Marsabit", "Isiolo"]),
    ("Rendille", "Rendille", "rel", ["Standard Rendille"], ["Marsabit"]),
    ("Turkana", "Ng'aturkana", "tuv", ["Standard Turkana"], ["Turkana"]),
    ("Teso", "Ateso", "teo", ["Standard Ateso"], ["Busia"]),
    ("Kuria", "Ekiguria", "kuj", ["Simbiti", "Standard Kuria"], ["Migori"]),
    ("Mijikenda", "Mijikenda", "nyf",
     ["Giriama", "Duruma", "Digo", "Rabai", "Chonyi", "Kambe", "Ribe"],
     ["Kilifi", "Kwale", "Mombasa"]),
    ("Taita", "Kitaita", "dav",
     ["Kidawida", "Kisagalla", "Kasigau"], ["Taita Taveta"]),
]


# --------------------------------------------------------------------------- #
# Cybersecurity glossary (English + Kiswahili reference).
# (slug, english_name, english_definition, swahili_name, swahili_definition, source_column)
# --------------------------------------------------------------------------- #
GLOSSARY = [
    (
        "phishing",
        "Phishing",
        "A fraudulent message, email, SMS or website that impersonates a trusted "
        "person or organisation to trick someone into revealing passwords, money "
        "or personal information.",
        "Usanifu (Phishing)",
        "Ujumbe, barua pepe, SMS au tovuti ya udanganyifu inayojifanya kuwa mtu au "
        "taasisi inayoaminika ili kumtia mtu ujanjaujanja afichue nywila, pesa au "
        "taarifa binafsi.",
        "Translate: Phishing",
    ),
    (
        "malware",
        "Malware",
        "Any software intentionally designed to cause damage, gain unauthorised "
        "access, or disrupt a device, network or data.",
        "Programu hasidi",
        "Programu yoyote iliyoundwa kwa nia ya kuharibu, kupata ufikiaji bila "
        "idhini, au kuvuruga kifaa, mtandao au data.",
        "Translate: Malware",
    ),
    (
        "spyware",
        "Spyware",
        "Software that secretly gathers information about a person's activity, "
        "such as browsing, keystrokes or credentials, and sends it to a third party.",
        "Programu pelelezi",
        "Programu inayokusanya kwa siri taarifa kuhusu shughuli za mtu, kama vile "
        "kupita kwenye mtandao au kuingiza nywila, na kuzipeleka kwa mtu mwingine.",
        "Translate: Spyware",
    ),
    (
        "ransomware",
        "Ransomware",
        "Malicious software that locks or encrypts files, data or a device and "
        "demands payment (a ransom) before restoring access.",
        "Programu za fidia",
        "Programu hasidi inayofunga au kusimba faili, data au kifaa na kudai "
        "malipo (fidia) kabla ya kurudisha ufikiaji.",
        "Translate: Ransomware",
    ),
    (
        "trojan",
        "Trojan",
        "Malware disguised as legitimate, useful software so that a user installs "
        "it voluntarily, after which it performs harmful actions.",
        "Trojan (programu ya udanganyifu)",
        "Programu hasidi inayojifanya kuwa programu halali na muhimu ili "
        "mtumiaji aiingize mwenyewe, kisha ifanye vitendo hatarishi.",
        "Translate: Trojan",
    ),
    (
        "virus",
        "Virus",
        "A type of malware that attaches itself to files or programs and spreads "
        "when those files are opened, damaging or altering a system.",
        "Virusi",
        "Aina ya programu hasidi inayojishikiza kwenye faili au programu na "
        "kuenea pale faili zinapofunguliwa, ikiharibu au kubadilisha mfumo.",
        "Translate: Virus",
    ),
    (
        "worm",
        "Worm",
        "Self-replicating malware that spreads automatically across devices and "
        "networks without needing a host file or user action.",
        "Mdudu (worm)",
        "Programu hasidi inayojizalisha na kuenea yenyewe kwenye vifaa na "
        "mitandao bila kutegemea faili mwenyeji au hatua ya mtumiaji.",
        "Translate: Worm",
    ),
    (
        "social-engineering",
        "Social Engineering",
        "Manipulating people psychologically into revealing confidential "
        "information or performing actions that compromise security.",
        "Uhandisi wa kijamii",
        "Kuwanasihi watu kisaikolojia wafichue taarifa za siri au wafanye "
        "vitendo vinavyoharibu usalama.",
        "Translate: Social Engineering",
    ),
    (
        "password-security",
        "Password Security",
        "Practices that keep passwords strong, unique and secret so that accounts "
        "cannot be accessed by unauthorised people.",
        "Usalama wa nywila",
        "Mbinu zinazohakikisha nywila ni imara, za kipekee na za siri ili akaunti "
        "zisifikiliwe na watu wasioidhinishwa.",
        "Translate: Password Security",
    ),
    (
        "identity-theft",
        "Identity Theft",
        "When someone steals another person's personal information and uses it to "
        "pretend to be them, often to access accounts or commit fraud.",
        "Wizi wa utambulisho",
        "Wakati mtu anaiba taarifa binafsi za mtu mwingine na kuzitumia kujifanya "
        "yeye, mara nyingi ili kufikia akaunti au kufanya udanganyifu.",
        "Translate: Identity Theft",
    ),
    (
        "data-breach",
        "Data Breach",
        "An incident in which confidential or personal data is accessed, leaked "
        "or stolen without authorisation.",
        "Uvujaji wa data",
        "Tukio ambapo data ya siri au binafsi inafikiliwa, inavuja au inaibiwa "
        "bila idhini.",
        "Translate: Data Breach",
    ),
    (
        "two-factor-authentication",
        "Two-Factor Authentication (2FA)",
        "An extra verification step beyond a password, such as a one-time code "
        "sent to a phone, that makes account access more secure.",
        "Uthibitishaji wa hatua mbili",
        "Hatua ya ziada ya uthibitisho zaidi ya nywila, kama msimbo wa mara moja "
        "unaotumwa kwenye simu, unaofanya ufikiaji wa akaunti kuwa salama zaidi.",
        "Translate: Two-Factor Authentication",
    ),
    (
        "firewall",
        "Firewall",
        "A security barrier that monitors and filters incoming and outgoing "
        "network traffic to block unauthorised or dangerous connections.",
        "Kizuizi cha moto (firewall)",
        "Kizuizi cha usalama kinachofuatilia na kuchuja trafiki ya mtandao "
        "inayoingia na kutoka ili kuzuia miunganisho hatarishi.",
        "Translate: Firewall",
    ),
    (
        "encryption",
        "Encryption",
        "Converting readable information into a coded form so that only people "
        "with the correct key can read it.",
        "Usimbaji fiche",
        "Kubadilisha taarifa inayosomeka kuwa msimbo ili watu walio na ufunguo "
        "sahihi pekee waweze kuisoma.",
        "Translate: Encryption",
    ),
    (
        "decryption",
        "Decryption",
        "Turning encrypted (coded) information back into its readable original "
        "form using the correct key.",
        "Kufungua msimbo",
        "Kurudisha taarifa iliyosimbwa (iliyofichwa) kuwa hali yake ya awali "
        "inayosomeka kwa kutumia ufunguo sahihi.",
        "Translate: Decryption",
    ),
    (
        "vpn",
        "VPN (Virtual Private Network)",
        "A service that creates a private, encrypted connection over the "
        "internet, hiding your activity and location from others.",
        "Mtandao wa kibinafsi (VPN)",
        "Huduma inayounda muunganisho wa kibinafsi uliosimbwa juu ya mtandao, "
        "ikificha shughuli na mahali ulipo.",
        "Translate: VPN",
    ),
    (
        "public-wifi-risk",
        "Public Wi-Fi Risk",
        "The danger of using open, unsecured Wi-Fi networks, where attackers may "
        "intercept your data or set up fake hotspots.",
        "Hatari ya Wi-Fi ya umma",
        "Hatari ya kutumia mitandao ya Wi-Fi iliyo wazi na isiyo na usalama, "
        "ambapo washambuliaji wanaweza kunasa data yako au kuweka vituo vya "
        "uongo.",
        "Translate: Public Wi-Fi Risk",
    ),
    (
        "brute-force-attack",
        "Brute Force Attack",
        "A method of guessing passwords or keys by systematically trying many "
        "combinations until the correct one is found.",
        "Shambulio la nguvu (brute force)",
        "Mbinu ya kubahatisha nywila au funguo kwa kujaribu michanganyiko mingi "
        "hadi ipatikane sahihi.",
        "Translate: Brute Force Attack",
    ),
    (
        "ddos-attack",
        "DDoS Attack",
        "A Distributed Denial of Service attack floods a website or service with "
        "traffic from many sources so that it becomes unavailable.",
        "Shambulio la kuzima huduma (DDoS)",
        "Shambulio la kuzima huduma kwa kusambaza trafiki nyingi kutoka vyanzo "
        "vingi hadi tovuti au huduma ishindwe kufanya kazi.",
        "Translate: DDoS Attack",
    ),
    (
        "man-in-the-middle-attack",
        "Man-in-the-Middle Attack",
        "An attack where a criminal secretly intercepts and possibly alters "
        "communication between two parties who believe they are talking directly.",
        "Shambulio la mtu wa kati",
        "Shambulio ambapo mhalifu ananasa na huenda akabadilisha mawasiliano "
        "kati ya watu wawili wanaodhani wanawasiliana moja kwa moja.",
        "Translate: Man-in-the-Middle Attack",
    ),
    (
        "zero-day-vulnerability",
        "Zero-Day Vulnerability",
        "A software weakness that attackers can exploit before the developer is "
        "aware of it or has released a fix.",
        "Udhaifu wa siku sufuri (zero-day)",
        "Udhaifu wa programu ambao washambuliaji wanaweza kutumia kabla mtengenezaji "
        "kujua au kutoa suluhisho.",
        "Translate: Zero-Day Vulnerability",
    ),
    (
        "software-patching",
        "Software Patching",
        "Installing updates released by developers to fix bugs and close security "
        "gaps in software.",
        "Kusasisha programu",
        "Kufunga masasisho yaliyotolewa na watengenezaji ili kurekebisha hitilafu "
        "na kuziba mianya ya usalama katika programu.",
        "Translate: Software Patching",
    ),
    (
        "botnet",
        "Botnet",
        "A network of infected devices, controlled remotely by criminals, used to "
        "send spam or launch attacks without the owners' knowledge.",
        "Mtandao wa roboti (botnet)",
        "Mtandao wa vifaa vilivyoambukizwa, unaodhibitiwa kwa mbali na wahalifu, "
        "unaotumika kutuma taka au kuanzisha mashambulio bila wamiliki kujua.",
        "Translate: Botnet",
    ),
    (
        "clickjacking",
        "Clickjacking",
        "A trick that hides or disguises a link or button so that a user clicks "
        "something harmful without realising it.",
        "Udanganyifu wa mibofyo",
        "Mbinu inayoficha au kufunika kiungo au kitufe ili mtumiaji abonyeze "
        "kitu hatarishi bila kujua.",
        "Translate: Clickjacking",
    ),
    (
        "spoofing",
        "Spoofing",
        "Pretending to be a trusted person, device or website by faking an "
        "identity, such as a caller ID, email address or website address.",
        "Kujifanya mwingine (spoofing)",
        "Kujifanya kuwa mtu, kifaa au tovuti inayoaminika kwa kughushi "
        "utambulisho, kama nambari ya simu, anwani ya barua pepe au tovuti.",
        "Translate: Spoofing",
    ),
    (
        "backdoor",
        "Backdoor",
        "A hidden way of accessing a system that bypasses normal security, often "
        "planted by attackers or left by developers.",
        "Mlango wa nyuma",
        "Njia iliyofichwa ya kuingia kwenye mfumo inayopita usalama wa kawaida, "
        "mara nyingi hupandwa na washambuliaji au kuachwa na watengenezaji.",
        "Translate: Backdoor",
    ),
    (
        "rootkit",
        "Rootkit",
        "Malware that hides itself and other malicious activity deep inside a "
        "system, making it very hard to detect or remove.",
        "Rootkit (programu ya kujificha)",
        "Programu hasidi inayojificha yenyewe na shughuli nyingine hatarishi "
        "ndani ya mfumo, ikifanya iwe vigumu kuigundua au kuiondoa.",
        "Translate: Rootkit",
    ),
    (
        "keylogger",
        "Keylogger",
        "Software or hardware that secretly records every key a person types, "
        "including passwords and messages.",
        "Kirekodi vifunguo (keylogger)",
        "Programu au kifaa kinachorekodi kwa siri kila kitufe mtu anachobonyeza, "
        "ikiwemo nywila na ujumbe.",
        "Translate: Keylogger",
    ),
    (
        "session-hijacking",
        "Session Hijacking",
        "An attack where a criminal takes over an active logged-in session "
        "(often by stealing a cookie or token) to act as the victim.",
        "Utekaji wa kikao (session hijacking)",
        "Shambulio ambapo mhalifu anachukua kikao kinachotumika (mara nyingi kwa "
        "kuiba kuki au tokeni) ili kufanya kama mwathirika.",
        "Translate: Session Hijacking",
    ),
    (
        "cyber-hygiene",
        "Cyber Hygiene",
        "Everyday safe online habits, such as strong passwords, regular updates "
        "and caution with links, that keep people and devices secure.",
        "Usafi wa mtandao",
        "Mazoea salama ya kila siku mtandaoni, kama nywila imara, masasisho ya "
        "mara kwa mara na kuwa mwangalifu na viungo, yanayolinda watu na vifaa.",
        "Translate: Cyber Hygiene",
    ),
]


# --------------------------------------------------------------------------- #
# Awareness messages.
# (slug, english_name, english_definition, swahili_name, swahili_definition, source_column)
# --------------------------------------------------------------------------- #
MESSAGES = [
    (
        "msg-suspicious-links",
        "Do not click suspicious links.",
        "Never open links or attachments from unexpected or unknown senders; "
        "verify the source first and delete the message if in doubt.",
        "Usibonyeze viungo vinavyoshukiwa.",
        "Usifungue viungo au viambatisho kutoka kwa watumaji usiowajua au "
        "usiotarajia; hakikisha chanzo kwanza na ufute ujumbe ikiwa huna uhakika.",
        "Translate: Do not click suspicious links.",
    ),
    (
        "msg-strong-passwords",
        "Use strong passwords.",
        "Create long, unique passwords using a mix of letters, numbers and "
        "symbols, and never reuse the same password on different accounts.",
        "Tumia nywila imara.",
        "Tengeneza nywila ndefu na za kipekee kwa kutumia mchanganyiko wa herufi, "
        "nambari na alama, na usitumie nywila moja kwenye akaunti tofauti.",
        "Translate: Use strong passwords.",
    ),
    (
        "msg-update-software",
        "Update your software.",
        "Keep your operating system, apps and antivirus up to date so that known "
        "security weaknesses are fixed.",
        "Sasisha programu zako.",
        "Kaa ukisasisha mfumo wako wa uendeshaji, programu na kinga ya virusi ili "
        "udhaifu unaojulikana urekebishwe.",
        "Translate: Update your software.",
    ),
    (
        "msg-enable-2fa",
        "Enable two-factor authentication.",
        "Turn on an extra verification step so that a stolen password alone is "
        "not enough to access your account.",
        "Washa uthibitishaji wa hatua mbili.",
        "Washa hatua ya ziada ya uthibitisho ili nywila iliyoibiwa peke yake "
        "isitoshe kufikia akaunti yako.",
        "Translate: Enable two-factor authentication.",
    ),
    (
        "msg-public-wifi",
        "Be careful on public Wi-Fi.",
        "Avoid entering passwords or banking details on open public Wi-Fi; use "
        "mobile data or a trusted VPN instead.",
        "Jihadhari unapotumia Wi-Fi ya umma.",
        "Epuka kuweka nywila au taarifa za benki kwenye Wi-Fi ya umma iliyo "
        "wazi; tumia data ya simu au VPN inayoaminika.",
        "Translate: Be careful on public Wi-Fi.",
    ),
]


# --------------------------------------------------------------------------- #
# Contributor milestones.
# (code, name, description, metric, threshold, points, sort_order)
# --------------------------------------------------------------------------- #
MILESTONES = [
    ("first_translation", "First Translation",
     "Submitted your first community translation.", "submissions", 1, 10, 1),
    ("context_provider", "Context Provider",
     "Explained how translations are used and gave examples.",
     "context_submissions", 3, 15, 2),
    ("five_translations", "Active Contributor",
     "Contributed at least five translations.", "submissions", 5, 25, 3),
    ("first_approval", "Approved Translator",
     "Had a translation approved as canonical.", "approved", 1, 30, 4),
    ("five_approved", "Trusted Translator",
     "Had five translations approved as canonical.", "approved", 5, 60, 5),
    ("polyglot", "Multilingual Contributor",
     "Contributed translations in more than one language.", "languages", 2, 40, 6),
    ("peer_reviewer", "Peer Reviewer",
     "Reviewed and corrected others' submissions.", "reviews", 10, 50, 7),
    ("specialist_reviewer", "Specialist Reviewer",
     "Completed twenty specialist review decisions.", "reviews", 20, 100, 8),
    ("community_voice", "Community Voice",
     "Received strong community support across submissions.",
     "support_received", 25, 40, 9),
]
