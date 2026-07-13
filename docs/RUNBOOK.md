# RUNBOOK.md — Real-Inventory Dry-Run

**Applies to:** v0.1 (`v0.1-synthetic-mvp`). Fully offline. **No live Threads
calls, no Telegram sends, no cron.** This runbook lets the operator point the
frozen pipeline at a *real but sanitized* inventory and inspect scoring +
matching against the 20 synthetic rental posts.

---

## 0. Golden rules

- The 20 rental posts stay **synthetic**. We never invent inventory — you supply it.
- The inventory file must be **sanitized**: no personal/private data (see §1).
- Everything runs with `--dry-run` (Telegram cards are printed, never sent).
- If anything looks wrong, **roll back to the tag** (§8).

## 1. Prepare a real but sanitized `inventory.csv`

Create `data/inventory_real.csv` with **exactly these columns** (canonical schema):

| Column | Meaning | Example |
|--------|---------|---------|
| `property_id` | Your internal unique id | `P001` |
| `area` | District/location (match target) | `BSD` |
| `building` | Building/complex name | `Green Office Park` |
| `property_type` | `apartment` / `house` / `kontrakan` / `kost` | `apartment` |
| `bedrooms` | Integer | `2` |
| `monthly_price` | Integer IDR/month | `7500000` |
| `furnished` | `1`/`0` (or true/false) | `1` |
| `available_from` | ISO date | `2026-08-01` |
| `features` | `;`-separated tags | `Near AEON;pool` |
| `status` | `available` / `reserved` / `unavailable` / `rented` | `available` |
| `listing_url` | Public listing link | `https://…/P001` |

**NEVER include** (the validator hard-rejects these): owner phone/WhatsApp,
owner name, KTP/NIK/passport/ID, tenant history, email, bank/account/financial
records, salary/income, or any private personal information.

> Match uses `area` (→ location), `property_type`, `bedrooms`, `monthly_price`.
> Keep `area` values consistent with the monitored locations
> (`BSD`, `Alam Sutera`, `Gading Serpong`, `Tangerang Selatan`) so leads match.

A blank template lives at `data/inventory_template.csv`.

## 2. Validate required columns (and reject PII)

```bash
cd ~/rental-demand-signal-agent
python scripts/validate_inventory.py data/inventory_real.csv data/inventory_adapted.csv
```

- ✅ Prints `VALID: N rows … M available listings written` and produces the
  matcher-ready `data/inventory_adapted.csv` (only `available`/blank-status rows).
- ❌ Any missing required column, forbidden PII column, duplicate `property_id`,
  or bad type => prints `VALIDATION FAILED: …` and **writes nothing** (exit ≠ 0).

The validator maps your canonical schema to the frozen matcher's format, so the
v0.1 pipeline runs **unchanged** — no edits to `rdsa/`.

> Note: we write to `data/inventory_adapted.csv`, **not** `data/inventory.csv`.
> The latter is the committed sample the test-suite depends on — leave it alone.
> Both `inventory_real.csv` and `inventory_adapted.csv` are git-ignored.

## 3. Run all 20 synthetic posts against the real inventory

```bash
export RDSA_DB_PATH=data/dryrun.sqlite3
export RDSA_INVENTORY_CSV=data/inventory_adapted.csv
rm -f data/dryrun.sqlite3
python -m rdsa.cli init-db
python -m rdsa.cli scan --source synthetic --dry-run
```

`--source synthetic` guarantees **no network call**. `--dry-run` prints alert
cards to stdout instead of sending to Telegram.

## 4. Inspect scoring and matching output

The scan prints, per hot/qualified lead: score, `{rule +pts reason}` breakdown,
extracted fields, matched listings, and the source link. To query the DB after:

```bash
python -m rdsa.cli list                       # all leads
python -m rdsa.cli list --class hot_lead      # just hot
python -m rdsa.cli list --class qualified_lead
```

Sanity check the numbers against `docs/SCORING_RULES.md` (v1.1: hot ≥85,
qualified ≥60, watch ≥35).

## 5. Preview Telegram alert cards WITHOUT sending

`--dry-run` already does this — the exact card text that *would* be sent is
printed. Confirm each card has: class, score, breakdown, extracted fields,
matched inventory, source URL, `Status: new (manual review)`. **Do not** run
`rdsa notify` without `--dry-run` unless you intend to actually send (and only
after Telegram creds are set + you accept a real send).

## 6. Review unmatched and borderline leads

- **Unmatched hot/qualified:** cards showing `Matches:` empty ⇒ your inventory
  has no listing meeting location+type+bedrooms+budget. Expected if the synthetic
  demand doesn't line up with your real stock — note the gaps.
- **Borderline (watch band, 35–59):** not alerted, but stored. Inspect with:
  ```bash
  python -m rdsa.cli list --class watch
  ```
  These are weak/ambiguous seekers — useful to eyeball whether the rubric is
  drawing the hot/qualified/watch lines where you'd want on *real* phrasing.

## 7. Tune configuration WITHOUT hardcoding fixture-specific rules

All tunables live in **one place** — do not edit per-post logic:

- **Bands:** `rdsa/scoring_config.py → THRESHOLDS` (`hot`/`qualified`/`watch`).
- **Weights:** `rdsa/scoring_config.py → POINTS` / `PENALTIES`.
- **Signal lists:** `SPAM_SIGNALS`, `BROKER_SIGNALS`, `RELATIVE_BUDGET_SIGNALS`,
  `RENTAL_CONTEXT_SIGNALS` (add general keywords, never a specific test phrase).
- **Keywords/locations/budget:** `rdsa/config.py` (`KEYWORDS`, `LOCATIONS`,
  `QUERY_BUDGET`) and env vars.

Rules to keep it honest:
1. **Never** add a literal that matches a single synthetic post to force a result.
2. If you change weights/thresholds, **bump `SCORE_VERSION`** (e.g. v1.1→v1.2)
   and add a changelog note in `docs/SCORING_RULES.md`.
3. Re-run `python -m pytest -q` — the band test is bound to `THRESHOLDS`, so it
   follows your change; fix any fixture labels only to match the *documented* rule.
4. Re-run the dry-run and re-inspect (§3–6).

## 8. Roll back to the safe tag

If a tuning experiment goes wrong:

```bash
# discard uncommitted changes and return to the frozen MVP:
git stash            # or: git checkout -- .
git checkout v0.1-synthetic-mvp        # detached HEAD at the frozen MVP
# to hard-reset your working branch to the tag (destructive):
git reset --hard v0.1-synthetic-mvp
```

Delete the scratch DB anytime: `rm -f data/dryrun.sqlite3`.

## Cleanup

```bash
rm -f data/dryrun.sqlite3 data/inventory_adapted.csv
```
Your `data/inventory_real.csv` and `data/inventory_adapted.csv` are git-ignored,
so real data is never committed. The committed `data/inventory.csv` sample is
left untouched for the test-suite.
