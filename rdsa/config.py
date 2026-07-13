import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
KEYWORDS = ["cari sewa", "cari kontrakan", "cari apartemen", "rent apartment", "looking for apartment", "sewa rumah", "kontrakan"]
LOCATIONS = ["BSD", "Alam Sutera", "Gading Serpong", "Tangerang Selatan"]
QUERY_BUDGET = int(os.getenv("RDSA_QUERY_BUDGET_PER_RUN", "40"))
DB_PATH = os.getenv("RDSA_DB_PATH", str(ROOT / "data" / "rdsa.sqlite3"))
INVENTORY_CSV = os.getenv("RDSA_INVENTORY_CSV", str(ROOT / "data" / "inventory.csv"))
THREADS_LIVE_ENABLED = os.getenv("THREADS_LIVE_ENABLED", "false")
THREADS_APP_ID = os.getenv("THREADS_APP_ID", "")
THREADS_APP_SECRET = os.getenv("THREADS_APP_SECRET", "")
THREADS_REDIRECT_URI = os.getenv("THREADS_REDIRECT_URI", "")
THREADS_USER_TOKEN = os.getenv("THREADS_USER_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "automation-lab/threads-scraper")
APIFY_LIVE_ENABLED = os.getenv("APIFY_LIVE_ENABLED", "false")
APIFY_MAX_TOTAL = int(os.getenv("APIFY_MAX_TOTAL", "20"))
APIFY_MAX_PER_QUERY = int(os.getenv("APIFY_MAX_PER_QUERY", "5"))
APIFY_WARN_USD = float(os.getenv("APIFY_WARN_USD", "3.75"))
APIFY_STOP_USD = float(os.getenv("APIFY_STOP_USD", "4.25"))
APIFY_QUERIES = ["cari apartemen BSD", "butuh apartemen BSD", "cari apartemen Alam Sutera", "cari rumah sewa Tangerang"]
APIFY_USAGE_PATH = os.getenv("APIFY_USAGE_PATH", str(ROOT / "data" / "apify_usage.json"))
