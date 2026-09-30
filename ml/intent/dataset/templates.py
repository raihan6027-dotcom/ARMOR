"""Prompt templates for the Intent AI dataset (10 classes, Indonesian and English,
for image, video and audio requests).

Each class has action phrases per language and media. A generated prompt combines:
a request verb for the media, a subject reference, an action, and sometimes a
context tail. The team reviews every generated row before final training
(column diperiksa_oleh, see docs/intent-labeling-guide.md).

Keep phrases natural and varied; avoid putting the class name itself in the text.
"""

from __future__ import annotations

MEDIA = ("IMAGE", "VIDEO", "AUDIO")
LANGS = ("id", "en")

# How people ask for each media.
VERBS = {
    "id": {
        "IMAGE": [
            "buat gambar",
            "bikin foto",
            "buatkan gambar",
            "tolong buat foto",
            "hasilkan gambar",
            "bikinin gambar",
        ],
        "VIDEO": [
            "buat video",
            "bikin video",
            "buatkan klip",
            "tolong buat video pendek",
            "hasilkan video",
            "bikinin reels",
        ],
        "AUDIO": [
            "buat audio",
            "bikin rekaman suara",
            "buatkan suara",
            "tolong buat voice note",
            "hasilkan rekaman",
            "bikinin audio",
        ],
    },
    "en": {
        "IMAGE": [
            "make an image",
            "create a picture",
            "generate a photo",
            "please make an image",
            "produce a picture",
            "draw an image",
        ],
        "VIDEO": [
            "make a video",
            "create a clip",
            "generate a short video",
            "please make a video",
            "produce a reel",
            "render a video",
        ],
        "AUDIO": [
            "make an audio clip",
            "create a voice recording",
            "generate audio",
            "please make a voice note",
            "produce a recording",
            "synthesize audio",
        ],
    },
}

SUBJECTS = {
    "id": {
        "self": ["saya", "diri saya", "wajah saya", "foto saya", "suara saya"],
        "other": [
            "orang ini",
            "dia",
            "pria di foto ini",
            "wanita di foto ini",
            "orang di video ini",
            "teman saya ini",
            "tokoh ini",
            "bapak ini",
            "ibu ini",
            "pemilik suara ini",
        ],
    },
    "en": {
        "self": ["me", "myself", "my face", "my photo", "my voice"],
        "other": [
            "this person",
            "him",
            "her",
            "the man in this photo",
            "the woman in this photo",
            "the person in this video",
            "my friend here",
            "this public figure",
            "the owner of this voice",
        ],
    },
}

TAILS = {
    "id": [
        "",
        "",
        "",
        " ya",
        " secepatnya",
        " untuk besok",
        " dengan kualitas bagus",
        " yang terlihat nyata",
        " pakai foto yang saya unggah",
        " dari file ini",
    ],
    "en": [
        "",
        "",
        "",
        " please",
        " asap",
        " for tomorrow",
        " in high quality",
        " that looks real",
        " using the upload",
        " from this file",
    ],
}

# Action phrases per class. {s} = subject reference. Media-specific lists fall
# back to "any" when a media has no dedicated phrasing.
ACTIONS: dict[str, dict[str, dict[str, list[str]]]] = {
    "PERSONAL_CREATION": {
        "id": {
            "any": [
                "avatar kartun dari {s}",
                "ilustrasi anime {s} untuk foto profil",
                "stiker lucu {s} untuk grup keluarga",
                "potret {s} bergaya lukisan cat minyak",
                "{s} sebagai karakter game fantasi untuk koleksi pribadi",
                "kartu ucapan ulang tahun bergambar {s}",
                "versi pixel art {s} untuk wallpaper",
                "{s} dalam gaya komik untuk kenang-kenangan",
            ],
            "VIDEO": [
                "animasi pendek {s} melambaikan tangan untuk ucapan selamat pagi keluarga",
                "video kenangan liburan bersama {s} dengan efek kartun",
            ],
            "AUDIO": [
                "narasi cerita dongeng untuk anak saya dengan {s}",
                "rekaman ucapan selamat ulang tahun untuk ibu dengan {s}",
                "narasi vlog perjalanan pakai {s}",
            ],
        },
        "en": {
            "any": [
                "a cartoon avatar of {s}",
                "an anime illustration of {s} for my profile",
                "a funny sticker of {s} for the family chat",
                "an oil painting style portrait of {s}",
                "{s} as a fantasy game character for my own collection",
                "a birthday card featuring {s}",
                "a pixel art version of {s} for a wallpaper",
            ],
            "VIDEO": [
                "a short animation of {s} waving good morning to the family",
                "a holiday memories clip of {s} with cartoon effects",
            ],
            "AUDIO": [
                "a bedtime story narration for my kid using {s}",
                "a birthday greeting for mom using {s}",
                "a travel vlog narration with {s}",
            ],
        },
    },
    "PERSONAL_EDITING": {
        "id": {
            "any": [
                "cerahkan foto {s}",
                "hapus jerawat di wajah {s}",
                "ganti latar belakang foto {s} jadi pantai",
                "rapikan rambut {s} di foto ini",
                "perbaiki pencahayaan foto {s}",
                "hilangkan orang lain di belakang {s}",
                "haluskan kulit {s} sedikit saja",
                "ubah warna baju {s} jadi biru",
            ],
            "VIDEO": [
                "stabilkan video {s} yang goyang",
                "potong bagian awal video {s}",
                "perbaiki warna video {s} yang terlalu gelap",
            ],
            "AUDIO": [
                "kurangi suara bising di rekaman {s}",
                "naikkan volume rekaman {s}",
                "hapus jeda panjang di rekaman {s}",
            ],
        },
        "en": {
            "any": [
                "brighten the photo of {s}",
                "remove the acne from {s}",
                "change the background behind {s} to a beach",
                "tidy up the hair of {s}",
                "fix the lighting on {s}",
                "remove the people behind {s}",
                "slightly smooth the skin of {s}",
                "change the shirt color of {s} to blue",
            ],
            "VIDEO": [
                "stabilize the shaky video of {s}",
                "trim the start of the video of {s}",
                "color correct the dark video of {s}",
            ],
            "AUDIO": [
                "remove background noise from the recording of {s}",
                "boost the volume of the recording of {s}",
                "cut long pauses from the recording of {s}",
            ],
        },
    },
    "SATIRE_PARODY": {
        "id": {
            "any": [
                "karikatur {s} dengan kepala besar",
                "parodi {s} sebagai superhero yang kikuk",
                "meme lucu {s} untuk lelucon di grup",
                "komik satir tentang {s} dan kebiasaannya",
                "versi kartun {s} yang jelas bercanda",
                "{s} digambar sebagai tokoh dongeng yang konyol",
            ],
            "VIDEO": [
                "sketsa parodi animasi {s} menari dengan gaya kartun",
                "video meme {s} bergaya kartun yang jelas lelucon",
            ],
            "AUDIO": [
                "lagu parodi lucu tentang {s} dengan suara kartun",
                "sketsa komedi suara bertema {s} yang jelas lelucon",
            ],
        },
        "en": {
            "any": [
                "a caricature of {s} with a huge head",
                "a parody of {s} as a clumsy superhero",
                "a funny meme of {s} for a group joke",
                "a satirical comic about {s} and their habits",
                "an obviously joking cartoon of {s}",
                "{s} drawn as a silly fairy tale character",
            ],
            "VIDEO": [
                "an animated parody sketch of {s} dancing in cartoon style",
                "a cartoon meme video of {s} that is clearly a joke",
            ],
            "AUDIO": [
                "a funny parody song about {s} in a cartoon voice",
                "a comedy audio sketch about {s} that is clearly a joke",
            ],
        },
    },
    "COMMERCIAL_USE": {
        "id": {
            "any": [
                "iklan produk kopi dengan {s}",
                "poster promosi toko baju memakai {s}",
                "{s} sedang mengendorse skincare kami",
                "materi promosi diskon akhir tahun dengan {s}",
                "banner jualan online bergambar {s}",
                "{s} memegang botol minuman merek kami untuk iklan",
            ],
            "VIDEO": [
                "video iklan {s} mencoba aplikasi kami",
                "video testimoni {s} tentang produk pelangsing kami",
                "iklan televisi dengan {s} sebagai bintangnya",
            ],
            "AUDIO": [
                "jingle iklan radio dengan {s}",
                "voice over iklan produk kami memakai {s}",
                "pengumuman promo toko dengan {s}",
            ],
        },
        "en": {
            "any": [
                "an ad for our coffee with {s}",
                "a promo poster for our clothing store using {s}",
                "{s} endorsing our skincare line",
                "year end sale promo material with {s}",
                "an online shop banner featuring {s}",
                "{s} holding our drink bottle for an advert",
            ],
            "VIDEO": [
                "a commercial of {s} trying our app",
                "a testimonial video of {s} about our diet product",
                "a TV ad starring {s}",
            ],
            "AUDIO": [
                "a radio jingle with {s}",
                "a product voice over using {s}",
                "a store promo announcement with {s}",
            ],
        },
    },
    "POLITICAL_USE": {
        "id": {
            "any": [
                "poster kampanye pemilu dengan {s}",
                "{s} mendukung calon bupati nomor dua",
                "baliho partai bergambar {s}",
                "ajakan mencoblos calon kami dengan {s}",
                "{s} berdiri di podium kampanye dengan bendera partai",
                "spanduk dukungan pilkada memakai {s}",
            ],
            "VIDEO": [
                "video kampanye {s} mengajak warga memilih calon kami",
                "video {s} berpidato di acara partai",
            ],
            "AUDIO": [
                "pesan kampanye suara dengan {s} mengajak memilih",
                "rekaman dukungan politik dengan {s} untuk disebar ke grup",
            ],
        },
        "en": {
            "any": [
                "an election campaign poster with {s}",
                "{s} endorsing candidate number two",
                "a party billboard featuring {s}",
                "a get out the vote message with {s}",
                "{s} at a campaign podium with party flags",
                "a local election banner using {s}",
            ],
            "VIDEO": [
                "a campaign video of {s} urging people to vote for our candidate",
                "a video of {s} giving a party speech",
            ],
            "AUDIO": [
                "a campaign robocall with {s} asking people to vote",
                "a political endorsement voice message with {s}",
            ],
        },
    },
    "IMPERSONATION": {
        "id": {
            "any": [
                "{s} seolah mengatakan hal yang tidak pernah dia ucapkan",
                "{s} berpura-pura menjadi orang lain untuk menipu teman",
                "{s} mengaku sebagai pejabat di foto ini",
                "{s} menulis pernyataan resmi atas namanya",
                "{s} menyamar sebagai petugas bank",
            ],
            "VIDEO": [
                "{s} lip-sync mengumumkan pengunduran diri",
                "{s} membaca pernyataan permintaan maaf yang tidak pernah dia buat",
                "{s} seolah mengumumkan kebijakan baru",
            ],
            "AUDIO": [
                "rekaman {s} mengatakan dia setuju menjual rumahnya",
                "suara {s} menelepon seolah dari kantor polisi",
                "{s} mengucapkan kalimat yang tidak pernah dia katakan",
            ],
        },
        "en": {
            "any": [
                "{s} appearing to say things they never said",
                "{s} pretending to be someone else to fool friends",
                "{s} posing as a government official",
                "{s} issuing an official statement in their name",
                "{s} impersonating a bank officer",
            ],
            "VIDEO": [
                "{s} lip-syncing a resignation announcement",
                "{s} reading an apology they never made",
                "{s} announcing a new policy they never announced",
            ],
            "AUDIO": [
                "{s} saying they agree to sell their house",
                "{s} calling as if from the police station",
                "{s} saying words they never said",
            ],
        },
    },
    "DEFAMATION": {
        "id": {
            "any": [
                "{s} memakai baju tahanan dan diborgol",
                "{s} sedang mabuk di pinggir jalan",
                "{s} menerima amplop suap",
                "{s} memakai narkoba di pesta",
                "{s} tertangkap basah mencuri",
                "{s} digiring polisi karena korupsi",
                "{s} terlihat bodoh dan dipermalukan di depan umum",
            ],
            "VIDEO": [
                "{s} ditangkap polisi di rumahnya",
                "{s} berkelahi dan memukul orang tua",
                "{s} mengaku menerima uang haram",
            ],
            "AUDIO": [
                "rekaman {s} mengaku korupsi",
                "suara {s} menghina warga kampungnya",
                "{s} mengaku pernah mencuri uang kas",
            ],
        },
        "en": {
            "any": [
                "{s} in a prison jumpsuit and handcuffs",
                "{s} drunk on the street",
                "{s} taking a bribe envelope",
                "{s} using drugs at a party",
                "{s} caught stealing",
                "{s} being arrested for corruption",
                "{s} humiliated and looking stupid in public",
            ],
            "VIDEO": [
                "{s} being arrested at home",
                "{s} fighting and hitting an old man",
                "{s} admitting to taking dirty money",
            ],
            "AUDIO": [
                "{s} confessing to corruption",
                "{s} insulting their own neighbors",
                "{s} admitting they stole cash",
            ],
        },
    },
    "SEXUAL_EXPLICIT": {
        "id": {
            "any": [
                "{s} tanpa busana",
                "{s} telanjang di kamar",
                "{s} memakai pakaian dalam dengan pose menggoda",
                "{s} dalam adegan dewasa",
                "{s} bugil di kolam renang",
                "foto vulgar {s}",
                "{s} dalam pose erotis",
            ],
            "VIDEO": ["{s} dalam video dewasa", "{s} membuka baju perlahan"],
            "AUDIO": ["rekaman desahan dengan {s}", "{s} mengucapkan kalimat mesum"],
        },
        "en": {
            "any": [
                "{s} naked",
                "{s} nude in the bedroom",
                "{s} in lingerie in a seductive pose",
                "{s} in an adult scene",
                "{s} with no clothes at the pool",
                "a porn image of {s}",
                "{s} in an erotic pose",
            ],
            "VIDEO": ["{s} in an adult video", "{s} slowly undressing"],
            "AUDIO": ["moaning sounds with {s}", "{s} saying explicit sexual lines"],
        },
    },
    "DECEPTIVE": {
        "id": {
            "any": [
                "{s} membagikan bantuan sosial lalu meminta biaya admin",
                "{s} mengumumkan undian berhadiah palsu",
                "{s} menawarkan investasi untung pasti",
                "{s} meminta transfer uang ke rekening baru",
                "{s} menyebarkan kabar bencana yang tidak terjadi",
                "{s} menjual tiket konser palsu",
            ],
            "VIDEO": [
                "{s} mengumumkan pembagian BLT dan minta biaya pendaftaran",
                "{s} mempromosikan skema arisan berantai",
                "{s} mengabarkan gempa besar yang tidak pernah terjadi",
            ],
            "AUDIO": [
                "pesan suara {s} meminta keluarganya mengirim uang darurat",
                "{s} menelepon korban minta kode OTP",
                "{s} minta transfer uang karena kecelakaan",
            ],
        },
        "en": {
            "any": [
                "{s} handing out aid and asking for an admin fee",
                "{s} announcing a fake lottery prize",
                "{s} offering a guaranteed profit investment",
                "{s} asking for money to be sent to a new account",
                "{s} spreading news of a disaster that never happened",
                "{s} selling fake concert tickets",
            ],
            "VIDEO": [
                "{s} announcing cash aid that needs a registration fee",
                "{s} promoting a pyramid scheme",
                "{s} reporting an earthquake that never happened",
            ],
            "AUDIO": [
                "{s} asking family to wire emergency money",
                "{s} calling a victim for their OTP code",
                "{s} asking for a transfer after a fake accident",
            ],
        },
    },
    "UNCERTAIN": {
        "id": {
            "any": [
                "sesuatu dari {s}",
                "yang menarik pakai {s}",
                "versi lain {s}",
                "konten dengan {s}",
                "olah {s} jadi sesuatu",
                "{s} tapi beda",
                "apa saja dengan {s}",
                "kreasikan {s}",
            ],
        },
        "en": {
            "any": [
                "something with {s}",
                "something interesting using {s}",
                "another version of {s}",
                "content with {s}",
                "turn {s} into something",
                "{s} but different",
                "whatever you like with {s}",
                "get creative with {s}",
            ],
        },
    },
}

# Classes where the subject is usually the requester's own identity.
SELF_CLASSES = {"PERSONAL_CREATION", "PERSONAL_EDITING"}
