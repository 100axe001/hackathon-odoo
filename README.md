# DealFlow360

A self-governing B2B sales operations platform, built for the Odoo hackathon final round.

**The premise:** a quote sold today should not be able to quietly lose the company money.
The system enforces discount policy itself, reacts to real stock, keeps subscriptions and
one-time sales reconciled on one order, and lets the customer negotiate in-app instead of
over email.

The rule that separates this from a quote-to-invoice form: **the rep never asks for
approval — the engine scores the quotation and routes it, from configuration, not code.**

---

## Run it

```bash
docker compose up -d                                   # Postgres 16 on :5433

cd backend
python -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python reset_db.py                         # drop, create, seed
./.venv/bin/uvicorn main:app --port 8000               # API + /docs

cd ../frontend
npm install && npm run dev
```

The API self-documents at <http://localhost:8000/docs> — 63 endpoints grouped by domain
with full request and response models.

### Sign in

Every account uses the password `dealflow123`.

| Email | Role | What they can do |
| --- | --- | --- |
| `rep@dealflow360.com` | Sales Rep | Build quotations, discount, upsell, submit, fulfil, answer the customer. Sees only their own deals. |
| `manager@dealflow360.com` | Sales Manager | First approval step, Deal Health, configure ceilings and the approval chain |
| `finance@dealflow360.com` | Finance | Second approval step, record payments, reconcile billing |
| `admin@dealflow360.com` | Admin | Products, warehouses, plans, tiers, accounts, reporting |
| `customer@acmecorp.com` | Customer | Portal only: view, counter, confirm, track orders and billing |

`rep2@` and `rep3@` exist so the reporting filters and the discount-anomaly baseline have
more than one distribution to compare.

### Other scripts

| Script | Does |
| --- | --- |
| `backend/reset_db.py` | Drop, recreate, reseed. The normal path — safe to run any time. |
| `backend/seed_large.py` | 793-row stress dataset: 40 companies, 60 products, 80 quotations |
| `backend/wipe_data.py` | Empties every table. Requires `--yes`; otherwise reports only. |

---

## What it does

| Capability | Where the logic lives |
| --- | --- |
| Multi-tier discount governance, automated routing | `app/utils/blended.py`, `app/utils/approval.py` |
| Live upsell with real margin impact | `app/utils/upsell.py`, `app/utils/margin.py` |
| Multi-warehouse split and backorders | `app/utils/fulfillment.py` |
| Hybrid one-time + recurring billing, proration | `app/utils/billing.py` |
| Deal health: stalled, anomaly, slippage | `app/utils/deal_health.py`, `app/utils/anomaly.py` |
| Customer portal negotiation and re-approval | `app/routes/portal.py` |

---

## How it is put together

Five backend layers, and the boundary is enforced rather than suggested:

```
app/routes/      HTTP only. No route touches a database session.
app/database/    Data access. Every function prefixed db_*
app/utils/       Domain logic. Prefixed <domain>_util_*. No FastAPI imports.
app/schemas/     Pydantic request and response models
app/models/      SQLAlchemy tables
```

The frontend mirrors it: every URL lives in `src/api/apiEndpoints.js`, every call goes
through one client in `src/api/client.js`, and each function in `src/api/api-functions/`
carries an `// Expected:` comment that is the contract with the backend's response model.

**The screens display what the backend computed. They do not compute.** No discount
ceiling, risk level, approval chain or margin is worked out in the browser.

---

## Read next

| Document | For |
| --- | --- |
| [`docs/architecture/data-model.md`](docs/architecture/data-model.md) | The tables and how they relate |
| [`docs/architecture/api-contract.md`](docs/architecture/api-contract.md) | Every endpoint, and who may call it |
| [`docs/engineering/risk-engine-and-ml.md`](docs/engineering/risk-engine-and-ml.md) | How discount governance decides, and why ML does not |
| [`docs/engineering/warehouse-split.md`](docs/engineering/warehouse-split.md) | The allocation algorithm |
| [`docs/engineering/billing-proration.md`](docs/engineering/billing-proration.md) | Mid-cycle changes and credit notes |
| [`docs/deliverables/`](docs/deliverables/) | Architecture diagram and what we would build next |

---

## Checks

Run the ones for what you touched.

| Task | Command |
| --- | --- |
| Backend tests | `(cd backend && ./.venv/bin/python -m pytest)` |
| Python lint + format | `pre-commit run --all-files` |
| Frontend lint | `(cd frontend && npm run lint:check)` |
| Frontend format | `(cd frontend && npm run format:check)` |
| Frontend build | `(cd frontend && npm run build)` |

Format Python with **black**. Ruff is configured as a linter only here — `ruff --fix` is
fine, `ruff format` is not.

---

## Decisions worth not re-litigating

| Decision | Why |
| --- | --- |
| Postgres, not SQLite | `Numeric` for money. Float rounding on a discount is a real bug, not a theoretical one. |
| No migrations | `reset_db.py` drops, recreates and reseeds in seconds, and the demo depends on that being safe. |
| Two-path risk score | A single average dilutes one badly-over line to nothing. See `risk-engine-and-ml.md`. |
| ML advises, never decides | The z-score flags a deal for a human. Approval routing is deterministic. |
| Stall-prediction model cut | Tested, and it did not beat a simple rule. Evidence in `research/`. |

---

## Outstanding

There are no `TODO` markers in the source — `no-warning-comments` is an error and lint
runs with `--max-warnings 0`, so incomplete work is recorded here instead.

- [ ] Quotation numbers are read-then-increment with no lock, so two simultaneous creates
      could collide. Fine for a single-operator demo.
- [ ] Export PDF goes through the browser print dialog rather than rendering server-side;
      Export XLS is a CSV, which Excel opens natively.
- [ ] Multi-currency is a bonus in the brief and is not implemented: price lists carry a
      currency column but every seeded row is USD.
