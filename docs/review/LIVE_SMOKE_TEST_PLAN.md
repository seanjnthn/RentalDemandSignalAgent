# LIVE_SMOKE_TEST_PLAN.md — Rental Demand Signal Agent

Run this **only after** `threads_keyword_search` is approved and a real user token
is available. It confirms the live pipeline works end-to-end and stays compliant.
Never auto-posts. Keep scans low-volume (well under the 2,200 queries / 24h limit).

> Prereqs: Meta app Live, `threads_keyword_search` approved, real token in
> `THREADS_USER_TOKEN`, `THREADS_APP_ID`/`THREADS_APP_SECRET` set, `RDSA_DB_PATH`
> configured. Telegram only needed if you intend a real (non-dry-run) alert.

---

## 0. Pre-flight (safety first)
- [ ] Confirm App Dashboard shows `threads_keyword_search` = **Approved (Live)**.
- [ ] `RDSA_QUERY_BUDGET_PER_RUN` set low (e.g. 10) for first live run.
- [ ] Token refreshed via the OAuth flow; not expired.
- [ ] Telegram **disabled** for this smoke test (`TELEGRAM_BOT_TOKEN` empty) so
      nothing sends; use `--dry-run` regardless.

## 1. Connect / token sanity
```bash
python -c "from rdsa.threads_client import ThreadsClient; \
  c=ThreadsClient(open('.threads_token').read().strip()); \
  print('token ok' if c.search('cari apartemen', limit=1) else 'no results')"
```
Confirm a GET succeeds and (post-approval) returns public posts, not just own.

## 2. Single keyword × location (manual)
```bash
python -m rdsa.cli scan --source threads \
  --keyword "cari apartemen" --location "BSD" --dry-run
```
- [ ] Output shows real public posts (not synthetic).
- [ ] Each has extracted fields + score + class.
- [ ] No network calls other than `GET /keyword_search`.

## 3. Full planned query set (bounded)
```bash
python -m rdsa.cli init-db
python -m rdsa.cli scan --source threads --dry-run
```
- [ ] Number of API calls ≤ `QUERY_BUDGET`.
- [ ] Dedup works (re-run → 0 new).
- [ ] No post text is fabricated; permalinks resolve to real public posts.

## 4. Classification spot-check
- [ ] Real broker/listing accounts → `agent_broker`.
- [ ] Promo/spam → `spam` / `irrelevant`.
- [ ] Genuine seekers with budget+location → `hot`/`qualified`.

## 5. Inventory matching (optional, with sanitized CSV)
```bash
export RDSA_INVENTORY_CSV=data/inventory_adapted.csv
python -m rdsa.cli scan --source threads --dry-run   # then: rdsa match
```
- [ ] hot/qualified leads show matches; others show none.

## 6. Compliance assertions (must hold)
- [ ] `python -m pytest tests/test_no_write_paths.py tests/test_http.py` → pass.
- [ ] No `.post()`/`.put()`/`.delete()` to `graph.threads.net` anywhere.
- [ ] No Telegram message sent (dry-run / token empty).

## 7. Telegram send (only when you truly want it)
After review, set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`, then (without
`--dry-run`) confirm **only** hot/qualified cards go to the **group** — never to
any Threads user.

## 8. Stop / rollback
- Kill the process; `rdsa purge` clears local store if needed.
- If the live call misbehaves, revert to tag `v0.1-synthetic-mvp` for the safe
  offline baseline.
