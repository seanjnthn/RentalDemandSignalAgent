# DATA_DELETION_INSTRUCTIONS.md — Rental Demand Signal Agent

Meta requires apps that access user data to tell users how to request deletion of
their data, and to provide either a deletion callback URL or clear instructions in
the App Dashboard. This document serves both as the **instructions for users** and
as the basis for the **App Dashboard "Data Deletion Request URL"** field.

---

## For users (publish this verbatim or link it from your privacy policy)

### How to request deletion of your data

Rental Demand Signal Agent only ever stores **public** Threads post metadata
(post id, public username, post text, public post link, timestamp, and extracted
rental requirements). It never stores private messages or personal contact
details. If you want your post's metadata removed from our records:

1. Open the public Threads post you want removed.
2. Copy its **post link (permalink)** or **post id**.
3. Email a deletion request to **[operator email]** with the subject
   `Data Deletion Request`, including the post link/id and, optionally, the
   Threads username.
4. We will verify the request and delete the matching record(s) within **30 days**,
   and confirm by reply.

You may also request deletion of **all** data we hold referencing your username by
stating "delete all my data" in the request.

## What we delete

- The public post text, id, username, permalink, timestamp, extracted fields, and
  the lead score/status associated with the requested post/username.

## What we cannot delete

- The original post itself — that lives on Threads and is controlled by you / Meta.
- Any data we never collected (private messages, etc.).

## Operator implementation notes (how the deletion is actually performed)

The CLI exposes a purge command. To honor a verified request, the operator runs:

```bash
# Delete a single lead by post id:
python -m rdsa.cli purge --post-id <POST_ID>

# Delete everything referencing a username:
python -m rdsa.cli purge --author <USERNAME>

# Wipe the entire local lead store (nuclear option, after confirmation):
python -m rdsa.cli purge --all
```

`purge` removes rows from the SQLite store (`leads`, `authors`, `alerts`,
`status_history`) — it does **not** touch Threads or any inventory file.

## App Dashboard setup

- In the App Dashboard, under **App Settings → Advanced → Data Deletion Request**,
  set the **Data Deletion Request URL** to a page that displays the instructions
  above (e.g. `https://[your-host]/data-deletion`).
- Ensure `[operator email]` is monitored so requests are honored within 30 days.
