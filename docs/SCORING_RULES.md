# SCORING_RULES.md — Rental Demand Signal Agent (MVP)

**Score version:** `v1.0`
**Last updated:** 2026-07-13

The lead score is a **transparent, additive 0–100** value. Every point is
attributable to a named rule, and the full breakdown is stored with the lead and
shown in the Telegram alert. No black-box model — rules first.

---

## 1. Scoring philosophy

- **Additive & capped.** Start at 0, add points per rule, clamp to `[0, 100]`.
- **Explainable.** Each rule emits `{rule, points, reason}`.
- **Signal-based.** Because the API returns no follower/geo/engagement data,
  scoring uses **text signals + extraction confidence** only.
- **Penalties for noise.** Broker/spam/offering signals subtract points and also
  drive classification.

## 2. Point budget (max 100)

| # | Rule | Max pts | How points are awarded |
|---|------|--------:|------------------------|
| R1 | **Clear rental intent (seeking)** | 25 | +25 explicit ("cari", "butuh", "looking for", "need apartment"); +10 implicit/ambiguous; 0 none. |
| R2 | **Target location match** | 20 | +20 exact target (BSD/Alam Sutera/Gading Serpong/Tangsel); +10 adjacent/broader (Serpong, Tangerang); 0 none/other. |
| R3 | **Budget stated** | 15 | +15 explicit numeric budget (any period: /bulan, /tahun, etc. — currency IDR); +7 relative ("murah", "under X"); 0 none. |
| R4 | **Property type specified** | 10 | +10 apartment/house/kontrakan/kost clearly stated; +5 vague ("tempat tinggal"); 0 none. |
| R5 | **Bedrooms specified** | 8 | +8 explicit ("2BR", "2 kamar"); 0 none. |
| R6 | **Move-in urgency** | 12 | +12 within ~30 days / "secepatnya"/"ASAP"/"bulan ini"; +6 1–3 months; +2 vague future; 0 none. |
| R7 | **Rental duration stated** | 5 | +5 explicit ("1 tahun", "12 months"); 0 none. |
| R8 | **Special requirements richness** | 5 | +5 two or more concrete requirements; +2 one; 0 none. |
| R9 | **Post freshness** | 10 | +10 ≤24h old; +6 ≤72h; +3 ≤7d; 0 older. |
| — | **Penalties** | (neg) | See §3. |

**Raw max before penalties:** 110 → clamped to 100. (The extra headroom means a
lead can lose a few points to a penalty and still score highly if it's genuinely strong.)

## 3. Penalties (subtractive)

| Code | Trigger | Points |
|------|---------|-------:|
| P1 | Agent/broker self-promo signals ("disewakan", "for rent", "hubungi kami", listing price + contact + multiple units) | −40 |
| P2 | Spam signals (unrelated promo, repeated emojis/links, MLM, giveaways) | −40 |
| P3 | Offering (not seeking) a property | −30 |
| P4 | Low overall extraction confidence (avg field confidence < 0.3) | −10 |
| P5 | Duplicate-ish author within throttle window | −10 |

## 4. Classification (derived from signals + score)

Classification is decided **before** trusting the score, using hard signals, then
the score refines within the "real seeker" band:

```
if spam_signals:                     class = spam
elif broker_signals:                 class = agent_broker
elif intent == 'offering':           class = irrelevant
elif intent != 'seeking':            class = irrelevant   (unclear / not renting)
else:  # genuine seeker
    if score >= 75:                  class = hot_lead
    elif score >= 55:                class = qualified_lead
    elif score >= 35:                class = watch
    else:                            class = irrelevant
```

### Band thresholds

| Band | Score range | Class | Sent to Telegram? |
|------|-------------|-------|:-----------------:|
| Hot | 75–100 | `hot_lead` | ✅ |
| Qualified | 55–74 | `qualified_lead` | ✅ |
| Watch | 35–54 | `watch` | ❌ (stored only) |
| Irrelevant | 0–34 | `irrelevant` | ❌ |
| Broker | (signal) | `agent_broker` | ❌ |
| Spam | (signal) | `spam` | ❌ |

## 5. Worked example

Post: *"Butuh apartemen 2BR di BSD secepatnya, budget 8jt/bulan, furnished, sewa 1 tahun."*

| Rule | Points | Reason |
|------|-------:|--------|
| R1 | +25 | "Butuh apartemen" = explicit seeking |
| R2 | +20 | "BSD" = exact target location |
| R3 | +15 | "budget 8jt/bulan" = explicit budget |
| R4 | +10 | "apartemen" = clear type |
| R5 | +8 | "2BR" = bedrooms specified |
| R6 | +12 | "secepatnya" = urgent |
| R7 | +5 | "sewa 1 tahun" = duration |
| R8 | +2 | "furnished" = one requirement |
| R9 | +10 | fresh (<24h) |
| **Raw** | **107 → 100** | clamp |

Result: **score 100 → `hot_lead` → sent to Telegram.**

## 6. Versioning

- This document is `score_version = "v1.0"`, stored on every lead.
- Changing weights/thresholds bumps the version so historical scores stay interpretable.
- The scorer must load weights from a single config block (`rdsa/scoring_config.py`
  or a YAML) so rules are tunable without code changes.
