SCORE_VERSION = "v1.1"
THRESHOLDS = {"hot": 85, "qualified": 60, "watch": 35}
POINTS = {"R1": 25, "R2": 20, "R3": 15, "R4": 10, "R5": 8, "R6": 12, "R7": 5, "R8": 5, "R9": 10}
PENALTIES = {"P1": -40, "P2": -40, "P3": -30, "P4": -10, "P5": -10}
SPAM_SIGNALS = ("giveaway", "join sekarang", "modal 100rb", "klik link di bio", "follow + repost")
BROKER_SIGNALS = ("disewakan", "for rent", "wa admin", "many units", "contact us")
# Third-party-demand phrases: the author is sourcing/placing on behalf of a client
# (broker/agent), even when rental intent, location, property type, and budget are explicit.
# These are CONTEXTUAL phrases, not the bare word "client", to avoid catching genuine
# first-person seekers (e.g. "saya cari apartemen untuk saya sendiri").
THIRD_PARTY_DEMAND_SIGNALS = (
    "ada client cari", "client saya mencari", "untuk client", "untuk klien",
    "klien sedang cari", "ada buyer/tenant cari", "mencarikan unit", "butuh listing",
    "titipan client", "co-broke", "cobroke", "property agent", "broker", "agen properti",
    "saya lagi ada client cari",
)
# Genuine first-person seeker controls: when present, keep the lead eligible
# (do NOT classify as agent_broker even if a third-party cue is nearby).
GENUINE_SEEKER_CONTROLS = (
    "untuk saya sendiri", "saya dan keluarga", "untuk ditempati", "untuk kami", "buat saya",
)
RELATIVE_BUDGET_SIGNALS = ("murah", "under", "flexible budget", "budget flexible")
RENTAL_CONTEXT_SIGNALS = ("apartemen", "apartment", "kontrakan", "kost", "kos", "rumah", "sewa", "rental")
