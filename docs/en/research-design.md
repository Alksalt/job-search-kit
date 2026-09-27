# Research and design

Research checked on 2026-09-27. Provider features can change; follow the linked primary documentation when setting up your installation. These notes distinguish documented capabilities from the choices made for this project.

| Evidence | Project decision |
| --- | --- |
| Codex documents computer use with access and platform conditions. [Source](https://learn.chatgpt.com/docs/computer-use) | Check available tools at runtime; do not embed a universal browser driver. |
| Codex local automations depend on the running local environment. [Source](https://learn.chatgpt.com/docs/automations?surface=app) | Ship explicit task prompts and setup instructions, not a silently installed scheduler. |
| Claude describes desktop computer use, distinct browser integration and several scheduling lifetimes. [Desktop](https://code.claude.com/docs/en/desktop), [scheduling](https://code.claude.com/docs/en/scheduled-tasks) | Share the same process across providers and require a single browser operator. |
| Claude supports filesystem-based skills. [Source](https://code.claude.com/docs/en/skills) | Keep this initial release as ordinary readable guides and prompts; no provider-specific skill package is needed. |
| NAV's vacancy feed uses JWT authentication and has token, update and removal handling requirements. [Source](https://navikt.github.io/pam-stilling-feed/) | Defer feed integration. Agent-assisted search and explicit vacancy entry are supported; no public feed completeness is claimed. |
| Removing sensitive information after a Git push may require history cleanup and coordination. [Source](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) | Build from new files, keep private runtime outside Git, and export only an explicit public manifest. |

We considered publishing a sanitized private repository, a hosted service and a prompt-only collection. A fresh local toolkit provides a smaller data boundary and a concrete attempt ledger without importing historical records or hosting applicant data. The [build plan](../../BUILD_PLAN.md) records the implementation scope.

The core can validate local state and file integrity. It cannot decide whether candidate claims are true, whether a website permits automation, or whether a portal received a submission. Those decisions need sources, the user's scope and the operator's actual observations. The safe response to uncertain submission status is reconciliation, not an automatic retry.

Future integrations should be optional and independently scoped: authenticated vacancy feeds with freshness handling, a user-chosen tracker adapter, and better evidence export. Each would add data flows that need a separate privacy review. None is advertised as part of this release.
