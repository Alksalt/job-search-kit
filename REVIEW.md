# Build and review record

Date: 2026-09-27. Scope: the fresh public toolkit, English/Bokmål instructions, synthetic tests and clean release export. Functional tests used synthetic applicant data and no live accounts or submissions. Separate local privacy comparisons kept their inputs outside the public tree.

## Analysis, research and implementation

A read-only architecture audit identified the reusable workflow and the private coupling to remove. Official provider, NAV and GitHub documentation informed the design. The alternatives and selected scope are recorded in [BUILD_PLAN.md](BUILD_PLAN.md) and the bilingual research notes. Separate agents implemented the core and the bilingual documentation; a third independently tested the release boundary. Integration and privacy checks were performed by the coordinating agent.

## Cycle 1 — correctness and recovery

An independent Claude Opus review inspected the implementation, tests and guides. Concrete findings included a recovery deadlock when a local packet was damaged after a Send action, source-file reuse invalidating unchanged managed snapshots, documentation parity and retention gaps, source-directory aliases, and missing late-receipt recovery. Some findings referred to files still being completed during review; those were checked against the final implementation rather than dismissed without verification.

Independent release tests also found filename disclosure in error reports and missed bare home-directory paths. These are covered by regression tests. The publication checker suppresses sensitive filename values and excludes routine untracked OS metadata while retaining an explicit export manifest.

Corrections completed: confirmed portal outcomes can be recorded despite damaged local evidence, with the integrity problem retained; managed copies are authoritative and original hashes are provenance; both packet extensions are validated before writing; platform path aliases are handled safely; a late receipt can correct the latest attempt previously marked not-sent without allowing a blind retry. English and Bokmål instructions now agree about initialization, managed uploads, retention, uncertainty and recovery. URL normalization preserves meaningful query/path differences, which still require operator deduplication. The fixed version passed 66 tests, the offline demo and the public-file check before cycle 2.

## Cycle 2 — security and privacy

An independent agent reproduced three additional defects with synthetic temporary files: an export could enter its source through a case alias on a case-insensitive filesystem; workspace verification overlooked hardlinks in unreferenced profile files; and concurrent manifest edits could produce an inconsistent successful export. All three were fixed and given regression tests. Existing ancestor identity is checked, workspace-wide hardlinks are reported, and the same captured manifest bytes are parsed, scanned and exported. The resulting 69-test suite passed on Python 3.11 and 3.14. No critical or high finding remained from this review.

## Cycle 3 — release and onboarding

An independent final reviewer exercised English and Bokmål setup, separate-process restarts, unknown/expired/rolling deadlines, duplicate-attempt rejection and late-receipt recovery. It found one onboarding issue: relative managed paths were ambiguous for portal uploads from the checkout. The command now returns absolute `upload_paths`; both guides explain the relative basis of stored paths. The reviewer independently confirmed that the corrected paths exist and match the managed files, checked documentation links and command parity, and found no unresolved release blocker.

## Verification of the cycle 1–3 revision (version 0.1.0)

These results apply to that revision. Cycle 4 below records what has been rechecked since.

- 70 synthetic tests passed on Python 3.11.14 and 3.14.3 on macOS; the offline demo passed on both. Windows runtime was not tested. Linux CI is configured, not claimed to have run here.
- The full CLI workflow was also exercised through separate processes in a synthetic Bokmål workspace, including deadline correction, blocked duplicate attempt, reconciliation and late receipt.
- All 45 public files passed the release checker and a private external identifier deny list. The approved name/GitHub attribution occurs only once, in README.md. A separate local phrase comparison found no matches; its inputs and deny terms were not copied into this project.
- All relative documentation links and Markdown fences were checked. The public tree contains exactly the manifest files, with no runtime workspace, bytecode, database, attachment, raw review transcript or Git history.
- A clean exported copy was checked independently during integration. Publication must use the final allowlisted export and should be rechecked after future edits.

The three cycles above were sequential review/fix/verification passes, not three approvals of an unchanged draft. Raw reviewer sessions and private comparison inputs stay outside the public project.

## Cycle 4 — attempt binding, historical receipts and release-check coverage

An independent audit's findings were checked against the code and corrected with synthetic regression tests, together with further issues found while reviewing the whole tree:

- **Receipt attached to the wrong attempt.** `receipt` and `reconcile` resolved whichever attempt was active, so a delayed receipt for an earlier attempt could silently mark a newer attempt sent, and `verify` still passed. Every resolution command now requires the exact attempt ID, compared inside the write transaction before any evidence is copied; a stale or wrong ID records nothing. The CLI still cannot prove that a receipt belongs to the named attempt.
- **Late receipts.** A late receipt was blocked by any other vacancy's unresolved attempt and could only target the latest attempt. It now applies per vacancy to any earlier attempt reconciled not-sent, never releases another unresolved attempt, and marks the vacancy sent so no further attempt is possible. If the vacancy was already sent through a newer attempt, the receipt is appended as a duplicate submission without rewriting the current record; a reference already recorded for the vacancy is refused. `show` lists each attempt with its outcome, and `verify` compares current records with the append-only history.
- **Fact and preference drift.** Screening records hashes of `candidate.md` and `preferences.md`. After either changes, packet, authorization, preview and attempt are refused until the vacancy is screened again, and `verify` lists affected vacancies. Screenings without hashes fail safely. Resolving an unresolved attempt is unaffected.
- **Release-check evasions.** Deny terms missed a UTF-8 byte-order mark in the deny file, other Unicode normalization forms, JSON escapes, invisible characters and line wraps. Terms, contents and filenames are now normalized, and decoded JSON, TOML and Python string literals and HTML entities are scanned without executing code or echoing values. New high-confidence patterns cover compact international phone numbers, cloud access key IDs, Slack and similar tokens, lowercase bearer tokens, encrypted and DSA private keys and passwords embedded in URLs. Staged contents of listed files are scanned, tracked links and submodules are rejected, and a linked worktree's `.git` pointer is accepted but never exported. Files that `uv run` generates in the checkout are ignored and never exported. The toolkit's own private workspace names are refused in the manifest.
- **Portals without a letter.** A packet no longer requires both a CV and a letter. Any combination of CV, letter, named attachments and an approved answers file for portal form fields can be registered under the same hash, authorization and preview binding.
- **Documentation.** Both languages now cover backup, restore, relocation and upgrade; dated vacancy snapshots and final portal answers; document metadata that rendering does not reveal; the separate language choices; dated reports from scheduled runs, including unknown, rolling and overdue deadlines; and current limits. Deliberate gaps are listed in the [build plan](BUILD_PLAN.md) roadmap, not presented as features.

Changes for existing workspaces: `receipt` and `reconcile` require `--attempt-id` (listed by `show`), and vacancies screened before this revision must be screened again before a send. The version is now 0.2.0.

Remaining recovery limitation: a late receipt cannot yet be recorded while a newer attempt for the same vacancy is unresolved. Resolve that attempt using its own evidence first; never invent a not-sent result to bypass this restriction. An unresolved attempt for a different vacancy does not block the correction.

Validation in this cycle: 87 synthetic tests, including Git-based release tests, passed on Python 3.12 on macOS; the offline demo and the release check of the source tree passed with no findings. Independent integration then passed the same 87 tests and demo on Python 3.11 and 3.14, plus 14 separate runtime acceptance scenarios and 10 separate privacy/export scenarios. Those checks covered stale resolution commands through separate CLI processes, historical and duplicate receipts, profile drift, CV-only packets, Unicode/JSON evasions, filename redaction and exact exported bytes. Damaged historical evidence still allowed a truthful receipt while retaining integrity warnings. The same-vacancy unresolved-retry restriction above was confirmed as a limitation, not counted as fixed.

All 45 public source files passed the external private deny list and local identifier/phrase comparison, with only the authorized README attribution present. The source tree contained exactly the manifest files, with no generated environment, runtime records or Git history. The coordinating reviewer also clarified the exact-attempt instruction and the distinction between ordinary and late receipts in both guides. Recheck every new export after later edits. Linux CI, Windows and real provider or employer sessions were not tested here.

## Experience note — aggregate evidence and interpretation

The creator requested a dated account of the original private search. English and Bokmål experience notes now share only authorized aggregate results, with no employer identities, contact details, private circumstances or underlying records. These outcomes belong to the original workflow, not to this fresh public implementation. The notes explicitly state that creator-associated aggregates are attributable rather than anonymous.

A separate evidence agent reviewed cumulative events, identified duplicate result rows and checked the difference between invitations, completed interviews and offers. The coordinating agent checked current canonical records and retained rounded application/rejection totals because historical data do not support a precise denominator. The earlier outreach audit keeps its own cutoff and distinguishes networking conversations from hiring interviews. Rejection records include some administrative closures; silence and candidate withdrawals are not presented as employer rejection.

Claude Opus 5.5, explicitly run at max effort, independently critiqued a sanitized aggregate brief. Its interpretation changes were integrated: prioritising suitable vacancies is a practical judgment from one search, not a measured national channel ranking; the summaries cannot be combined into comparative rates; and event definitions, dates and sources are central to honest reporting. No claims are made about AI causation, provider superiority, CV-only effectiveness, time saved or completed employment. NAV sources support writing practice and the validity of open applications, not comparative success rates.

This update changes documentation and the export manifest only. The release now contains 47 files. The source and clean export passed the release check with the external private deny list; a separate comparison against private identifiers and document phrases found no unapproved matches. Documentation links and fences were checked, and exported files and ZIP entries were compared byte for byte with the source. The runtime tests recorded above were not rerun for this prose update.

## Verification boundary

The CLI records operator declarations and local bytes. Tests cannot establish actual authorization, candidate truth, employer receipt, current portal behavior or availability of provider tools. An attempt ID binds a declaration to one attempt; it does not prove that a receipt belongs to it. The state database coordinates one workspace; the one-browser-operator rule is operational across workspaces. Local data is plaintext. The release checker uses heuristics and optional private deny terms, not a proof of anonymity. The export omits Git history; the checker scans staged contents but does not audit an existing history.
