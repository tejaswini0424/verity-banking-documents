# Deployment

## Vercel deployment preparation

`vercel.json` builds the React frontend and routes `/api`, `/docs`, and `/openapi.json` to the Python ASGI entrypoint. A persistent PostgreSQL DATABASE_URL is mandatory on Vercel; ephemeral SQLite is deliberately rejected. The provided provisioning script uses the already signed-in Vercel account, creates a new project and a free Neon resource through an existing integration, and connects sensitive database environment variables without logging them. **Provisioning requires the user's explicit approval and has not run.** Automatic approval review blocked it pending that approval.

Cloud private files are stored as binary records in the same PostgreSQL database and restored into `/tmp` only as an authorized cache. This keeps the small research deployment independent of another storage product. It is not intended for high-volume document storage. Processing finishes inside the function invocation; the deployed limits are 4 MB uploads and 10 generated documents per request. Text PDFs and synthetic documents work without a native Tesseract executable. Scanned OCR and local Ollama remain dependent on an available compatible service/runtime.

After approved provisioning, deployment uploads only the frontend sources, API entrypoint, backend sources, and runtime/configuration manifests. Local accounts, uploaded documents, environment files, tests, and private storage are excluded. The deployment is not complete until the returned Vercel deployment is READY and its live authentication/document workflows have been checked.

## Docker deployment

Docker Compose is prepared for a local research demonstration, with Nginx frontend, FastAPI backend, PostgreSQL, and persistent named volumes. Copy .env.example, choose a nonempty URL-safe database password, then `docker compose up --build`. Open http://localhost:8080. Database and backend ports are not publicly published. Frontend binds to loopback.

Docker and PostgreSQL execution are not verified on this machine. The current process-local jobs require a single backend replica; no Redis/Celery service is claimed. Dependencies have compatible ranges, but a production Python lockfile and image digest pinning remain future work.

Optional Ollama normally runs on the host. Set the Docker endpoint to `http://host.docker.internal:11434` only when that address is supported and the authorized service is accessible. A local `.env` value overrides the Compose default. No model is downloaded by Compose.

Before deployment with real documents: validate legal basis and retention, establish encryption and backup/access controls, provide TLS and COOKIE_SECURE=true, disable public registration where appropriate, implement role separation, durable workers, normalized migrations, input-resource isolation, logging/monitoring, deletion workflows, comprehensive security testing, and independent model validation. These are remaining engineering requirements, not completed capabilities.
