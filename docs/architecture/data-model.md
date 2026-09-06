# Data model

24 tables. The whole shape follows from one rule: **anything the engine decides is read
from a table, not written in code** — discount ceilings, risk cut-points, the approval
chain, replenishment points, cancellation policy and the upsell margin floor are all
rows an admin can change.

---

## Why PostgreSQL

Money is `Numeric(12,2)` and percentages are `Numeric(5,2)`, never `Float`.

SQLite has no decimal type — `NUMERIC` there gives you a column with numeric *affinity*
storing 8-byte floats, so `0.1 + 0.2` is `0.30000000000000004`. In a discount governance
system that is the one bug class that would actually embarrass you: the engine sums
`line_value × excess_pt / 100` across lines and compares against a configured threshold,
so float drift near a boundary lets the same quotation route MEDIUM on one run and HIGH
on the next.

Postgres also enforces foreign keys always. SQLite accepts `REFERENCES` and silently
ignores it unless every connection sets `PRAGMA foreign_keys=ON`, which means you can
delete a customer and keep their quotations pointing at nothing.

---

## Tables

### Identity & configuration

| Table | Key columns | Points at |
| --- | --- | --- |
| `users` | `email`, `password_hash`, `full_name`, `role`, `customer_id`, `created_at` | `customers` |
| `customers` | `name`, `tier_id`, `currency`, `created_at` | `discount_tiers` |
| `discount_tiers` | `name`, `max_discount_pct` | — |
| `category_ceilings` | `category`, `max_discount_pct` | — |
| `risk_thresholds` | `rule_type`, `level`, `min_excess_pt` | — |
| `approval_rules` | `level`, `step_order`, `role` | — |
| `upsell_rules` | `min_margin_pct`, `max_suggestions` | — |
| `price_lists` | `name`, `tier_id`, `currency`, `adjustment_pct` | `discount_tiers` |

### Catalogue & stock

| Table | Key columns | Points at |
| --- | --- | --- |
| `products` | `name`, `category`, `unit_price`, `cost_price`, `unit`, `tax_pct`, `description` | — |
| `warehouses` | `name`, `region`, `shipping_cost_weight`, `active` | — |
| `stock_levels` | `warehouse_id`, `product_id`, `qty_on_hand`, `qty_reserved`, `reorder_point`, `reorder_qty` | `products`, `warehouses` |
| `product_pairings` | `product_a_id`, `product_b_id`, `rank` | `products` |

### Quotations & governance

| Table | Key columns | Points at |
| --- | --- | --- |
| `quotations` | `number`, `customer_id`, `rep_id`, `status`, `promised_delivery_date`, `expected_delivery_date`, `fulfillment_status` | `customers`, `users` |
| `quotation_lines` | `quotation_id`, `product_id`, `qty`, `unit_price`, `cost_price`, `discount_pct`, `allowed_discount_pct` | `products`, `quotations` |
| `approval_steps` | `quotation_id`, `step_order`, `required_role`, `status`, `acted_by`, `acted_at`, `comment` | `quotations`, `users` |
| `audit_logs` | `quotation_id`, `user_id`, `action`, `note`, `created_at` | `quotations`, `users` |
| `negotiation_messages` | `quotation_id`, `quotation_line_id`, `author_id`, `body`, `counter_discount_pct`, `requested_delivery_date`, `created_at` | `quotation_lines`, `quotations`, `users` |

### Fulfillment

| Table | Key columns | Points at |
| --- | --- | --- |
| `fulfillment_allocations` | `quotation_id`, `product_id`, `warehouse_id`, `qty`, `shipping_cost`, `is_override`, `resolved_at` | `products`, `quotations`, `warehouses` |

### Billing

| Table | Key columns | Points at |
| --- | --- | --- |
| `subscription_plans` | `name`, `cycle`, `price`, `proration_enabled`, `refund_window_days`, `cancellation_fee_pct` | — |
| `subscriptions` | `customer_id`, `quotation_id`, `plan_id`, `qty`, `unit_price`, `status`, `started_at` | `customers`, `quotations`, `subscription_plans` |
| `billing_schedules` | `subscription_id`, `due_date`, `amount`, `is_prorated`, `note`, `invoice_id` | `invoices`, `subscriptions` |
| `invoices` | `number`, `quotation_id`, `customer_id`, `doc_type`, `line_type`, `amount`, `status` | `customers`, `quotations`, `users` |
| `invoice_lines` | `invoice_id`, `description`, `qty`, `amount`, `is_recurring` | `invoices` |

### Deal health

| Table | Key columns | Points at |
| --- | --- | --- |
| `deal_health_flags` | `quotation_id`, `type`, `severity`, `issue`, `z_score`, `days_idle`, `days_slipped` | `quotations` |

**24 tables.**


---

## Conventions

| Rule | Why |
| --- | --- |
| Money `Numeric(12,2)`, percentages `Numeric(5,2)`, never `Float` | Exact base-10 arithmetic, as above |
| `DateTime(timezone=True)`, stored UTC | A demo that crosses midnight should not change its own history |
| Enums are `String` + a Python `StrEnum`, not native Postgres enums | Adding a status must not need a migration in a build with no migrations |
| No `ON DELETE CASCADE` on configuration | Deleting a tier customers are on, or a warehouse that has shipped, is refused with a reason rather than silently taking rows with it |
| `app/models/__init__.py` imports every module | SQLAlchemy resolves relationships by name at mapper configuration; a module nobody imports fails far from the cause |

---

## The relationships that carry the product

**A quotation is the spine.** `quotation_lines` hold the terms, `approval_steps` the
chain that must sign them off, `audit_logs` who did what, `negotiation_messages` the
conversation with the customer, `fulfillment_allocations` where the stock came from, and
`invoices` what was billed. Every screen is a view onto one of those.

**Two ceilings meet on a line.** `discount_tiers.max_discount_pct` is what the customer's
tier allows; `category_ceilings.max_discount_pct` is what the product's category allows.
The line is held to `min()` of the two, and `quotation_lines.allowed_discount_pct` and
`excess_pt` are frozen onto the row when it is scored — so the audit trail stays truthful
even if configuration changes afterwards.

**Stock is not availability.** `stock_levels.qty_on_hand` minus `qty_reserved` is what can
actually be promised. Accepting a split writes `fulfillment_allocations` and increments
`qty_reserved`; a row with `warehouse_id = NULL` is the backorder — demand nothing could
cover.

**A credit note is an invoice with a negative amount**, distinguished by `doc_type`, not a
table of its own. One document type, one status calculation, one place to look.

---

## No migrations

There are none, deliberately. `reset_db.py` drops, recreates and reseeds in seconds, and
the demo depends on that being safe to run. The trade is real and stated: there is no
upgrade path for an existing database, which is the first thing to add with more time.
