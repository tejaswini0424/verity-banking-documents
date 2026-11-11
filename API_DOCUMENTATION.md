# Implemented API

Base path: `/api/v1`. Interactive OpenAPI documentation: `/docs` on the backend. All resources except registration/login and health require an eight-hour revocable HttpOnly cookie session. Unknown or other-owner records return 404.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | /auth/register | Create private analyst account; email/password |
| POST | /auth/login | Authenticate |
| GET | /auth/me | Current account |
| POST | /logout | Revoke session |
| GET | /health | Current capability configuration |
| GET | /workspace | Latest 500 owner records per collection |
| POST | /cases | Create case; name/reference |
| POST | /cases/{id}/documents | Multipart file upload, queues baseline processing |
| GET | /documents/{id} | Latest extracted data and findings |
| GET | /documents/{id}/file | Authenticated source download; optional page query |
| POST | /documents/{id}/process | Queue/retry; mode=ocr_rules, multimodal, hybrid |
| GET | /jobs/{id}/events | SSE actual job status/stage |
| POST | /cases/{id}/verify | Run cross-document and attachment checks |
| POST | /cases/{id}/reviews | Human outcome plus reason |
| POST | /datasets/generate | count, seed, scenario, document_type |
| POST | /experiments | dataset_id and name; evaluate latest completed results |
| GET | /reports/{id} | Actual case/dataset/experiment export; format=json or csv |

Uploads: PDF, PNG, JPEG; extension and magic bytes; 15 MB; PDFs up to 30 pages. Multimodal mode limits images to 8 pages. Passwords: 10–128 characters. Authentication attempts are limited per client IP in process memory. Origin checks reject browser mutations from origins outside ALLOWED_ORIGINS. A configured but unreachable Ollama endpoint causes an explicit failed job, not a synthetic fallback response.
