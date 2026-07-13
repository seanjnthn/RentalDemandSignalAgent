# TASKS.md — Rental Demand Signal Agent (MVP)

**Last updated:** 2026-07-13
**For Hermes:** delegate to Codex task-by-task after operator approval. Each task
is bite-sized, TDD-first, and offline-testable against the 20 synthetic posts.

Legend: ⬜ todo · 🔄 in progress · ✅ done · 🚫 blocked

---

## Phase 0 — Foundations & guardrails

- ⬜ **T0.1** Scaffold package: `rdsa/` module, `tests/`, `pyproject.toml`,
  `.gitignore` (ignore `.env`, `*.sqlite3`), `README.md`.
- ⬜ **T0.2** `rdsa/config.py`: load `.env`, expose keyword list, locations,
  thresholds, query budget, paths. Ship `.env.example`.
- ⬜ **T0.3** `tests/test_no_write_paths.py`: grep guard asserting no Threads
  write/reply/follow/DM/publish calls exist anywhere in `rdsa/`.

## Phase 1 — Data model & storage

- ⬜ **T1.1** `rdsa/db.py`: create SQLite schema from `LEAD_SCHEMA.md` DDL.
  Test: DB initializes; all tables/indexes exist.
- ⬜ **T1.2** Lead upsert + author upsert (idempotent). Test: inserting same
  `post_id` twice → 1 row; author `lead_count`/`last_seen` update.
- ⬜ **T1.3** `scan_runs` + `alerts` + `status_history` writers. Test: alert
  uniqueness constraint prevents double-alert.

## Phase 2 — Extraction (offline, synthetic data)

- ⬜ **T2.1** `rdsa/extractor.py`: intent detection (seeking/offering/unclear)
  for ID + EN. Test against synthetic posts' expected `rental_intent`.
- ⬜ **T2.2** Location extraction + confidence (target list + text). Test.
- ⬜ **T2.3** Property type + bedrooms extraction (apartemen/rumah/kontrakan/kost,
  "2BR"/"2 kamar"). Test.
- ⬜ **T2.4** Budget (min/max/currency/period) parsing incl. "8jt/bulan", "Rp",
  "under 10 juta". Test.
- ⬜ **T2.5** Move-in date + duration + special requirements extraction. Test.
- ⬜ **T2.6** `extract(post) -> Lead` integrator returning all fields + per-field
  confidence. Test: full extraction over all 20 synthetic posts.

## Phase 3 — Classification & scoring

- ⬜ **T3.1** `rdsa/scoring_config.py`: weights/thresholds from `SCORING_RULES.md v1.0`.
- ⬜ **T3.2** `rdsa/scorer.py`: additive score + `{rule,points,reason}` breakdown,
  clamp 0–100. Test: worked example → 100; each rule unit-tested.
- ⬜ **T3.3** `rdsa/classifier.py`: 6-class logic (spam/broker/offering signals
  first, then score bands). Test: every synthetic post → expected class.

## Phase 4 — Deduplication

- ⬜ **T4.1** `rdsa/ingest.py`: `dedup_hash` (normalized text), skip known
  `post_id`s, throttle same-author repeats within window. Test: duplicate set
  → only unique leads stored; second run adds 0.

## Phase 5 — Inventory matching

- ⬜ **T5.1** `rdsa/matcher.py`: load CSV inventory; match on location + type +
  bedrooms + budget overlap; return ranked matches with `match_reasons`.
  Test against a sample `data/inventory.csv`.

## Phase 6 — Threads client (read-only)

- ⬜ **T6.1** `rdsa/threads_client.py`: `search(q, location, since, until,
  limit, search_type='RECENT', media_type='TEXT')` → posts. **GET only.**
  Handle pagination, HTTP errors, rate-limit backoff. Unit-test with mocked HTTP
  (no live calls).
- ⬜ **T6.2** `rdsa/query_planner.py`: build keyword×location queries; enforce
  `RDSA_QUERY_BUDGET_PER_RUN`. Test: budget respected, no duplicate queries.

## Phase 7 — Telegram notifier (send-only)

- ⬜ **T7.1** `rdsa/notifier.py`: format review card (fields + score breakdown +
  matches + source link + status hint); `sendMessage` to configured chat.
  Only hot/qualified; skip already-alerted. Test with mocked HTTP.

## Phase 8 — CLI orchestration

- ⬜ **T8.1** `rdsa/cli.py`: `scan` (full pipeline), `reprocess` (re-run extract/
  score on stored raw), `match`, `notify`, `status <post_id> <new_status>`,
  `list`, `purge`. Test: `scan` over synthetic fixture end-to-end offline.
- ⬜ **T8.2** Wire idempotency: re-running `scan` on same data adds 0 leads / 0 alerts.

## Phase 9 — Docs & handoff

- ⬜ **T9.1** `README.md`: setup, `.env`, running scans, status workflow, limits.
- ⬜ **T9.2** `docs/RUNBOOK.md`: scheduling via Hermes cron, rate-limit budget,
  App-Review gate reminder, troubleshooting.
- ⬜ **T9.3** Final compliance review (Hermes): confirm read-only, no auto-contact,
  minimal storage, secrets hygiene.

---

## Definition of Done (MVP)

1. `pytest` green, fully offline, over the 20 synthetic posts.
2. Classifications + scores match `SCORING_RULES.md v1.0`.
3. `test_no_write_paths.py` passes (no Threads write paths).
4. `scan` run is idempotent (second run: 0 new leads, 0 new alerts).
5. With live creds + a test chat, one `scan` posts a correctly formatted alert.
6. Hermes compliance review signed off.

## Delegation notes for Codex

- Build in phase order; each task is TDD (failing test → minimal code → pass → commit).
- **Do not** add any Threads write capability, other platforms, or a dashboard.
- Keep dependencies minimal (`requests`/`httpx`, `python-dotenv`, `pytest`).
- All network components must be unit-tested with **mocked** HTTP — no live calls in tests.
