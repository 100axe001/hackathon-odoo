# Warehouse Split Algorithm

**Specified:** 2026-09-05 · Implements PS §4 B6 and A4.

## What the brief asks for

> **A4** — *"Define shipping cost weighting used by the auto split logic to **minimise
> number of shipments**."*
>
> **B6** — *"Shows recommended warehouse split for the order based on live stock."*
> Displays warehouse name, quantity fulfilled from it, estimated shipment count and
> cost. Buttons: **Accept Suggested Split**, **Manual Override**. If stock arrives
> mid-fulfilment, a **"Consolidate Remaining Backorder"** prompt appears.

So the objective is ordered, not blended:

1. **Fewest shipments** — every extra box costs money and annoys the customer
2. **Then** lowest weighted cost

## The quantities

```text
available[w][p] = on_hand[w][p] − reserved[w][p]
demand[p]       = qty on the quotation line
```

**`available`, never `on_hand`.** Reserved stock is already promised to another order;
allocating it twice is how two customers get told the same unit is theirs.

A **shipment** is one warehouse sending one box, however many products it contains. So
shipment count is the number of *distinct warehouses used*, not the number of lines.
That is what makes this a covering problem rather than a per-line choice.

## The algorithm

Choosing the true minimum set of warehouses is set cover, which is NP-hard. A greedy
heuristic is the right trade here, and it is honest to say so.

```text
1. Single-warehouse pass
   If any one warehouse can cover EVERY line in full, use it. One shipment cannot be
   beaten. Among warehouses that can, pick the lowest shipping_cost_weight.

2. Greedy cover
   While demand remains:
     score each warehouse by how many units of the remaining demand it can cover
     pick the highest; tie-break on lower shipping_cost_weight, then on name so the
       result is deterministic
     allocate everything it can supply, decrement demand
     if the best warehouse covers nothing, stop

3. Backorder
   Whatever demand is left becomes an allocation row with warehouse_id = NULL.
```

**Why "covers the most" rather than "cheapest first":** cheapest-first optimises the
secondary objective at the expense of the primary one. A cheap depot holding two units
would be picked before a dear one holding forty, producing more boxes — exactly what A4
says to avoid.

**Determinism matters.** Ties break on weight, then name. A demo that produces a
different split on each run is not demonstrating an algorithm.

## Cost

```text
shipment_cost(w) = SHIPMENT_BASE_COST × shipping_cost_weight[w]
total_cost       = Σ shipment_cost(w) for each warehouse used
```

`shipping_cost_weight` is a multiplier configured per warehouse on Screen 18's sibling
admin page — a distant depot costs more per box. Backorders carry no cost until they
ship.

## Reserving

Accepting a split increments `reserved` on each allocated `stock_level`. Until then the
split is only a suggestion and holds nothing — otherwise merely *looking* at a
quotation would take stock out of circulation.

Overriding replaces the allocation rows and re-reserves against the new numbers.

## Backorder consolidation

A backorder row (`warehouse_id = NULL`) stays open until stock arrives. When it does,
the outstanding quantity is re-run through the same algorithm. B6 calls for the prompt
to appear automatically; for the demo a **Simulate Restock** button raises stock so the
moment can be shown on cue rather than waited for.

## Worked example

Order: **24 laptops**. Stock:

| Warehouse | on_hand | reserved | available | weight |
|---|---|---|---|---|
| Main Warehouse | 40 | 18 | **22** | 1.0 |
| East Depot | 10 | 6 | **4** | 1.4 |

- Step 1 finds no single warehouse holding 24 → no one-shipment answer
- Step 2 picks Main (covers 22 > 4), then East (covers the last 2)
- Demand is met: **2 shipments**, cost `25×1.0 + 25×1.4 = $60.00`

Had the order been for 30, the last 4 would become a backorder row rather than
silently under-shipping.

## Edge cases the tests pin

| Case | Expected |
|---|---|
| One warehouse can cover everything | 1 shipment, cheapest such warehouse |
| No warehouse can cover everything | fewest warehouses that can, greedily |
| Total available < demand | the remainder becomes a backorder row |
| Zero available anywhere | the whole order is a backorder |
| Two warehouses tie on coverage | lower weight wins, then name |
| An inactive warehouse | never allocated from |
