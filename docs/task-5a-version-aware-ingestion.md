# Task 5A: version-aware authoritative-source ingestion

## Smallest testable slice

Prove that the Content OS can accept immutable, repository-controlled versions of one
authoritative NIDDK source and deterministically retrieve the version that was current on a
requested date.

This slice adds validated evidence contracts and an in-memory catalog. It intentionally does not
add live downloads, PDF parsing, embeddings, a vector database, external AI calls, arbitrary
uploads, patient text, clinical decision support, or publishing.

## Invariants

- Only exact publisher/domain pairs in `AUTHORIZED_SOURCES` may be ingested.
- Every document version carries canonical URL, publication/effective/retrieval dates, immutable
  version ID, optional superseded version ID, and a SHA-256 content digest.
- The digest must match the stored text before ingestion succeeds.
- Duplicate versions are rejected; no update or delete API exists.
- Retrieval takes an explicit `as_of` date and returns citation/version provenance with every hit.
- The existing five agents, stage ordering, safety revision loop, and final human approval gate are
  unchanged.
- No PHI is permitted. The catalog exposes no patient-input or arbitrary-upload boundary.

## Acceptance tests

1. Two versions of the same NIDDK source select the older or newer version according to `as_of`.
2. A non-allowlisted host is rejected.
3. Modified text with a stale digest is rejected.
4. Duplicate immutable versions are rejected and ingestion audit receipts are append-only.
5. The catalog exposes no patient-text, live-fetch, delete, or publish operation.

## Next slice after approval

Task 5B should persist documents and ingestion events with an Alembic migration, add a reviewed
source-manifest loader, and inject the retriever into `ResearchAgent`. Retrieved evidence must
remain an input artifact in the same five-agent workflow; it must not skip evidence review,
safety review, or human approval.
