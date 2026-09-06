# API contract

63 endpoints. Every response is wrapped as `{success, message, data}`; the frontend client unwraps `data` and throws on
anything else, so every screen sees the payload or an error, never a half-shape.

Auth is a JWT in an httpOnly cookie. The **Who** column is enforced server-side —
the route guard in the browser only decides what to render.


## Auth

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | Public | Exchange credentials for a session cookie. |
| `POST` | `/auth/logout` | Public | Clear the session cookie. |
| `GET` | `/auth/me` | Public | Who the caller is. The frontend calls this on load to restore a session. |
| `POST` | `/auth/signup` | Public | Create an internal account and sign it in. |

## Quotations

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/quotations` | Any internal | Every quotation the caller may see. A rep sees only their own. |
| `POST` | `/quotations` | Any internal | Open an empty draft for a customer. |
| `GET` | `/quotations/{quotation_id}` | Any internal |  |
| `DELETE` | `/quotations/{quotation_id}` | Its creator | Throw away a quotation you opened. Refused once it has been billed or confirmed. |
| `GET` | `/quotations/{quotation_id}/approval-detail` | Any internal | Why this quotation was flagged, plus the chain and the audit trail. |
| `POST` | `/quotations/{quotation_id}/approve` | Any internal | Approve, return, or reject the step currently waiting on this caller. |
| `GET` | `/quotations/{quotation_id}/fulfillment-split` | Any internal | The recommended split. |
| `POST` | `/quotations/{quotation_id}/fulfillment/accept` | Any internal | Commit the suggested split and reserve the stock it uses. |
| `POST` | `/quotations/{quotation_id}/fulfillment/override` | Any internal | Replace the split with numbers a human chose. |
| `GET` | `/quotations/{quotation_id}/journey` | Any internal | Where this deal stands across quotation-to-cash, and the one next step. |
| `POST` | `/quotations/{quotation_id}/lines` | Any internal | Add a product to the quotation and re-score. |
| `PATCH` | `/quotations/{quotation_id}/lines/{line_id}` | Any internal | Validate one line's discount against its own ceiling. |
| `GET` | `/quotations/{quotation_id}/messages` | Any internal | The negotiation thread, as the rep sees it. |
| `POST` | `/quotations/{quotation_id}/messages` | Any internal | Answer the customer. PS section 3: a rep responds to negotiation requests. |
| `POST` | `/quotations/{quotation_id}/stage` | Any internal | Move a deal between the two pipeline stages nothing else owns. |
| `POST` | `/quotations/{quotation_id}/submit` | Any internal | Score the quotation and route it. |
| `GET` | `/quotations/{quotation_id}/upsell-suggestions` | Any internal | Ranked cross-sell candidates with the margin each would add. |

## Approvals

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/approvals` | Any internal | Everything waiting on this reviewer - not on somebody else. Admins see all. |

## Fulfillment

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/fulfillment/orders` | Any internal | Approved and confirmed quotations still waiting to ship. |
| `POST` | `/fulfillment/restock` | Any internal | Raise stock at a warehouse. |
| `GET` | `/fulfillment/stock` | Any internal | Live stock per warehouse. Available is computed, never stored. |

## Subscriptions

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/subscriptions` | Any internal |  |
| `GET` | `/subscriptions/{subscription_id}/billing-detail` | Any internal | One-time and recurring lines, separately, plus what is coming. |
| `POST` | `/subscriptions/{subscription_id}/cancel` | Any internal | Cancel and credit the unused remainder of the current period. |
| `POST` | `/subscriptions/{subscription_id}/modify` | Any internal | Change quantity mid-cycle, prorated for the remaining days. |

## Invoices

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/invoices` | Any internal |  |
| `GET` | `/invoices/{invoice_id}` | Any internal |  |
| `POST` | `/invoices/{invoice_id}/record-payment` | Finance, Admin | Record a payment and update the status. PS section 9 step 8. |

## Deal Health

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/deal-health` | Any internal | Recompute the board and return it grouped by flag type. |
| `POST` | `/deal-health/{flag_id}/escalate` | Any internal |  |
| `POST` | `/deal-health/{flag_id}/nudge` | Any internal |  |

## Products

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/products` | Any internal |  |
| `POST` | `/products` | Admin | Add a product to the catalogue. |
| `GET` | `/products/{product_id}` | Any internal |  |
| `PUT` | `/products/{product_id}` | Admin | Edit a product from Screen 17. |

## Dashboard

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/dashboard/summary` | Any internal | Counts computed from the data, and the real audit trail as activity. |

## Reports

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/reports` | Any internal | Numbers computed from the data, not stored counters. |

## Admin

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `PUT` | `/admin/approval-rules` | Admin, Manager | Rewrite which roles review which risk level. |
| `DELETE` | `/admin/category-ceilings/{category}` | Admin, Manager |  |
| `GET` | `/admin/customers` | Any internal | Companies a portal account can be attached to, and a quotation raised for. |
| `GET` | `/admin/discount-config` | Any internal | The tables that drive the risk engine. |
| `PUT` | `/admin/discount-config` | Admin, Manager | Change the ceilings. |
| `DELETE` | `/admin/discount-tiers/{name}` | Admin, Manager |  |
| `GET` | `/admin/subscription-plans` | Any internal |  |
| `PUT` | `/admin/subscription-plans` | Admin |  |
| `DELETE` | `/admin/subscription-plans/{plan_id}` | Admin |  |
| `GET` | `/admin/upsell-rule` | Any internal |  |
| `PUT` | `/admin/upsell-rule` | Admin | Raise the floor and thin-margin products stop being suggested. |
| `POST` | `/admin/users` | Admin | Create an account with a chosen role. |
| `GET` | `/admin/warehouses` | Any internal |  |
| `PUT` | `/admin/warehouses` | Admin | Warehouses and their shipping weighting, which the split objective uses. |
| `DELETE` | `/admin/warehouses/{warehouse_id}` | Admin |  |

## Customer Portal

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/portal/billing` | Customer | Invoices, credit notes and anything that bills again. |
| `GET` | `/portal/orders` | Customer | Agreed deals and where each one is shipping from. |
| `GET` | `/portal/profile` | Customer | The company, its pricing tier, and a count of what is open. |
| `GET` | `/portal/quotations` | Customer | The caller's own quotations. Scoped by customer_id, never by a filter. |
| `GET` | `/portal/quotations/{quotation_id}` | Customer | The customer's own quotation, with the negotiation thread. |
| `POST` | `/portal/quotations/{quotation_id}/confirm` | Customer | Confirm the final terms. |
| `POST` | `/portal/quotations/{quotation_id}/negotiate` | Customer | Record a change request and put the quotation under negotiation. |

## Service

| Method | Path | Who | What it does |
| --- | --- | --- | --- |
| `GET` | `/health` | Public |  |
