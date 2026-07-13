# VERTICAL_SLICE.md — Smallest end-to-end slice

**Last updated:** 2026-07-13

The goal of the first slice is to prove the **whole pipeline shape** end-to-end
with the least code, running **entirely offline on synthetic data** (no App
Review, no live token needed). Live Threads calls are swapped in later behind the
same interface.

---

## The slice: "synthetic post → scored lead → Telegram card"

```
data/synthetic_posts.json
        │
        ▼
 extract()  →  classify() + score()  →  dedup()  →  match(inventory.csv)
        │
        ▼
 persist to SQLite  →  notify() hot/qualified  →  Telegram (or dry-run stdout)
```

### What's IN the slice

1. Load the 20 synthetic posts from `data/synthetic_posts.json`.
2. `extract()` the structured fields (rules-based).
3. `score()` (v1.0) + `classify()` into the 6 classes.
4. `dedup()` on `post_id` + `dedup_hash`.
5. `match()` hot/qualified leads against `data/inventory.csv`.
6. `persist()` to SQLite (`leads`, `authors`, `alerts`).
7. `notify()` — format the review card; **`--dry-run` prints to stdout** instead
   of calling Telegram, so the slice needs no credentials.
8. Idempotency: a second run adds 0 leads and sends 0 alerts.

### What's OUT of the slice (added right after)

- Live Threads client (`threads_client.py`) — mocked/stubbed in the slice, real
  GET calls added in Phase 6 behind the identical `search()` signature.
- Real Telegram send — enabled by dropping `--dry-run` once a bot token exists.
- Status-workflow CLI subcommands, purge, reprocess (Phase 8).

### Why this is the right first slice

- Exercises every core transform (extract → score → classify → dedup → match →
  store → notify) with a stable, labeled fixture.
- Needs **no credentials and no App Review**, so Codex can build and we can
  verify correctness immediately.
- The only thing swapped later is the *data source* (synthetic → live API) and
  the *sink* (stdout → Telegram) — both behind clean interfaces.

### Acceptance for the slice

- `rdsa scan --source synthetic --dry-run` prints correctly formatted cards for
  exactly the hot + qualified synthetic leads.
- Stored classes/scores match the expected labels in `synthetic_posts.json`.
- Re-running is idempotent (0 new leads, 0 new alerts).
- `pytest` green, fully offline.

### Commands (target UX)

```bash
rdsa init-db
rdsa scan --source synthetic --dry-run     # slice: offline, prints cards
rdsa list --class hot_lead
rdsa status 4001 reviewed
# later, once creds + approval exist:
rdsa scan --source threads                 # live public search
```
