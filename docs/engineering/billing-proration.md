# Billing and Proration

**Specified:** 2026-09-05 · Implements PS §4 B7 and A5.

## What the brief asks for

> **B7** — *"Shows one time lines and recurring lines **separately** within the same
> order. Displays upcoming billing schedule for recurring lines. Handles mid cycle
> proration when quantity changes. Cancel or modify subscription controls, with an
> **automatic partial refund or credit note** trigger when applicable."*
>
> **§9 step 6** — *"Check that a one time product and a recurring subscription on the
> same order are billed correctly and separately."*
>
> **§9 step 8** — *"Confirm the order, record a payment, and check that the invoice
> status updates correctly."*

## Why one-time and recurring are separate invoices

A laptop is billed once. A support plan is billed every month, forever. Putting both on
one document means the customer either pays for the laptop twelve times or the plan
once — and reconciliation has no way to tell which lines recur.

So a confirmed order produces:

- **one** `ONE_TIME` invoice for the outright lines, due on Net 30
- **one** `RECURRING` invoice per billing period, generated from the schedule

They share `quotation_id`, so the order still reads as one order.

## Proration

The rule is one line:

```text
prorated_amount = price_delta × (remaining_days / cycle_days)
```

`price_delta` is the change in the periodic charge, not the new total:

```text
price_delta = (new_qty − old_qty) × unit_price
```

**Worked example.** $46/month, billed the 15th. On the 30th — 15 days into a 30-day
period already paid for — the customer goes from 1 seat to 3.

```text
price_delta = (3 − 1) × 46           = 92.00
prorated    = 92 × 15/30             = 46.00   charged now
```

Not $0 (they would get two seats free for half a month) and not $138 (they would pay
for three seats on days they had one).

**Downgrades run the same formula.** A negative `price_delta` yields a negative amount,
which is a credit note rather than a charge. One expression, both directions — a
separate refund path is where the two drift apart.

## Cancellation

Cancelling mid-cycle refunds the unused remainder:

```text
credit = −current_charge × (remaining_days / cycle_days)
```

Raised as a **credit note**, which is an invoice with `doc_type = CREDIT_NOTE` and a
negative amount. A credit note is a negative invoice in accounting terms; giving it its
own table would duplicate every field and split the customer's balance across two
places.

## Days, not seconds

Counted in whole days, matching how an invoice reads. Cycle length is the **actual**
calendar span — `relativedelta` handles the 28-to-31 day variation and month-end
rollover, so a plan billed on the 31st does not silently move to the 1st.

## Billing schedule

Each subscription carries forward-dated `BillingSchedule` rows: the next charge and
its date. B7 asks the screen to show what is coming, so it has to be stored rather
than derived at render time — and a prorated adjustment is a schedule row flagged
`is_prorated`, so the customer can see why one charge differs.

## Invoice status

```text
UNPAID    → nothing recorded
PARTIAL   → paid_amount > 0 but < amount
PAID      → paid_amount >= amount
```

Recording a payment sets `paid_amount`, `paid_at`, and recomputes the status. Status is
stored rather than derived so a report can group on it without recomputing every row.

## Nothing is billed before it ships

The wireframe's note on Screen 13: *"Partial invoicing stays reconciled with partial
delivery, nothing is billed before it ships."* A one-time invoice is raised from the
**fulfilled** quantity, so an order split across two warehouses with one on backorder
invoices only what actually went out.

## Edge cases the tests pin

| Case | Expected |
|---|---|
| Quantity increased mid-cycle | charge for the remaining days only |
| Quantity decreased mid-cycle | credit note, same formula, negative |
| Change on the first day of a cycle | full period charged |
| Change on the last day | close to zero, never negative for an increase |
| Cancellation mid-cycle | credit for the unused remainder |
| Cancelling an already-cancelled subscription | rejected, not a second credit |
| Payment below the total | `PARTIAL` |
| Payment at or above the total | `PAID` |
| One-time and recurring on one order | two invoices, never one |
