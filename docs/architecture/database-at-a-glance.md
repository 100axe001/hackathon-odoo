# The database, on one screen

24 tables. Full detail in [`data-model.md`](data-model.md); this is the version you can
hold in your head.

---

## The shape

```
                        ┌─────────────┐
                        │  customers  │──── tier ───▶ discount_tiers
                        └──────┬──────┘                     │
                               │                            │ ceilings the
                               │ buys                       │ engine reads
                               ▼                            ▼
  users ── rep ────▶ ┌──────────────────┐          category_ceilings
                     │    QUOTATIONS    │          risk_thresholds
                     │   ← the spine →  │          approval_rules
                     └────────┬─────────┘          upsell_rules
                              │
     ┌──────────┬─────────────┼──────────────┬───────────────┐
     ▼          ▼             ▼              ▼               ▼
quotation_  approval_    audit_logs   negotiation_    fulfillment_
  lines       steps                     messages       allocations
     │                                                      │
     │ product                                              │ from
     ▼                                                      ▼
  products ──────── stocked at ──────▶ stock_levels ──▶ warehouses
     │
     │ billed as
     ▼
 subscriptions ──▶ billing_schedules        invoices ──▶ invoice_lines
     │                                          ▲
     └───────── plan ──▶ subscription_plans     │
                                          quotations
```

`deal_health_flags`, `product_pairings` and `price_lists` hang off quotations, products and
tiers respectively.

---

## The one rule the shape follows

**Anything the engine decides is read from a table, not written in code.** Discount
ceilings, risk cut-points, the approval chain, replenishment points, cancellation policy
and the upsell margin floor are all rows an admin can change, and changing one changes
behaviour on the next submit.

---

## By group

| Group | Tables | Holds |
| --- | --- | --- |
| **Identity & config** | `users` `customers` `discount_tiers` `category_ceilings` `risk_thresholds` `approval_rules` `upsell_rules` `price_lists` | Everything the engine reads to make a decision |
| **Catalogue & stock** | `products` `warehouses` `stock_levels` `product_pairings` | What is sold, and where it physically is |
| **Quotations** | `quotations` `quotation_lines` `approval_steps` `audit_logs` `negotiation_messages` | The deal, its terms, its chain, its history |
| **Fulfillment** | `fulfillment_allocations` | Which warehouse covered which line, and the backorder |
| **Billing** | `subscription_plans` `subscriptions` `billing_schedules` `invoices` `invoice_lines` | What recurs, when, and what was billed |
| **Deal health** | `deal_health_flags` | Stalled, anomaly and slippage findings |

---

## Five things worth knowing

**The quotation is the spine.** Lines, approval steps, audit trail, the customer
conversation, stock allocations and invoices all point at it. Every screen in the app is a
view onto one of those relationships.

**Two ceilings meet on a line.** `discount_tiers.max_discount_pct` is what the customer's
tier allows; `category_ceilings.max_discount_pct` is what the product's category allows.
The line is held to the stricter. Both the resolved ceiling and the excess are **frozen
onto `quotation_lines`** when it is scored, so the audit trail stays truthful even if
configuration changes later.

**On hand is not available.** `stock_levels.qty_on_hand − qty_reserved` is what can
actually be promised. Accepting a split writes `fulfillment_allocations` and increments
`qty_reserved`. A row with `warehouse_id = NULL` is the backorder — demand nothing could
cover, stored rather than inferred.

**A credit note is an invoice with a negative amount**, distinguished by `doc_type`, not a
table of its own. One status calculation, one place to look.

**Money is `Numeric(12,2)`, percentages `Numeric(5,2)`, never `Float`.** SQLite has no
decimal type and would store these as floats, so `0.1 + 0.2` becomes
`0.30000000000000004` — and a system that sums discount excesses and compares them against
a threshold would route the same quotation MEDIUM on one run and HIGH on the next.

---

## Conventions

| Rule | Why |
| --- | --- |
| `DateTime(timezone=True)`, stored UTC | A demo that crosses midnight should not rewrite its own history |
| Enums are `String` + a Python `StrEnum` | Adding a status must not need a migration in a project that has none |
| No `ON DELETE CASCADE` on configuration | Deleting a tier customers are on, or a warehouse that has shipped, is refused with a reason rather than silently taking rows with it |
| `app/models/__init__.py` imports every module | SQLAlchemy resolves relationships by name at mapper-configuration time; a module nobody imports fails far from the cause |

---

## Two datasets

| Script | Rows | For |
| --- | --- | --- |
| `backend/reset_db.py` | ~260 | The demo. Carries Q-1042, the deal-health scenarios, and the stock arrangement the tests depend on. |
| `backend/seed_large.py` | 793 | Volume. 40 companies, 60 products, 80 quotations across the past year, for exercising lists, filters and sorting. |
| `backend/wipe_data.py` | — | Empties every table. Requires `--yes`; otherwise reports only. |

There are **no migrations**, deliberately: `reset_db.py` drops, recreates and reseeds in
seconds, and the demo depends on that being safe. The trade is real — no upgrade path for
an existing database — and it is the first thing to add with more time.
