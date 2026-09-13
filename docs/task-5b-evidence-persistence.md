# Task 5B: persistent evidence provenance

## Smallest testable slice

Persist one validated authoritative evidence document, its immutable versions, SHA-256 hashes,
and append-only ingestion receipts in SQL. Prove that the exact evidence and provenance survive a
new repository instance and retain Task 5A's deterministic `as_of` retrieval behavior.

## Invariants

- Task 5A publisher/domain, date, and SHA-256 validation runs before any database write.
- A logical document has a stable `source_id`; `(source_id, version_id)` identifies an immutable
  version.
- Document identity, version, and receipt are written in one transaction.
- A receipt references the exact source, version, and content digest that was persisted.
- Duplicate immutable versions and missing or cross-source supersession targets are rejected.
- Only ingest and read operations are exposed. There is no update, delete, live-fetch, upload,
  patient-input, model-provider, or publishing boundary.
- The five-agent order, evidence review, safety revision loop, and final human approval gate are
  unchanged. Persisted evidence is not automatically injected into an agent in this slice.
- No PHI is permitted.

## Acceptance tests

1. A successful ingestion atomically creates one document, one version, and one receipt.
2. A fresh repository instance reconstructs the same content, hash, dates, and citation metadata.
3. Invalid hashes and unauthorized publisher/domain pairs leave all three tables empty.
4. Duplicate versions do not overwrite content or append a second success receipt.
5. Supersession must point to an existing version of the same source.
6. Multiple persisted versions preserve Task 5A historical `as_of` selection.
7. Receipt foreign keys restrict deletion of referenced versions, and no mutation API exists.
8. Alembic upgrades through `0002`, reports no model/schema drift, and downgrades to base.
9. The existing full suite and coverage gate pass.

## Deferred to Task 5C

Reviewed source-manifest loading and safe retriever injection into `ResearchAgent`. Retrieved
evidence will remain an input artifact and will not bypass evidence review, safety review, or
human approval.
