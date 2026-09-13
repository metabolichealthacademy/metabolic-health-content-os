# Task 6A: deterministic safety and editorial review MVP

## Smallest testable slice

Apply a versioned, deterministic ruleset to the existing content and evidence artifacts. Blocking
medical-safety or evidence findings return the workflow to content revision. Editorial warnings
remain visible in the persisted safety artifact and may proceed only to the existing production
package and mandatory human-review gate.

## Ruleset

The ruleset identifier is `task-6a-v1`. Each finding records its category, severity, stable code,
message, optional minimal matched text, and ruleset version.

Blocking rules:

- `no_supported_claims`
- `missing_citations`
- `unsupported_source_reference`
- `missing_disclaimer`
- `personalized_medical_instruction`
- `medication_dose_instruction`

Warning rules:

- `absolute_medical_claim`
- `cure_or_guarantee_language`
- `editorial_clarity`

Rules identify content that requires revision or human scrutiny. They do not diagnose a patient,
recommend treatment, or establish scientific validity.

## Preserved boundaries

- The five-agent order and current orchestrator transitions are unchanged.
- Any blocking finding uses the existing content revision loop and increments its revision count.
- Warning-only reviews may reach production, but production remains `publish_ready=False`.
- Explicit human approval remains mandatory for completion.
- Structured review artifacts and workflow transitions use the existing SQL persistence,
  optimistic locking, and append-only audit history.
- Citation checks use the supplied evidence artifact. The safety stage does not retrieve evidence,
  replace a cited version, or bypass upstream evidence handling.
- Task 5B immutable evidence versions, hashes, receipts, and historical retrieval are unchanged.
- There is no PHI intake, patient interface, live retrieval, external model call, medication
  recommendation, authentication, publishing integration, or new database table.

## Acceptance tests

1. A supported educational draft passes the deterministic safety gate.
2. Missing or unsupported evidence linkage and missing disclaimers block.
3. Personalized diagnosis/treatment and medication dose-change instructions block.
4. Absolute, cure, guarantee, and long-sentence clarity findings warn without bypassing review.
5. Finding order and ruleset identifiers are deterministic.
6. Blocking content returns to content revision; warning-only content reaches human review.
7. Production remains non-publishable and completion still requires explicit human approval.
8. Structured safety findings survive SQL persistence with audit history intact.
9. Existing Task 5A/5B, workflow, API, migration, Ruff, and coverage checks pass.

## Deferred

Comprehensive clinical policy logic, drug interactions, emergency triage, pregnancy rules,
LLM-assisted review, scientific-validity grading, retriever injection, authentication, and
publishing remain separate reviewed tasks.
