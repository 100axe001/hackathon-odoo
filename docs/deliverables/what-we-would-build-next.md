# What We Would Build Next

**PS §8 deliverable** · 2026-09-05

What follows is ordered by what we would actually reach for first, and each item
says why it was not done rather than pretending it was out of scope.

## 1. Retire the read-path sample-data fallback

Every read in `frontend/src/api/api-functions/` wraps its call in a `try/catch` and
returns a `MOCK_*` constant from `src/api/mocks.js` when the request fails. That made
integration incremental during the build — ship one endpoint, one screen goes live — and
it keeps the UI alive when the API is down. It is a **demo affordance, not production
behaviour**: a user cannot tell seeded data from real data, and a dashboard that shows
plausible numbers while the backend is unreachable is worse than one that shows nothing.

The replacement is a shared error and empty state driven from `src/api/client.js`, after
which `mocks.js` is deleted. Mechanical work, but it has to land before anyone acts on a
number this app puts on screen. Writes are already correct — they let the failure reach
the screen rather than faking success. The single exception is `patchDiscount`, whose
offline path exists so the quotation builder still renders without a backend and is
documented as such at the call site; it goes at the same time.

## 2. Migrations

Deliberately skipped: `create_all()` plus a seed script, because the demo needs a
deterministic reset and migrations are pure overhead across a 24-hour build. The cost is
that the schema can only move forward by dropping the database, so there is no path that
preserves data. Generate a single `001_initial` from the final schema and start the
Alembic history there.

## 3. Document export

`reportlab` is already a declared dependency and nothing imports it. The Reports screen's
**Export PDF** and **Export XLS** buttons raise a toast and do nothing, and there is no
invoice PDF at all — which is the one that actually matters, because a B2B customer
expects a document they can file, not a screen they have to be logged in to see.

A render endpoint on `/invoices/{id}` returning a stream, plus a link from the invoice
detail, is contained work. It would be the first endpoint that does not return the
`{success, message, data}` envelope; that is a deliberate exception worth stating in
`docs/architecture/api-contract.md` rather than smuggling in.

## 4. Real stall prediction, once there is history to learn from

We built the feature pipeline and then **cut the model**, on evidence rather than
instinct. We evaluated logistic regression, random forest, gradient boosting and two
ensembles against a deterministic threshold rule:

| training rows | rule ROC-AUC | ML ROC-AUC |
|---|---|---|
| **60** | 0.761 | 0.710 |
| **100** | 0.732 | 0.681 |
| 200 | 0.680 | 0.768 |
| 800 | 0.744 | 0.895 |

At the volume we could seed, the model **loses**. It only overtakes the rule around 200
real historical outcomes. So we shipped `days_since_last_activity > N` as configured
business logic — which is what PS §4 B9 actually asks for — and spent the time on the
approval engine.

The strongest single feature was the interaction `days_idle × negotiation_rounds`, at
43% of permutation importance: a deal both gone quiet *and* haggled over repeatedly. A
threshold rule cannot express that, and it is the one genuine argument for a model. With
200+ real outcomes we would retrain and enable it. The notebook is in
`research/stall-model/`.

## 5. Robust anomaly detection

The z-score assumes an approximately normal spread. Real discount data is clustered on
round numbers (0, 5, 10, 15), right-skewed and bounded below at zero, so the nominal 2σ
flag rate is only approximate. A **median/MAD modified z-score** is the production
upgrade, and it is also resistant to the contamination problem: a rep whose history
already contains outliers has those outliers inflating their own baseline.

## 6. Optimal warehouse splitting

Ours is a greedy cover, and the spec says so. Choosing the true minimum set of
warehouses is set cover, which is NP-hard, but at realistic catalogue sizes an ILP
solver would find the optimum in milliseconds. We would also add:

- **Carrier and lead-time weighting**, so "fewest shipments" can lose to "arrives before
  the promised date"
- **Partial-line splitting across more than two warehouses**, which the greedy pass
  handles but has never been stress-tested
- Reserving with an expiry, so an abandoned quotation releases its stock

## 7. Smaller, well-understood additions

**Payment history.** `payments` was merged into `invoices`, which supports one payment
record per invoice. The status still moves correctly through PARTIAL because amounts
accumulate — but the *history* of who paid what and when collapses to the most recent. A
separate `payments` table is a one-table addition.

**Identity.** Auth sits behind a single middleware boundary, so swapping session auth for
an OIDC provider — Authentik or Keycloak — plus SCIM provisioning is a contained change
that never touches approval logic. Magic-link portal access (PS §4 A1 offers it as an
alternative) would follow the same path. `POST /admin/users` already provisions users and
has no screen; that screen comes with this work rather than before it.

**Multi-currency.** PS §7 marks it a bonus. `price_lists` already carries a currency
column and customers carry theirs; what is missing is an FX rate table and a decision
about which rate a quotation freezes at — almost certainly the date of submission, so an
approval chain cannot change price while it is being reviewed.

**Upsell ranking.** Suggestions come from a seeded `product_pairings` table. Genuine
co-occurrence mining needs transaction history that does not exist yet. Once it does, the
same endpoint shape serves a real ranking — the frontend would not change.

---

## What we would not change

Two decisions we would defend rather than revisit:

**The two-path risk engine.** A single blended formula cannot satisfy the brief: PS §10
wants one $450 line 8pt over to flag a $3,030 quotation *and* many slightly-over lines
to be caught together. Value-weighting alone dilutes the first to 1.19pt and routes it
LOW. Scoring the worst line separately and taking `max()` is not a workaround; it is
what the requirement actually says.

**ML never touching approval routing.** Governance has to be deterministic, auditable
and explainable to the person whose deal was blocked. The z-score is advisory and feeds
one screen.
