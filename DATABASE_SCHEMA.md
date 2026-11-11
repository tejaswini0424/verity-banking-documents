# Implemented database schema

This initial baseline uses four physical SQLAlchemy tables:

| Table | Columns |
| --- | --- |
| users | id UUID string PK, email unique indexed, password salt/hash, role |
| sessions | token SHA-256 PK, user_id FK, expires |
| records | id UUID string PK, kind indexed, owner FK indexed, parent indexed, data JSON text, created |

Record kinds: case, document, job, review, dataset, experiment, audit, analysis_run. Relationships between record entities are currently maintained in application code with owner checks. `parent` is an indexed reference, not an enforced database foreign key.

This differs from the approved final normalized schema. A future migration must split case/document/extraction/check/finding/review/dataset/experiment/report entities into typed tables with foreign keys and explicit versioning. No Alembic migration is delivered yet. Startup creates the initial tables and marks interrupted jobs failed.

Raw files, rendered pages, and SQLite data live under configured private STORAGE_DIR. PostgreSQL uses the same SQLAlchemy models through DATABASE_URL. Back up both the database and private files consistently.
