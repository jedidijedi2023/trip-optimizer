# Trip Optimizer — QA report (2026-10-02)

## Architecture and scope

- Frontend: Next.js 16 App Router, React 19, TypeScript. The user interface is a client component with React state and browser `localStorage`; the API URL is compiled from `NEXT_PUBLIC_API_URL`.
- Build: pnpm lockfile; `next build` with `GITHUB_PAGES=true` exports static HTML under the `/<repository>/` base path. There is no Vite or React Router. Navigation among Search, Saved and Sources is in-page state; there are no internal routes to deep-link to.
- Backend: FastAPI on Render. The main `/api/search` uses Travelpayouts/Aviasales cached flight data when a private server token exists, Travelgate HOTELTEST official demo, and RateHawk sandbox only when configured. Tourvisor and Travelata have no main-search credentials. `/api/validation/search` isolates demo/sandbox/mock adapters. The dated public-price catalogue is separate from trip totals.
- Storage: browser `localStorage`; backend optional PostgreSQL/Redis. No booking/payment endpoint.
- GitHub Actions: `.github/workflows/pages.yml` runs typecheck, static build and Pages deployment. `.nojekyll` preserves Next asset paths. The backend is deployed independently from the root TRIP repository.
- Tests: Python `unittest`, Node test runner for frontend logic, Playwright Chromium smoke tests against the static export.

## Findings

| ID | Severity | Area | Steps to reproduce | Expected | Actual | Root cause | Fix | Regression test | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QA-01 | P1 | Source switches | Turn off all three source groups, press Search | Explain that at least one source is required; do not call API | Empty search was sent | No effective-source validation in UI or API | Validate effective source groups before search; API returns 422 | `search.test.mjs`, Playwright all-off, `test_api.py` | Fixed; Pages and Render verified |
| QA-02 | P1 | Search race | Start a slow search, change destination before response | Old response never replaces new filters | Old response could appear under new country | Fetch had no abort/generation guard | Abort on parameter/mode changes and ignore stale response | Playwright delayed API response | Fixed; Pages verified |
| QA-03 | P2 | Foreign operator switch | Keep foreign operators on, turn positioning off | Direct-start foreign package model remains selectable | All foreign models disappeared | The model tied every foreign package to positioning | Keep direct foreign model; gate only gateway model | `search.test.mjs`, `test_api.py` | Fixed; tests pass |
| QA-04 | P2 | Calendar validation | Enter an impossible date such as `2026-02-30` | Show validation error | Regex accepted it; date iteration could be invalid | Format-only date validation | Round-trip ISO date validation | `search.test.mjs` | Fixed; tests pass |
| QA-05 | P2 | Price provenance | Inspect `savings` on generated MOCK offers | No claimed economic savings | Synthetic baseline subtraction populated `savings` | Mock calculation reused a comparison field | Leave `savings=null` for all mock offers | `search.test.mjs` | Fixed; tests pass |
| QA-06 | P2 | Provider failure | Travelgate times out while retail flight adapter is available | Other source completes and UI shows per-provider failure | Existing provider isolation worked | Separate try/catch per adapter | Added `test_live_search.py` | Verified locally |
| QA-07 | P2 | External script | Load published page and read browser console | No errors | Travelpayouts Drive's `emrldtp.cc` config request is CORS-blocked and logs `config is not valid` | Remote publisher configuration; script was previously supplied for this site | Keep script for account verification; no private token exposed | `audit-production.mjs` | External blocker; no first-party page exceptions |
| QA-08 | P1 | Live operator pricing | Search for family 2+3 | Source-linked complete package price if supplier authorizes API access | Public catalogue has partial prices; Tourvisor/Travelata exact tariffs unavailable | Individual trial/partner credentials absent | UI keeps source-linked observations separate from family totals | API registry and public-price tests | Provider-access blocker |
| QA-09 | P1 | Render Blueprint | Run configured `startCommand` from configured `rootDir` | FastAPI imports and starts | `ModuleNotFoundError: No module named 'backend'` | Blueprint root was `backend`, but imports use `backend.*` from repository root | Use repository root and `backend.api.main:app` | `test_deploy.py` | Fixed; local import and Render health verified |

## Test coverage and release checklist

| Area | Result |
| --- | --- |
| Production home, reload, source-linked tour details and country selection | 11 Chromium smoke tests passed on Pages after deploy |
| GitHub Pages base path and JS/CSS 404s | Static export and Pages tested; no first-party failed responses or requests |
| Search source combinations | Node unit tests; all-off E2E; backend 422 test |
| Visa and Schengen gateway | Python visa tests and Node no-FRA test; rules fail closed when evidence is absent |
| Split family 2+3 | Python itinerary/pricing tests and Node one-outbound/separate-returns test |
| Provider timeout/429/5xx, fallback provenance | Python `test_http.py`, `test_validation_search.py`, `test_live_search.py` |
| Mobile widths 375, 390, 768, 1366, 1920 | Playwright on local and Pages: no horizontal overflow; Search and detail dialog accessible |
| Price arithmetic and synthetic exclusion | Python pricing tests; frontend mock savings test |
| Frontend secret scan | No candidate private secret values in frontend source/export or seven Git revisions of each repository; `.env` files untracked |
| Lint, typecheck, unit/integration, E2E, production build | PASS: 0 lint errors/warnings, 9 frontend unit, 56 backend, 11 local and 11 Pages E2E, build PASS |
| Render and GitHub Pages deployment | Pages workflow run #9 succeeded for `87e705f`; Render `/api/health` 200 and new all-off API validation returned 422 |

The production browser audit saw 1 document, 13 scripts, 2 stylesheets, 3 fonts and 3 fetches; `/api/search` returned 200. There were no first-party 4xx/5xx responses or uncaught page exceptions. The only failed network request and three console errors came from the third-party Travelpayouts Drive `emrldtp.cc/entrypoint_config` request, which the supplier must repair or configure.

The public catalogue is not automatically refreshed and cannot prove bookable tariffs for a 2+3 family. The Travelpayouts Data API supplies cached individual flight prices; it does not grant tour-operator API access. Full foreign package + positioning totals also require confirmed prices for flights, package, baggage, gateway hotel, transfers, visas and fees, so those totals remain unavailable in live mode rather than being invented.
