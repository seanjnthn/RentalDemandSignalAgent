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
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
