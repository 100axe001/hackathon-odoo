# DealFlow360 — Risk & ML Build Plan (Updated)

## Purpose

This document defines the risk-scoring and ML layer for DealFlow360 and keeps two concepts strictly separate:

1. **Business-rule discount risk** — authoritative for approval routing.
2. **ML deal-health intelligence** — advisory intelligence for anomaly/stall detection.

The frontend must display backend-calculated results; it must never be the source of truth for approval decisions.

---

# 1. Risk Architecture

```text
Quotation
   │
   ├── Line Discount Validation
   │       └── checks each line against:
   │            customer-tier ceiling
   │            category ceiling
   │
   ├── Blended Discount Risk Engine
   │       └── aggregates quotation-level discount risk
   │
   └── Approval Router
           ├── LOW  → no approval
           ├── MEDIUM → Sales Manager
           └── HIGH → Sales Manager → Finance
```

Separately:

```text
Quotation + Activity History
          │
          ├── Discount Anomaly Detection
          │       └── rep-specific historical baseline
          │
          ├── Stall Prediction
          │       └── ML probability
          │
          └── Delivery Slippage
                  └── deterministic date comparison

                         ↓

                 Deal Health Dashboard
```

**Important:** ML stall/anomaly scores must not replace the business-rule approval engine.

---

# 2. Line-Level Discount Validation — MUST BUILD

This is the first layer of discount governance.

For every quotation line:

```text
effective_limit =
    min(customer_tier_limit, category_limit)
```

Example:

```text
Gold customer = 15% maximum
Hardware     = 15% maximum
Service      = 10% maximum

Laptop       = 12% → OK
Setup Service = 18% → OVER by 8 points
```

The quotation is therefore flagged because the service line exceeds its own stricter limit.

The limits must be read from the database/configuration tables, not hardcoded in the frontend or approval endpoint.

### Backend result

```json
{
  "status": "OVER",
  "over_by_pct": 8,
  "allowed_discount_pct": 10
}
```

The frontend displays this result live.

### API

```text
PATCH /quotations/{id}/lines/{line_id}
```

The frontend may call this on blur/debounce, but the backend remains authoritative.

---

# 3. Blended Discount Risk — MUST BUILD

The blended risk score is a **business-rule engine**, not ML.

Its purpose is to decide whether the quotation requires approval and which approval level is required.

It should consider:

- Each line's allowed discount
- Discount given
- Amount/value affected by the discount
- Number of violating lines
- Total excess discount across the quotation
- Worst single-line violation
- Configured approval rules

## 3.1 Two paths, not one

A single aggregate number cannot satisfy the problem statement, because the PS
demands two different things that pull in opposite directions:

| PS requirement | What it needs |
|---|---|
| §10 headline: one $450 service line 8pt over flags a $3,030 quote | catch the **worst single line**, no matter how small its share of the order |
| §10 "why blended": many lines each slightly over add up to real margin loss | catch the **aggregate**, even when no single line looks alarming |

A value-weighted average alone **fails the first case**. In the PS's own headline
example the offending line is 15% of order value, so weighting dilutes an 8pt
violation down to about 1.2pt and routes it LOW — the opposite of what the
wireframe shows. Worse, a 15pt violation buried in a large compliant order
dilutes to 0.11pt and disappears entirely.

So the engine computes **two independent scores** and takes the higher resulting
level. This is exactly what PS §4 A3 asks for: *"compute a blended risk score and
route to the highest required level."*

```text
                 ┌─ worst-line path ──> worst_level ─┐
quotation lines ─┤                                    ├─> max() ─> risk_level
                 └─ blended path ─────> blended_level ┘
```

## 3.2 Per-line quantities

```text
list_value_i   = unit_price_i × qty_i                    (BEFORE discount)
excess_pt_i    = max(0, discount_pct_i − allowed_pct_i)
excess_value_i = list_value_i × excess_pt_i / 100        (money given away)
```

`allowed_pct_i` is `min(customer_tier_limit, category_limit)` from section 2.

**Use list value, never net value, as the denominator base.** Net value shrinks as
discounts grow, so a net-based denominator perversely inflates the score for the
same violation. List value is stable.

## 3.3 Path A — worst single line

```text
worst_excess_pt = max(excess_pt_i)   across all lines, 0 if none
```

## 3.4 Path B — blended aggregate

```text
total_excess_value = Σ excess_value_i
quote_list_value   = Σ list_value_i

blended_excess_pt  = total_excess_value / quote_list_value × 100
```

Read this as: **"taken as a whole, this order is N percentage points over
policy."** It is in the same unit as the line excess, which keeps both paths
comparable and both thresholds meaningful to a human.

Note that this term already accounts for the **number of violating lines** —
more violations means a larger sum. No separate count rule is needed; the count
is reported for the explanation text in section 5, not used in routing.

### Optional display score

The wireframes never show a numeric score (Screens 5 and 6 show only the
HIGH/MEDIUM/LOW badge), but the API returns a bounded one for the audit record:

```text
blended_score = min(1.0, blended_excess_pt / SCORE_CAP_PT)     SCORE_CAP_PT = 10.0
```

This is genuinely 0–1. The previous draft of this document claimed a score of
`0.71` that was not derivable from its own formula, and its formula was
unbounded — both are fixed here.

## 3.5 Thresholds — configuration, not constants

Stored in a `RiskThreshold` table so Screen 18 drives them:

| rule_type | level | min_excess_pt |
|---|---|---|
| `WORST_LINE` | MEDIUM | 0.01 (any violation at all) |
| `WORST_LINE` | HIGH | 5.0 |
| `BLENDED` | MEDIUM | 1.0 |
| `BLENDED` | HIGH | 3.0 |

And the chain in an `ApprovalRule` table, mapping 1:1 onto Screen 18's three rows:

| level | step_order | role |
|---|---|---|
| MEDIUM | 1 | SALES_MANAGER |
| HIGH | 1 | SALES_MANAGER |
| HIGH | 2 | FINANCE |

## 3.6 Reference implementation

```python
# risk/blended.py

ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def _level(value, medium_at, high_at):
    if value >= high_at:
        return "HIGH"
    if value >= medium_at:
        return "MEDIUM"
    return "LOW"


def score_quotation(lines, cfg):
    """lines: [{product, qty, unit_price, discount_pct, allowed_pct}]

    `allowed_pct` is min(tier_limit, category_limit), resolved per line
    from the configuration tables before this is called.
    """
    per_line, total_excess_value, quote_list_value = [], 0.0, 0.0

    for ln in lines:
        list_value = ln["unit_price"] * ln["qty"]
        excess_pt = max(0.0, ln["discount_pct"] - ln["allowed_pct"])

        quote_list_value += list_value
        total_excess_value += list_value * excess_pt / 100.0

        per_line.append({**ln, "excess_pt": excess_pt})

    worst = max(per_line, key=lambda l: l["excess_pt"], default=None)
    worst_pt = worst["excess_pt"] if worst else 0.0

    blended_pt = (
        total_excess_value / quote_list_value * 100.0 if quote_list_value else 0.0
    )

    worst_level = _level(worst_pt, cfg.worst_medium_pt, cfg.worst_high_pt)
    blended_level = _level(blended_pt, cfg.blended_medium_pt, cfg.blended_high_pt)

    # PS section 4 A3: route to the HIGHEST required level.
    risk_level = max(worst_level, blended_level, key=lambda lv: ORDER[lv])

    if risk_level == "LOW":
        decided_by = "NONE"
    elif ORDER[worst_level] > ORDER[blended_level]:
        decided_by = "WORST_LINE"
    elif ORDER[blended_level] > ORDER[worst_level]:
        decided_by = "BLENDED"
    else:
        decided_by = "BOTH"

    return {
        "risk_level": risk_level,
        "decided_by": decided_by,
        "worst_line_excess_pt": round(worst_pt, 2),
        "worst_line": worst["product"] if worst and worst_pt > 0 else None,
        "blended_excess_pt": round(blended_pt, 2),
        "blended_score": round(min(1.0, blended_pt / cfg.score_cap_pt), 3),
        "violating_line_count": sum(1 for l in per_line if l["excess_pt"] > 0),
        "total_excess_value": round(total_excess_value, 2),
        "required_approval": cfg.chain_for(risk_level),
    }
```

## 3.7 Verified behaviour

Every row below was produced by running the implementation above.

| Scenario | worst | blended | level | decided_by |
|---|---|---|---|---|
| **PS §10 headline (Q-1042)** — one 8pt service line | 8.00 pt | 1.19 pt | **HIGH** | WORST_LINE |
| **PS §10 "why blended"** — 2/3/2 pt across equal lines | 3.00 pt | 2.33 pt | MEDIUM | BOTH |
| **Death by a thousand cuts** — 5 lines each 4pt over | 4.00 pt | 4.00 pt | **HIGH** | **BLENDED** |
| Fully compliant quote | 0.00 pt | 0.00 pt | LOW | NONE |
| One 1pt violation on a tiny line | 1.00 pt | 0.00 pt | MEDIUM | WORST_LINE |
| 15pt violation hidden in a large clean order | 15.00 pt | 0.11 pt | **HIGH** | WORST_LINE |

Rows 1 and 6 are why the worst-line path exists — the blended figure alone would
route both LOW. Row 3 is why the blended path exists — no single line reaches the
5pt HIGH cutoff, yet $200 of margin has quietly gone, and it correctly escalates
to Sales Manager **plus** Finance.

Keep these six cases as unit tests. They are the specification.

### Output

```json
{
  "risk_level": "HIGH",
  "decided_by": "WORST_LINE",
  "worst_line_excess_pt": 8.0,
  "worst_line": "Onsite Setup Service",
  "blended_excess_pt": 1.19,
  "blended_score": 0.119,
  "violating_line_count": 1,
  "total_excess_value": 36.0,
  "required_approval": ["SALES_MANAGER", "FINANCE"]
}
```

`decided_by` exists so section 5's "Why This Quote Was Flagged" text can name the
actual cause instead of guessing, and so a reviewer can see which rule fired.

## 3.8 Order-level discounts

PS §4 B3 allows "line level **or order level** discounts". An order-level
discount must be **pushed down onto the lines proportionally before scoring**,
otherwise it bypasses every per-line ceiling and escapes governance entirely.
Apply it to `discount_pct_i`, then score normally.

---

# 4. Approval Routing — MUST BUILD

Approval routing is driven by the **business-rule blended risk**, never by ML.

The level fed to this router is the **higher of the two paths** from section 3:

```text
risk_level = max(worst_line_level, blended_level)
```

Never route on the blended aggregate alone — see section 3.1 for why that fails
the problem statement's own headline example.

```text
LOW
  → no approval
  → fulfillment

MEDIUM
  → Sales Manager
  → fulfillment after approval

HIGH
  → Sales Manager
  → Finance
  → fulfillment after approval
```

The approval rules must come from the admin configuration:

```text
Discount Range | Approval Required
-----------------------------------
Within limit   | None
Medium risk    | Sales Manager
High risk      | Sales Manager + Finance
```

### Required audit trail

Every:

- submit
- approve
- reject
- return
- resubmit
- discount edit

must create an audit record containing:

```text
user
timestamp
action
quotation
reason/comment
```

---

# 5. Dynamic "Why Flagged" Explanation

The approval screen should generate its explanation from the actual calculation.

Do NOT hardcode:

```text
"Worst single line was 8pt over."
```

Instead:

```text
"{product} is {over_by}pt over its own limit, which triggered this review."
```

For multiple violations:

```text
"{count} lines exceed their configured limits.
The worst violation is {product} at {over_by}pt over.
The combined discount pattern produced a {risk_level} blended risk."
```

This makes the explanation trustworthy and demo-friendly.

---

# 6. Discount Anomaly Detection — MUST BUILD

This is **ML/statistical intelligence for Deal Health**, not approval routing.

For each sales rep, calculate a historical discount baseline.

```python
# ml/anomaly.py

import numpy as np

# Tunables. Keep them named and importable so they can be defended
# in review and adjusted without touching the logic.
MIN_HISTORY = 5      # quotes needed before a rep gets a personal baseline
MIN_STD = 2.0        # floor on spread, in discount percentage points
PLATFORM_MEAN = 8.0  # fallback baseline for reps with thin history
PLATFORM_STD = 4.0

HIGH_Z = 3.0         # z above this -> severity HIGH
MEDIUM_Z = 2.0       # z above this -> severity MEDIUM (also the flag threshold)


def rep_discount_baseline(
    historical_discounts: list[float],
) -> tuple[float, float]:
    """Mean and spread of a rep's past effective quote discounts.

    `historical_discounts` holds one value per PAST quote, expressed as
    quote-level effective discount percent:

        (list_total - net_total) / list_total * 100

    The quote being scored is excluded, otherwise it drags its own
    baseline toward itself and hides the anomaly.
    """
    if len(historical_discounts) < MIN_HISTORY:
        # Not enough history to trust a personal baseline.
        return PLATFORM_MEAN, PLATFORM_STD

    mean = float(np.mean(historical_discounts))

    # ddof=1 -> sample standard deviation. The population form (the numpy
    # default) understates spread at small n and inflates every z-score.
    # max(...) floors the denominator: a very consistent rep would otherwise
    # produce a near-zero std, and an ordinary discount would explode into a
    # double-digit z. A bare `or 1.0` does not cover this, because `or` only
    # substitutes on exactly 0.0.
    std = max(float(np.std(historical_discounts, ddof=1)), MIN_STD)

    return mean, std


def is_anomalous(
    discount_pct: float,
    rep_mean: float,
    rep_std: float,
    threshold: float = MEDIUM_Z,
) -> tuple[bool, float]:
    """One-sided test: only unusually HIGH discounts are of interest.

    A discount far BELOW a rep's average costs the company nothing, so
    `abs()` would be wrong here.
    """
    z_score = (discount_pct - rep_mean) / rep_std

    return z_score > threshold, round(float(z_score), 2)


def severity_for(z_score: float) -> str:
    """Maps a z-score onto the severity field returned by GET /deal-health."""
    if z_score > HIGH_Z:
        return "HIGH"
    if z_score > MEDIUM_Z:
        return "MEDIUM"
    return "NONE"
```

### Why these constants, if asked

| Constant | Value | Justification |
|---|---|---|
| `MEDIUM_Z` | 2.0 | Conventional outlier cutoff; one-sided 2 sigma flags roughly the top 2% of quotes. Configurable. |
| `MIN_HISTORY` | 5 | Three points cannot estimate a spread. Adding a single quote to a 3-point history can swing a z-score from 9.9 to 2.3 for the same discount. |
| `MIN_STD` | 2.0 pt | Without a floor, a rep whose past discounts are `[5, 5, 6]` has std 0.47, and an ordinary 7% discount scores z = 3.54 and is falsely flagged. |
| `ddof=1` | sample | The population form inflates z by roughly 22% at n=3 and 12% at n=5. |

### Known limitation, and the correct answer to it

A rep who *consistently* discounts at 22% has a mean of 22 and a near-zero
spread, so a fresh 22% quote scores z = 0.0 and is never flagged.

This is correct behaviour, not a defect. Anomaly detection asks
"is this unusual **for this rep**", and the answer is genuinely no. The
chronic over-discounter is caught by the **business-rule engine** in
sections 2 to 4, which asks the separate question "is this discount
**allowed**". The two layers cover each other; neither is sufficient alone.

### Distribution caveat

The z-score assumes an approximately normal spread. Real discount data is
clustered on round numbers (0, 5, 10, 15), right-skewed, and bounded below
at zero, so the nominal 2% flag rate is approximate. For a prototype on
seeded data this is fine. A median/MAD-based modified z-score would be the
production upgrade, and belongs in the "what we would build next" note.

### Example

```text
Rep history (6 past quotes) = 4%, 6%, 8%, 8%, 10%, 12%
Rep historical average      = 8.0%
Rep standard deviation      = 2.83%   (sample, ddof=1)
New discount                = 22%

z = (22 - 8.0) / 2.83
  = 4.95

→ anomaly, severity HIGH
```

**Seeding note:** seed the rep history explicitly, then assert the z-score
the API returns. A history that merely *looks* plausible will not reproduce
these numbers. For instance `[5, 8, 11, 8, 8, 8]` also averages 8%, but its
sample std is 1.90, which the MIN_STD floor lifts to 2.00, giving z = 7.00
rather than 4.95. The demo must print
what this document claims.

Deal Health can display:

```text
Delta LLC
Discount 22% vs avg 8%
Anomalous
```

This matches the intended Deal Health experience.

### Important distinction

A discount can be:

```text
Business-rule violation: YES
ML anomaly: NO
```

or:

```text
Business-rule violation: NO
ML anomaly: YES
```

They answer different questions.

- **Business rules:** "Is this discount allowed?"
- **Anomaly detection:** "Is this discount unusual for this rep?"

---

# 7. Deal Stall Prediction — DO NOT BUILD (evidence below)

> **Decision, 2026-09-05: do not build the stall model.** This was tested rather than
> guessed. See `research/stall-model/stall_model_viability.ipynb` for the full experiment.
>
> At the seed volume we actually plan (60–100 quotations) a gradient-boosted model is
> **worse** than a one-line threshold rule by 0.05 ROC-AUC. It only overtakes the rule
> at roughly 200+ rows. Two independent findings support the decision — see 7.1.
>
> Ship `days_since_last_activity > N` as configured business logic. PS §4 B9 asks for
> *"quotations inactive for more than a configured number of days"* — the problem
> statement itself specifies a threshold rule. Implementing exactly that is the
> specification, not a compromise.

The remainder of this section documents what was evaluated and what would be required
to revisit the decision.

It belongs only in **Deal Health**.

It does NOT determine manager/finance approval.

## 7.1 What the experiment found

Synthetic data was generated from a latent stall propensity with genuine class
overlap — deliberately *not* the two separable clusters this document originally
proposed, which would have guaranteed a flattering result. Rule baselines were scored
without cross-validation, which favours them; so an ML win would have been a real win.

**Finding 1 — sample size.** ML only beats the rule once there are ~200+ rows:

| training rows | rule ROC-AUC | ML ROC-AUC | verdict |
|---|---|---|---|
| **60** | 0.761 | 0.710 | **rule wins** |
| **100** | 0.732 | 0.681 | **rule wins** |
| 200 | 0.680 | 0.768 | ML wins |
| 400 | 0.672 | 0.838 | ML wins |
| 800 | 0.744 | 0.895 | ML wins |

The two bold rows are the volume this project actually plans to seed.

**Finding 2 — signal concentration.** Even with plenty of data, the ML advantage
disappears when stalling is driven mostly by inactivity alone:

| share of signal in `days_idle` | rule | ML | gain |
|---|---|---|---|
| 0.30 | 0.605 | 0.939 | +0.334 |
| 0.60 | 0.762 | 0.885 | +0.123 |
| 0.75 | 0.831 | 0.852 | +0.021 |
| 0.90 | 0.889 | 0.870 | **−0.019** |

We do not know where real sales data sits on this axis. If stalling is mostly "nobody
touched it in three weeks" — which is plausible — the model adds nothing at any volume.

**Incidental result.** The strongest feature was the engineered interaction
`days_idle × negotiation_rounds` (43% of permutation importance) — a deal that is both
idle *and* has been haggled over repeatedly. A single-threshold rule cannot express
that. This is the one genuine argument for a model, and it is exactly what small
samples cannot learn.

**Honest caveat.** Logistic regression (0.917) edged out the tree ensembles (0.895–0.916),
partly because the simulated data was generated from a logistic process. On real data
the ordering could differ. It does not affect the decision, which rests on sample size.

## 7.2 Judge-facing answer

> "We evaluated a stall-prediction model — logistic regression, random forest, gradient
> boosting, and soft-voting and stacked ensembles — against a deterministic threshold
> rule. At the data volume available it gave no lift, so we shipped the rule and spent
> the time on the approval engine. The feature pipeline is in place; with real
> historical outcomes, retraining is a contained change."

This answers "why no ML?" with evidence rather than an excuse.

## 7.3 What would change the decision

- **200+ real historical quotations with known outcomes.** Not seeded — real.
- Confirmation that stalling is genuinely multi-factor rather than idle-time-dominated.
- The core quote → approve → fulfil → bill flow already demoing cleanly.

The reference implementation below is retained for that future, not for this build.

### Features

```python
FEATURES = [
    "days_since_last_activity",
    "discount_pct",
    "blended_risk_score",
    "quote_value",
    "negotiation_rounds",
    "customer_tier_encoded",
]
```

### Model

A lightweight logistic regression is sufficient.

```python
import numpy as np
from sklearn.linear_model import LogisticRegression
import joblib


def build_training_set(seed_quotations):
    X = np.array([
        [q[f] for f in FEATURES]
        for q in seed_quotations
    ])

    y = np.array([
        q["stalled"]
        for q in seed_quotations
    ])

    return X, y


def train_and_save(
    seed_quotations,
    path="deal_health_model.joblib",
):
    X, y = build_training_set(seed_quotations)

    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)

    joblib.dump(model, path)

    return model


def predict_stall_risk(model, quotation_features):
    x = np.array([[
        quotation_features[f]
        for f in FEATURES
    ]])

    return float(model.predict_proba(x)[0][1])
```

### Training data

Use approximately:

```text
60–100 seeded quotations
```

with two synthetic clusters:

```text
Healthy:
- recent activity
- normal discounts
- fewer negotiation rounds

Stalled:
- old activity
- higher discounts
- more negotiation rounds
```

Label them:

```text
healthy → 0
stalled → 1
```

Be transparent with judges:

> "The prototype model is trained on our seeded dataset. With production usage, we would retrain it on actual historical outcomes."

Do not claim the prototype was trained on real customer history.

---

# 8. Delivery Promise Slippage — MUST BUILD, NO ML REQUIRED

This is deterministic business logic.

Compare:

```text
promised_delivery_date
vs
current_expected_delivery_date
```

If:

```text
current_expected_delivery_date > promised_delivery_date
```

create a Deal Health slippage flag.

Example:

```json
{
  "type": "delivery_slippage",
  "issue": "Delivery expected 3 days after promised date"
}
```

This completes the three Deal Health categories:

```text
Stalled Deals
Discount Anomalies
Delivery Slippage
```

---

# 9. Deal Health API

```text
GET /deal-health
```

Response should conceptually contain:

```json
{
  "stalled": [],
  "anomalies": [],
  "slippage": []
}
```

Each flag should contain enough information for the frontend to explain the reason:

```json
{
  "id": "flag-123",
  "quotation_id": "quote-456",
  "type": "discount_anomaly",
  "severity": "HIGH",
  "issue": "Discount 22% vs avg 8%",
  "flagged_at": "...",
  "recommended_action": "ESCALATE"
}
```

Actions:

```text
POST /deal-health/{id}/escalate
POST /deal-health/{id}/nudge
```

---

# 10. Re-Negotiation Must Re-run Business Risk

Customer negotiation is another critical path.

```text
Customer changes discount
        ↓
Backend updates quotation
        ↓
Recalculate line-level limits
        ↓
Recalculate blended business risk
        ↓
Apply approval routing
```

If the new terms require approval:

```text
Customer confirms
      ↓
Pending Approval
      ↓
Sales Manager
      ↓
Finance if required
```

Do not use stall ML or anomaly ML to make this routing decision.

---

# 11. Startup / Deployment Strategy

### Always build

```text
1. Line discount validation
2. Blended discount risk
3. Approval routing
4. Audit logging
5. Discount anomaly detection
6. Delivery slippage
```

### Build if ahead

```text
7. Stall prediction
```

### Skip unless everything else is finished

```text
8. ML/co-occurrence-based upsell ranking
```

The core workflow is more valuable than an additional ML feature.

---

# 12. Seed Data for a Deterministic Demo

Do not rely on random data.

Create explicit scenarios:

### Scenario A — Approval

```text
Customer: Gold
Product: Setup Service
Allowed: 10%
Given: 18%
Result: HIGH / approval required
```

### Scenario B — Anomaly

```text
Rep average: 8%
Rep std dev: ~3%
New discount: 22%
Result: Discount anomaly
```

### Scenario C — Stall

```text
Days since activity: 14+
Negotiation rounds: 4+
Discount: elevated
Result: high stall probability
```

### Scenario D — Slippage

```text
Promised: Sept 10
Expected: Sept 13
Result: 3-day delivery slippage
```

These should be seeded deliberately so the five-minute demo always produces the intended results.

---

# 13. Judge-Facing Explanation

Use this distinction if questioned:

> **"Our approval engine is deterministic business logic. It reads the configured customer-tier and category discount limits, calculates line-level violations and a blended quotation risk, and routes the approval chain accordingly."**

Then:

> **"ML is used separately for Deal Health. We use rep-specific statistical anomaly detection to identify unusual discounts and, if enabled, logistic regression to estimate stall probability. Those signals help managers prioritize deals but never override governance rules."**

For synthetic training:

> **"The prototype stall model is trained on our seeded dataset. In production, it would continuously learn from actual historical deal outcomes."**

---

# 14. 24-Hour Priority

```text
Hour 0–1
→ Seed deterministic risk scenarios
→ Create rep discount history
→ Create stall training data if attempting ML

Core build
→ Line discount validation
→ Blended risk engine
→ Approval routing
→ Audit trail

Hour 18–20
→ Integrate discount anomaly with Deal Health
→ Add delivery slippage
→ Add stall ML only if core flow is stable

Final testing
→ Quote with excessive discount
→ Manager approval
→ Finance approval
→ Customer renegotiation
→ Re-approval
→ Fulfillment
→ Billing
→ Deal Health
```

---

# 15. Final Architecture Rule

The system should always follow this separation:

```text
                  ┌──────────────────────────┐
                  │   CONFIGURED RULES       │
                  │ tier + category limits   │
                  └────────────┬─────────────┘
                               ↓
Quotation → Line Validation → Blended Risk → Approval Router
                                             ↓
                                      Manager / Finance


Quotation + History → ML / Statistics → Deal Health
                                      ├─ Discount anomaly
                                      └─ Stall probability

Order + Dates → Business Rules → Delivery Slippage
```

**Never make ML the authority for discount approval.**

The strongest national-level implementation is therefore not "more AI"; it is a **real, deterministic sales governance engine with ML layered on top for proactive deal intelligence.**
