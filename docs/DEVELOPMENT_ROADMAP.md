# Remaining work toward the approved final architecture

The initial end-to-end OCR/rules baseline is runnable and verified. Architecture approval remains valid; subsequent development does not need another architecture approval unless scope changes materially.

1. Split the frontend workflow dispatcher into dedicated page modules and add component/browser regression tests, focus management, notifications, and richer filtering.
2. Introduce normalized domain entities and Alembic migrations, preserving existing baseline data. Add pagination and true aggregate statistics beyond the current 500-record workspace limit.
3. Replace in-process jobs with durable workers, concurrency controls, cancellation, and recovery.
4. Validate local multimodal inference with a chosen installed vision model. Save immutable run references in experiments; implement a true multimodal-only comparator separately from verification rules.
5. Add field correction history, source bounding boxes, multiple label/layout extraction strategies, and conflicting-field detection.
6. Implement validated visual tampering indicators and near-duplicate candidates with transparent limitations.
7. Add team reviewer assignments and role-based authorization, retention/deletion controls, and production authentication operations.
8. Build held-out applicant/template datasets, robustness perturbations, extraction and detection metrics with uncertainty, reproducible model comparisons, and independent real-document evaluation where authorized.
9. Add PDF reports, charts, report artifact persistence, and research documentation based on actual experiments.
10. Execute Docker/PostgreSQL integration checks, production hardening, and complete the approved acceptance checklist before declaring the full project complete.
