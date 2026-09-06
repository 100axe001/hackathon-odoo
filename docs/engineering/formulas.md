# Every formula, and what each term means

One page. Every number the system computes, the expression that produces it, and a
definition of each symbol. Nothing here is approximate — these are the expressions as
implemented, and the file each lives in.

All arithmetic is `Decimal`, never float. Money rounds half-up to 2 places at the point it
is stored or shown, never mid-calculation.

---

## 1. The discount ceiling for a line

`app/utils/discount.py`

```
allowed_pct  =  min(tier_ceiling_pct, category_ceiling_pct)
excess_pt    =  max(0, discount_pct − allowed_pct)
```

| Term | Means |
| --- | --- |
| `tier_ceiling_pct` | What this customer's tier may be discounted by. From `discount_tiers.max_discount_pct`. |
| `category_ceiling_pct` | What this product's category may be discounted by. From `category_ceilings.max_discount_pct`. |
| `allowed_pct` | The ceiling this line is actually held to. **The stricter of the two wins.** |
| `discount_pct` | What the rep gave on this line. |
| `excess_pt` | How far over the line is, in **percentage points**. Never negative — a line under its ceiling is not credit against another line that is over. |

> A Gold customer may take 15%, but a Services line is capped at 10%. Give 18% on that
> line and `allowed_pct = 10`, so `excess_pt = 8`.

**Points, not percent.** `excess_pt` is a difference between two percentages, so its unit
is percentage points. Saying "8% over" would be ambiguous; "8 points over" is not.

---

## 2. Blended risk

`app/utils/blended.py`

Two independent scores. **Both are in percentage points**, so the same thresholds mean the
same thing on either path.

### Per line

```
list_value    =  unit_price × qty
excess_value  =  list_value × excess_pt / 100
```

| Term | Means |
| --- | --- |
| `list_value` | The line at **list price, before any discount**. |
| `excess_value` | The money given away *above policy* on this line. |

**Why list and not net.** A net denominator shrinks as discounts grow, so the identical
violation would score higher on a more heavily discounted quote. List value is a fixed
reference.

### The two paths

```
worst_pt    =  max(excess_pt over all lines)

blended_pt  =  Σ excess_value  /  Σ list_value  × 100
```

| Term | Means |
| --- | --- |
| `worst_pt` | The single worst line, in points over its own ceiling. Catches one badly-over line. |
| `blended_pt` | The whole order's excess as a share of its list value. Catches many slightly-over lines. |

### The decision

```
worst_level    =  level(worst_pt,   worst_medium_pt,   worst_high_pt)
blended_level  =  level(blended_pt, blended_medium_pt, blended_high_pt)

risk_level     =  max(worst_level, blended_level)
```

`level(v, m, h)` returns HIGH if `v ≥ h`, MEDIUM if `v ≥ m`, otherwise LOW. All four
cut-points are rows in `risk_thresholds`, not constants.

**Why both paths are needed.** Take the brief's own example: a $3,030 order where one $450
service line is 8 points over. Its excess value is $36, so `blended_pt = 36 / 3030 × 100 =
1.19` — nowhere near a threshold. A single-average design routes that LOW, which is the
opposite of what the brief requires. The worst-line path catches it. Conversely, three
lines each 2–3 points over would pass a worst-line-only test; the blended path catches
those. `max()` of the two is what satisfies both halves.

### Display score

```
blended_score  =  min(1, blended_pt / score_cap_pt)
```

A 0–1 normalisation for display only, capped at `score_cap_pt = 10`. **It decides
nothing** — routing uses the levels above.

---

## 3. Margin

`app/utils/margin.py`

```
line_net     =  unit_price × qty × (100 − discount_pct) / 100
line_margin  =  line_net − (cost_price × qty)

margin       =  Σ line_margin
margin_pct   =  margin / Σ line_net × 100
```

| Term | Means |
| --- | --- |
| `line_net` | What the customer pays for this line after its discount. |
| `cost_price` | What the product costs us. Stored per product, copied onto the line when it is added. |
| `margin_pct` | Margin as a share of **net revenue**, not of list. |

**Cost does not move with the discount.** Every point of discount comes straight out of
margin, which is the entire reason the ceilings exist.

---

## 4. Discount anomaly

`app/utils/anomaly.py`

```
baseline_mean, baseline_std  =  mean(history), max(stdev(history), 2.0)

z  =  (discount_pct − baseline_mean) / baseline_std
```

| Term | Means |
| --- | --- |
| `history` | This rep's effective discount on each of their **past** quotations. The one being scored is excluded. |
| `baseline_mean` | That rep's normal discount. |
| `baseline_std` | Sample standard deviation (`ddof=1`), floored at 2.0 points. |
| `z` | How many standard deviations above their own normal this quote is. |

Flagged when `z > 2.0`; severity HIGH when `z > 3.0`.

Three constants, each for a reason:

| Constant | Value | Why |
| --- | --- | --- |
| `MIN_HISTORY` | 5 | Below five past quotes there is no pattern, only noise. Falls back to a platform baseline of mean 8.0, std 4.0. |
| `ddof` | 1 (sample) | The population form understates spread at small n and inflates every z — by about 22% at n=3. |
| `MIN_STD` | 2.0 | A very consistent rep has near-zero spread, so an ordinary discount would explode into a double-digit z. A bare `or 1.0` does not fix this: it only catches exactly zero. |

**One-sided on purpose.** A discount far *below* a rep's average costs the company
nothing, so `abs(z)` would be wrong.

**This is advisory.** It flags a deal for a human. It has no path to approval routing.

---

## 5. Proration

`app/utils/billing.py`

```
cycle_days     =  (period_start + cycle) − period_start
remaining      =  clamp(0, cycle_days, period_end − change_date)

price_delta    =  (new_qty − old_qty) × unit_price
amount         =  price_delta × remaining / cycle_days
```

| Term | Means |
| --- | --- |
| `cycle_days` | The **real calendar length** of this billing period, via `relativedelta`. February is 28. |
| `remaining` | Days left in the period, clamped so a change dated outside it charges the whole period rather than producing a negative remainder. |
| `price_delta` | The change in the periodic charge — **not** the new total. |
| `amount` | Positive is a charge, **negative is a credit note**. |

**One expression covers both directions.** A downgrade gives a negative delta, therefore a
negative amount, which is exactly a credit. A separate refund path is where two
implementations drift apart.

### Cancellation

```
credit  =  prorate(current_charge, old_qty=1, new_qty=0)     # unused remainder

if days_since_start > refund_window_days:   credit = 0
else:                                        credit −= credit × cancellation_fee_pct / 100
```

`refund_window_days` and `cancellation_fee_pct` are columns on `subscription_plans`, so
the policy is configuration rather than code. The fee shrinks the credit toward zero — it
does not grow the refund.

---

## 6. Invoice status

`app/utils/billing.py`

```
paid ≤ 0        →  Unpaid
paid ≥ amount   →  Paid
otherwise       →  Partial

balance_due  =  max(0, amount − paid_amount)
```

`balance_due` is floored at zero: an overpayment settles the invoice, it is not owed back
on the same line. Status is **stored**, not derived on read, so reports can group on it.

---

## 7. Shipping cost

`app/utils/fulfillment.py`

```
shipment_cost  =  25.00 × warehouse.shipping_cost_weight
total_cost     =  Σ shipment_cost over warehouses used
```

`shipping_cost_weight` is a per-warehouse multiplier (Main 1.0, East Depot 1.4, EU Transit
2.1) — a relative expense of shipping from there, editable in the admin screen. It is the
**tie-break**, never the primary objective. See [`algorithms.md`](algorithms.md).

---

## 8. Stock availability

`app/models/fulfillment.py`

```
available  =  qty_on_hand − qty_reserved

needs_restock  =  reorder_point > 0  and  available ≤ reorder_point
```

**On hand is not available.** Reserved units are already promised to another deal.
Replenishment is measured against `available`, not `qty_on_hand`, because stock that is
spoken for cannot cover a new order.

In the demo Main Warehouse holds 40 laptops with 39 reserved — one free. That is why
Q-1042 has to split across two warehouses on every run.
