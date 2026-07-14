from types import SimpleNamespace

import pytest

from rdsa import config
from rdsa.cli import process_raw
from rdsa.extractor import extract
from rdsa.matcher import load_inventory, match
from rdsa.notifier import format_preview_card
from rdsa.scorer import score
from rdsa.classifier import classify


POST = {"id": "live-1", "text": "cari apartemen BSD 2 kamar 6 jt/bulan secepatnya",
        "username": "operator-test", "timestamp": "2026-07-13T00:00:00Z",
        "permalink": "https://threads.net/p/live-1"}


def args(pilot=True):
    return SimpleNamespace(dry_run=True, pilot=pilot)


def test_real_missing_disables_matching_and_never_loads_sample(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(config, "INVENTORY_REAL_CSV", str(tmp_path / "missing.csv"))
    result = process_raw([POST], "apify", args(), None, inventory_mode="real")
    output = capsys.readouterr().out
    assert result["matching_enabled"] is False
    assert "Inventory matches: Not configured" in output
    assert "INV001" not in output
    assert output.count("Real inventory is not configured.") == 1


def test_explicit_synthetic_mode_still_matches_fixture():
    result = process_raw([POST], "synthetic", args(), None, inventory_mode="synthetic")
    assert result["inventory_matches"] > 0


def test_invalid_mode_raises_and_none_is_silent(monkeypatch, capsys):
    with pytest.raises(ValueError):
        process_raw([], "apify", args(), None, inventory_mode="bogus")
    process_raw([], "apify", args(), None, inventory_mode="none")
    assert "Real inventory is not configured" not in capsys.readouterr().out


def test_synthetic_ids_cannot_enter_real_mode_card():
    lead = classify(score(extract(POST)))
    lead.lead_class = "hot_lead"
    lead.matched_inventory = match(lead, load_inventory("data/inventory.csv"))
    # A real-mode live scan must not use this fixture list at all.
    lead.matched_inventory = []
    card = format_preview_card(lead, matching_enabled=False)
    assert lead.matched_inventory == []
    assert "INV" not in card
    assert "Inventory matches: Not configured" in card


def test_process_raw_current_metrics_are_per_scan():
    first = process_raw([POST], "apify", args(), None, inventory_mode="none")
    second = process_raw([POST], "apify", args(), None, inventory_mode="none")
    assert first["raw_posts"] == 1 and first["new_rows"] == 1
    assert second["raw_posts"] == 1 and second["new_rows"] == 1
    assert first["classifications"] == second["classifications"]
