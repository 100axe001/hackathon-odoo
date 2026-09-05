# AGENTS.md — frontend

Rules for the React UI. The root `AGENTS.md` still applies.

## Plain JavaScript, deliberately

No TypeScript. This was a 24-hour-build decision: no compile step fighting
AI-generated components against backend shapes. The cost is that **nothing catches a
shape mismatch for you**, so the discipline below replaces the compiler.

## Components never call `fetch` directly

Two steps, always both:

1. Add the URL to the right `<resource>Endpoints` object in `src/api/apiEndpoints.js`.
   Parameterised URLs are functions that encode their arguments.
2. Add a wrapper in `src/api/api-functions/<resource>.js` that goes through `apiGet` /
   `apiSend` from `../client` and falls back to its `MOCK_*` constant.

`src/api/client.js` is the only place `fetch` appears. It unwraps the backend's
`{success, message, data}` envelope so callers work with plain payloads.

## The `// Expected:` comment is the contract

Every api-function carries one, naming the exact response shape:

```js
// Expected: [{id, customer_name, amount, status}]
export async function loadQuotations() {
  try {
    return await apiGet(quotationEndpoints.list);
  } catch {
    return MOCK_QUOTATIONS;
  }
}
```

Keep it accurate and matching `backend/app/schemas/<resource>.py`, which is the source
of truth. Do not guess a shape.

**Why the try/catch matters:** a missing endpoint falls back to mock, so the app never
crashes and integration is incremental — ship one endpoint, one screen goes live. But a
**wrong** shape does not throw; it renders `undefined`. Match field names exactly.

## Mock data mirrors the seed

`src/api/mocks.js` and `backend/seed.py` hold the same records. Screens then look
identical before and after an endpoint goes live, which makes a regression obvious.
Change one, change the other.

## Layout

| What | Where | Naming |
| --- | --- | --- |
| App root | `src/App.jsx` | providers only; the only default export |
| Route table + guards | `src/routes/` | `index.jsx`, `RequireRole.jsx` |
| Shells | `src/components/layout/` | `AppLayout`, `PortalLayout` |
| Session | `src/hooks/useSession.jsx` | `useSession()` |
| Screens | `src/pages/<resource>/` | `PascalCase.jsx`, filename matches the component |
| UI primitives | `src/components/ui/` | `PascalCase.jsx`, one component per file |
| Shell chrome | `src/components/layout/` | `Sidebar`, `PortalNav`, `LogoMark`, … |
| Design tokens, nav | `src/constants/` | `theme.js` (`C`), `nav.js` (`NAV_ITEMS`) |
| API URLs | `src/api/apiEndpoints.js` | grouped `<resource>Endpoints` objects |
| API calls | `src/api/api-functions/<resource>.js` | one function per endpoint |
| Mock fallbacks | `src/api/mocks.js` | `MOCK_<SCREEN>` |
| Request wrapper | `src/api/client.js` | the only `fetch` in the codebase |

Screens with both a list and a detail view live together:
`pages/quotations/QuotationsScreen.jsx` and `QuotationDetailScreen.jsx`.

**Named exports everywhere**, except `App.jsx`. Import primitives by their explicit
path — `import { Card } from "@/components/ui/Card"` — not through a barrel. There is
no `index.js` in `components/ui/`, deliberately: `StatCard` composes `Card`, and a
barrel would make that a cycle.

`@/` resolves to `frontend/src` (`vite.config.js`). Use it instead of deep relative
paths.

## Adding a screen

1. Create `src/pages/<resource>/<Name>Screen.jsx` with a named export.
2. Reuse the primitives in `src/components/ui/` — do not write a second button.
3. Add the route to `src/routes/index.jsx`, under the layout and guard it belongs to.
4. If it needs data, add the endpoint and api-function first (see above) so the
   screen never calls `fetch` itself.

Keep a screen under a few hundred lines. If one grows past that it is usually doing
more than one job — extract a section into `src/components/<Area>/`.

## Routing

`react-router-dom`. Paths mirror the brief's navigation key and
`docs/architecture/api-contract.md`, so a URL reads the same in the browser, in the
docs, and in a judge's test script.

- Navigate with `useNavigate()`; read params with `useParams()`. **Never pass a
  `setRoute` prop** — that was the old hand-rolled switch and it is gone.
- The sidebar uses `NavLink`, so active state comes from the URL. A detail screen keeps
  its section highlighted because `NavLink` matches the path prefix.
- Two shells, deliberately sharing nothing: `AppLayout` (sidebar) for internal roles,
  `PortalLayout` (no sidebar) for customers. The brief §7 requires the portal to be a
  real separate view, not an internal screen relabelled.
- `RequireRole` is the **UI half only**. The server half is what protects data: every
  internal endpoint must reject a customer token, and `/portal/*` must reject an
  internal one. Never rely on the guard alone.

## Linting

`npm run lint:check` must pass with zero warnings before you finish.

`no-undef` is the main safety net in a codebase with no type checker — it catches a
hook used but never imported, which is a bug a green Vite build will happily ship.

## Styling

Tailwind v4 through `@tailwindcss/vite`, so there is no `tailwind.config.js` — theme
tokens live in `src/index.css`. Use the existing `C` colour constants and primitives
rather than new arbitrary values.

## Before you finish

From the repository root:

```bash
(cd frontend && npm run format:check && npm run build)
```
