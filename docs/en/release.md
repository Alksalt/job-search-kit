# Public release runbook

This repository and a person's private workspace have different purposes. Publishing the code does not authorize publishing a candidate's records. The release exporter uses `public-files.json`; it does not copy the whole directory or Git history.

See [SECURITY.md](../../SECURITY.md) for the security boundary and reporting guidance.

## Check and export

From the checkout:

```sh
python3 -m unittest discover -s tests
python3 -m jobkit demo
python3 -m jobkit.release check
python3 -m jobkit.release export --output "$HOME/job-search-kit-public-export"
```

With uv, prefix the same commands with `uv run`; the files it generates (`.venv/`, `uv.lock` and a root `*.egg-info/`) are ignored and never exported.

The output must be a new directory outside the checkout. For a personalized check, create a private deny file outside this repository containing sensitive terms, one per line, then pass it without copying its contents into an issue or chat:

```sh
python3 -m jobkit.release check --deny-file "$HOME/job-search-private/release-deny.txt"
python3 -m jobkit.release export \
  --output "$HOME/job-search-kit-public-export-checked" \
  --deny-file "$HOME/job-search-private/release-deny.txt"
```

Use names, private usernames, email addresses, phone numbers, addresses, account identifiers and private domains relevant to your own copy. Include local-format phone numbers; only international `+` numbers are recognized without a deny term. Do not add a real deny file to the public manifest. Terms match in contents and filenames regardless of letter case, Unicode normalization form, a UTF-8 byte-order mark or invisible formatting characters such as soft hyphens, and in contents also across line wraps. JSON, TOML and Python string escapes and HTML entities are decoded before matching; YAML escapes are not. A scanner can find patterns and supplied terms; it cannot prove that arbitrary prose or a new attachment contains no personal information.

Review the actual exported files before publishing. Check the manifest, README attribution, examples, comments, dependency files and repository URLs. Exclude local instructions, hidden settings, runtime databases, receipts, CVs, letters, screenshots, backups, transcripts and secrets. Check filenames as well as contents. Any new file needs an explicit manifest decision.

The export is a clean directory, not a published GitHub repository. Initialize a new Git history in that export if you choose to publish it. Do not reuse a personal project's `.git` directory or upload the original workspace. GitHub publishing remains a separate user action or explicit instruction.

In a Git checkout, `check` also rejects tracked files outside the manifest, tracked links or submodules, and findings in the staged contents of manifest files. It never scans earlier commits. A linked worktree's `.git` pointer file is accepted and never exported. The only fully checked publication route is this clean export with a new Git history; an existing history needs its own review.

## Review and limitations

Read the [review record](../../REVIEW.md) for the actual checks performed and findings resolved. Local tests and a synthetic demo do not certify a real portal, a provider account, a schedule or an employer submission. Recheck the release after changes; previous results apply only to the files reviewed.

## If something private was published

Stop further publication. Revoke exposed credentials first, then remove the information and assess repository history, forks and copies. Follow [GitHub's sensitive-data removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository). Deleting the current file alone does not remove old Git commits. Do not paste the sensitive value into a public incident report.
