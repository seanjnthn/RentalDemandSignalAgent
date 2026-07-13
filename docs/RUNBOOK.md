# MVP runbook

Install with `python -m pip install -e .[test]`. Copy `.env.example` to `.env` and keep tokens local. Until Meta App Review grants `threads_keyword_search`, use the offline synthetic source.

```text
rdsa init-db
rdsa scan --source synthetic --dry-run
rdsa list --class hot_lead
rdsa status 4001 reviewed
```

The live client is deliberately stubbed until the operator has a Meta Threads app and approved permissions. When enabled, keep `RDSA_QUERY_BUDGET_PER_RUN` well below the 2,200-query rolling limit; the default planner uses at most 40 combinations per run. Telegram must be configured with the operator's group `TELEGRAM_CHAT_ID`; no Threads user is ever a message target.

Terminal statuses can be purged locally with `rdsa purge`. The MVP stores public post text for review and does not automatically advance status or contact authors.
