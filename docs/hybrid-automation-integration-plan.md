# MHA hybrid automation stack — implementation contract (2026-11-23)

Status: **integration blueprint / NOT deployed**. This is the first, reviewable installment for the existing Content OS. ChatGPT plugin installations provide interactive capabilities inside ChatGPT, not service credentials or persistent API-to-API integration for the deployed FastAPI service.

## Objective

Build a **human-approved** evidence-to-publication production line for Metabolic Health Academy (MHA) and its Metabolic Health News (MHN) outlet. Keep the existing deterministic Content OS orchestration and append-only audit history as the source of truth; do not fork a competing automation product.

## Modules and responsibilities

| Stage | Primary capability | Input | Output | Approval / safety |
| --- | --- | --- | --- | --- |
| 1. Topic intake | User / scheduled editorial queue | Topic, channel, audience, references | Workflow ID and assignment | No protected health information |
| 2. Discovery | Firecrawl search/scrape; curated guideline and PubMed source retrieval | Research question | URL, title, publication and retrieval dates, text, provenance | Reject unsupported/low-quality sources |
| 3. Evidence synthesis | Existing research/evidence agents; optional reviewed LLM adapter | Versioned evidence records | Claims, supporting/contradictory evidence, limitations | Explicit citation-to-claim mapping |
| 4. Draft | Content strategy agent | Approved claims, audience, brand profile | Long script, short script, newsletter and captions | Plain-language and clinical review |
| 5. Safety | Existing deterministic gate and human medical reviewer | Complete content package | Pass/fail findings and reviewer decision | Fail closed; no medical/medication advice or unreviewed claims |
| 6. Production | Canva design templates, approved presenter/voice assets and editing workflow | Approved content and visual brief | Design IDs, image/video asset references | Label Dustin Beck as an AI educational presenter, not a physician |
| 7. Delivery | TinyFish only for explicitly approved browser operations; official platform APIs preferred | Frozen approved release manifest | Draft/upload/post receipt, timestamps, URLs | Separate publish approval; idempotency and preflight checks |
| 8. Measurement | PostHog for MHA-owned site/app events, platform-native analytics for social metrics | Consented analytics events and platform exports | Dashboard and editorial feedback | No PHI; privacy and tracking review |

## Non-negotiable release gates

1. Never include patient-identifiable information, private patient data, or clinical records.
2. Every medical claim needs a stable supporting source, access date, version where relevant, and a limitation/uncertainty field.
3. A machine-generated draft must not be marked medically approved by an AI.
4. A human medical reviewer must approve the exact content revision *before* production; substantive production edits invalidate approval.
5. A human publisher must separately approve exact destination, copy, visual, time and account *before* an external publish or submit action.
6. Missing approval, citation, expiry status or destination means **BLOCK**. No automatic retry of a publish action after an ambiguous response.
7. Never use the user's personal physician credentials or employer branding as implied endorsements. Presenter: **Dustin Beck — AI educational presenter (not a physician)**.
8. Preserve content SHA-256, evidence hashes, reviewer ID/time, provider receipt IDs, per-channel release status and append-only audit events.
9. Keep API keys/credentials in deployment secret storage; no tokens in prompts, log events, GitHub commits or examples.
10. Install/enable only minimum app permissions. Respect website terms, consent and platform publication policies.

## Minimum data contract for an integration adapter

A provider-independent `ExternalJob` envelope should include:

```json
{
  "workflow_id": "uuid",
  "content_revision_sha256": "sha256-hex",
  "provider": "firecrawl|canva|tinyfish|posthog",
  "operation": "provider-defined",
  "idempotency_key": "stable-opaque-identifier",
  "status": "queued|running|succeeded|failed|needs_review",
  "source_refs": [],
  "artifact_refs": [],
  "attempt": 0,
  "approved_by": null,
  "approved_at": null,
  "provider_receipt_id": null,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

Track operational provenance in the existing audit system. Never place raw credentials, unpublished patient data, or unlicensed copyrighted media in jobs.

## Practical roll-out order

- **Phase A / current:** Record integration contract, approval policy and required mappings. Verify which Canva account, PostHog project, publisher destinations and service-level credentials are intended. Plugin installation itself is complete; service integration is not.
- **Phase B / research pilot:** Build a Firecrawl adapter behind an interface with fixtures, retries, domain allowlisting, source provenance, timeout handling, and offline tests. Test on publicly available MASLD guideline material; compare to authoritative guideline originals.
- **Phase C / Canva pilot:** Reuse the MHA brand kit and existing templates; generate a **draft** 60-second MASLD Short graphic package and save references, without publishing.
- **Phase D / measurement pilot:** Confirm PostHog project and website consent/analytics plan; instrument owned website conversion events and dashboard. Do not assume PostHog can directly report YouTube/Instagram/TikTok metrics.
- **Phase E / publisher pilot:** Connect official platform APIs where approved. For TinyFish browser publishing, require named account, explicit approval, pre-submission preview and captured receipt; disable unattended posting in V1.
- **Phase F / operations:** Scheduled research intake, health checks, failure notifications, cost controls, content-staleness review and post-release monitoring.

## Acceptance criteria before production activation

- Unit and integration tests cover source errors, duplicate jobs, approval invalidation and ambiguous publish outcomes.
- Human sign-off is tested as a separate service identity/role, not merely a prompt convention.
- Publishing is opt-in and disabled by default; test runs cannot publish.
- Persistent audit records link source > claim > script > assets > approval > release.
- Every external connector has secret handling, permissions, rate limits, cost budgets and a kill switch.
- The existing Ruff and pytest gates pass and a peer-reviewed PR is merged.

## Known constraints

- ChatGPT plugins are enabled in the user's workspace, but this does **not** expose their credentials to this GitHub application.
- Canva accounts and brand kit must be selected before writes, PostHog project must be identified, and TinyFish authenticated browser profile must be explicitly configured if needed.
- No social account authorization, autonomous publishing or PostHog event instrumentation is claimed by this document.
- This document does not introduce executable adapters or override the existing safety engine.
