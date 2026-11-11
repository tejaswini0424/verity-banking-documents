# Verity · Banking Document Intelligence

**Project title:** A Multimodal Large Language Model Framework for Automated Banking Document Verification and Fraud Detection.

A runnable research baseline with a React/TypeScript interface, 32 navigable catalog routes, FastAPI, persistent account-private workspaces, synthetic banking PDFs, source evidence, deterministic verification, human review, and reproducible baseline evaluation.

## Current implementation

- Registration, login, logout, scrypt password hashes, revocable eight-hour HttpOnly session cookies, owner-level resource isolation, origin validation, and authentication throttling.
- Cases; PDF/PNG/JPEG upload validation; private UUID-based file storage; text-PDF extraction and page rendering; Tesseract integration when the executable is installed.
- Five synthetic document classes: salary slip, bank statement, identity, address proof, loan application.
- Label-based field extraction with exact text and page references. Financial arithmetic, required fields, expiry, applicant-name consistency, required-document checks, and exact duplicates.
- Transparent findings, a human review queue, reasoned review outcomes, job stages, retry, SSE status endpoint, dashboard activity derived from persisted records.
- Seeded synthetic clean/altered PDFs with separate ground-truth manifests; baseline precision/recall/F1 and confusion counts; JSON/CSV exports.
- Optional Ollama vision-language extraction and hybrid fallback fields, schema validation, model/prompt version recording, and unverified-evidence flags. Disabled unless configured. Live model inference has **not** been verified on this machine.
- Responsive sidebar, direct URL navigation, search across pages/cases/documents/datasets/experiments, light/dark themes, errors and empty states.

This is an **initial runnable baseline**, not the completed research framework or a production banking system. The UI explicitly labels unimplemented capabilities.

## Run locally

Python 3.12+ and Node.js 22+ are recommended. The baseline was tested on Python 3.14 and Node.js 26 in this workspace.

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 48123
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev -- --port 5178 --strictPort
```

Open **http://127.0.0.1:5178**. Backend documentation: **http://127.0.0.1:48123/docs**. Register your own account; there is no default user or password.

SQLite and private files are created under `storage/`. Keep that directory out of source control. Environment variables are read from the process environment; the local command does not automatically load `.env`. See INSTALLATION_GUIDE.md for configuration.

## Demonstrate the workflow

1. Register an account.
2. Open **Fraud scenario simulator**, choose salary slips, mixed scenario, six documents, seed 42.
3. Open **Processing monitor** and wait for completion.
4. Inspect **Document viewer**, **Field extraction**, and **Financial consistency**.
5. Open **Cross-document verification** and run case checks.
6. Record a reasoned outcome in **Review workspace**.
7. Open **Performance evaluation** and evaluate the generated dataset.
8. Download the actual case/experiment report from **Reports**.

Generated documents are marked fictional. A clean synthetic example passing its checks is not issuer verification. The engine always routes automated results to human review.

## Optional multimodal inference

Install Ollama separately and obtain a vision-capable model suited to your hardware. Set `OLLAMA_MODEL` to its installed model identifier and `OLLAMA_URL` to your authorized local service URL **before** starting the backend. No weights are bundled or automatically downloaded. Then select multimodal or hybrid processing on a document inspection page.

The adapter sends base64 page images to `/api/chat`, requests schema-constrained JSON, validates its output and page references, and records `prompt_version`. Quotes matching extracted text are `text_verified`; other quotes remain `model_reported_unverified` and create review findings. This is evidence validation, not a guarantee of correct extraction.

API contract references: [Ollama vision](https://docs.ollama.com/capabilities/vision), [structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [chat API](https://docs.ollama.com/api/chat).

## Verification

```powershell
python -m pytest tests -q --basetemp=storage/pytest-local
npm test --prefix frontend
npm run build --prefix frontend
```

Use a fresh `--basetemp` directory if Windows has retained a previous directory under a different account. Tests use a separate temporary database; production workspace data is not used. Multimodal HTTP responses are mocked only in isolated adapter tests, never in application functionality.

Latest local verification (11 November 2026): 19 backend tests and 2 frontend tests passed, and the production build succeeded. The backend suite covers synthetic document generation, processing, evaluation, human review, and report export. It emitted one upstream Starlette/AnyIO deprecation warning.

## Docker

Vercel configuration is also prepared; see DEPLOYMENT_GUIDE.md. Cloud provisioning and live deployment are pending explicit approval to create a new free Neon database. No cloud deployment has been claimed as complete.

Copy `.env.example` to `.env`, set a nonempty URL-safe `POSTGRES_PASSWORD`, and run:

```powershell
docker compose up --build
```

Open http://localhost:8080. Compose uses PostgreSQL and persistent named volumes. Docker execution has not been verified in this environment. Do not expose this research baseline to the Internet without the production work listed below.

## Remaining approved scope

Visual tampering localization, bounding-box overlays, near-duplicate matching, editable field correction, shared reviewer roles, normalized domain tables and Alembic migrations, a durable worker queue, cancellation, PDF reports, held-out applicant/template splits, real annotated datasets, image perturbation robustness experiments, calibration, model-comparison runs on consistent held-out sets, and comprehensive automated browser tests remain unfinished.

The local background worker uses FastAPI BackgroundTasks. Restarted running jobs become failed and can be retried; no distributed execution or automatic job recovery is claimed. SQLite is verified; PostgreSQL is configured but not integration-tested. Session cookies replace the originally proposed JWT design to support immediate logout revocation; only the analyst role is implemented.

The workspace endpoint currently returns the newest 500 records per collection. Large-scale pagination and aggregate endpoints are future work. Processing is designed for small research datasets, not untrusted high-volume workloads. Exact library resolutions for the frontend are in package-lock.json; backend compatible ranges are in requirements.txt.

See the architecture, API, evaluation, deployment, and testing guides for details.
