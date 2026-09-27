# Job Search Kit

[Norsk bokmål](README.nb.md)

A local job-search workflow for people using Codex, Claude Code, or both. Keep verified candidate facts, screen vacancies, reuse approved application text, and record supervised application attempts with evidence. English and Norwegian Bokmål guides and prompts are included.

This is a fresh public implementation. It contains no real applicant profile, application records or account setup. A separate [experience note](docs/en/experience.md) shares the creator's authorized aggregate results and lessons from the original private workflow. Those results are not an evaluation of this public toolkit, and it does not promise employment outcomes.

## Start with the offline demo

Requires Python 3.11 or newer. Run commands from this directory; no Python packages or API keys are required for the core.

The examples use a POSIX shell. On Windows, ask your agent to adapt them to your installed Python and shell; Windows has not been locally tested.

```sh
python3 -m jobkit --help
python3 -m jobkit demo
```

The demo uses synthetic data and sends nothing. For your own search, choose a private workspace **outside this checkout and outside every Git repository**:

```sh
python3 -m jobkit --workspace "$HOME/job-search-private" init --language en
python3 -m jobkit --workspace "$HOME/job-search-private" verify
```

Initialization creates `candidate.md` and `preferences.md` in the private workspace. Fill them with your own information, optionally using the expanded [blank templates](templates/). Keep CVs, letters, portal screenshots, receipts and account details there. Do not enter your personal information into this repository or its issues.

Prefer to start through your agent? Open this checkout in Codex or Claude Code and paste:

> Read AGENTS.md and help me set up my own job search. Check Python 3.11+, ask for my target roles, locations, languages and binding constraints, and initialize an empty private workspace outside this checkout and all Git repositories. Help me fill its candidate facts and preferences using sources I provide; leave unsupported facts unknown. Start with discovery only. Do not create a schedule or send applications unless I explicitly request that scope.

## What you can do

- [Run a search and supervised application workflow](docs/en/workflow.md).
- [Set up optional Codex or Claude automations](docs/en/automations.md).
- Copy [English prompts](prompts/en/) or [Bokmål prompts](prompts/nb/) into your agent.
- Read the [research and design choices](docs/en/research-design.md) and the [build plan with known gaps](BUILD_PLAN.md).
- Read [what the original search taught us](docs/en/experience.md), including rejections, interviews and the limits of the evidence.
- [Check and export the public release](docs/en/release.md).

The CLI records evidence and enforces workflow transitions. It does not control a browser, install a scheduler, connect to NAV or synchronize Notion. Use the computer or browser tools actually available in your agent, subject to the platform's rules and your explicit scope. The agent must check the real portal before a send action.

Unknown send status is a reason to reconcile the existing attempt, never to click again. One browser operator may work on a machine at a time. A recorded approval or receipt is evidence supplied by the operator; the CLI cannot independently prove what a portal displayed or accepted.

## For contributors

[AGENTS.md](AGENTS.md) routes agent work. Use only synthetic fixtures for tests and examples. Apart from the explicitly authorized aggregate experience note and attribution, keep public documentation free of applicant facts and credentials. Run the checks in the [release runbook](docs/en/release.md) before sharing a copy.

## Attribution

Original idea: [Oleksandr Altukhov](https://github.com/Alksalt).
