# Verification record · 10 November 2026

## Automated checks

- Backend: 17 pytest tests passed. This includes live Tesseract OCR of a rendered synthetic salary-slip scan, five clean document types, altered-document checks, authentication, owner isolation, uploads, evidence pages, jobs/SSE, reviews, reports, and isolated multimodal adapter contract tests.
- Frontend: 2 Vitest catalog tests passed; exactly 32 unique route entries with required metadata.
- Production build: TypeScript and Vite passed. Charts split into a separate chunk.
- One upstream Starlette/AnyIO deprecation warning remains; it did not fail the suite.

## Interactive browser checks

- Registered a fictional local test account.
- Generated six fictional salary documents with seed 42 and mixed scenario labels.
- Observed all six background jobs complete.
- Ran evaluation and observed TP=4, FP=0, TN=2, FN=0. These values test synthetic-template behavior only.
- Opened all 32 sidebar routes and checked that each page heading matched its navigation entry.
- Searched for synthetic-2.pdf and opened its source pages and exact extracted evidence.
- Reloaded a direct document-library URL and observed persistent records and the signed-in session.
- Inspected the dashboard at a 390 × 844 mobile viewport, opened the navigation drawer, and reset viewport sizing.
- Inspected light and dark themes; restored light mode.
- Saved docs/dashboard-preview.png from the final dashboard. The browser preview remains on http://127.0.0.1:5178/dashboard.

## Not verified / not delivered

No live multimodal model was installed or invoked. HTTP model tests use isolated mocks. Docker is not installed in this environment, so Compose and PostgreSQL were not run. No issuer verification, visual forgery model, held-out real-document study, normalized migrations, team administration, durable distributed queue, or automated browser regression suite is claimed.

Initial sandbox attempts could not reach loopback services and Windows denied the default pytest temporary folder. Verification used local service processes with network permission and fresh workspace-owned pytest base directories. No firewall or system security settings were changed.
