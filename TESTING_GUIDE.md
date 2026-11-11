# Testing

Run from repository root:

```powershell
python -m pytest tests -q --basetemp=storage/pytest-local
npm test --prefix frontend
npm run build --prefix frontend
```

Backend tests cover the five clean document classes, incorrect arithmetic, missing fields, upload signatures/types, source-page evidence, jobs/SSE, review prerequisites, actual evaluation/export, authentication/logout/origin validation, account isolation, and invalid-generation side effects. Optional adapter tests use isolated HTTP mocks to verify schema/image payloads, evidence matching, out-of-range-page rejection, and missing configuration. They do not prove live model quality.

Frontend tests verify the 32-entry unique route catalog and metadata. The production build performs strict TypeScript checks. An automated Playwright E2E suite is not yet supplied. Browser workflow checks and any environment limitations are recorded in docs/VERIFICATION.md.

Tests create their own database in a temporary directory. A workspace-local pytest base directory avoids Windows temporary-folder access conflicts. Do not point test configuration at production storage.
