# Optional agent automations

The Python toolkit does not schedule jobs or operate your computer. You choose an agent, confirm its available tools and create each schedule yourself or explicitly ask that agent to create it. Keep the public checkout available for code and guides; point each task to the private workspace for personal data.

## First run, with either provider

1. Open this checkout in your agent and read `AGENTS.md`.
2. Tell it the absolute path to your private workspace and which sources and files it may read. Check the provider's privacy settings before sharing sensitive information with it.
3. Ask it to run `python3 -m jobkit --help` and a read-only workspace check. Keep the configured model; no particular model is required here.
4. Run each selected prompt manually once. Inspect the output, date handling, source links and workspace changes before scheduling it.
5. Confirm the timezone, frequency, source scope and allowed writes. A scheduled discovery task is not permission to send applications.

Each scheduled prompt saves a dated private report in `<workspace>/reports/`, stating whether the run completed or failed, what it checked and the next actions, including unknown, rolling and overdue deadlines. Read those reports; a missing report means the run did not complete. Before backing up, moving or upgrading the workspace or the toolkit, pause every schedule and follow the [backup and upgrade steps](workflow.md#back-up-restore-move-or-upgrade).

## Codex

Use the computer tools that your installation exposes. Availability depends on the operating system, account and access settings; check [OpenAI's computer-use guide](https://learn.chatgpt.com/docs/computer-use) rather than assuming an existing browser session is accessible.

For recurrence, use the app's supported automation interface. Local runs need the machine on and the app running. See [OpenAI's automation guide](https://learn.chatgpt.com/docs/automations?surface=app). The prompts below are task text, not an installed schedule.

## Claude Code

Open this checkout; `CLAUDE.md` loads the shared `AGENTS.md`. The [desktop guide](https://code.claude.com/docs/en/desktop) describes current computer-use support and limitations. Browser viewing and interactive browser control are distinct; use the dedicated Chrome integration when interaction requires it, after checking its permissions.

Choose scheduling deliberately: session-scoped `/loop` and durable desktop schedules have different lifetimes. Confirm which one you set up using the [scheduled-task guide](https://code.claude.com/docs/en/scheduled-tasks). No loop, cron entry or background task is created by this repository.

## Copyable schedule requests

Replace every `<...>` value before using these requests. The agent must ask about any decisive missing scope, not invent it. Suggested times are examples, not defaults already configured.

**Daily discovery, example 08:30:**

> Create an optional daily task at 08:30 in `<timezone>`. Use the checkout at `<checkout>` and private workspace at `<workspace>`. Follow `prompts/en/discover.md`, search only `<approved sources>` for `<role scope>`, and return at most `<count>` relevant new vacancies. You may add and screen records in this workspace. Do not contact anyone or submit applications. If the environment cannot run this schedule, explain the limitation without claiming it is installed.

**Daily deadlines, example 09:00:**

> Create a daily task at 09:00 in `<timezone>`. Use `<checkout>` and `<workspace>` and follow `prompts/en/deadlines.md`. Review deadlines within the next seven days and every overdue, unknown or rolling deadline, verify material changes on original vacancy pages, and report blocked actions in the dated report. Do not send applications or messages.

**Weekly review, example Friday 16:00:**

> Create a weekly task on Friday at 16:00 in `<timezone>`. Use `<checkout>` and `<workspace>` and follow `prompts/en/weekly-review.md`. Summarize recorded progress, unresolved attempts and next actions. Recommend changes; do not alter my search criteria, write new application prose or contact anyone without a separate request.

**Supervised apply is an explicit task:** use [the application prompt](../../prompts/en/apply-supervised.md) for a stated set of vacancy IDs. Do not attach it to the schedules above. Existing authorization remains valid within its exact scope, but it does not authorize new employers or future batches.

To pause or remove a schedule, use the same provider interface that created it and verify the resulting status. When changing providers, pause the old schedules first to prevent duplicate work. Neither provider's completion message proves that an employer received an application; inspect receipt evidence.
