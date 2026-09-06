# The two algorithms

Warehouse splitting and approval routing. Both make a decision the business would
otherwise make by hand, and both are written so the reason for each choice survives.

The formulas they use are defined in [`formulas.md`](formulas.md).

---

## 1. Warehouse split

`app/utils/fulfillment.py`

### The objective, and why it is ordered

**Fewest shipments first. Shipping cost only as a tie-break.**

That ordering is a business call, not an optimisation detail. A customer receiving three
separate parcels is worse than a slightly higher freight bill, and the brief (§4-A4) says
to minimise the number of shipments.

The consequence is worth stating plainly: **the algorithm does not pick the cheapest
warehouse.** It picks the one that clears the most outstanding demand. Cheapest-first
optimises the secondary objective and produces more boxes.

### The algorithm

```
INPUT   demand: {product_id -> units required}
        warehouses: each with {product_id -> units available}
                    and a shipping_cost_weight

STEP 0  Order warehouses by (shipping_cost_weight, name).
        Deterministic — a split that differs between runs demonstrates nothing.

STEP 1  Can one warehouse cover the entire order?
        If yes, take it and stop. One shipment beats every multi-warehouse
        answer, so this is checked before any combination is considered.
        Ordered by weight, so the cheapest single warehouse that can do it wins.

STEP 2  Otherwise, greedy cover. Repeat until nothing is left:
          - score every warehouse by how many outstanding units it could supply
          - take the highest score; tie-break on lower shipping weight
          - allocate what it can, subtract from remaining
          - if the best warehouse can supply nothing, stop

STEP 3  Anything still outstanding becomes an allocation row with
        warehouse_id = NULL. That row IS the backorder.

OUTPUT  allocations, shipment count, total cost, units backordered
```

### Why greedy rather than optimal

Minimum set cover is NP-hard. Greedy is the standard approximation and is provably within
a `ln(n)` factor — with a handful of warehouses and a handful of products, that gap is
almost always zero. An exact solver would cost complexity and demo-time latency to fix a
difference that does not appear at this scale.

### Details that matter

| Detail | Why |
| --- | --- |
| A backorder is a **stored row**, not an inferred gap | It can be listed, counted, and shown to the customer as "partly on backorder" rather than recomputed from a difference every time |
| Accepting a split increments `qty_reserved` | This is what makes stock actually move. Until then the suggestion holds nothing |
| Inactive warehouses are filtered out before the algorithm runs | Stock in a depot we do not ship from is not available to promise |
| Availability is `on_hand − reserved` | Stock already promised to another deal cannot cover this one |

### Worked example — the demo

Q-1042 needs 2 laptops, 1 setup service, 1 warranty.

| Warehouse | Laptops available | Weight |
| --- | --- | --- |
| Main Warehouse | 1 (40 on hand, 39 reserved) | 1.0 |
| East Depot | 4 | 1.4 |

Step 1 finds no single warehouse holding everything — Main is one laptop short. Step 2
takes Main first (it clears the most: 1 laptop + service + warranty = 3 units), then East
Depot for the remaining laptop. **Two shipments, cost 25×1.0 + 25×1.4 = $60, nothing
backordered.**

The seeded reservation of 39 is deliberate: it guarantees the split happens on every run
rather than only when stock happens to be low.

---

## 2. Approval routing

`app/utils/blended.py`, `app/utils/approval.py`

### The algorithm

```
ON SUBMIT

STEP 1  For each line, resolve allowed_pct = min(tier, category) ceiling
        and record excess_pt. Write both onto the line.

STEP 2  Score two independent paths (see formulas.md §2):
          worst_pt    — the single worst line
          blended_pt  — the whole order's excess over its list value

STEP 3  risk_level = max(level(worst_pt), level(blended_pt))

STEP 4  If risk_level is LOW: delete any existing steps, mark the quotation
        Approved, and stop. No reviewer is involved.

STEP 5  Otherwise read approval_rules for that level and create one
        approval_steps row per required role, in step_order.

STEP 6  Write an audit row. Commit once.
```

### Why the verdict is frozen onto the line

`allowed_discount_pct` and `excess_pt` are **written to the row**, not merely returned. If
an admin changes a ceiling tomorrow, the audit trail still shows the rule that was in force
when the decision was made. Recomputing on read would silently rewrite history.

### Acting on a step

Three checks, each blocking a specific way the chain could be sidestepped:

| Check | Prevents |
| --- | --- |
| `quotation.rep_id ≠ caller` | A rep approving their own discount — the premise of the product |
| `step.required_role == caller.role`, first pending step only | Finance signing off before the manager has |
| `quotation.status == Pending Approval` | Acting on a quotation that is no longer awaiting review |

The third is the subtle one. **Returning** a quotation sets it back to Draft but leaves the
later steps pending. Without this check, finance could approve that Draft and drive it to
Approved without the rep ever revising it. There is a test that fails if the check is
removed.

### Rebuild, never append

On resubmit the chain is deleted and rebuilt from the new risk level. A quotation that
comes back with a smaller discount needs **fewer** reviewers, not the old ones plus new.

### The same engine runs on customer confirm

When a customer confirms in the portal, the negotiated terms are re-scored by this exact
code path. If they talked the discount past a threshold, the quotation re-enters approval
rather than confirming. That is the brief's §4-B8 requirement, and it is the same function
— not a second implementation that could drift.

Confirming is refused while a quotation is mid-approval, precisely because confirming
rebuilds the chain and would otherwise erase a decision a manager had already made.
