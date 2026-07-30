import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
KEYWORDS = ["cari sewa", "cari kontrakan", "cari apartemen", "rent apartment", "looking for apartment", "sewa rumah", "kontrakan"]
CANONICAL_AREAS = ["BSD", "Gading Serpong", "Alam Sutera", "Suvarna Sutera", "Tangerang Selatan"]
LOCATIONS = CANONICAL_AREAS
NEARBY_AREA_MAP = {"BSD": ["Gading Serpong"], "Gading Serpong": ["BSD"]}

_AREA_ALIASES = {
    "bsd": "BSD", "bsd city": "BSD",
    "gading serpong": "Gading Serpong", "gs": "Gading Serpong",
    "alam sutera": "Alam Sutera", "alsut": "Alam Sutera",
    "suvarna sutra": "Suvarna Sutera", "suvarna sutera": "Suvarna Sutera",
    "tangsel": "Tangerang Selatan", "tangerang selatan": "Tangerang Selatan",
}

def canonical_area(raw):
    if raw is None:
        return None
    value = " ".join(str(raw).strip().lower().split())
    return _AREA_ALIASES.get(value, raw if raw in CANONICAL_AREAS else None)
QUERY_BUDGET = int(os.getenv("RDSA_QUERY_BUDGET_PER_RUN", "40"))
DB_PATH = os.getenv("RDSA_DB_PATH", str(ROOT / "data" / "rdsa.sqlite3"))
INVENTORY_CSV = os.getenv("RDSA_INVENTORY_CSV", str(ROOT / "data" / "inventory.csv"))
INVENTORY_REAL_CSV = os.getenv("RDSA_INVENTORY_REAL_CSV", str(ROOT / "data" / "inventory_real.csv"))
INVENTORY_MODE = os.getenv("RDSA_INVENTORY_MODE", "real").strip().lower()
LEAD_RETENTION_DAYS = int(os.getenv("RDSA_LEAD_RETENTION_DAYS", "90"))
PILOT_QUERIES = ["apartemen", "rumah sewa", "kontrakan", "sewa apartemen"]
PILOT_MAX_TOTAL_CHARGE_USD = float(os.getenv("RDSA_PILOT_MAX_TOTAL_CHARGE_USD", "0.10"))
THREADS_LIVE_ENABLED = os.getenv("THREADS_LIVE_ENABLED", "false")
THREADS_APP_ID = os.getenv("THREADS_APP_ID", "")
THREADS_APP_SECRET = os.getenv("THREADS_APP_SECRET", "")
THREADS_REDIRECT_URI = os.getenv("THREADS_REDIRECT_URI", "")
THREADS_USER_TOKEN = os.getenv("THREADS_USER_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_SEND_ENABLED = os.getenv("RDSA_TELEGRAM_SEND_ENABLED", "false").strip().lower() == "true"
TELEGRAM_ALLOWED_CHAT_ID = os.getenv("TELEGRAM_ALLOWED_CHAT_ID", TELEGRAM_CHAT_ID).strip()
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "automation-lab/threads-scraper")
APIFY_LIVE_ENABLED = os.getenv("APIFY_LIVE_ENABLED", "false")
APIFY_MAX_TOTAL = int(os.getenv("APIFY_MAX_TOTAL", "20"))
APIFY_MAX_PER_QUERY = int(os.getenv("APIFY_MAX_PER_QUERY", "5"))
APIFY_WARN_USD = float(os.getenv("APIFY_WARN_USD", "3.75"))
APIFY_STOP_USD = float(os.getenv("APIFY_STOP_USD", "4.25"))
APIFY_QUERIES = ["cari apartemen BSD", "butuh apartemen BSD", "cari apartemen Alam Sutera", "cari rumah sewa Tangerang"]
APIFY_USAGE_PATH = os.getenv("APIFY_USAGE_PATH", str(ROOT / "data" / "apify_usage.json"))
BUDGET_PLAUSIBLE_MIN = int(os.getenv("RDSA_BUDGET_PLAUSIBLE_MIN", "500000"))
BUDGET_PLAUSIBLE_MAX = int(os.getenv("RDSA_BUDGET_PLAUSIBLE_MAX", "500000000"))

# ---------------------------------------------------------------------------
# v0.7 — Safe daily scheduler foundation (kill switches default to OFF)
# ---------------------------------------------------------------------------
# Both scheduler kill switches default to FALSE. Scheduled execution refuses to
# run unless RDSA_SCHEDULER_ENABLED=true AND an explicit CLI confirmation flag
# is supplied. Telegram delivery during a scheduled run additionally requires
# RDSA_SCHEDULER_SEND_ENABLED=true. Existing APIFY_LIVE_ENABLED / RDSA_TELEGRAM_SEND_ENABLED
# remain unchanged; live execution is enabled in-process only after preflight.
SCHEDULER_ENABLED = os.getenv("RDSA_SCHEDULER_ENABLED", "false").strip().lower() == "true"
SCHEDULER_SEND_ENABLED = os.getenv("RDSA_SCHEDULER_SEND_ENABLED", "false").strip().lower() == "true"
# Application-level UI feature flag. This does not enable Apify, Telegram,
# Scheduler, or scheduled sending by itself.
DASHBOARD_OPERATOR_CONTROLS_ENABLED = os.getenv(
    "RDSA_DASHBOARD_OPERATOR_CONTROLS_ENABLED", "false"
).strip().lower() == "true"
# Conservative overall timeout for a scheduled run (seconds). No automatic retry on timeout.
SCHEDULER_TIMEOUT_SECONDS = int(os.getenv("RDSA_SCHEDULER_TIMEOUT_SECONDS", "900"))
# Git-ignored runtime directory for the cross-process lock file.
RUNTIME_DIR = os.getenv("RDSA_RUNTIME_DIR", str(ROOT / "runtime"))
LOCK_PATH = os.path.join(RUNTIME_DIR, "scheduler.lock")
# Configurable approved query set (data, not duplicated logic).
SCHEDULER_QUERIES = [
    "cari apartemen BSD",
    "apartemen Gading Serpong",
    "rumah sewa Tangerang Selatan",
    "kontrakan Tangerang",
]
SCHEDULER_MAX_PER_QUERY = int(os.getenv("RDSA_SCHEDULER_MAX_PER_QUERY", "5"))
SCHEDULER_MAX_TOTAL = int(os.getenv("RDSA_SCHEDULER_MAX_TOTAL", "20"))
SCHEDULER_MAX_CHARGE_USD = float(os.getenv("RDSA_SCHEDULER_MAX_TOTAL_CHARGE_USD", "0.10"))
# Conservative grace period before a non-terminal scheduled run may be treated
# as interruption-candidate. The process must first be verifiably dead AND have
# no active matching lock. Age alone (started_at beyond grace) is NEVER enough.
SCHEDULER_INTERRUPTION_GRACE_SECONDS = int(os.getenv("RDSA_SCHEDULER_INTERRUPTION_GRACE_SECONDS", "3600"))

# ---------------------------------------------------------------------------
# v0.9 — Manual-scan Telegram notification capability (always-off by default)
# ---------------------------------------------------------------------------
# Master safety kill switch. When true AND Telegram credentials are valid, every
# completed manual dashboard scan sends a completion summary + up to 3 lead cards
# to Telegram. Permissions are process-local to the manual child — the parent
# Streamlit process never globally enables scheduler sending.
# Default: false. Production may set true after validation.
MANUAL_SEND_ENABLED = os.getenv("RDSA_MANUAL_SEND_ENABLED", "false").strip().lower() == "true"

# ---------------------------------------------------------------------------
# v0.7.4 — Interrupted run recovery status set
# ---------------------------------------------------------------------------
# Terminal-but-unresolved states that must NEVER be auto-retried and are never
# treated as "completed" or eligible for automatic retry. `interrupted` is the
# explicit auditable terminal status for an OS/process kill mid-run.
RUN_STATUS_INTERRUPTED = "interrupted"
# Non-terminal states: a run is only "unresolved" (reconciliation candidate) if
# its status is in this set AND it has no terminal finished_at.
RUN_STATUS_NON_TERMINAL = (
    "starting", "preflight", "actor_started", "actor_completed",
    "persistence", "delivery", "cleanup",
)
# Terminal states that are NOT interruption (already resolved; refuse reconcile).
RUN_STATUS_TERMINAL_RESOLVED = (
    "completed", "completed_no_new_leads", "completed_no_eligible_leads",
    "failed", "blocked_cost_limit", "blocked_lock", "refused",
)
# Major lifecycle phases recorded in current_phase at each stage.
RUN_PHASES = (
    "starting", "preflight", "actor_started", "actor_completed",
    "persistence", "delivery", "cleanup",
)

