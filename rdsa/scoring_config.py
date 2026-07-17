SCORE_VERSION = "v1.1"
THRESHOLDS = {"hot": 85, "qualified": 60, "watch": 35}
POINTS = {"R1": 25, "R2": 20, "R3": 15, "R4": 10, "R5": 8, "R6": 12, "R7": 5, "R8": 5, "R9": 10}
PENALTIES = {"P1": -40, "P2": -40, "P3": -30, "P4": -10, "P5": -10}
SPAM_SIGNALS = ("giveaway", "join sekarang", "modal 100rb", "klik link di bio", "follow + repost")
BROKER_SIGNALS = ("disewakan", "for rent", "wa admin", "many units", "contact us")
# Supply-side / offering phrases: the author is ADVERTISING a unit for rent/sale
# (owner or agent offering), not seeking one. These take priority over demand-side
# "cari/butuh" language. Includes bare forms (e.g. "sewakan" without the "di-" prefix)
# and contextual listing language (availability, asking price, contact invitation).
OFFERING_SIGNALS = (
    "disewakan", "sewakan", "dijual", "jual", "buka opsi", "tersedia unit", "ready unit",
    "unit available", "available for rent", "saya ada unit", "kami ada unit", "punya unit",
    "listing available", "open listing", "unit kami", "unit owner", "pemilik langsung",
    "direct owner", "bisa survey", "jadwal viewing", "harga sewa", "unit furnish",
    "unit furnished", "promo sewa", "silakan hubungi", "dm untuk detail", "wa untuk info",
    "menerima titip", "agent listing", "broker listing", "ada unit", "unit dijual",
    "unit disewakan", "sewa unit", "jual unit", "markup", "under market price",
    "boleh dm", "boleh hubungi",
)
# Structural listing cues: when several co-occur, the post is a listing even without
# an explicit offering verb. Combinations of specs + price + facility + availability +
# contact invitation + listing URL + marketing language.
LISTING_STRUCTURE_SIGNALS = (
    "fasilitas", "facility", "amenities", "spek", "spesifikasi", "spec", "harga", "price",
    "booking", "survey", "tour", "virtual tour", "video tour", "wa", "whatsapp", "dm", "chat",
    "hubungi", "kontak", "contact", "tautan", "link", "url", "bit.ly", "wa.me", "furniture",
    "furnished", "semi furnished", "full furnished", "strategis", "premium", "eksklusif",
    "investasi", "cocok untuk", "ready", "available", "tersedia",
)
# Genuine first-person seeker controls: when present, keep the lead eligible
# (do NOT classify as agent_broker even if a third-party or offering cue is nearby).
# Keep these SPECIFIC (e.g. "untuk saya sendiri") — broad tokens like bare "saya cari"
# or property-description phrases like "untuk tinggal" are excluded: the former also
# appears inside third-party phrases ("client saya cari"); the latter describes a
# property's suitability, not the author's own demand.
GENUINE_SEEKER_CONTROLS = (
    "untuk saya sendiri", "saya dan keluarga", "untuk ditempati", "untuk kami", "buat saya",
)
RELATIVE_BUDGET_SIGNALS = ("murah", "under", "flexible budget", "budget flexible")
# (broker/agent), even when rental intent, location, property type, and budget are explicit.
# These are CONTEXTUAL phrases, not the bare word "client", to avoid catching genuine
# first-person seekers (e.g. "saya cari apartemen untuk saya sendiri").
THIRD_PARTY_DEMAND_SIGNALS = (
    "ada client cari", "client saya cari", "client saya mencari", "untuk client", "untuk klien",
    "klien sedang cari", "ada buyer/tenant cari", "mencarikan unit", "butuh listing",
    "titipan client", "co-broke", "cobroke", "property agent", "broker", "agen properti",
    "saya lagi ada client cari",
)
RENTAL_CONTEXT_SIGNALS = ("apartemen", "apartment", "kontrakan", "kost", "kos", "rumah", "sewa", "rental")
# First-person occupancy / family / school demand — an author who wants to LIVE in the
# unit with their household. These are deliberately specific (not bare "saya cari") so they
# do not catch third-party agents ("client saya cari"). When present with a seeking intent
# and no strong-listing proof, an ambiguous offering-form word (e.g. bare "sewa"/"kontrak")
# must NOT force an agent_broker classification.
GENUINE_SEEKER_HOUSEHOLD = (
    "anakku", "anak saya", "anak kami", "anak akan sekolah", "anak sebentar",
    "mau di sekolahin", "sekolahin anak", "lama nyari", "udah lama nyari",
    "sudah lama nyari", "sudah lama mencari", "lama mencari", "nyari kontrakan",
    "cari kontrakan", "rumah kecil", "kontrakan kecil",
)
# Strong-listing proof: when ANY of these is present, the post is a genuine supply listing,
# NOT a seeker — even if first-person occupancy/family context also appears. Covers explicit
# offering verbs, unit ownership/availability, explicit price (harga sewa + amount), facilities,
# and contact CTA. NOTE: a bare "harga sewa" with NO following amount is the ambiguous seeker
# phrase ("harga sewanya gak terlalu mehol") and is therefore NOT treated as proof.
STRONG_LISTING_SIGNALS = (
    "disewakan", "sewakan", "dijual", "jual", "buka opsi", "menerima titip",
    "agent listing", "broker listing", "cari penyewa", "cari tenant", "butuh penyewa",
    "butuh tenant",
    "ada unit", "saya ada unit", "kami ada unit", "punya unit", "unit available",
    "available for rent", "ready unit", "tersedia unit", "listing available", "open listing",
    "unit kami", "unit owner", "pemilik langsung", "direct owner", "unit disewakan",
    "unit dijual", "sewa unit", "jual unit", "harga sewa",
    "fasilitas", "furniture", "furnished", "amenities", "spek", "spesifikasi",
    "dm untuk detail", "wa untuk info", "silakan hubungi", "boleh dm", "boleh hubungi",
    "wa admin", "contact us",
)
