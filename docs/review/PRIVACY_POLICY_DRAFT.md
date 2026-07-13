# PRIVACY_POLICY_DRAFT.md — Rental Demand Signal Agent

> Draft privacy policy text. Host this publicly (e.g. GitHub Pages / a static
> host) and enter the URL in the App Dashboard "Privacy Policy URL" field. Replace
> `[operator placeholders]` before publishing. Written to satisfy Meta's data-
> handling expectations and to be honest about this app's minimal footprint.

---

# Privacy Policy — Rental Demand Signal Agent

**Effective date:** [2026-07-13]
**Controller:** [Operator name / entity], [contact email]
**Service:** Rental Demand Signal Agent (the "Service")

## 1. What the Service does

The Service searches **public** Threads posts for people looking to rent a home
in the Greater Serpong / South Tangerang area (Indonesia). For each public post
it extracts rental requirements, computes a transparent lead score, classifies
the post, and matches strong leads to the operator's own property inventory.
Results are shown to a **human operator** for manual review.

## 2. Data we access through Threads

- **Public post data only**, retrieved via the official Threads Graph API
  (`keyword_search`): post id, text, media type, permalink, timestamp, and
  username of the public author.
- We do **not** access private messages, followers, likes, close-friends, or any
  non-public information.
- We do **not** read or manage replies, comments, or conversations.

## 3. Data we store

We store a **minimal** set of public lead metadata for the operator's manual
review:

- Post id, public author username, post text, public permalink, post timestamp.
- Extracted rental requirements (location, type, bedrooms, budget, dates,
  duration, requirements) and a lead score/classification.
- Operator-set review status (new / reviewed / contacted / responded / viewing
  scheduled / converted / rejected).

We do **not** store private personal data, contact details, identity documents,
financial records, or any inventory that includes owner/tenant personal
information. Inventory is sanitized before use (no names, phones, or identifiers).

## 4. How we use data

- Solely to surface **public** rental-demand signals to the operator for **manual**
  human review.
- We do **not** contact Threads users automatically. The operator is solely
  responsible for any outreach, conducted through normal Threads channels.
- We do **not** use data for advertising, profiling beyond the stated lead score,
  or any secondary purpose.

## 5. Legal basis

We process only information that users have published publicly on Threads. We
rely on the public availability of this content and, where applicable, the
operator's legitimate interest in identifying prospective renters, subject to this
policy and applicable law (including Indonesia's PDP Law and, where relevant,
GDPR for EEA users).

## 6. Data retention

- Public lead metadata is retained only as long as needed for review, then deleted
  on a routine basis (default: operator-initiated purge; no automatic long-term
  archive).
- We do not retain data longer than necessary for the Service's purpose.

## 7. Your rights / data deletion

You may request deletion of any public post metadata the Service holds about you.
See **Data Deletion Instructions** (in-app and at [deletion URL]) for how to
submit a request; we honor verified requests within [30] days. You may also
exercise rights to access, rectify, or object to processing as provided by
applicable law.

## 8. Sharing

We do not sell or share personal data. The Service sends lead summaries **only**
to the operator's own designated Telegram review group; it never messages Threads
users.

## 9. Security

Access to the Service is restricted to the operator. Credentials (Threads tokens,
Telegram token) are stored locally and never committed to code repositories.

## 10. Changes

We will post changes to this policy and update the effective date.

## 11. Contact

Questions or deletion requests: [contact email].
