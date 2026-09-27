# Job Search Kit: design and delivery

This is a fresh, public implementation of a personal job-search workflow. No source history, applicant records, transcripts, attachments, account configuration, or source code is migrated.

## Analysis

The transferable value is the sequence: discover, deduplicate, check requirements against sourced facts, prepare approved wording, inspect the actual portal, record an attempt before the send action, and reconcile a receipt afterward. Candidate-specific criteria and private tracker integrations do not belong in the shared product.

## Research and brainstorm

Official provider documentation supports local agent workflows, computer/browser tools and scheduling, with platform and account differences. The public product must describe capability checks rather than promise a universal browser driver. NAV provides a vacancy feed subject to authentication and freshness obligations; this first release uses user-provided vacancies and agent-assisted discovery instead of a feed crawler. See the bilingual research notes for sources.

Options considered:

| Option | Decision |
| --- | --- |
| Sanitized copy of a personal repository | Rejected: personal assumptions, attachments and history remain difficult to audit. |
| Hosted application with accounts | Deferred: unnecessary hosting, credentials and applicant-data handling for the first useful release. |
| Prompt collection only | Rejected: cannot reliably preserve attempt state or detect changed packets. |
| Local toolkit with shared agent procedures | Selected: runnable offline core, private workspace outside the source tree, compatible with either provider. |

## Implementation plan

1. Python standard-library CLI: private initialization, stable vacancy identity, eligibility state, hashed packet records, scoped authorization, preview record, serialized send attempts and receipt reconciliation.
2. English and Norwegian Bokmål onboarding, discovery, writing, submission, interview and review procedures; provider setup and opt-in scheduling prompts.
3. Explicit public-file manifest, privacy checks, archive export and CI using synthetic fixtures only.
4. Three sequential review-and-fix cycles: correctness, security/privacy, release and onboarding. Record actual findings and verification, including limitations.

## Completion criteria

The documented offline demo and safety tests pass; personal data is absent except the authorized attribution; no private history or runtime state enters the release archive; all three review cycles are recorded. Real employer submission, live account setup, feed synchronization and GitHub publishing are outside this build and must not be claimed as tested.

## Known gaps and roadmap

These are not delivered features. Each needs its own design, failure and recovery tests, and privacy review.

| Gap | Current handling | Direction |
| --- | --- | --- |
| Outcomes after sending: responses, interviews, rejections, offers, withdrawals, follow-ups | The tracker ends at `sent`; keep a private note | A per-attempt outcome model with evidence-backed, append-only transitions |
| Applications made before or outside the toolkit | Record them as `skip` with evidence so they are not repeated; they do not count as sent | Evidence-backed import that records a submission without inventing an attempt |
| Conflicting past submissions: a receipt attached to the wrong attempt or vacancy, or a sent record later disproved | Late receipts add history, including duplicate submissions; sent records cannot be corrected | An append-only correction record that can never release a send by itself |
| Vacancy feeds and tracker adapters | Agent-assisted discovery and manual `add` | Optional, separately scoped integrations |
| Existing Git history in publication checks | Not scanned; publish a clean export with a new history | Use a dedicated history scanner before reusing any history |
| Real portals, provider computer-use tools, schedulers and Windows | Not tested | Report results from actual use, without private data |
