import importlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from rdsa.dashboard_repository import (
    get_inventory,
    get_lead,
    get_leads,
    get_matching_groups,
    get_overview,
    normalize_matches,
    update_lead_status,
)
from rdsa.db import connect

ROOT = Path(__file__).resolve().parents[1]
REAL_IDS = {
    "APT-GS-MTOWN-1BR-001",
    "HSE-SS-FEDORA-2P1-001",
    "KSK-BSD-INTERMODA-001",
}


def _env_without_pythonpath():
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return env


def _seed(path, matches):
    c = connect(path)
    c.execute(
        "INSERT INTO leads(post_id,source_url,author_username,post_timestamp,fetched_at,first_seen,last_seen,raw_text,desired_location,property_type,bedrooms,budget_max,budget_currency,budget_period,budget_confidence,lead_class,lead_score,matched_inventory,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("legacy-test", "https://example.com/p/1", "person", "2026-07-14T00:00:00Z", "2026-07-14T00:00:00Z", "2026-07-14T00:00:00Z", "2026-07-14T00:00:00Z", "rental request", "BSD", "apartment", 1, 10000000, "IDR", "month", "high", "hot_lead", 90, json.dumps(matches), "new"),
    )
    c.commit()
    c.close()


def test_fresh_terminal_imports_all_dashboard_modules():
    modules = ["dashboard.app"]
    script = "import importlib; [importlib.import_module(name) for name in %r]" % modules
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=_env_without_pythonpath(), capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "ModuleNotFoundError" not in result.stderr

    for page in sorted((ROOT / "dashboard" / "pages").glob("*.py")):
        script = "import runpy; runpy.run_path(%r, run_name='__main__')" % str(page)
        result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=_env_without_pythonpath(), capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"{page.name}: {result.stderr}"
        assert "ModuleNotFoundError" not in result.stderr


def test_app_imports_directly():
    assert importlib.import_module("dashboard.app")


def test_streamlit_boots_without_pythonpath():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        ["streamlit", "run", "dashboard/app.py", "--server.headless", "true", "--server.port", str(port)],
        cwd=ROOT, env=_env_without_pythonpath(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    output = ""
    booted = False
    deadline = time.time() + 45
    try:
        while time.time() < deadline:
            if process.poll() is not None:
                break
            try:
                with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                    if response.status == 200:
                        booted = True
                        break
            except Exception:
                pass
            time.sleep(0.25)
        else:
            raise AssertionError("Streamlit did not return HTTP 200")
        assert booted, "Streamlit did not return HTTP 200"
        assert process.poll() is None
    finally:
        process.terminate()
        try:
            output, _ = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
        assert "Traceback (most recent call last)" not in output
        assert "ModuleNotFoundError" not in output


def test_legacy_matches_are_labeled_but_real_matches_are_active(tmp_path):
    matches = [
        {"property_id": "INV001", "match_type": "exact_match"},
        {"property_id": "APT-GS-MTOWN-1BR-001", "match_type": "exact_match"},
    ]
    normalized = normalize_matches(matches, "BSD")
    assert normalized[0]["is_legacy"] is True
    assert normalized[0]["legacy_note"] == "Legacy synthetic match — not an active inventory recommendation"
    assert normalized[0]["match_type"] == "legacy_synthetic"
    assert normalized[1]["is_legacy"] is False

    path = tmp_path / "mixed.sqlite3"
    _seed(path, matches)
    lead = get_lead("legacy-test", path)
    assert lead["match_types"] == ["exact_match"]
    assert get_overview({}, path)["exact_match"] == 1
    assert len(get_matching_groups(path)["exact_match"]) == 1
    assert get_matching_groups(path)["exact_match"][0]["match"]["property_id"] in REAL_IDS


def test_legacy_only_is_excluded_from_active_contract(tmp_path):
    path = tmp_path / "legacy-only.sqlite3"
    stored = [{"property_id": "INV001", "match_type": "exact_match"}, {"property_id": "INV010"}]
    _seed(path, stored)
    lead = get_lead("legacy-test", path)
    assert lead["matches"] and all(item["is_legacy"] for item in lead["matches"])
    assert lead["match_types"] == []
    overview = get_overview({}, path)
    assert all(overview[key] == 0 for key in ("exact_match", "nearby_alternative", "tentative_match", "no_match"))
    assert all(not group for group in get_matching_groups(path).values())
    assert get_leads({"match_type": "exact_match"}, path) == []

    before = json.dumps(stored, sort_keys=True)
    update_lead_status("legacy-test", "reviewed", db_path=path)
    with connect(path) as c:
        after = c.execute("SELECT matched_inventory FROM leads WHERE post_id='legacy-test'").fetchone()[0]
    assert json.dumps(json.loads(after), sort_keys=True) == before


def test_only_real_inventory_ids_are_visible():
    inventory = get_inventory()
    assert {row["inventory_id"] for row in inventory["rows"]} == REAL_IDS
    assert not any(row["inventory_id"].startswith("INV") for row in inventory["rows"])


def test_dashboard_has_no_delivery_or_network_imports():
    text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "dashboard").rglob("*.py"))
    for forbidden in ("apify_provider", "TelegramNotifier", "requests", "send_lead_cards"):
        assert forbidden not in text


def test_overview_snapshot_shows_only_active_ids_and_marks_legacy(tmp_path):
    """Overview Lead-snapshot must not present legacy INVxxx as active matches."""
    from dashboard.app import _active_match_label  # bootstrap already ran on import
    mixed = [{"property_id": "INV001", "match_type": "exact_match"},
             {"property_id": "APT-GS-MTOWN-1BR-001", "match_type": "exact_match"}]
    legacy_only = [{"property_id": "INV005"}]
    real_only = [{"property_id": "KSK-BSD-INTERMODA-001", "match_type": "exact_match"}]
    assert _active_match_label({"matches": normalize_matches(mixed, "BSD")}) == "APT-GS-MTOWN-1BR-001"
    assert _active_match_label({"matches": normalize_matches(legacy_only, "BSD")}) == "No active real inventory match"
    assert _active_match_label({"matches": normalize_matches(real_only, "BSD")}) == "KSK-BSD-INTERMODA-001"
    assert _active_match_label({"matches": []}) == ""
