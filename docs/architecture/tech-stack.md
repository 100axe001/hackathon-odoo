# Tech Stack

**Decided:** 2026-09-05 · **Status:** locked

Quick reference. The schema is in [`data-model.md`](data-model.md) and every endpoint
in [`api-contract.md`](api-contract.md).


| Field | Choice | Note |
|---|---|---|
| **Frontend** | React + plain JavaScript (Vite) | 19 HTML mockups exist at `~/Desktop/backup` — convert to JSX. No TypeScript. |
| **Routing** | `react-router-dom` | SPA. The customer portal must be a separate route group, not a hidden sidebar. |
| **Styling** | Tailwind CSS + Material 3 tokens | Move off the play CDN to a real build. Delete `carbon/DESIGN.md`. |
| **Backend** | Python 3.12 + FastAPI + Uvicorn | ~47 endpoints. Free OpenAPI page at `/docs`. |
| **Validation** | Pydantic v2 | Runtime validation — matters because the client is untyped JS. |
| **Database** | PostgreSQL 16 (Docker Compose) | Exact `NUMERIC(12,2)` money. Never float. |
| **ORM** | SQLAlchemy 2.0 | DB swap is a connection-string change. |
| **Migrations** | **None** — `create_all()` + `seed.py` + `reset_db.py` | Alembic is overhead in 24h. The demo needs deterministic reset anyway. |
| **Auth** | bcrypt + PyJWT, httpOnly cookie | `passlib` is broken against bcrypt 4.x — skip it. |
| **Authorization** | Row scoping + action gating, server-side | A rep may never approve their own quotation. |
| **Frontend ↔ Backend** | Vite `server.proxy`, `/api` → `:8000` | **No CORS middleware** — adding it breaks the auth cookie. |
| **ML** | `numpy` only (z-score anomaly) | scikit-learn dropped: the stall model was tested and cut. |
| **PDF / XLSX** | `reportlab` / `openpyxl` | Not WeasyPrint — cairo/pango system deps are an install trap. |
| **Dates** | `python-dateutil` | `relativedelta` for billing cycles and month-ends. |
| **Testing** | `pytest` | The six blended-risk scenarios. |
| **Environment** | pyenv 3.12.0 + project-local `.venv` | Nothing installed to system Python. |
| **Deployment** | localhost only | Do not deploy at hour 23. |

## Ports

| Service | Port |
|---|---|
| Vite dev server | `5173` |
| FastAPI | `8000` |
| PostgreSQL | `5432` |

## Explicitly excluded, and why

| Not using | Why |
|---|---|
| Next.js | The frontend is a plain React SPA. |
| TypeScript | Team's speed call. Pydantic covers the API boundary instead. |
| Alembic | Migrations go unused in a 24-hour build. |
| Celery / Redis | Nothing here is genuinely asynchronous. |
| scikit-learn / joblib | Stall model measured as *worse* than a threshold rule at our seed size. |
| WeasyPrint | System library install trap on Linux. |
| CORS middleware | The proxy makes it unnecessary, and it breaks cookie auth. |

---
