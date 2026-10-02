# Global Travel Optimizer

Travel planning prototype with a Next.js frontend and a separate FastAPI backend. GitHub Pages publishes the frontend as a static site. The built-in catalogue contains dated observations from public seller pages; these are historical component prices, not live quotes or complete trip prices. Demo and sandbox prices remain separate from real-price comparisons.

## GitHub Pages

The workflow at `.github/workflows/pages.yml` builds `frontend/out` and publishes it on each push to `main`. In the repository's **Settings → Pages**, select **GitHub Actions** as the build and deployment source. The workflow derives the project subpath from the repository name, including support for a `<username>.github.io` repository at the domain root.

Pages cannot run Python or Next.js API endpoints. With no backend URL configured, the site displays its bundled public-price archive and demo scenarios; source checks and API tests are disabled with an explanation. No new prices are fetched in this mode.

To enable the server features, host `backend.api.main:app` separately over HTTPS and set the repository Actions variable `NEXT_PUBLIC_API_URL` to its public origin, for example `https://api.example.com`. Set `FRONTEND_ORIGINS` in the backend to the Pages origin, for example `https://username.github.io`. The frontend variable is public and must never contain API keys. Provider credentials belong only in the backend environment, never in GitHub Pages or repository files.

## Local development

From `frontend`, run `pnpm install --frozen-lockfile` and `pnpm dev`. From the repository root, install `backend/requirements.txt` into a Python virtual environment, then run `python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000`. The frontend defaults to the local API at port 8000 outside the GitHub Pages build.

To test the Pages build locally, set `GITHUB_PAGES=true` and `GITHUB_REPOSITORY=username/repository`, then run `pnpm build` in `frontend`. The static output is `frontend/out`.

## Quality checks

The release workflow runs `pnpm lint`, `pnpm typecheck`, `pnpm test`, a Pages production build, and `pnpm test:e2e` (Chromium). The browser tests serve the exported build under `/trip-optimizer/` and cover reload, source filters, country selection, in-flight search changes, split-family controls, details, and mobile widths. Install the official Playwright browser once with `pnpm exec playwright install chromium`. Run backend tests with `python -m unittest discover -s tests`. Findings and provider-access limits are recorded in [`docs/qa_report.md`](docs/qa_report.md).
